import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field, model_validator

from app.domain.enums import TransactionType
from app.schemas.common import APIModel


class TransactionCreate(APIModel):
    fund_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    date: date
    type: TransactionType
    units: Decimal = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    total_amount: Decimal = Field(gt=0)
    borrowed_amount: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_payload(self) -> "TransactionCreate":
        if self.type is TransactionType.SELL:
            self.units = -abs(self.units)
            if self.lot_id is None:
                raise ValueError("SELL transactions must reference a lot_id")
        elif self.type is TransactionType.DIVIDEND_REINVEST and self.lot_id is None:
            raise ValueError("DIVIDEND_REINVEST transactions must reference a lot_id")

        if self.borrowed_amount > self.total_amount:
            raise ValueError("borrowed_amount cannot exceed total_amount")

        return self


class TransactionRead(APIModel):
    id: uuid.UUID
    fund_id: uuid.UUID
    lot_id: uuid.UUID | None
    date: date
    type: TransactionType
    units: Decimal
    price_per_unit: Decimal
    total_amount: Decimal
    borrowed_amount: Decimal
    equity_amount: Decimal
