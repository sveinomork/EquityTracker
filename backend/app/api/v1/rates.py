import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import MarketDataServiceDependency
from app.schemas.rate import LoanRateBatchCreate, LoanRateRead

router = APIRouter(prefix="/funds/{fund_id}/rates", tags=["rates"])

FromDateQuery = Annotated[date | None, Query()]
ToDateQuery = Annotated[date | None, Query()]
LimitQuery = Annotated[int | None, Query(ge=1, le=5000)]


@router.post("", response_model=list[LoanRateRead], status_code=status.HTTP_201_CREATED)
def add_rates(
    fund_id: uuid.UUID,
    payload: LoanRateBatchCreate,
    service: MarketDataServiceDependency,
) -> list[LoanRateRead]:
    return [LoanRateRead.model_validate(rate) for rate in service.add_rates(fund_id, payload)]


@router.get("", response_model=list[LoanRateRead])
def list_rates(
    fund_id: uuid.UUID,
    service: MarketDataServiceDependency,
    from_date: FromDateQuery = None,
    to_date: ToDateQuery = None,
    limit: LimitQuery = None,
) -> list[LoanRateRead]:
    rates = service.list_rates(fund_id, from_date=from_date, to_date=to_date, limit=limit)
    return [LoanRateRead.model_validate(rate) for rate in rates]
