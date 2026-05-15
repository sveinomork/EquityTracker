from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import PortfolioAnalyticsServiceDependency
from app.schemas.reports import PortfolioPeriodReport, ReportPeriodOptions, ReportPeriodType

AsOfDateQuery = Annotated[date | None, Query()]

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/period", response_model=PortfolioPeriodReport)
def get_period_report(
    service: PortfolioAnalyticsServiceDependency,
    period_type: ReportPeriodType,
    period_value: str,
) -> PortfolioPeriodReport:
    """Return one report payload for monthly, quarterly, or yearly period selection."""
    return service.get_period_report(period_type=period_type, period_value=period_value)


@router.get("/period-options", response_model=ReportPeriodOptions)
def get_period_options(
    service: PortfolioAnalyticsServiceDependency,
    period_type: ReportPeriodType,
    as_of_date: AsOfDateQuery = None,
) -> ReportPeriodOptions:
    """Return available historical period values for one report period type."""
    return service.get_report_period_options(period_type=period_type, as_of_date=as_of_date)
