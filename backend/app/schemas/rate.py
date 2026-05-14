import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class LoanRateCreate(APIModel):
    """Request model for one loan rate entry."""
    effective_date: date
    nominal_rate: Decimal = Field(gt=0)


class LoanRateBatchCreate(APIModel):
    """Request model for a batch of loan rate entries."""
    items: list[LoanRateCreate]


class LoanRateRead(APIModel):
    """Response model for stored loan rates."""
    id: uuid.UUID
    fund_id: uuid.UUID
    effective_date: date
    nominal_rate: Decimal
