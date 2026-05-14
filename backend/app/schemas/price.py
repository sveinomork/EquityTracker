import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class DailyFundPriceCreate(APIModel):
    """Request model for one daily fund price entry."""
    date: date
    price: Decimal = Field(gt=0)


class DailyFundPriceBatchCreate(APIModel):
    """Request model for a batch of daily price entries."""
    items: list[DailyFundPriceCreate]


class DailyFundPriceRead(APIModel):
    """Response model for stored daily fund prices."""
    id: uuid.UUID
    fund_id: uuid.UUID
    date: date
    price: Decimal
