import calendar
import math
import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.domain.enums import TransactionType
from app.domain.exceptions import NotFoundError, ValidationError
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
    PortfolioHistoryPoint,
    PortfolioSummary,
    PortfolioTotals,
    ReturnSplitMetrics,
    ReturnMetrics,
    TaxSummary,
    TrueNetWorthBreakdown,
)
from app.schemas.reports import (
    FundPeriodReportSummary,
    PortfolioPeriodReport,
    PortfolioPeriodReportSummary,
    ReportPeriodOption,
    ReportPeriodOptions,
    ReportPeriodType,
)
from app.services.interest_service import InterestService

DECIMAL_ZERO = Decimal("0")
DECIMAL_100 = Decimal("100")
DECIMAL_365 = Decimal("365")
DECIMAL_22_PCT = Decimal("0.22")
DECIMAL_78_PCT = Decimal("0.78")
WINDOWS = ((14, "d14_pct"), (30, "d30_pct"), (90, "d90_pct"), (180, "d180_pct"), (365, "y1_pct"))
PERIOD_KEYS = (
    "d1",
    "d7",
    "d14",
    "d30",
    "d60",
    "d90",
    "d180",
    "ytd",
    "m12",
    "m24",
    "total",
)
MAX_PRICE_STALENESS_DAYS = 7
DISTRIBUTING_FUNDS = {"FHY", "HHR", "HHRP"}


@dataclass(slots=True)
class LotComputation:
    """Computed runtime values for one BUY lot."""
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
    """Intermediate totals used to build true-net-worth outputs."""
    total_invested_capital: Decimal
    total_market_value: Decimal
    total_allocated_debt: Decimal
    total_unrealized_gain_before_tax: Decimal
    total_accumulated_interest_cost: Decimal
    total_tax_credit_received: Decimal
    total_deferred_tax_accumulating: Decimal
    total_paid_tax_distributing: Decimal
    true_net_worth_nok: Decimal


@dataclass(slots=True)
class LotCapitalState:
    """Remaining and realized principal state for one lot."""
    remaining_units: Decimal
    remaining_cost: Decimal
    remaining_equity: Decimal
    remaining_borrowed: Decimal
    sold_cost: Decimal
    sale_proceeds: Decimal


class PortfolioAnalyticsService:
    """Analytics service for fund and portfolio performance calculations."""
    def __init__(
        self,
        fund_repository: FundRepository,
        transaction_repository: TransactionRepository,
        price_repository: PriceRepository,
        rate_repository: RateRepository,
        interest_service: InterestService,
    ) -> None:
        """Initialize analytics dependencies for repositories and interest logic."""
        self.fund_repository = fund_repository
        self.transaction_repository = transaction_repository
        self.price_repository = price_repository
        self.rate_repository = rate_repository
        self.interest_service = interest_service

    def get_fund_summary(self, fund_id: uuid.UUID, as_of_date: date | None = None) -> FundSummary:
        """Build a full analytics summary for one fund."""
        # Returns a complete analytics summary for a single fund including capital split,
        # current value, profit/loss, returns, borrowing costs, period metrics, tax, and true net worth.
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
        total_cost = DECIMAL_ZERO
        total_equity = DECIMAL_ZERO
        total_borrowed = DECIMAL_ZERO
        weighted_days_sum = DECIMAL_ZERO
        for lot in lots:
            capital_state = self._lot_capital_state_as_of(
                buy_transaction=lot.lot,
                related_transactions=lot.related_transactions,
                as_of_date=effective_date,
            )
            effective_cost = capital_state.remaining_cost
            effective_equity = capital_state.remaining_equity
            effective_borrowed = capital_state.remaining_borrowed
            total_cost += effective_cost
            total_equity += effective_equity
            total_borrowed += effective_borrowed
            weighted_days_sum += effective_cost * Decimal(max((effective_date - lot.lot.date).days, 1))
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
        realized_profit_from_sold_positions, total_sale_proceeds, _ = (
            self._realized_profit_from_sold_positions(transactions, rates)
        )
        profit_loss_gross_including_realized = (
            profit_loss_gross + realized_profit_from_sold_positions
        )
        profit_loss_net = net_equity_value - total_equity - total_interest_paid
        effective_equity_contribution = total_equity + total_interest_paid
        average_days_owned = (
            weighted_days_sum / total_cost if total_cost > DECIMAL_ZERO else DECIMAL_ZERO
        )
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
            latest_price_date=latest_price.date if latest_price is not None else effective_date,
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
            realized_profit_from_sold_positions=realized_profit_from_sold_positions,
            average_days_owned=average_days_owned,
            profit_loss_gross=profit_loss_gross,
            profit_loss_gross_including_realized=profit_loss_gross_including_realized,
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
                    profit_loss_gross,
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
        """Build lot-level analytics summary for one fund."""
        # Returns a per-lot breakdown for a fund showing each individual purchase lot's
        # current units, value, cost basis, interest, profit/loss, and period metrics.
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
            capital_state = self._lot_capital_state_as_of(
                buy_transaction=item.lot,
                related_transactions=item.related_transactions,
                as_of_date=effective_date,
            )
            effective_cost = capital_state.remaining_cost
            effective_equity = capital_state.remaining_equity
            effective_borrowed = capital_state.remaining_borrowed

            lot_equity_contribution = effective_equity + item.allocated_interest_paid
            profit_loss_net = (
                item.current_value
                - item.outstanding_borrowed
                - effective_equity
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
                        cost=effective_cost,
                        equity=effective_equity,
                        borrowed=effective_borrowed,
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
        """Build a combined summary across all funds in the portfolio."""
        # Aggregates all fund summaries into a portfolio-level overview with combined totals
        # and period metrics across all funds.
        effective_date = as_of_date or date.today()
        funds = self.fund_repository.list_all()
        fund_summaries = [self.get_fund_summary(fund.id, effective_date) for fund in funds]
        portfolio_period_metrics = self._build_portfolio_period_metrics(fund_summaries, effective_date)
        total_cost = sum(
            (item.capital_split.total_cost for item in fund_summaries), start=DECIMAL_ZERO
        )
        total_market_value = sum((item.current_value for item in fund_summaries), start=DECIMAL_ZERO)
        weighted_days_numerator = sum(
            (
                item.average_days_owned * item.capital_split.total_cost
                for item in fund_summaries
            ),
            start=DECIMAL_ZERO,
        )
        weighted_average_days_invested = (
            weighted_days_numerator / total_cost if total_cost > DECIMAL_ZERO else DECIMAL_ZERO
        )

        weighted_annualized_entries = [
            item
            for item in fund_summaries
            if item.capital_split.total_cost > DECIMAL_ZERO
            and item.returns.annualized_return_on_cost_weighted_pct is not None
        ]
        weighted_annualized_denominator = sum(
            (item.capital_split.total_cost for item in weighted_annualized_entries),
            start=DECIMAL_ZERO,
        )
        weighted_annualized_return_on_cost_pct = (
            sum(
                (
                    item.returns.annualized_return_on_cost_weighted_pct
                    * item.capital_split.total_cost
                    for item in weighted_annualized_entries
                ),
                start=DECIMAL_ZERO,
            )
            / weighted_annualized_denominator
            if weighted_annualized_denominator > DECIMAL_ZERO
            else None
        )

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
            weighted_average_days_invested=weighted_average_days_invested,
            weighted_annualized_return_on_cost_pct=weighted_annualized_return_on_cost_pct,
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

    def get_portfolio_history(self, as_of_date: date | None = None) -> list[PortfolioHistoryPoint]:
        """Build portfolio history snapshots for all trading days up to a date."""
        # Returns snapshots for all available trading days (price dates)
        # up to as_of_date, showing market value, equity, debt, and net value over time.

        effective_date = as_of_date or date.today()
        funds = self.fund_repository.list_all()

        # Pre-fetch all data per fund
        fund_data = []
        for fund in funds:
            transactions = self.transaction_repository.list_for_fund(fund.id)
            if not transactions:
                continue
            buy_txns = [t for t in transactions if t.type is TransactionType.BUY]
            if not buy_txns:
                continue
            rates = self.rate_repository.list_for_fund(fund.id)
            prices = sorted(
                self.price_repository.list_for_fund(fund.id, to_date=effective_date),
                key=lambda item: item.date,
            )
            fund_data.append((fund, transactions, rates, prices))

        if not fund_data:
            return []

        first_date = min(t.date for _, txns, _, _ in fund_data for t in txns)

        # Build snapshots on every available trading day across all funds.
        snapshot_dates = sorted(
            {
                price.date
                for _, _, _, prices in fund_data
                for price in prices
                if first_date <= price.date <= effective_date
            }
        )

        if not snapshot_dates:
            return []

        points: list[PortfolioHistoryPoint] = []
        for snap_date in snapshot_dates:
            total_equity = DECIMAL_ZERO
            total_borrowed = DECIMAL_ZERO
            total_interest = DECIMAL_ZERO
            total_market_value = DECIMAL_ZERO

            for _fund, transactions, rates, prices in fund_data:
                buy_lots = [
                    t
                    for t in transactions
                    if t.type is TransactionType.BUY
                    and self._transaction_effective_date_for_history(_fund, t, prices) <= snap_date
                ]
                if not buy_lots:
                    continue

                for buy_txn in buy_lots:
                    related = [
                        t for t in transactions
                        if t.lot_id == buy_txn.id
                        and self._transaction_effective_date_for_history(_fund, t, prices) <= snap_date
                    ]
                    interest = self.interest_service.calculate_for_lot(
                        buy_txn, related, rates, snap_date
                    )
                    remaining_fraction = self._remaining_buy_fraction_as_of(
                        buy_transaction=buy_txn,
                        related_transactions=related,
                    )
                    total_interest += interest.total_paid
                    total_borrowed += interest.current_outstanding_borrowed
                    total_equity += Decimal(buy_txn.equity_amount) * remaining_fraction

                # Units at snap_date
                units = DECIMAL_ZERO
                for t in transactions:
                    if self._transaction_effective_date_for_history(_fund, t, prices) > snap_date:
                        continue
                    if t.type in (TransactionType.BUY, TransactionType.DIVIDEND_REINVEST):
                        units += Decimal(t.units)
                    elif t.type is TransactionType.SELL:
                        # SELL units may be stored as negative; use abs() so we always subtract
                        units -= abs(Decimal(t.units))

                # Use implied post-dividend price when reinvests occur on the snap_date
                # but no official price exists for that date (e.g. FHY on 2024-12-31).
                # This prevents using a stale pre-dividend price with post-dividend unit counts.
                price = self._effective_price_for_history(prices, transactions, snap_date)

                total_market_value += units * price

            net_value = total_market_value - total_borrowed - total_equity - total_interest
            points.append(
                PortfolioHistoryPoint(
                    date=snap_date,
                    market_value=total_market_value,
                    total_equity=total_equity,
                    total_borrowed=total_borrowed,
                    total_interest_paid=total_interest,
                    net_value=net_value,
                )
            )

        return points

    def get_fund_period_reconciliation(
        self,
        ticker: str = "FHY",
        as_of_date: date | None = None,
    ) -> FundPeriodReconciliation:
        """Build period reconciliation rows for one fund ticker."""
        # Returns a detailed period-by-period reconciliation table for a fund identified by ticker,
        # showing prices, units, value changes, dividends, interest, and tax for each period window.
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
            latest_price_date=latest_price.date if latest_price is not None else effective_date,
            as_of_date=effective_date,
        )
        return FundPeriodReconciliation(
            fund_id=fund.id,
            fund_name=fund.name,
            ticker=fund.ticker,
            as_of_date=effective_date,
            rows=rows,
        )

    def get_report_period_options(
        self,
        period_type: ReportPeriodType,
        as_of_date: date | None = None,
    ) -> ReportPeriodOptions:
        """Return all selectable period values within available historical data."""
        data_range = self._portfolio_data_range()
        if data_range is None:
            raise ValidationError("No portfolio data available for report generation")

        data_start, data_end = data_range
        effective_end = min(as_of_date or date.today(), data_end)
        options = self._build_period_options(period_type, data_start, effective_end)
        return ReportPeriodOptions(
            period_type=period_type,
            data_start_date=data_start,
            data_end_date=data_end,
            options=options,
        )

    def get_period_report(
        self,
        period_type: ReportPeriodType,
        period_value: str,
    ) -> PortfolioPeriodReport:
        """Build a report payload with START and END-of-period snapshots for a calendar period."""
        data_range = self._portfolio_data_range()
        if data_range is None:
            raise ValidationError("No portfolio data available for report generation")

        data_start, data_end = data_range
        period_start, period_end, normalized_value = self._resolve_report_period_bounds(
            period_type,
            period_value,
        )

        if period_end < data_start:
            raise ValidationError("Requested period is before available portfolio data")
        if period_start > data_end:
            raise ValidationError("Requested period is after available portfolio data")

        # Fetch snapshots at period start and end
        # If period_start is before data_start, use data_start instead
        start_snapshot_date = max(period_start, data_start)
        end_snapshot_date = min(period_end, data_end)

        portfolio_start = self.get_portfolio_summary(as_of_date=start_snapshot_date)
        portfolio_end = self.get_portfolio_summary(as_of_date=end_snapshot_date)

        # Build fund rows with start/end period values
        fund_rows: list[FundPeriodReportSummary] = []
        
        # Create lookup of funds by ID for easy matching between start and end snapshots
        start_funds_by_id = {f.fund_id: f for f in portfolio_start.funds}
        
        for end_fund_summary in portfolio_end.funds:
            fund_id = end_fund_summary.fund_id
            start_fund_summary = start_funds_by_id.get(fund_id)
            
            fund_transactions = self.transaction_repository.list_for_fund(fund_id)
            
            # Calculate units, cost, and prices at period start
            start_units = self._fund_units_as_of(fund_transactions, start_snapshot_date)
            start_cost = start_fund_summary.capital_split.total_cost if start_fund_summary else Decimal(0)
            start_price = self.price_repository.latest_on_or_before(
                fund_id,
                start_snapshot_date,
            )
            start_value = start_fund_summary.current_value if start_fund_summary else Decimal(0)
            
            # Calculate units, cost, and prices at period end
            end_units = self._fund_units_as_of(fund_transactions, end_snapshot_date)
            end_cost = end_fund_summary.capital_split.total_cost
            end_price = self.price_repository.latest_on_or_before(
                fund_id,
                end_snapshot_date,
            )
            end_value = end_fund_summary.current_value
            
            fund_rows.append(
                FundPeriodReportSummary(
                    fund_id=fund_id,
                    fund_name=end_fund_summary.fund_name,
                    ticker=end_fund_summary.ticker,
                    start_units=start_units,
                    start_price=start_price.price if start_price is not None else None,
                    start_cost=start_cost,
                    start_value=start_value,
                    end_units=end_units,
                    end_price=end_price.price if end_price is not None else None,
                    end_cost=end_cost,
                    end_value=end_value,
                    latest_price_date=end_price.date if end_price is not None else None,
                    summary=end_fund_summary,
                )
            )

        fund_rows.sort(
            key=lambda item: item.end_value,
            reverse=True,
        )

        return PortfolioPeriodReport(
            period_type=period_type,
            period_value=normalized_value,
            period_start=period_start,
            period_end=period_end,
            data_start_date=data_start,
            data_end_date=data_end,
            portfolio_start=PortfolioPeriodReportSummary(
                as_of_date=portfolio_start.as_of_date,
                totals=portfolio_start.totals,
                period_metrics=portfolio_start.period_metrics,
            ),
            portfolio_end=PortfolioPeriodReportSummary(
                as_of_date=portfolio_end.as_of_date,
                totals=portfolio_end.totals,
                period_metrics=portfolio_end.period_metrics,
            ),
            funds=fund_rows,
        )

    def _portfolio_data_range(self) -> tuple[date, date] | None:
        """Return the overall data range across transactions and prices."""
        transaction_range = self.transaction_repository.get_date_range()
        price_range = self.price_repository.get_date_range()
        if transaction_range is None and price_range is None:
            return None

        starts = [item[0] for item in (transaction_range, price_range) if item is not None]
        ends = [item[1] for item in (transaction_range, price_range) if item is not None]
        return min(starts), max(ends)

    def _resolve_report_period_bounds(
        self,
        period_type: ReportPeriodType,
        period_value: str,
    ) -> tuple[date, date, str]:
        """Parse one report period value and return normalized bounds."""
        if period_type == "monthly":
            match = re.fullmatch(r"(\d{4})-(\d{2})", period_value)
            if match is None:
                raise ValidationError("Monthly period must use format YYYY-MM")
            year = int(match.group(1))
            month = int(match.group(2))
            if month < 1 or month > 12:
                raise ValidationError("Monthly period month must be between 01 and 12")
            start_date = date(year, month, 1)
            end_date = date(year, month, calendar.monthrange(year, month)[1])
            return start_date, end_date, f"{year:04d}-{month:02d}"

        if period_type == "quarterly":
            match = re.fullmatch(r"(\d{4})-Q([1-4])", period_value)
            if match is None:
                raise ValidationError("Quarterly period must use format YYYY-QN")
            year = int(match.group(1))
            quarter = int(match.group(2))
            start_month = ((quarter - 1) * 3) + 1
            end_month = start_month + 2
            start_date = date(year, start_month, 1)
            end_date = date(year, end_month, calendar.monthrange(year, end_month)[1])
            return start_date, end_date, f"{year:04d}-Q{quarter}"

        if period_type == "yearly":
            match = re.fullmatch(r"(\d{4})", period_value)
            if match is None:
                raise ValidationError("Yearly period must use format YYYY")
            year = int(match.group(1))
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            return start_date, end_date, f"{year:04d}"

        raise ValidationError("Unsupported report period type")

    def _build_period_options(
        self,
        period_type: ReportPeriodType,
        data_start: date,
        data_end: date,
    ) -> list[ReportPeriodOption]:
        """Build selectable period values between start and end dates."""
        if data_start > data_end:
            return []

        options: list[ReportPeriodOption] = []
        if period_type == "monthly":
            cursor = date(data_start.year, data_start.month, 1)
            while cursor <= data_end:
                month_end = date(
                    cursor.year,
                    cursor.month,
                    calendar.monthrange(cursor.year, cursor.month)[1],
                )
                option_end = min(month_end, data_end)
                options.append(
                    ReportPeriodOption(
                        value=f"{cursor.year:04d}-{cursor.month:02d}",
                        label=f"{cursor.year:04d}-{cursor.month:02d}",
                        start_date=cursor,
                        end_date=option_end,
                    )
                )
                if cursor.month == 12:
                    cursor = date(cursor.year + 1, 1, 1)
                else:
                    cursor = date(cursor.year, cursor.month + 1, 1)
            return options

        if period_type == "quarterly":
            quarter_start_month = ((data_start.month - 1) // 3) * 3 + 1
            cursor = date(data_start.year, quarter_start_month, 1)
            while cursor <= data_end:
                quarter = ((cursor.month - 1) // 3) + 1
                end_month = cursor.month + 2
                quarter_end = date(
                    cursor.year,
                    end_month,
                    calendar.monthrange(cursor.year, end_month)[1],
                )
                option_end = min(quarter_end, data_end)
                options.append(
                    ReportPeriodOption(
                        value=f"{cursor.year:04d}-Q{quarter}",
                        label=f"{cursor.year:04d} Q{quarter}",
                        start_date=cursor,
                        end_date=option_end,
                    )
                )
                if cursor.month >= 10:
                    cursor = date(cursor.year + 1, 1, 1)
                else:
                    cursor = date(cursor.year, cursor.month + 3, 1)
            return options

        if period_type == "yearly":
            cursor_year = data_start.year
            while cursor_year <= data_end.year:
                start_date = date(cursor_year, 1, 1)
                end_date = date(cursor_year, 12, 31)
                options.append(
                    ReportPeriodOption(
                        value=f"{cursor_year:04d}",
                        label=f"{cursor_year:04d}",
                        start_date=start_date,
                        end_date=min(end_date, data_end),
                    )
                )
                cursor_year += 1
            return options

        return options

    def _compute_lots(
        self,
        transactions: list[Transaction],
        rates: list,
        latest_price_value: Decimal,
        as_of_date: date,
    ) -> list[LotComputation]:
        """Compute current state metrics for each BUY lot."""
        # Computes the current state for each BUY lot: remaining units, current market value,
        # outstanding borrowed amount, total interest paid, and current monthly/annual cost.
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
        """Build period metrics for a single lot across all windows."""
        # Builds return metrics for all standard period windows (d1, d7, d30, d180, ytd, m12, m24, total)
        # for a single lot, including gross change, interest cost, tax credit, and net margins.
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
        latest_price_date: date,
        as_of_date: date,
    ) -> PeriodMetricsByWindow:
        """Build fund-level period metrics based on reconciliation rows."""
        # Builds period return metrics for an entire fund by delegating to reconciliation rows
        # and mapping each row into a PeriodMetrics object.
        rows = self._build_fund_period_reconciliation_rows(
            fund=fund,
            transactions=transactions,
            lots=lots,
            rates=rates,
            latest_price_value=latest_price_value,
            latest_price_date=latest_price_date,
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
            d14=metrics_map["d14"],
            d30=metrics_map["d30"],
            d60=metrics_map["d60"],
            d90=metrics_map["d90"],
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
        latest_price_date: date,
        as_of_date: date,
    ) -> list[FundPeriodReconciliationRow]:
        """Build reconciliation rows for each configured period window."""
        # Builds one reconciliation row per period key containing start/end prices, units, value change,
        # net cashflow, dividends, interest, tax, and return percentage for the fund.
        earliest_buy = self._first_buy_date(transactions) or as_of_date
        total_cost = sum(
            (
                Decimal(item.total_amount)
                for item in transactions
                if item.type is TransactionType.BUY
            ),
            start=DECIMAL_ZERO,
        )
        rolling_period_end = min(as_of_date, latest_price_date)
        rows: list[FundPeriodReconciliationRow] = []
        for key in PERIOD_KEYS:
            period_end = as_of_date if key == "total" else rolling_period_end
            start_date = self._period_start_for_key(key, period_end)
            effective_start = earliest_buy if key == "total" else start_date
            if effective_start > period_end:
                effective_start = period_end

            days = max((period_end - effective_start).days, 1)
            start_price_value = self._resolve_start_price(
                fund.id,
                effective_start,
                latest_price_value,
                transactions,
            )

            units_t0 = self._fund_units_as_of(transactions, effective_start)
            units_t1 = self._fund_units_as_of(transactions, period_end)
            value_t1 = units_t1 * latest_price_value
            if key == "total":
                value_t0 = total_cost
            else:
                value_t0 = units_t0 * start_price_value
            dividends_in_period = self._sum_dividends_for_fund_between(
                transactions,
                effective_start,
                period_end,
            )
            net_external_cashflow = self._sum_external_cashflow_for_fund_between(
                transactions,
                effective_start,
                period_end,
            )
            if key == "total":
                # For the total period, value_t0 = total_cost (all BUY amounts).
                # Sold lots contribute 0 to value_t1 but their cost is in value_t0.
                # Add sale proceeds back so gross_value_change = (remaining_value + proceeds) - cost.
                total_sell_proceeds = sum(
                    (
                        abs(Decimal(t.total_amount))
                        for t in transactions
                        if t.type is TransactionType.SELL
                    ),
                    start=DECIMAL_ZERO,
                )
                gross_value_change = value_t1 + total_sell_proceeds - value_t0
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
                        end_date=period_end,
                    )
                    for lot in lots
                ),
                start=DECIMAL_ZERO,
            )
            interest_tax_credit = allocated_interest_cost * DECIMAL_22_PCT

            regime = self._resolve_tax_regime(fund, period_end)
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
                    end_date=period_end,
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
        """Aggregate period metrics from all fund summaries."""
        # Aggregates individual fund period metrics into combined portfolio-level period metrics
        # by summing value changes, interest, tax, and recalculating return percentages.
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
        """Compute true net worth components for one fund."""
        # Computes the true net worth for a single fund by subtracting debt, deferred or paid tax,
        # and net interest cost (after the 22% tax credit) from current market value.
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
        """Aggregate true net worth components across all funds."""
        # Sums all per-fund true net worth components into a single portfolio-level breakdown.
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
        """Resolve tax regime name for a fund and date."""
        # Returns the applicable tax regime string for a fund: "distributing_pre_2026" for
        # distributing funds, otherwise "accumulating_2026".
        if fund.ticker in DISTRIBUTING_FUNDS:
            return "distributing_pre_2026"
        return "accumulating_2026"

    def _taxable_gain_base(self, fund: Fund, unrealized_gain_before_tax: Decimal) -> Decimal:
        """Determine taxable gain base with optional manual override."""
        # Returns the taxable gain base, using a manual override if configured on the fund,
        # otherwise clamping the unrealized gain to zero as a floor.
        if fund.manual_taxable_gain_override is not None:
            return Decimal(fund.manual_taxable_gain_override)
        return max(unrealized_gain_before_tax, DECIMAL_ZERO)

    def _period_start_for_key(self, period_key: str, as_of_date: date) -> date:
        """Map a period key to its computed start date."""
        # Maps a period key (d1, d7, d30, d180, ytd, m12, m24, total) to its corresponding
        # start date relative to as_of_date.
        if period_key == "d1":
            return as_of_date - timedelta(days=1)
        if period_key == "d7":
            return as_of_date - timedelta(days=7)
        if period_key == "d14":
            return as_of_date - timedelta(days=14)
        if period_key == "d30":
            return as_of_date - timedelta(days=30)
        if period_key == "d60":
            return as_of_date - timedelta(days=60)
        if period_key == "d90":
            return as_of_date - timedelta(days=90)
        if period_key == "d180":
            return as_of_date - timedelta(days=180)
        if period_key == "ytd":
            return date(as_of_date.year, 1, 1)
        if period_key == "m12":
            return as_of_date - timedelta(days=365)
        if period_key == "m24":
            return as_of_date - timedelta(days=730)
        return date.min

    def _realized_profit_from_sold_positions(
        self,
        transactions: list[Transaction],
        rates: list,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """Returns (realized_profit_for_display, total_sale_proceeds, total_interest_on_sold).

        realized_profit_for_display = sale_proceeds - sold_cost
        sold_cost is allocated from BUY principal only (same basis as lot cost).
        Sells consume BUY units first; reinvested units are treated as zero-principal
        units in this BUY-principal view.

        total_sale_proceeds is returned for use in the Total period gross_value_change.
        total_interest_on_sold is returned for informational use.
        """
        buy_lots = {
            item.id: item for item in transactions if item.type is TransactionType.BUY
        }
        realized_profit = DECIMAL_ZERO
        total_sale_proceeds = DECIMAL_ZERO
        total_interest_on_sold = DECIMAL_ZERO

        for lot_id, lot in buy_lots.items():
            all_related = [t for t in transactions if t.lot_id == lot_id]
            has_sell = any(t.type is TransactionType.SELL for t in all_related)
            if not has_sell:
                continue

            capital_state = self._lot_capital_state_as_of(
                buy_transaction=lot,
                related_transactions=all_related,
            )
            total_sale_proceeds += capital_state.sale_proceeds
            realized_profit += capital_state.sale_proceeds - capital_state.sold_cost

        return realized_profit, total_sale_proceeds, total_interest_on_sold

    def _lot_capital_state_as_of(
        self,
        buy_transaction: Transaction,
        related_transactions: list[Transaction],
        as_of_date: date | None = None,
    ) -> LotCapitalState:
        """Return remaining and sold principal state for one lot.

        The principal pool for a lot consists of BUY plus DIVIDEND_REINVEST amounts.
        SELL transactions reduce that pool proportionally by outstanding principal units.
        """
        remaining_total_units = Decimal(buy_transaction.units)
        remaining_cost = Decimal(buy_transaction.total_amount)
        remaining_equity = Decimal(buy_transaction.equity_amount)
        remaining_borrowed = Decimal(buy_transaction.borrowed_amount)
        sold_cost = DECIMAL_ZERO
        sale_proceeds = DECIMAL_ZERO

        events = sorted(
            related_transactions,
            key=lambda item: (item.date, item.created_at),
        )
        for transaction in events:
            if as_of_date is not None and transaction.date > as_of_date:
                continue

            if transaction.type is TransactionType.DIVIDEND_REINVEST:
                reinvest_units = Decimal(transaction.units)
                if reinvest_units <= DECIMAL_ZERO:
                    continue
                # Reinvested dividends increase unit count, but do not represent
                # new contributed BUY principal in capital_split totals.
                remaining_total_units += reinvest_units
                continue

            if transaction.type is not TransactionType.SELL:
                continue

            sold_units = abs(Decimal(transaction.units))
            if sold_units <= DECIMAL_ZERO or remaining_total_units <= DECIMAL_ZERO:
                sale_proceeds += abs(Decimal(transaction.total_amount))
                continue

            sold_against_principal = min(sold_units, remaining_total_units)
            sold_ratio = sold_against_principal / remaining_total_units
            allocated_cost = remaining_cost * sold_ratio
            allocated_equity = remaining_equity * sold_ratio
            allocated_borrowed = remaining_borrowed * sold_ratio

            remaining_total_units -= sold_against_principal
            remaining_cost -= allocated_cost
            remaining_equity -= allocated_equity
            remaining_borrowed -= allocated_borrowed
            sold_cost += allocated_cost
            sale_proceeds += abs(Decimal(transaction.total_amount))

        return LotCapitalState(
            remaining_units=max(remaining_total_units, DECIMAL_ZERO),
            remaining_cost=max(remaining_cost, DECIMAL_ZERO),
            remaining_equity=max(remaining_equity, DECIMAL_ZERO),
            remaining_borrowed=max(remaining_borrowed, DECIMAL_ZERO),
            sold_cost=sold_cost,
            sale_proceeds=sale_proceeds,
        )

    def _first_buy_date(self, transactions: list[Transaction]) -> date | None:
        """Return the earliest BUY transaction date if present."""
        # Returns the earliest BUY transaction date, or None if there are no buy transactions.
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
        """Return net units for one lot as of a date."""
        # Returns the net unit count for a single lot as of value_date by applying all
        # related transactions (sells, reinvestments) that occurred on or before that date.
        if value_date < lot.date:
            return DECIMAL_ZERO
        units = Decimal(lot.units)
        for transaction in related_transactions:
            if transaction.date <= value_date:
                units += Decimal(transaction.units)
        return units

    def _remaining_buy_fraction_as_of(
        self,
        buy_transaction: Transaction,
        related_transactions: list[Transaction],
    ) -> Decimal:
        """Return remaining fraction of original BUY units after sells."""
        original_units = abs(Decimal(buy_transaction.units))
        if original_units <= DECIMAL_ZERO:
            return Decimal("1")

        sold_units_total = sum(
            (
                abs(Decimal(item.units))
                for item in related_transactions
                if item.type is TransactionType.SELL
            ),
            start=DECIMAL_ZERO,
        )
        remaining_units = max(original_units - sold_units_total, DECIMAL_ZERO)
        return remaining_units / original_units

    def _fund_units_as_of(self, transactions: list[Transaction], value_date: date) -> Decimal:
        """Return total fund units held as of a date."""
        # Returns the total net units held across all lots for a fund as of value_date,
        # accounting for buys, sells, and dividend reinvestments per lot.
        units_by_lot: dict[uuid.UUID, Decimal] = {}
        lot_ids: set[uuid.UUID] = set()
        for transaction in transactions:
            if transaction.type is TransactionType.BUY and transaction.date <= value_date:
                units_by_lot[transaction.id] = Decimal(transaction.units)
                lot_ids.add(transaction.id)

        for transaction in transactions:
            lot_id = transaction.lot_id
            if lot_id is not None and lot_id in lot_ids and transaction.date <= value_date:
                units_by_lot[lot_id] = units_by_lot.get(lot_id, DECIMAL_ZERO) + Decimal(
                    transaction.units
                )
        return sum(units_by_lot.values(), start=DECIMAL_ZERO)

    def _transaction_effective_date_for_history(
        self,
        fund: Fund,
        transaction: Transaction,
        prices: list,
    ) -> date:
        """Return effective transaction date used in history snapshots."""
        # Dividend reinvestments should line up with the first post-dividend price drop,
        # not the calendar year-end posting date, otherwise history snapshots spike.
        if transaction.type is TransactionType.DIVIDEND_REINVEST:
            return self._dividend_reinvest_effective_date_for_history(prices, transaction.date)
        return transaction.date

    def _dividend_reinvest_effective_date_for_history(
        self,
        prices: list,
        transaction_date: date,
    ) -> date:
        """Return the first post-dividend trading day that reflects the reinvestment."""
        previous_price = self._latest_price_value_as_of(prices, transaction_date)
        if previous_price <= DECIMAL_ZERO:
            return transaction_date

        dividend_drop_threshold = Decimal("0.98")
        post_dividend_prices = [price for price in prices if price.date > transaction_date][:15]
        for price in post_dividend_prices:
            current_price = Decimal(price.price)
            if current_price <= previous_price * dividend_drop_threshold:
                return price.date
            previous_price = current_price

        return transaction_date

    def _first_trading_day_on_or_after(self, prices: list, start_date: date) -> date | None:
        """Return first available trading day on or after a date."""
        # Returns the first available price date on or after start_date from the price list.
        for price in prices:
            if price.date >= start_date:
                return price.date
        return None

    def _effective_price_for_history(
        self, prices: list, transactions: list, snap_date: date
    ) -> Decimal:
        """Resolve best available price for a history snapshot date."""
        # Returns the best available price for a fund at a snapshot date.
        # Priority order:
        #  1. Official price on exactly snap_date.
        #  2. Implied post-dividend NAV from DIVIDEND_REINVEST transactions on snap_date
        #     (when no official price exists on that date, e.g. FHY 2024-12-31 and 2025-12-31).
        #     Using a stale pre-dividend price with post-dividend unit counts would overstate value.
        #  3. Implied NAV from BUY transactions on snap_date, only when no prior price exists at all
        #     (e.g. HHRP first purchase on 2025-09-30 before any price data).
        #  4. Latest official price on or before snap_date.
        has_price_on_snap = any(p.date == snap_date for p in prices)

        if not has_price_on_snap:
            # Check for dividend reinvests — they carry the post-dividend NAV
            reinvests = [
                t
                for t in transactions
                if t.type is TransactionType.DIVIDEND_REINVEST
                and t.date == snap_date
                and Decimal(t.units) > DECIMAL_ZERO
            ]
            if reinvests:
                total_amount = sum(Decimal(t.total_amount) for t in reinvests)
                total_units = sum(Decimal(t.units) for t in reinvests)
                if total_units > DECIMAL_ZERO:
                    return total_amount / total_units

            # No prior price at all — use BUY implied NAV (first purchase of a new fund)
            latest = self._latest_price_value_as_of(prices, snap_date)
            if latest == DECIMAL_ZERO:
                implied_nav = self._latest_implied_nav_on_or_before(transactions, snap_date)
                if implied_nav is not None:
                    return implied_nav

        return self._latest_price_value_as_of(prices, snap_date)

    def _latest_implied_nav_on_or_before(
        self,
        transactions: list[Transaction],
        value_date: date,
    ) -> Decimal | None:
        """Return implied NAV from the latest BUY/DIVIDEND_REINVEST day up to a date."""
        candidates = [
            item
            for item in transactions
            if item.date <= value_date
            and item.type in (TransactionType.BUY, TransactionType.DIVIDEND_REINVEST)
            and Decimal(item.units) > DECIMAL_ZERO
        ]
        if not candidates:
            return None

        latest_date = max(item.date for item in candidates)
        same_day = [item for item in candidates if item.date == latest_date]
        total_amount = sum((Decimal(item.total_amount) for item in same_day), start=DECIMAL_ZERO)
        total_units = sum((Decimal(item.units) for item in same_day), start=DECIMAL_ZERO)
        if total_units <= DECIMAL_ZERO:
            return None
        return total_amount / total_units

    def _latest_price_value_as_of(self, prices: list, value_date: date) -> Decimal:
        """Return latest known price value on or before a date."""
        for price in reversed(prices):
            if price.date <= value_date:
                return Decimal(price.price)
        return DECIMAL_ZERO

    def _sum_dividends_for_lot_between(
        self,
        related_transactions: list[Transaction],
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Sum dividend reinvest amounts for one lot in a date range."""
        # Sums the total amount of DIVIDEND_REINVEST transactions for a lot within the given date range.
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
        """Sum dividend reinvest amounts for one fund in a date range."""
        # Sums the total amount of DIVIDEND_REINVEST transactions for a fund within the given date range.
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
        """Compute net BUY minus SELL cashflow for a date range."""
        # Returns the net external cashflow for a fund in the date range: total BUY amounts
        # minus total SELL amounts for transactions strictly after start_date.
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
        """Resolve start price for period calculations with safe fallbacks."""
        # Finds the best available price for a fund at the start of a period. Adjusts for
        # post-dividend NAV drops and falls back to the first available price if none precedes the date.
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
        """Compute cost-weighted average holding days for BUY transactions."""
        # Returns the cost-weighted average number of days that the invested capital
        # has been held across all buy transactions.
        if total_cost <= DECIMAL_ZERO:
            return DECIMAL_ZERO

        weighted_sum = DECIMAL_ZERO
        for transaction in buy_transactions:
            days_owned = Decimal(max((as_of_date - transaction.date).days, 1))
            weighted_sum += Decimal(transaction.total_amount) * days_owned
        return weighted_sum / total_cost

    def _safe_percentage(self, numerator: Decimal, denominator: Decimal) -> Decimal | None:
        """Return percentage result or None when denominator is not positive."""
        # Divides numerator by denominator and returns the result as a percentage,
        # or None if the denominator is zero or negative.
        if denominator <= DECIMAL_ZERO:
            return None
        return (numerator / denominator) * DECIMAL_100

    def _annualized_roe(
        self,
        net_value_after_interest: Decimal,
        equity: Decimal,
        days_owned: Decimal,
    ) -> Decimal | None:
        """Compute annualized return on equity for one position."""
        # Computes the annualized return on equity using compound growth, returning None
        # if equity, days, or net value is non-positive.
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
        """Compute annualized return from start and end values over time."""
        # Computes the annualized return given a start value, end value, and holding period in days,
        # returning None for invalid inputs.
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
        """Build gross and after-interest return split metrics."""
        # Builds a ReturnSplitMetrics object with gross and after-interest return amounts,
        # percentages, and annualized figures for a given period.
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
        """Compute XIRR-based annualized return on invested cost."""
        # Computes the XIRR-based annualized return on cost by building cashflows from
        # all buy/sell transactions and the current portfolio terminal value.
        cashflows = self._build_return_on_cost_cashflows(transactions, lots, as_of_date)
        return self._xirr_percentage(cashflows)

    def _build_return_on_cost_cashflows(
        self,
        transactions: list[Transaction],
        lots: list[LotComputation],
        as_of_date: date,
    ) -> list[tuple[date, Decimal]]:
        """Build cashflow tuples used for XIRR return calculations."""
        # Builds the cashflow list for XIRR: negative amounts for buys, positive for sells,
        # and the current market value as a terminal inflow on as_of_date.
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
        """Solve and return XIRR percentage from dated cashflows."""
        # Solves for the XIRR (extended internal rate of return) using a bisection method
        # on the net present value equation, returning the result as a percentage.
        if not cashflows:
            return None

        has_positive = any(amount > DECIMAL_ZERO for _, amount in cashflows)
        has_negative = any(amount < DECIMAL_ZERO for _, amount in cashflows)
        if not has_positive or not has_negative:
            return None

        ordered = sorted(cashflows, key=lambda item: item[0])
        first_date = ordered[0][0]

        def npv(rate: float) -> float:
            """Compute net present value for a candidate XIRR rate."""
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
        """Build performance percentages for standard lookback windows."""
        # Computes price-based return percentages for standard lookback windows (14d, 30d, 90d, 180d, 1y)
        # by comparing the latest price to the reference price for each window.
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
