from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import TransactionType
from app.schemas.transaction import TransactionCreate


def test_sell_transaction_requires_lot_id() -> None:
    with pytest.raises(ValidationError):
        TransactionCreate(
            fund_id=uuid4(),
            date=date(2024, 1, 1),
            type=TransactionType.SELL,
            units=Decimal("1"),
            price_per_unit=Decimal("100"),
            total_amount=Decimal("100"),
            borrowed_amount=Decimal("0"),
        )


def test_sell_transaction_is_normalized_to_negative_units() -> None:
    payload = TransactionCreate(
        fund_id=uuid4(),
        lot_id=uuid4(),
        date=date(2024, 1, 1),
        type=TransactionType.SELL,
        units=Decimal("2"),
        price_per_unit=Decimal("100"),
        total_amount=Decimal("200"),
        borrowed_amount=Decimal("0"),
    )

    assert payload.units == Decimal("-2")
