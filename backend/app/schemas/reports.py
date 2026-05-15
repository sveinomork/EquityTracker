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
    """Fund-level report row with start/end period values."""
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    # Period-start snapshot
    start_units: Decimal
    start_price: Decimal | None
    start_cost: Decimal  # total_cost at period start
    start_value: Decimal  # current_value at period start
    # Period-end snapshot
    end_units: Decimal
    end_price: Decimal | None
    end_cost: Decimal  # total_cost at period end
    end_value: Decimal  # current_value at period end
    # Latest price info for end-of-period
    latest_price_date: date | None
    # Full fund summary at period end
    summary: FundSummary


class PortfolioPeriodReport(APIModel):
    """Period report with start and end-of-period portfolio snapshots."""
    period_type: ReportPeriodType
    period_value: str
    period_start: date
    period_end: date
    data_start_date: date
    data_end_date: date
    portfolio_start: PortfolioPeriodReportSummary  # Portfolio state at period start
    portfolio_end: PortfolioPeriodReportSummary    # Portfolio state at period end
    funds: list[FundPeriodReportSummary]
