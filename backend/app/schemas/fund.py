import uuid
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class FundCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    ticker: str = Field(min_length=1, max_length=32)
    is_distributing: bool = False
    manual_taxable_gain_override: Decimal | None = Field(default=None, ge=0)


class FundTaxConfigUpdate(APIModel):
    is_distributing: bool | None = None
    manual_taxable_gain_override: Decimal | None = Field(default=None, ge=0)


class FundRead(APIModel):
    id: uuid.UUID
    name: str
    ticker: str
    is_distributing: bool
    manual_taxable_gain_override: Decimal | None
