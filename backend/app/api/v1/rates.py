import uuid

from fastapi import APIRouter, status

from app.api.dependencies import MarketDataServiceDependency
from app.schemas.rate import LoanRateBatchCreate, LoanRateRead

router = APIRouter(prefix="/funds/{fund_id}/rates", tags=["rates"])


@router.post("", response_model=list[LoanRateRead], status_code=status.HTTP_201_CREATED)
def add_rates(
    fund_id: uuid.UUID,
    payload: LoanRateBatchCreate,
    service: MarketDataServiceDependency,
) -> list[LoanRateRead]:
    return [LoanRateRead.model_validate(rate) for rate in service.add_rates(fund_id, payload)]
