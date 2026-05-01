import math
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.domain.enums import TransactionType
from app.domain.exceptions import NotFoundError
from app.models.transaction import Transaction
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.rate_repository import RateRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.analytics import (
    BorrowingCosts,
    CapitalSplit,
    FundLotsSummary,
    FundSummary,
    LotCapitalSplit,
    LotSummary,
    PerformanceWindows,
    PortfolioSummary,
    PortfolioTotals,
    ReturnMetrics,
)
from app.services.interest_service import InterestService

DECIMAL_ZERO = Decimal("0")
DECIMAL_100 = Decimal("100")
WINDOWS = ((14, "d14_pct"), (30, "d30_pct"), (90, "d90_pct"), (180, "d180_pct"), (365, "y1_pct"))


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
        average_days_owned = self._average_days_owned(buy_transactions, total_cost, effective_date)

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
                return_on_equity_net_pct=self._safe_percentage(profit_loss_net, total_equity),
                annualized_return_on_equity_pct=self._annualized_roe(
                    net_equity_value - total_interest_paid,
                    total_equity,
                    average_days_owned,
                ),
            ),
            borrowing_costs=BorrowingCosts(
                monthly_current=current_monthly_cost,
                annual_current=current_annual_cost,
            ),
            performance_windows=self._build_performance_windows(
                fund_id, effective_date, latest_price_value
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
                            Decimal(item.lot.equity_amount),
                        ),
                        annualized_return_on_equity_pct=self._annualized_roe(
                            item.current_value
                            - item.outstanding_borrowed
                            - item.allocated_interest_paid,
                            Decimal(item.lot.equity_amount),
                            Decimal(days_owned),
                        ),
                    ),
                )
            )

        return FundLotsSummary(
            fund_id=fund.id,
            fund_name=fund.name,
            ticker=fund.ticker,
            lots=payload_lots,
        )

    def get_portfolio_summary(self, as_of_date: date | None = None) -> PortfolioSummary:
        effective_date = as_of_date or date.today()
        funds = self.fund_repository.list_all()
        fund_summaries = [self.get_fund_summary(fund.id, effective_date) for fund in funds]

        totals = PortfolioTotals(
            current_value=sum((item.current_value for item in fund_summaries), start=DECIMAL_ZERO),
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
        )
        return PortfolioSummary(as_of_date=effective_date, funds=fund_summaries, totals=totals)

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

    def _build_performance_windows(
        self,
        fund_id: uuid.UUID,
        as_of_date: date,
        latest_price_value: Decimal,
    ) -> PerformanceWindows:
        values: dict[str, Decimal | None] = {}
        for days, field_name in WINDOWS:
            reference_date = as_of_date - timedelta(days=days)
            reference_price = self.price_repository.latest_on_or_before(fund_id, reference_date)
            reference_value = (
                Decimal(reference_price.price) if reference_price is not None else DECIMAL_ZERO
            )
            values[field_name] = (
                self._safe_percentage(
                    latest_price_value - reference_value,
                    reference_value,
                )
                if reference_value > DECIMAL_ZERO
                else None
            )
        return PerformanceWindows(**values)
