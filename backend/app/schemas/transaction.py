import uuid
from datetime import date as dt_date
from decimal import Decimal

from pydantic import Field, model_validator

from app.domain.enums import TransactionType
from app.schemas.common import APIModel


class TransactionCreate(APIModel):
    """Request model for creating a transaction."""
    fund_id: uuid.UUID
    lot_id: uuid.UUID | None = None
    date: dt_date
    type: TransactionType
    units: Decimal = Field(gt=0)
    price_per_unit: Decimal = Field(gt=0)
    total_amount: Decimal = Field(gt=0)
    borrowed_amount: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def validate_payload(self) -> "TransactionCreate":
        """Apply transaction-type validation and unit normalization rules."""
        if self.type is TransactionType.SELL:
            self.units = -abs(self.units)
        elif self.type is TransactionType.DIVIDEND_REINVEST and self.lot_id is None:
            raise ValueError("DIVIDEND_REINVEST transactions must reference a lot_id")

        if self.borrowed_amount > self.total_amount:
            raise ValueError("borrowed_amount cannot exceed total_amount")

        return self


class TransactionUpdate(APIModel):
    """Request model for partially updating a transaction."""
    lot_id: uuid.UUID | None = None
    date: dt_date | None = None
    type: TransactionType | None = None
    units: Decimal | None = Field(default=None, gt=0)
    price_per_unit: Decimal | None = Field(default=None, gt=0)
    total_amount: Decimal | None = Field(default=None, gt=0)
    borrowed_amount: Decimal | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_payload(self) -> "TransactionUpdate":
        """Apply consistency checks for optional update fields."""
        if self.type is TransactionType.DIVIDEND_REINVEST and self.lot_id is None:
            raise ValueError("DIVIDEND_REINVEST transactions must reference a lot_id")

        if (
            self.borrowed_amount is not None
            and self.total_amount is not None
            and self.borrowed_amount > self.total_amount
        ):
            raise ValueError("borrowed_amount cannot exceed total_amount")

        return self


class TransactionRead(APIModel):
    """Response model for transaction resources."""
    id: uuid.UUID
    fund_id: uuid.UUID
    lot_id: uuid.UUID | None
    date: dt_date
    type: TransactionType
    units: Decimal
    price_per_unit: Decimal
    total_amount: Decimal
    borrowed_amount: Decimal
    equity_amount: Decimal
