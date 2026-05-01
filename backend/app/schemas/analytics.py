import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class CapitalSplit(APIModel):
    total_cost: Decimal
    total_equity: Decimal
    total_borrowed: Decimal


class LotCapitalSplit(APIModel):
    cost: Decimal
    equity: Decimal
    borrowed: Decimal


class ReturnMetrics(APIModel):
    return_on_total_assets_pct: Decimal | None = None
    return_on_equity_net_pct: Decimal | None = None
    annualized_return_on_equity_pct: Decimal | None = None


class BorrowingCosts(APIModel):
    monthly_current: Decimal
    annual_current: Decimal


class PerformanceWindows(APIModel):
    d14_pct: Decimal | None = Field(default=None, serialization_alias="14d_pct")
    d30_pct: Decimal | None = Field(default=None, serialization_alias="30d_pct")
    d90_pct: Decimal | None = Field(default=None, serialization_alias="90d_pct")
    d180_pct: Decimal | None = Field(default=None, serialization_alias="180d_pct")
    y1_pct: Decimal | None = Field(default=None, serialization_alias="1y_pct")


class FundSummary(APIModel):
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    as_of_date: date
    capital_split: CapitalSplit
    current_value: Decimal
    net_equity_value: Decimal
    total_dividend_reinvested: Decimal
    total_interest_paid: Decimal
    average_days_owned: Decimal
    profit_loss_gross: Decimal
    profit_loss_net: Decimal
    returns: ReturnMetrics
    borrowing_costs: BorrowingCosts
    performance_windows: PerformanceWindows


class LotSummary(APIModel):
    lot_id: uuid.UUID
    purchase_date: date
    days_owned: int
    original_units: Decimal
    current_units: Decimal
    capital_split: LotCapitalSplit
    current_value: Decimal
    allocated_interest_paid: Decimal
    profit_loss_net: Decimal
    returns: ReturnMetrics


class FundLotsSummary(APIModel):
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    lots: list[LotSummary]


class PortfolioTotals(APIModel):
    current_value: Decimal
    net_equity_value: Decimal
    total_interest_paid: Decimal
    total_equity: Decimal
    total_borrowed: Decimal
    profit_loss_net: Decimal


class PortfolioSummary(APIModel):
    as_of_date: date
    funds: list[FundSummary]
    totals: PortfolioTotals
