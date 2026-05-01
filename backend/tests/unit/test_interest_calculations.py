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
            nominal_rate=Decimal("0.0365"),
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
    assert result.current_annual_cost.quantize(Decimal("0.01")) == Decimal("91.25")
