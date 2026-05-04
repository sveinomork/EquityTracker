import math
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.domain.enums import TransactionType
from app.domain.exceptions import NotFoundError
from app.models.fund import Fund
from app.models.transaction import Transaction
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.rate_repository import RateRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.analytics import (
    BorrowingCosts,
    CapitalSplit,
    FundPeriodReconciliation,
    FundPeriodReconciliationRow,
    FundLotsSummary,
    FundSummary,
    LotCapitalSplit,
    LotSummary,
    PeriodMetrics,
    PeriodMetricsByWindow,
    PerformanceWindows,
    PortfolioSummary,
    PortfolioTotals,
    ReturnSplitMetrics,
    ReturnMetrics,
    TaxSummary,
    TrueNetWorthBreakdown,
)
from app.services.interest_service import InterestService

DECIMAL_ZERO = Decimal("0")
DECIMAL_100 = Decimal("100")
DECIMAL_365 = Decimal("365")
DECIMAL_22_PCT = Decimal("0.22")
DECIMAL_78_PCT = Decimal("0.78")
WINDOWS = ((14, "d14_pct"), (30, "d30_pct"), (90, "d90_pct"), (180, "d180_pct"), (365, "y1_pct"))
PERIOD_KEYS = ("d1", "d7", "d30", "d180", "ytd", "m12", "m24", "total")
MAX_PRICE_STALENESS_DAYS = 7
DISTRIBUTING_FUNDS = {"FHY", "HHR", "HHRP"}


@dataclass(slots=True)
class LotComputation:
    lot: Transaction
    related_transactions: list[Transaction]
    current_units: Decimal
    current_value: Decimal
    outstanding_borrowed: Decimal
    allocated_interest_paid: Decimal
    current_monthly_cost: Decimal
    current_annual_cost: Decimal


@dataclass(slots=True)
class TrueNetWorthComputation:
    total_invested_capital: Decimal
    total_market_value: Decimal
    total_allocated_debt: Decimal
    total_unrealized_gain_before_tax: Decimal
    total_accumulated_interest_cost: Decimal
    total_tax_credit_received: Decimal
    total_deferred_tax_accumulating: Decimal
    total_paid_tax_distributing: Decimal
    true_net_worth_nok: Decimal


class PortfolioAnalyticsService:
    def __init__(
        self,
        fund_repository: FundRepository,
        transaction_repository: TransactionRepository,
        price_repository: PriceRepository,
        rate_repository: RateRepository,
        interest_service: InterestService,
    ) -> None:
        self.fund_repository = fund_repository
        self.transaction_repository = transaction_repository
        self.price_repository = price_repository
        self.rate_repository = rate_repository
        self.interest_service = interest_service

    def get_fund_summary(self, fund_id: uuid.UUID, as_of_date: date | None = None) -> FundSummary:
        fund = self.fund_repository.get(fund_id)
        if fund is None:
            raise NotFoundError("Fund not found")

        effective_date = as_of_date or date.today()
        transactions = self.transaction_repository.list_for_fund(fund_id)
        latest_price = self.price_repository.latest_on_or_before(fund_id, effective_date)
        latest_price_value = (
            Decimal(latest_price.price) if latest_price is not None else DECIMAL_ZERO
        )
        rates = self.rate_repository.list_for_fund(fund_id)

        lots = self._compute_lots(transactions, rates, latest_price_value, effective_date)
        buy_transactions = [
            transaction for transaction in transactions if transaction.type is TransactionType.BUY
        ]
        total_cost = sum(
            (Decimal(item.total_amount) for item in buy_transactions), start=DECIMAL_ZERO
        )
        total_equity = sum(
            (Decimal(item.equity_amount) for item in buy_transactions), start=DECIMAL_ZERO
        )
        total_borrowed = sum(
            (Decimal(item.borrowed_amount) for item in buy_transactions), start=DECIMAL_ZERO
        )
        total_dividend_reinvested = sum(
            (
                Decimal(item.total_amount)
                for item in transactions
                if item.type is TransactionType.DIVIDEND_REINVEST
            ),
            start=DECIMAL_ZERO,
        )
        current_value = sum((item.current_value for item in lots), start=DECIMAL_ZERO)
        outstanding_borrowed = sum((item.outstanding_borrowed for item in lots), start=DECIMAL_ZERO)
        total_interest_paid = sum(
            (item.allocated_interest_paid for item in lots), start=DECIMAL_ZERO
        )
        current_monthly_cost = sum((item.current_monthly_cost for item in lots), start=DECIMAL_ZERO)
        current_annual_cost = sum((item.current_annual_cost for item in lots), start=DECIMAL_ZERO)
        net_equity_value = current_value - outstanding_borrowed
        profit_loss_gross = current_value - total_cost
        profit_loss_net = net_equity_value - total_equity - total_interest_paid
        effective_equity_contribution = total_equity + total_interest_paid
        average_days_owned = self._average_days_owned(buy_transactions, total_cost, effective_date)
        annualized_return_on_cost_weighted = self._weighted_annualized_return_on_cost(
            transactions,
            lots,
            effective_date,
        )
        period_metrics = self._build_fund_period_metrics(
            fund=fund,
            transactions=transactions,
            lots=lots,
            rates=rates,
            latest_price_value=latest_price_value,
            as_of_date=effective_date,
        )
        total_return = period_metrics.total.return_split
        true_net_worth = self._build_true_net_worth(
            fund=fund,
            transactions=transactions,
            total_cost=total_cost,
            current_value=current_value,
            outstanding_borrowed=outstanding_borrowed,
            total_interest_paid=total_interest_paid,
            as_of_date=effective_date,
        )

        return FundSummary(
            fund_id=fund.id,
            fund_name=fund.name,
            ticker=fund.ticker,
            as_of_date=effective_date,
            capital_split=CapitalSplit(
                total_cost=total_cost,
                total_equity=total_equity,
                total_borrowed=total_borrowed,
            ),
            current_value=current_value,
            net_equity_value=net_equity_value,
            total_dividend_reinvested=total_dividend_reinvested,
            total_interest_paid=total_interest_paid,
            average_days_owned=average_days_owned,
            profit_loss_gross=profit_loss_gross,
            profit_loss_net=profit_loss_net,
            returns=ReturnMetrics(
                return_on_total_assets_pct=self._safe_percentage(profit_loss_gross, total_cost),
                return_on_equity_net_pct=self._safe_percentage(
                    profit_loss_net,
                    effective_equity_contribution,
                ),
                annualized_return_on_equity_pct=self._annualized_roe(
                    net_equity_value,
                    effective_equity_contribution,
                    average_days_owned,
                ),
                annualized_return_on_cost_weighted_pct=annualized_return_on_cost_weighted,
            ),
            borrowing_costs=BorrowingCosts(
                monthly_current=current_monthly_cost,
                annual_current=current_annual_cost,
            ),
            performance_windows=self._build_performance_windows(
                fund_id,
                effective_date,
                transactions,
            ),
            period_metrics=period_metrics,
            total_return=total_return,
            tax_summary=TaxSummary(
                regime=self._resolve_tax_regime(fund, effective_date),
                taxable_gain_base_nok=self._taxable_gain_base(
                    fund,
                    current_value - total_cost,
                ),
                deferred_tax_nok=true_net_worth.total_deferred_tax_accumulating,
                paid_dividend_tax_nok=true_net_worth.total_paid_tax_distributing,
                interest_tax_credit_nok=true_net_worth.total_tax_credit_received,
            ),
            true_net_worth=TrueNetWorthBreakdown(
                total_invested_capital=true_net_worth.total_invested_capital,
                total_market_value=true_net_worth.total_market_value,
                total_allocated_debt=true_net_worth.total_allocated_debt,
                total_unrealized_gain_before_tax=true_net_worth.total_unrealized_gain_before_tax,
                total_accumulated_interest_cost=true_net_worth.total_accumulated_interest_cost,
                total_tax_credit_received=true_net_worth.total_tax_credit_received,
                total_deferred_tax_accumulating=true_net_worth.total_deferred_tax_accumulating,
                total_paid_tax_distributing=true_net_worth.total_paid_tax_distributing,
                true_net_worth_nok=true_net_worth.true_net_worth_nok,
            ),
        )

    def get_fund_lots_summary(
        self,
        fund_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> FundLotsSummary:
        fund = self.fund_repository.get(fund_id)
        if fund is None:
            raise NotFoundError("Fund not found")

        effective_date = as_of_date or date.today()
        transactions = self.transaction_repository.list_for_fund(fund_id)
        latest_price = self.price_repository.latest_on_or_before(fund_id, effective_date)
        latest_price_value = (
            Decimal(latest_price.price) if latest_price is not None else DECIMAL_ZERO
        )
        rates = self.rate_repository.list_for_fund(fund_id)
        lots = self._compute_lots(transactions, rates, latest_price_value, effective_date)

        payload_lots: list[LotSummary] = []
        for item in lots:
            original_units = Decimal(item.lot.units)
            lot_equity_contribution = Decimal(item.lot.equity_amount) + item.allocated_interest_paid
            profit_loss_net = (
                item.current_value
                - item.outstanding_borrowed
                - Decimal(item.lot.equity_amount)
                - item.allocated_interest_paid
            )
            days_owned = max((effective_date - item.lot.date).days, 1)
            payload_lots.append(
                LotSummary(
                    lot_id=item.lot.id,
                    purchase_date=item.lot.date,
                    days_owned=days_owned,
                    original_units=original_units,
                    current_units=item.current_units,
                    purchase_price_per_unit=Decimal(item.lot.price_per_unit),
                    capital_split=LotCapitalSplit(
                        cost=Decimal(item.lot.total_amount),
                        equity=Decimal(item.lot.equity_amount),
                        borrowed=Decimal(item.lot.borrowed_amount),
                    ),
                    current_value=item.current_value,
                    allocated_interest_paid=item.allocated_interest_paid,
                    profit_loss_net=profit_loss_net,
                    returns=ReturnMetrics(
                        return_on_equity_net_pct=self._safe_percentage(
                            profit_loss_net,
                            lot_equity_contribution,
                        ),
                        annualized_return_on_equity_pct=self._annualized_roe(
                            item.current_value - item.outstanding_borrowed,
                            lot_equity_contribution,
                            Decimal(days_owned),
                        ),
                    ),
                    period_metrics=self._build_lot_period_metrics(
                        fund=fund,
                        lot=item,
                        rates=rates,
                        latest_price_value=latest_price_value,
                        as_of_date=effective_date,
                    ),
                )
            )

        return FundLotsSummary(
            fund_id=fund.id,
            fund_name=fund.name,
            ticker=fund.ticker,
            market_price_per_unit=latest_price_value,
            market_price_date=latest_price.date if latest_price is not None else None,
            lots=payload_lots,
        )

    def get_portfolio_summary(self, as_of_date: date | None = None) -> PortfolioSummary:
        effective_date = as_of_date or date.today()
        funds = self.fund_repository.list_all()
        fund_summaries = [self.get_fund_summary(fund.id, effective_date) for fund in funds]
        portfolio_period_metrics = self._build_portfolio_period_metrics(fund_summaries, effective_date)
        total_cost = sum(
            (item.capital_split.total_cost for item in fund_summaries), start=DECIMAL_ZERO
        )
        total_market_value = sum((item.current_value for item in fund_summaries), start=DECIMAL_ZERO)

        totals = PortfolioTotals(
            total_cost=total_cost,
            total_market_value=total_market_value,
            current_value=total_market_value,
            net_equity_value=sum(
                (item.net_equity_value for item in fund_summaries), start=DECIMAL_ZERO
            ),
            total_interest_paid=sum(
                (item.total_interest_paid for item in fund_summaries), start=DECIMAL_ZERO
            ),
            total_equity=sum(
                (item.capital_split.total_equity for item in fund_summaries), start=DECIMAL_ZERO
            ),
            total_borrowed=sum(
                (item.capital_split.total_borrowed for item in fund_summaries), start=DECIMAL_ZERO
            ),
            profit_loss_net=sum(
                (item.profit_loss_net for item in fund_summaries), start=DECIMAL_ZERO
            ),
            total_return=portfolio_period_metrics.total.return_split,
            true_net_worth_nok=sum(
                (item.true_net_worth.true_net_worth_nok for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            true_net_worth=self._build_portfolio_true_net_worth(fund_summaries),
        )
        return PortfolioSummary(
            as_of_date=effective_date,
            funds=fund_summaries,
            totals=totals,
            period_metrics=portfolio_period_metrics,
        )

    def get_fund_period_reconciliation(
        self,
        ticker: str = "FHY",
        as_of_date: date | None = None,
    ) -> FundPeriodReconciliation:
        fund = self.fund_repository.get_by_ticker(ticker)
        if fund is None:
            raise NotFoundError("Fund not found")

        effective_date = as_of_date or date.today()
        transactions = self.transaction_repository.list_for_fund(fund.id)
        latest_price = self.price_repository.latest_on_or_before(fund.id, effective_date)
        latest_price_value = (
            Decimal(latest_price.price) if latest_price is not None else DECIMAL_ZERO
        )
        rates = self.rate_repository.list_for_fund(fund.id)
        lots = self._compute_lots(transactions, rates, latest_price_value, effective_date)

        rows = self._build_fund_period_reconciliation_rows(
            fund=fund,
            transactions=transactions,
            lots=lots,
            rates=rates,
            latest_price_value=latest_price_value,
            as_of_date=effective_date,
        )
        return FundPeriodReconciliation(
            fund_id=fund.id,
            fund_name=fund.name,
            ticker=fund.ticker,
            as_of_date=effective_date,
            rows=rows,
        )

    def _compute_lots(
        self,
        transactions: list[Transaction],
        rates: list,
        latest_price_value: Decimal,
        as_of_date: date,
    ) -> list[LotComputation]:
        buy_lots = [
            transaction for transaction in transactions if transaction.type is TransactionType.BUY
        ]
        computed: list[LotComputation] = []
        for lot in buy_lots:
            related_transactions = [item for item in transactions if item.lot_id == lot.id]
            current_units = Decimal(lot.units) + sum(
                (Decimal(item.units) for item in related_transactions),
                start=DECIMAL_ZERO,
            )
            interest = self.interest_service.calculate_for_lot(
                lot, related_transactions, rates, as_of_date
            )
            computed.append(
                LotComputation(
                    lot=lot,
                    related_transactions=related_transactions,
                    current_units=current_units,
                    current_value=current_units * latest_price_value,
                    outstanding_borrowed=interest.current_outstanding_borrowed,
                    allocated_interest_paid=interest.total_paid,
                    current_monthly_cost=interest.current_monthly_cost,
                    current_annual_cost=interest.current_annual_cost,
                )
            )
        return computed

    def _build_lot_period_metrics(
        self,
        fund: Fund,
        lot: LotComputation,
        rates: list,
        latest_price_value: Decimal,
        as_of_date: date,
    ) -> PeriodMetricsByWindow:
        metrics: dict[str, PeriodMetrics] = {}
        for key in PERIOD_KEYS:
            start_date = self._period_start_for_key(key, as_of_date)
            effective_start = lot.lot.date if key == "total" else start_date
            if effective_start > as_of_date:
                effective_start = as_of_date

            days = max((as_of_date - effective_start).days, 1)
            start_price_value = self._resolve_start_price(
                fund.id,
                effective_start,
                latest_price_value,
            )

            units_t0 = self._lot_units_as_of(lot.lot, lot.related_transactions, effective_start)
            value_t0 = units_t0 * start_price_value
            value_t1 = lot.current_units * latest_price_value
            dividends_in_period = self._sum_dividends_for_lot_between(
                lot.related_transactions,
                effective_start,
                as_of_date,
            )
            gross_value_change = value_t1 - value_t0

            allocated_interest_cost = self.interest_service.calculate_period_interest_for_lot(
                buy_transaction=lot.lot,
                related_transactions=lot.related_transactions,
                rates=rates,
                start_date=effective_start,
                end_date=as_of_date,
            )
            interest_tax_credit = allocated_interest_cost * DECIMAL_22_PCT

            regime = self._resolve_tax_regime(fund, as_of_date)
            running_dividend_tax = (
                dividends_in_period * DECIMAL_22_PCT if regime == "distributing_pre_2026" else DECIMAL_ZERO
            )
            if regime == "distributing_pre_2026":
                # Reinvested dividends do not add cash liquidity, but still create dividend tax.
                net_liquidity_margin = -running_dividend_tax + interest_tax_credit - allocated_interest_cost
                net_value_margin = (
                    gross_value_change
                    - running_dividend_tax
                    + interest_tax_credit
                    - allocated_interest_cost
                )
            else:
                net_liquidity_margin = interest_tax_credit - allocated_interest_cost
                net_value_margin = (gross_value_change * DECIMAL_78_PCT) - (
                    allocated_interest_cost * DECIMAL_78_PCT
                )

            return_pct_lot = self._safe_percentage(gross_value_change, value_t0)
            return_split = self._build_return_split_metrics(
                gross_value_change=gross_value_change,
                allocated_interest_cost=allocated_interest_cost,
                period_capital_base=value_t0,
                days=days,
            )

            metrics[key] = PeriodMetrics(
                start_date=effective_start,
                end_date=as_of_date,
                days=days,
                period_capital_base_nok=value_t0,
                return_pct_fund=return_pct_lot,
                brutto_value_change_nok=gross_value_change,
                allocated_interest_cost_nok=allocated_interest_cost,
                interest_tax_credit_nok=interest_tax_credit,
                running_dividend_tax_nok=running_dividend_tax,
                net_liquidity_margin_nok=net_liquidity_margin,
                net_value_margin_nok=net_value_margin,
                return_split=return_split,
            )

        return PeriodMetricsByWindow(**metrics)

    def _build_fund_period_metrics(
        self,
        fund: Fund,
        transactions: list[Transaction],
        lots: list[LotComputation],
        rates: list,
        latest_price_value: Decimal,
        as_of_date: date,
    ) -> PeriodMetricsByWindow:
        rows = self._build_fund_period_reconciliation_rows(
            fund=fund,
            transactions=transactions,
            lots=lots,
            rates=rates,
            latest_price_value=latest_price_value,
            as_of_date=as_of_date,
        )

        metrics_map = {
            row.period_key: PeriodMetrics(
                start_date=row.start_date,
                end_date=row.end_date,
                days=row.days,
                period_capital_base_nok=row.period_capital_base_nok,
                return_pct_fund=row.return_pct_fund,
                brutto_value_change_nok=row.gross_value_change_nok,
                allocated_interest_cost_nok=row.allocated_interest_cost_nok,
                interest_tax_credit_nok=row.interest_tax_credit_nok,
                running_dividend_tax_nok=row.running_dividend_tax_nok,
                net_liquidity_margin_nok=row.net_liquidity_margin_nok,
                net_value_margin_nok=row.net_value_margin_nok,
                return_split=self._build_return_split_metrics(
                    gross_value_change=row.gross_value_change_nok,
                    allocated_interest_cost=row.allocated_interest_cost_nok,
                    period_capital_base=row.period_capital_base_nok,
                    days=row.days,
                ),
            )
            for row in rows
        }

        return PeriodMetricsByWindow(
            d1=metrics_map["d1"],
            d7=metrics_map["d7"],
            d30=metrics_map["d30"],
            d180=metrics_map["d180"],
            ytd=metrics_map["ytd"],
            m12=metrics_map["m12"],
            m24=metrics_map["m24"],
            total=metrics_map["total"],
        )

    def _build_fund_period_reconciliation_rows(
        self,
        fund: Fund,
        transactions: list[Transaction],
        lots: list[LotComputation],
        rates: list,
        latest_price_value: Decimal,
        as_of_date: date,
    ) -> list[FundPeriodReconciliationRow]:
        earliest_buy = self._first_buy_date(transactions) or as_of_date
        units_t1 = sum((item.current_units for item in lots), start=DECIMAL_ZERO)
        total_cost = sum(
            (
                Decimal(item.total_amount)
                for item in transactions
                if item.type is TransactionType.BUY
            ),
            start=DECIMAL_ZERO,
        )
        rows: list[FundPeriodReconciliationRow] = []
        for key in PERIOD_KEYS:
            start_date = self._period_start_for_key(key, as_of_date)
            effective_start = earliest_buy if key == "total" else start_date
            if effective_start > as_of_date:
                effective_start = as_of_date

            days = max((as_of_date - effective_start).days, 1)
            start_price_value = self._resolve_start_price(
                fund.id,
                effective_start,
                latest_price_value,
                transactions,
            )

            units_t0 = self._fund_units_as_of(transactions, effective_start)
            value_t1 = units_t1 * latest_price_value
            if key == "total":
                value_t0 = total_cost
            else:
                value_t0 = units_t0 * start_price_value
            dividends_in_period = self._sum_dividends_for_fund_between(
                transactions,
                effective_start,
                as_of_date,
            )
            net_external_cashflow = self._sum_external_cashflow_for_fund_between(
                transactions,
                effective_start,
                as_of_date,
            )
            if key == "total":
                gross_value_change = value_t1 - value_t0
                period_capital_base = value_t0
            else:
                gross_value_change = (value_t1 - value_t0) - net_external_cashflow
                period_capital_base = value_t0 + net_external_cashflow

            allocated_interest_cost = sum(
                (
                    self.interest_service.calculate_period_interest_for_lot(
                        buy_transaction=lot.lot,
                        related_transactions=lot.related_transactions,
                        rates=rates,
                        start_date=effective_start,
                        end_date=as_of_date,
                    )
                    for lot in lots
                ),
                start=DECIMAL_ZERO,
            )
            interest_tax_credit = allocated_interest_cost * DECIMAL_22_PCT

            regime = self._resolve_tax_regime(fund, as_of_date)
            running_dividend_tax = (
                dividends_in_period * DECIMAL_22_PCT if regime == "distributing_pre_2026" else DECIMAL_ZERO
            )
            if regime == "distributing_pre_2026":
                # Reinvested dividends are taxable but do not create cash inflow.
                net_liquidity_margin = -running_dividend_tax + interest_tax_credit - allocated_interest_cost
                net_value_margin = (
                    gross_value_change
                    - running_dividend_tax
                    + interest_tax_credit
                    - allocated_interest_cost
                )
            else:
                net_liquidity_margin = interest_tax_credit - allocated_interest_cost
                net_value_margin = (gross_value_change * DECIMAL_78_PCT) - (
                    allocated_interest_cost * DECIMAL_78_PCT
                )

            if key != "total" and units_t0 <= DECIMAL_ZERO:
                return_pct_fund = None
            else:
                return_pct_fund = self._safe_percentage(gross_value_change, period_capital_base)

            rows.append(
                FundPeriodReconciliationRow(
                    period_key=key,
                    start_date=effective_start,
                    end_date=as_of_date,
                    days=days,
                    regime=regime,
                    units_t0=units_t0,
                    units_t1=units_t1,
                    start_price=start_price_value,
                    end_price=latest_price_value,
                    value_t0=value_t0,
                    value_t1=value_t1,
                    net_external_cashflow_nok=net_external_cashflow,
                    period_capital_base_nok=period_capital_base,
                    gross_value_change_nok=gross_value_change,
                    dividends_in_period_nok=dividends_in_period,
                    running_dividend_tax_nok=running_dividend_tax,
                    allocated_interest_cost_nok=allocated_interest_cost,
                    interest_tax_credit_nok=interest_tax_credit,
                    net_liquidity_margin_nok=net_liquidity_margin,
                    net_value_margin_nok=net_value_margin,
                    return_pct_fund=return_pct_fund,
                )
            )

        return rows

    def _build_portfolio_period_metrics(
        self,
        fund_summaries: list[FundSummary],
        as_of_date: date,
    ) -> PeriodMetricsByWindow:
        metrics: dict[str, PeriodMetrics] = {}
        for key in PERIOD_KEYS:
            period_entries = [getattr(item.period_metrics, key) for item in fund_summaries]
            if not period_entries:
                metrics[key] = PeriodMetrics(
                    start_date=as_of_date,
                    end_date=as_of_date,
                    days=1,
                    period_capital_base_nok=DECIMAL_ZERO,
                    return_pct_fund=None,
                    brutto_value_change_nok=DECIMAL_ZERO,
                    allocated_interest_cost_nok=DECIMAL_ZERO,
                    interest_tax_credit_nok=DECIMAL_ZERO,
                    running_dividend_tax_nok=DECIMAL_ZERO,
                    net_liquidity_margin_nok=DECIMAL_ZERO,
                    net_value_margin_nok=DECIMAL_ZERO,
                    return_split=self._build_return_split_metrics(
                        gross_value_change=DECIMAL_ZERO,
                        allocated_interest_cost=DECIMAL_ZERO,
                        period_capital_base=DECIMAL_ZERO,
                        days=1,
                    ),
                )
                continue

            gross_value_change = sum(
                (item.brutto_value_change_nok for item in period_entries), start=DECIMAL_ZERO
            )
            allocated_interest = sum(
                (item.allocated_interest_cost_nok for item in period_entries), start=DECIMAL_ZERO
            )
            interest_tax_credit = sum(
                (item.interest_tax_credit_nok for item in period_entries), start=DECIMAL_ZERO
            )
            running_dividend_tax = sum(
                (item.running_dividend_tax_nok for item in period_entries), start=DECIMAL_ZERO
            )
            net_liquidity = sum(
                (item.net_liquidity_margin_nok for item in period_entries), start=DECIMAL_ZERO
            )
            net_value = sum((item.net_value_margin_nok for item in period_entries), start=DECIMAL_ZERO)
            base_value = sum((item.period_capital_base_nok for item in period_entries), start=DECIMAL_ZERO)
            period_days = max((as_of_date - min(item.start_date for item in period_entries)).days, 1)

            metrics[key] = PeriodMetrics(
                start_date=min(item.start_date for item in period_entries),
                end_date=as_of_date,
                days=period_days,
                period_capital_base_nok=base_value,
                return_pct_fund=self._safe_percentage(gross_value_change, base_value),
                brutto_value_change_nok=gross_value_change,
                allocated_interest_cost_nok=allocated_interest,
                interest_tax_credit_nok=interest_tax_credit,
                running_dividend_tax_nok=running_dividend_tax,
                net_liquidity_margin_nok=net_liquidity,
                net_value_margin_nok=net_value,
                return_split=self._build_return_split_metrics(
                    gross_value_change=gross_value_change,
                    allocated_interest_cost=allocated_interest,
                    period_capital_base=base_value,
                    days=period_days,
                ),
            )

        return PeriodMetricsByWindow(**metrics)

    def _build_true_net_worth(
        self,
        fund: Fund,
        transactions: list[Transaction],
        total_cost: Decimal,
        current_value: Decimal,
        outstanding_borrowed: Decimal,
        total_interest_paid: Decimal,
        as_of_date: date,
    ) -> TrueNetWorthComputation:
        unrealized_gain_before_tax = current_value - total_cost
        tax_credit = total_interest_paid * DECIMAL_22_PCT
        regime = self._resolve_tax_regime(fund, as_of_date)
        taxable_gain_base = self._taxable_gain_base(fund, unrealized_gain_before_tax)
        deferred_tax = taxable_gain_base * DECIMAL_22_PCT if regime != "distributing_pre_2026" else DECIMAL_ZERO
        paid_dividend_tax = (
            self._sum_dividends_for_fund_between(
                transactions,
                self._first_buy_date(transactions) or as_of_date,
                as_of_date,
            )
            * DECIMAL_22_PCT
            if regime == "distributing_pre_2026"
            else DECIMAL_ZERO
        )

        true_net_worth = (
            current_value
            - outstanding_borrowed
            - deferred_tax
            - paid_dividend_tax
            - total_interest_paid
            + tax_credit
        )
        return TrueNetWorthComputation(
            total_invested_capital=total_cost,
            total_market_value=current_value,
            total_allocated_debt=outstanding_borrowed,
            total_unrealized_gain_before_tax=unrealized_gain_before_tax,
            total_accumulated_interest_cost=total_interest_paid,
            total_tax_credit_received=tax_credit,
            total_deferred_tax_accumulating=deferred_tax,
            total_paid_tax_distributing=paid_dividend_tax,
            true_net_worth_nok=true_net_worth,
        )

    def _build_portfolio_true_net_worth(
        self,
        fund_summaries: list[FundSummary],
    ) -> TrueNetWorthBreakdown:
        return TrueNetWorthBreakdown(
            total_invested_capital=sum(
                (item.true_net_worth.total_invested_capital for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_market_value=sum(
                (item.true_net_worth.total_market_value for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_allocated_debt=sum(
                (item.true_net_worth.total_allocated_debt for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_unrealized_gain_before_tax=sum(
                (item.true_net_worth.total_unrealized_gain_before_tax for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_accumulated_interest_cost=sum(
                (item.true_net_worth.total_accumulated_interest_cost for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_tax_credit_received=sum(
                (item.true_net_worth.total_tax_credit_received for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_deferred_tax_accumulating=sum(
                (item.true_net_worth.total_deferred_tax_accumulating for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            total_paid_tax_distributing=sum(
                (item.true_net_worth.total_paid_tax_distributing for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
            true_net_worth_nok=sum(
                (item.true_net_worth.true_net_worth_nok for item in fund_summaries),
                start=DECIMAL_ZERO,
            ),
        )

    def _resolve_tax_regime(self, fund: Fund, value_date: date) -> str:
        if fund.ticker in DISTRIBUTING_FUNDS:
            return "distributing_pre_2026"
        return "accumulating_2026"

    def _taxable_gain_base(self, fund: Fund, unrealized_gain_before_tax: Decimal) -> Decimal:
        if fund.manual_taxable_gain_override is not None:
            return Decimal(fund.manual_taxable_gain_override)
        return max(unrealized_gain_before_tax, DECIMAL_ZERO)

    def _period_start_for_key(self, period_key: str, as_of_date: date) -> date:
        if period_key == "d1":
            return as_of_date - timedelta(days=1)
        if period_key == "d7":
            return as_of_date - timedelta(days=7)
        if period_key == "d30":
            return as_of_date - timedelta(days=30)
        if period_key == "d180":
            return as_of_date - timedelta(days=180)
        if period_key == "ytd":
            return date(as_of_date.year, 1, 1)
        if period_key == "m12":
            return as_of_date - timedelta(days=365)
        if period_key == "m24":
            return as_of_date - timedelta(days=730)
        return date.min

    def _first_buy_date(self, transactions: list[Transaction]) -> date | None:
        buy_dates = [item.date for item in transactions if item.type is TransactionType.BUY]
        if not buy_dates:
            return None
        return min(buy_dates)

    def _lot_units_as_of(
        self,
        lot: Transaction,
        related_transactions: list[Transaction],
        value_date: date,
    ) -> Decimal:
        if value_date < lot.date:
            return DECIMAL_ZERO
        units = Decimal(lot.units)
        for transaction in related_transactions:
            if transaction.date <= value_date:
                units += Decimal(transaction.units)
        return units

    def _fund_units_as_of(self, transactions: list[Transaction], value_date: date) -> Decimal:
        units_by_lot: dict[uuid.UUID, Decimal] = {}
        lot_ids: set[uuid.UUID] = set()
        for transaction in transactions:
            if transaction.type is TransactionType.BUY and transaction.date <= value_date:
                units_by_lot[transaction.id] = Decimal(transaction.units)
                lot_ids.add(transaction.id)

        for transaction in transactions:
            if transaction.lot_id in lot_ids and transaction.date <= value_date:
                units_by_lot[transaction.lot_id] = units_by_lot.get(transaction.lot_id, DECIMAL_ZERO) + Decimal(
                    transaction.units
                )
        return sum(units_by_lot.values(), start=DECIMAL_ZERO)

    def _sum_dividends_for_lot_between(
        self,
        related_transactions: list[Transaction],
        start_date: date,
        end_date: date,
    ) -> Decimal:
        return sum(
            (
                Decimal(item.total_amount)
                for item in related_transactions
                if item.type is TransactionType.DIVIDEND_REINVEST
                and start_date <= item.date <= end_date
            ),
            start=DECIMAL_ZERO,
        )

    def _sum_dividends_for_fund_between(
        self,
        transactions: list[Transaction],
        start_date: date,
        end_date: date,
    ) -> Decimal:
        return sum(
            (
                Decimal(item.total_amount)
                for item in transactions
                if item.type is TransactionType.DIVIDEND_REINVEST
                and start_date <= item.date <= end_date
            ),
            start=DECIMAL_ZERO,
        )

    def _sum_external_cashflow_for_fund_between(
        self,
        transactions: list[Transaction],
        start_date: date,
        end_date: date,
    ) -> Decimal:
        return sum(
            (
                Decimal(item.total_amount)
                for item in transactions
                if start_date < item.date <= end_date
                and item.type is TransactionType.BUY
            ),
            start=DECIMAL_ZERO,
        ) - sum(
            (
                Decimal(item.total_amount)
                for item in transactions
                if start_date < item.date <= end_date and item.type is TransactionType.SELL
            ),
            start=DECIMAL_ZERO,
        )

    def _resolve_start_price(
        self,
        fund_id: uuid.UUID,
        start_date: date,
        fallback_latest_price: Decimal,
        transactions: list[Transaction] | None = None,
    ) -> Decimal:
        price_on_or_before = self.price_repository.latest_on_or_before(fund_id, start_date)
        if price_on_or_before is not None:
            # If dividends were reinvested between the found price date and the start_date,
            # the NAV dropped after that price — use the first post-dividend price instead.
            if transactions is not None:
                has_dividend_after_price = any(
                    item.type is TransactionType.DIVIDEND_REINVEST
                    and price_on_or_before.date < item.date <= start_date
                    for item in transactions
                )
                if has_dividend_after_price:
                    first_after = self.price_repository.earliest_on_or_after(fund_id, start_date)
                    if first_after is not None:
                        return Decimal(first_after.price)
            return Decimal(price_on_or_before.price)

        first_after = self.price_repository.earliest_on_or_after(fund_id, start_date)
        if first_after is not None:
            return Decimal(first_after.price)

        return fallback_latest_price

    def _average_days_owned(
        self,
        buy_transactions: list[Transaction],
        total_cost: Decimal,
        as_of_date: date,
    ) -> Decimal:
        if total_cost <= DECIMAL_ZERO:
            return DECIMAL_ZERO

        weighted_sum = DECIMAL_ZERO
        for transaction in buy_transactions:
            days_owned = Decimal(max((as_of_date - transaction.date).days, 1))
            weighted_sum += Decimal(transaction.total_amount) * days_owned
        return weighted_sum / total_cost

    def _safe_percentage(self, numerator: Decimal, denominator: Decimal) -> Decimal | None:
        if denominator <= DECIMAL_ZERO:
            return None
        return (numerator / denominator) * DECIMAL_100

    def _annualized_roe(
        self,
        net_value_after_interest: Decimal,
        equity: Decimal,
        days_owned: Decimal,
    ) -> Decimal | None:
        if (
            equity <= DECIMAL_ZERO
            or days_owned <= DECIMAL_ZERO
            or net_value_after_interest <= DECIMAL_ZERO
        ):
            return None

        try:
            growth_factor = net_value_after_interest / equity
            exponent = Decimal("365") / days_owned
            annualized = Decimal(str(math.pow(float(growth_factor), float(exponent)) - 1.0))
        except (InvalidOperation, OverflowError):
            return None
        return annualized * DECIMAL_100

    def _annualized_return_from_values(
        self,
        end_value: Decimal,
        start_value: Decimal,
        days_owned: Decimal,
    ) -> Decimal | None:
        if start_value <= DECIMAL_ZERO or days_owned <= DECIMAL_ZERO or end_value <= DECIMAL_ZERO:
            return None

        try:
            growth_factor = end_value / start_value
            exponent = DECIMAL_365 / days_owned
            annualized = Decimal(str(math.pow(float(growth_factor), float(exponent)) - 1.0))
        except (InvalidOperation, OverflowError):
            return None
        return annualized * DECIMAL_100

    def _build_return_split_metrics(
        self,
        gross_value_change: Decimal,
        allocated_interest_cost: Decimal,
        period_capital_base: Decimal,
        days: int,
    ) -> ReturnSplitMetrics:
        after_interest_amount = gross_value_change - allocated_interest_cost
        days_owned = Decimal(max(days, 1))

        gross_annualized = self._annualized_return_from_values(
            end_value=period_capital_base + gross_value_change,
            start_value=period_capital_base,
            days_owned=days_owned,
        )
        after_interest_annualized = self._annualized_return_from_values(
            end_value=period_capital_base + after_interest_amount,
            start_value=period_capital_base,
            days_owned=days_owned,
        )

        return ReturnSplitMetrics(
            gross_amount_nok=gross_value_change,
            gross_pct=self._safe_percentage(gross_value_change, period_capital_base),
            gross_annualized_pct=gross_annualized,
            after_interest_amount_nok=after_interest_amount,
            after_interest_pct=self._safe_percentage(after_interest_amount, period_capital_base),
            after_interest_annualized_pct=after_interest_annualized,
        )

    def _weighted_annualized_return_on_cost(
        self,
        transactions: list[Transaction],
        lots: list[LotComputation],
        as_of_date: date,
    ) -> Decimal | None:
        cashflows = self._build_return_on_cost_cashflows(transactions, lots, as_of_date)
        return self._xirr_percentage(cashflows)

    def _build_return_on_cost_cashflows(
        self,
        transactions: list[Transaction],
        lots: list[LotComputation],
        as_of_date: date,
    ) -> list[tuple[date, Decimal]]:
        cashflows: list[tuple[date, Decimal]] = []
        for transaction in transactions:
            if transaction.date > as_of_date:
                continue
            if transaction.type is TransactionType.BUY:
                cashflows.append((transaction.date, -Decimal(transaction.total_amount)))
            elif transaction.type is TransactionType.SELL:
                cashflows.append((transaction.date, Decimal(transaction.total_amount)))

        terminal_value = sum((item.current_value for item in lots), start=DECIMAL_ZERO)
        if terminal_value > DECIMAL_ZERO:
            cashflows.append((as_of_date, terminal_value))
        return cashflows

    def _xirr_percentage(self, cashflows: list[tuple[date, Decimal]]) -> Decimal | None:
        if not cashflows:
            return None

        has_positive = any(amount > DECIMAL_ZERO for _, amount in cashflows)
        has_negative = any(amount < DECIMAL_ZERO for _, amount in cashflows)
        if not has_positive or not has_negative:
            return None

        ordered = sorted(cashflows, key=lambda item: item[0])
        first_date = ordered[0][0]

        def npv(rate: float) -> float:
            total = 0.0
            for flow_date, amount in ordered:
                years = (flow_date - first_date).days / 365.0
                total += float(amount) / math.pow(1.0 + rate, years)
            return total

        low = -0.999999
        high = 1.0

        try:
            f_low = npv(low)
            f_high = npv(high)
        except (InvalidOperation, OverflowError, ZeroDivisionError, ValueError):
            return None

        if f_low == 0.0:
            return Decimal(str(low * 100.0))
        if f_high == 0.0:
            return Decimal(str(high * 100.0))

        for _ in range(40):
            if f_low * f_high < 0.0:
                break
            high *= 2.0
            if high > 1_000_000.0:
                return None
            try:
                f_high = npv(high)
            except (InvalidOperation, OverflowError, ZeroDivisionError, ValueError):
                return None
        else:
            return None

        mid = 0.0
        for _ in range(100):
            mid = (low + high) / 2.0
            try:
                f_mid = npv(mid)
            except (InvalidOperation, OverflowError, ZeroDivisionError, ValueError):
                return None

            if abs(f_mid) < 1e-8:
                break
            if f_low * f_mid <= 0.0:
                high = mid
                f_high = f_mid
            else:
                low = mid
                f_low = f_mid

        return Decimal(str(mid * 100.0))

    def _build_performance_windows(
        self,
        fund_id: uuid.UUID,
        as_of_date: date,
        _transactions: list[Transaction],
    ) -> PerformanceWindows:
        values: dict[str, Decimal | None] = {}
        latest_price = self.price_repository.latest_on_or_before_with_max_staleness(
            fund_id,
            as_of_date,
            MAX_PRICE_STALENESS_DAYS,
        )
        if latest_price is None:
            for _, field_name in WINDOWS:
                values[field_name] = None
            return PerformanceWindows(**values)

        latest_price_value = Decimal(latest_price.price)
        for days, field_name in WINDOWS:
            reference_date = as_of_date - timedelta(days=days)
            reference_price = self.price_repository.latest_on_or_before_with_max_staleness(
                fund_id,
                reference_date,
                MAX_PRICE_STALENESS_DAYS,
            )
            if reference_price is None:
                values[field_name] = None
                continue

            reference_price_value = Decimal(reference_price.price)
            total_return_factor = (latest_price_value / reference_price_value) - Decimal("1")
            values[field_name] = total_return_factor * DECIMAL_100

        return PerformanceWindows(**values)
