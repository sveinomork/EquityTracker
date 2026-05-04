from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.domain.enums import TransactionType
from app.models.loan_rate_history import LoanRateHistory
from app.models.transaction import Transaction
from app.services.interest_service import InterestService


def test_interest_calculation_reduces_balance_after_partial_sale() -> None:
    lot_id = uuid4()
    fund_id = uuid4()
    buy_transaction = Transaction(
        id=lot_id,
        fund_id=fund_id,
        lot_id=None,
        date=date(2024, 1, 1),
        type=TransactionType.BUY,
        units=Decimal("100"),
        price_per_unit=Decimal("100"),
        total_amount=Decimal("10000"),
        borrowed_amount=Decimal("5000"),
        equity_amount=Decimal("5000"),
    )
    sell_transaction = Transaction(
        fund_id=fund_id,
        lot_id=lot_id,
        date=date(2024, 1, 11),
        type=TransactionType.SELL,
        units=Decimal("-50"),
        price_per_unit=Decimal("100"),
        total_amount=Decimal("5000"),
        borrowed_amount=Decimal("0"),
        equity_amount=Decimal("5000"),
    )
    rates = [
        LoanRateHistory(
            fund_id=fund_id,
            effective_date=date(2024, 1, 1),
            nominal_rate=Decimal("3.65"),
        )
    ]

    result = InterestService().calculate_for_lot(
        buy_transaction=buy_transaction,
        related_transactions=[sell_transaction],
        rates=rates,
        as_of_date=date(2024, 1, 20),
    )

    assert result.total_paid.quantize(Decimal("0.01")) == Decimal("7.50")
    assert result.current_outstanding_borrowed == Decimal("2500")
    assert result.current_monthly_cost.quantize(Decimal("0.01")) == Decimal("7.73")
    assert result.current_annual_cost.quantize(Decimal("0.01")) == Decimal("91.25")


def test_interest_monthly_cost_uses_actual_days_in_month() -> None:
    fund_id = uuid4()
    buy_transaction = Transaction(
        id=uuid4(),
        fund_id=fund_id,
        lot_id=None,
        date=date(2026, 1, 1),
        type=TransactionType.BUY,
        units=Decimal("100"),
        price_per_unit=Decimal("3201"),
        total_amount=Decimal("320100"),
        borrowed_amount=Decimal("320100"),
        equity_amount=Decimal("0"),
    )
    rates = [
        LoanRateHistory(
            fund_id=fund_id,
            effective_date=date(2026, 1, 1),
            nominal_rate=Decimal("4.38"),
        )
    ]

    result = InterestService().calculate_for_lot(
        buy_transaction=buy_transaction,
        related_transactions=[],
        rates=rates,
        as_of_date=date(2026, 1, 31),
    )

    assert result.current_monthly_cost.quantize(Decimal("0.01")) == Decimal("1190.77")


def test_period_interest_uses_daily_balances_and_rate_changes() -> None:
    lot_id = uuid4()
    fund_id = uuid4()
    buy_transaction = Transaction(
        id=lot_id,
        fund_id=fund_id,
        lot_id=None,
        date=date(2024, 1, 1),
        type=TransactionType.BUY,
        units=Decimal("100"),
        price_per_unit=Decimal("100"),
        total_amount=Decimal("10000"),
        borrowed_amount=Decimal("5000"),
        equity_amount=Decimal("5000"),
    )
    sell_transaction = Transaction(
        fund_id=fund_id,
        lot_id=lot_id,
        date=date(2024, 1, 11),
        type=TransactionType.SELL,
        units=Decimal("-50"),
        price_per_unit=Decimal("100"),
        total_amount=Decimal("5000"),
        borrowed_amount=Decimal("0"),
        equity_amount=Decimal("5000"),
    )
    rates = [
        LoanRateHistory(
            fund_id=fund_id,
            effective_date=date(2024, 1, 1),
            nominal_rate=Decimal("3.65"),
        ),
        LoanRateHistory(
            fund_id=fund_id,
            effective_date=date(2024, 1, 13),
            nominal_rate=Decimal("7.30"),
        ),
    ]

    result = InterestService().calculate_period_interest_for_lot(
        buy_transaction=buy_transaction,
        related_transactions=[sell_transaction],
        rates=rates,
        start_date=date(2024, 1, 5),
        end_date=date(2024, 1, 15),
    )

    assert result.quantize(Decimal("0.01")) == Decimal("4.50")
