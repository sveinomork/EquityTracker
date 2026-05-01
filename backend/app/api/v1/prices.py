import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import MarketDataServiceDependency
from app.schemas.price import DailyFundPriceBatchCreate, DailyFundPriceRead

router = APIRouter(prefix="/funds/{fund_id}/prices", tags=["prices"])

FromDateQuery = Annotated[date | None, Query()]
ToDateQuery = Annotated[date | None, Query()]
LimitQuery = Annotated[int | None, Query(ge=1, le=5000)]


@router.post("", response_model=list[DailyFundPriceRead], status_code=status.HTTP_201_CREATED)
def add_prices(
    fund_id: uuid.UUID,
    payload: DailyFundPriceBatchCreate,
    service: MarketDataServiceDependency,
) -> list[DailyFundPriceRead]:
    return [
        DailyFundPriceRead.model_validate(price) for price in service.add_prices(fund_id, payload)
    ]


@router.get("", response_model=list[DailyFundPriceRead])
def list_prices(
    fund_id: uuid.UUID,
    service: MarketDataServiceDependency,
    from_date: FromDateQuery = None,
    to_date: ToDateQuery = None,
    limit: LimitQuery = None,
) -> list[DailyFundPriceRead]:
    prices = service.list_prices(fund_id, from_date=from_date, to_date=to_date, limit=limit)
    return [DailyFundPriceRead.model_validate(price) for price in prices]
