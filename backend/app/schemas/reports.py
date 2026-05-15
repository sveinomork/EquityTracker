import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from app.schemas.analytics import FundSummary, PeriodMetricsByWindow, PortfolioTotals
from app.schemas.common import APIModel

ReportPeriodType = Literal["monthly", "quarterly", "yearly"]


class ReportPeriodOption(APIModel):
    """One selectable report period value and its resolved bounds."""
    value: str
    label: str
    start_date: date
    end_date: date


class ReportPeriodOptions(APIModel):
    """Available report period values within the portfolio data range."""
    period_type: ReportPeriodType
    data_start_date: date
    data_end_date: date
    options: list[ReportPeriodOption]


class PortfolioPeriodReportSummary(APIModel):
    """Portfolio-level metrics for one selected reporting period."""
    as_of_date: date
    totals: PortfolioTotals
    period_metrics: PeriodMetricsByWindow


class FundPeriodReportSummary(APIModel):
    """Fund-level report row including units and latest price date as of the report date."""
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    units: Decimal
    latest_price_date: date | None
    summary: FundSummary


class PortfolioPeriodReport(APIModel):
    """Combined report payload for portfolio totals and each individual fund."""
    period_type: ReportPeriodType
    period_value: str
    period_start: date
    period_end: date
    as_of_date: date
    data_start_date: date
    data_end_date: date
    portfolio: PortfolioPeriodReportSummary
    funds: list[FundPeriodReportSummary]
