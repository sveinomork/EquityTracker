import uuid

from fastapi import APIRouter, status

from app.api.dependencies import MarketDataServiceDependency
from app.schemas.price import DailyFundPriceBatchCreate, DailyFundPriceRead

router = APIRouter(prefix="/funds/{fund_id}/prices", tags=["prices"])


@router.post("", response_model=list[DailyFundPriceRead], status_code=status.HTTP_201_CREATED)
def add_prices(
    fund_id: uuid.UUID,
    payload: DailyFundPriceBatchCreate,
    service: MarketDataServiceDependency,
) -> list[DailyFundPriceRead]:
    return [
        DailyFundPriceRead.model_validate(price) for price in service.add_prices(fund_id, payload)
    ]
