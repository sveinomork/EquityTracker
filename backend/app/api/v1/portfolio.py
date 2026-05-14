from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import PortfolioAnalyticsServiceDependency
from app.schemas.analytics import FundPeriodReconciliation, PortfolioHistoryPoint, PortfolioSummary

AsOfDateQuery = Annotated[date | None, Query()]

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/summary", response_model=PortfolioSummary)
def get_portfolio_summary(
    service: PortfolioAnalyticsServiceDependency,
    as_of_date: AsOfDateQuery = None,
) -> PortfolioSummary:
    """Return portfolio-level totals and period metrics."""
    return service.get_portfolio_summary(as_of_date)


@router.get("/history", response_model=list[PortfolioHistoryPoint])
def get_portfolio_history(
    service: PortfolioAnalyticsServiceDependency,
    as_of_date: AsOfDateQuery = None,
) -> list[PortfolioHistoryPoint]:
    """Return portfolio history points for all trading days up to a date."""
    return service.get_portfolio_history(as_of_date)


@router.get("/reconciliation/fund-period", response_model=FundPeriodReconciliation)
def get_fund_period_reconciliation(
    service: PortfolioAnalyticsServiceDependency,
    ticker: str = "FHY",
    as_of_date: AsOfDateQuery = None,
) -> FundPeriodReconciliation:
    """Return period reconciliation metrics for a single fund."""
    return service.get_fund_period_reconciliation(ticker=ticker, as_of_date=as_of_date)
