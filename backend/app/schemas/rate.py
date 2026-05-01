import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class LoanRateCreate(APIModel):
    effective_date: date
    nominal_rate: Decimal = Field(gt=0)


class LoanRateBatchCreate(APIModel):
    items: list[LoanRateCreate]


class LoanRateRead(APIModel):
    id: uuid.UUID
    fund_id: uuid.UUID
    effective_date: date
    nominal_rate: Decimal
