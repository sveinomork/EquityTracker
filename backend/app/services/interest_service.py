from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from app.domain.enums import TransactionType
from app.models.loan_rate_history import LoanRateHistory
from app.models.transaction import Transaction

DECIMAL_ZERO = Decimal("0")
DECIMAL_100 = Decimal("100")
DECIMAL_365 = Decimal("365")
DECIMAL_12 = Decimal("12")


@dataclass(slots=True)
class InterestBreakdown:
    total_paid: Decimal
    current_outstanding_borrowed: Decimal
    current_monthly_cost: Decimal
    current_annual_cost: Decimal


class InterestService:
    def calculate_for_lot(
        self,
        buy_transaction: Transaction,
        related_transactions: list[Transaction],
        rates: list[LoanRateHistory],
        as_of_date: date,
    ) -> InterestBreakdown:
        original_units = Decimal(buy_transaction.units)
        current_borrowed = Decimal(buy_transaction.borrowed_amount)
        total_interest_paid = DECIMAL_ZERO

        balances_by_date: dict[date, Decimal] = {}
        for transaction in related_transactions:
            if transaction.type is TransactionType.SELL:
                sold_units = abs(Decimal(transaction.units))
                reduction_ratio = sold_units / original_units if original_units else DECIMAL_ZERO
                balances_by_date[transaction.date] = balances_by_date.get(
                    transaction.date, DECIMAL_ZERO
                ) - (Decimal(buy_transaction.borrowed_amount) * reduction_ratio)

        day = buy_transaction.date
        while day <= as_of_date:
            current_borrowed += balances_by_date.get(day, DECIMAL_ZERO)
            if current_borrowed < DECIMAL_ZERO:
                current_borrowed = DECIMAL_ZERO

            active_rate = self._find_active_rate(rates, day)
            if active_rate is not None and current_borrowed > DECIMAL_ZERO:
                total_interest_paid += (
                    current_borrowed * Decimal(active_rate.nominal_rate) / DECIMAL_365
                )

            day += timedelta(days=1)

        current_rate = self._find_active_rate(rates, as_of_date)
        annual_cost = (
            current_borrowed * Decimal(current_rate.nominal_rate)
            if current_rate is not None
            else DECIMAL_ZERO
        )
        monthly_cost = annual_cost / DECIMAL_12 if annual_cost else DECIMAL_ZERO

        return InterestBreakdown(
            total_paid=total_interest_paid,
            current_outstanding_borrowed=current_borrowed,
            current_monthly_cost=monthly_cost,
            current_annual_cost=annual_cost,
        )

    def _find_active_rate(
        self,
        rates: list[LoanRateHistory],
        value_date: date,
    ) -> LoanRateHistory | None:
        active_rate: LoanRateHistory | None = None
        for rate in rates:
            if rate.effective_date <= value_date:
                active_rate = rate
            else:
                break
        return active_rate
