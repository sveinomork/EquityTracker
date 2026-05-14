import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import FundServiceDependency, PortfolioAnalyticsServiceDependency
from app.schemas.analytics import FundLotsSummary, FundSummary
from app.schemas.fund import FundCreate, FundRead, FundTaxConfigUpdate

AsOfDateQuery = Annotated[date | None, Query()]

router = APIRouter(prefix="/funds", tags=["funds"])


@router.post("", response_model=FundRead, status_code=status.HTTP_201_CREATED)
def create_fund(payload: FundCreate, service: FundServiceDependency) -> FundRead:
    """Create a new fund from the provided payload."""
    return FundRead.model_validate(service.create_fund(payload))


@router.get("", response_model=list[FundRead])
def list_funds(service: FundServiceDependency) -> list[FundRead]:
    """Return all funds registered in the portfolio."""
    return [FundRead.model_validate(fund) for fund in service.list_funds()]


@router.patch("/{fund_id}/tax-config", response_model=FundRead)
def update_fund_tax_config(
    fund_id: uuid.UUID,
    payload: FundTaxConfigUpdate,
    service: FundServiceDependency,
) -> FundRead:
    """Update tax configuration fields for a single fund."""
    return FundRead.model_validate(service.update_tax_config(fund_id, payload))


@router.get("/{fund_id}/summary", response_model=FundSummary)
def get_fund_summary(
    fund_id: uuid.UUID,
    service: PortfolioAnalyticsServiceDependency,
    as_of_date: AsOfDateQuery = None,
) -> FundSummary:
    """Return summary metrics for a fund at a given date."""
    return service.get_fund_summary(fund_id, as_of_date)


@router.get("/{fund_id}/lots", response_model=FundLotsSummary)
def get_fund_lots(
    fund_id: uuid.UUID,
    service: PortfolioAnalyticsServiceDependency,
    as_of_date: AsOfDateQuery = None,
) -> FundLotsSummary:
    """Return lot-level position details for a fund."""
    return service.get_fund_lots_summary(fund_id, as_of_date)
