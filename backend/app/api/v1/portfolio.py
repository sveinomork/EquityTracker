from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import PortfolioAnalyticsServiceDependency
from app.schemas.analytics import PortfolioSummary

AsOfDateQuery = Annotated[date | None, Query()]

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
def get_portfolio_summary(
    service: PortfolioAnalyticsServiceDependency,
    as_of_date: AsOfDateQuery = None,
) -> PortfolioSummary:
    return service.get_portfolio_summary(as_of_date)
