import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class DailyFundPriceCreate(APIModel):
    date: date
    price: Decimal = Field(gt=0)


class DailyFundPriceBatchCreate(APIModel):
    items: list[DailyFundPriceCreate]


class DailyFundPriceRead(APIModel):
    id: uuid.UUID
    fund_id: uuid.UUID
    date: date
    price: Decimal
