import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.enums import TransactionType
from app.models.loan_rate_history import LoanRateHistory
from app.models.transaction import Transaction

DECIMAL_ZERO = Decimal("0")
DECIMAL_100 = Decimal("100")
DECIMAL_365 = Decimal("365")
DECIMAL_366 = Decimal("366")


@dataclass(slots=True)
class InterestBreakdown:
    """Computed interest totals and current borrowing cost metrics for a lot."""
    total_paid: Decimal
    current_outstanding_borrowed: Decimal
    current_monthly_cost: Decimal
    current_annual_cost: Decimal


class InterestService:
    """Interest calculation logic for leveraged lot positions."""
    def calculate_for_lot(
        self,
        buy_transaction: Transaction,
        related_transactions: list[Transaction],
        rates: list[LoanRateHistory],
        as_of_date: date,
    ) -> InterestBreakdown:
        """Calculate cumulative and current borrowing costs for one lot."""
        balances_by_date = self._build_balance_adjustments(buy_transaction, related_transactions)
        current_borrowed = self._borrowed_balance_on_date(
            buy_transaction=buy_transaction,
            balances_by_date=balances_by_date,
            value_date=as_of_date,
        )
        total_interest_paid = self._calculate_total_interest_paid(
            buy_transaction=buy_transaction,
            balances_by_date=balances_by_date,
            rates=rates,
            as_of_date=as_of_date,
        )

        current_rate = self._find_active_rate(rates, as_of_date)
        annual_cost = (
            current_borrowed * Decimal(current_rate.nominal_rate) / DECIMAL_100
            if current_rate is not None
            else DECIMAL_ZERO
        )
        monthly_cost = self._current_month_cost(
            current_borrowed=current_borrowed,
            current_rate=current_rate,
            as_of_date=as_of_date,
        )

        return InterestBreakdown(
            total_paid=total_interest_paid,
            current_outstanding_borrowed=current_borrowed,
            current_monthly_cost=monthly_cost,
            current_annual_cost=annual_cost,
        )

    def calculate_period_interest_for_lot(
        self,
        buy_transaction: Transaction,
        related_transactions: list[Transaction],
        rates: list[LoanRateHistory],
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Calculate borrowing interest accrued within a date range."""
        effective_start = max(start_date, buy_transaction.date)
        if end_date <= effective_start:
            return DECIMAL_ZERO

        balances_by_date = self._build_balance_adjustments(buy_transaction, related_transactions)
        current_borrowed = self._borrowed_balance_on_date(
            buy_transaction=buy_transaction,
            balances_by_date=balances_by_date,
            value_date=effective_start,
        )

        total_interest_paid = DECIMAL_ZERO
        day = effective_start + timedelta(days=1)
        while day <= end_date:
            current_borrowed += balances_by_date.get(day, DECIMAL_ZERO)
            if current_borrowed < DECIMAL_ZERO:
                current_borrowed = DECIMAL_ZERO

            active_rate = self._find_active_rate(rates, day)
            if active_rate is not None and current_borrowed > DECIMAL_ZERO:
                total_interest_paid += (
                    current_borrowed * Decimal(active_rate.nominal_rate) / DECIMAL_100 / DECIMAL_365
                )

            day += timedelta(days=1)

        return total_interest_paid

    def _find_active_rate(
        self,
        rates: list[LoanRateHistory],
        value_date: date,
    ) -> LoanRateHistory | None:
        """Return the latest effective rate on or before a date."""
        active_rate: LoanRateHistory | None = None
        for rate in rates:
            if rate.effective_date <= value_date:
                active_rate = rate
            else:
                break
        return active_rate

    def get_nominal_rate_for_date(
        self,
        rates: list[LoanRateHistory],
        value_date: date,
    ) -> Decimal:
        """Return nominal rate value for a date, or zero if no rate is active."""
        active_rate = self._find_active_rate(rates, value_date)
        if active_rate is None:
            return DECIMAL_ZERO
        return Decimal(active_rate.nominal_rate)

    def _days_in_year(self, value_date: date) -> Decimal:
        """Return the number of days in the date's year as Decimal."""
        return DECIMAL_366 if calendar.isleap(value_date.year) else DECIMAL_365

    def _build_balance_adjustments(
        self,
        buy_transaction: Transaction,
        related_transactions: list[Transaction],
    ) -> dict[date, Decimal]:
        """Build per-date borrowed-balance reductions caused by SELL transactions."""
        original_units = Decimal(buy_transaction.units)
        current_borrowed = Decimal(buy_transaction.borrowed_amount)
        balances_by_date: dict[date, Decimal] = {}
        remaining_units = original_units
        borrowed_for_allocation = current_borrowed
        sell_transactions = sorted(
            [item for item in related_transactions if item.type is TransactionType.SELL],
            key=lambda item: item.date,
        )
        for transaction in sell_transactions:
            sold_units = min(abs(Decimal(transaction.units)), remaining_units)
            reduction_ratio = (
                sold_units / remaining_units if remaining_units > DECIMAL_ZERO else DECIMAL_ZERO
            )
            borrowed_reduction = borrowed_for_allocation * reduction_ratio
            balances_by_date[transaction.date] = (
                balances_by_date.get(transaction.date, DECIMAL_ZERO) - borrowed_reduction
            )
            borrowed_for_allocation -= borrowed_reduction
            remaining_units -= sold_units
        return balances_by_date

    def _borrowed_balance_on_date(
        self,
        buy_transaction: Transaction,
        balances_by_date: dict[date, Decimal],
        value_date: date,
    ) -> Decimal:
        """Return outstanding borrowed balance for a lot at a given date."""
        current_borrowed = Decimal(buy_transaction.borrowed_amount)
        for day, delta in sorted(balances_by_date.items()):
            if day <= value_date:
                current_borrowed += delta
            else:
                break
        if current_borrowed < DECIMAL_ZERO:
            return DECIMAL_ZERO
        return current_borrowed

    def _calculate_total_interest_paid(
        self,
        buy_transaction: Transaction,
        balances_by_date: dict[date, Decimal],
        rates: list[LoanRateHistory],
        as_of_date: date,
    ) -> Decimal:
        """Accumulate day-by-day interest from buy date through as_of_date."""
        current_borrowed = Decimal(buy_transaction.borrowed_amount)
        total_interest_paid = DECIMAL_ZERO
        day = buy_transaction.date
        while day <= as_of_date:
            current_borrowed += balances_by_date.get(day, DECIMAL_ZERO)
            if current_borrowed < DECIMAL_ZERO:
                current_borrowed = DECIMAL_ZERO

            active_rate = self._find_active_rate(rates, day)
            if active_rate is not None and current_borrowed > DECIMAL_ZERO:
                total_interest_paid += (
                    current_borrowed * Decimal(active_rate.nominal_rate) / DECIMAL_100 / DECIMAL_365
                )

            day += timedelta(days=1)
        return total_interest_paid

    def _current_month_cost(
        self,
        current_borrowed: Decimal,
        current_rate: LoanRateHistory | None,
        as_of_date: date,
    ) -> Decimal:
        """Estimate the current month borrowing cost from active rate and balance."""
        if current_rate is None or current_borrowed <= DECIMAL_ZERO:
            return DECIMAL_ZERO

        days_in_month = Decimal(str(calendar.monthrange(as_of_date.year, as_of_date.month)[1]))
        return (
            current_borrowed
            * Decimal(current_rate.nominal_rate)
            / DECIMAL_100
            * days_in_month
            / self._days_in_year(as_of_date)
        )
