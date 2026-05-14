import uuid
from datetime import date
from decimal import Decimal

from pydantic import Field

from app.schemas.common import APIModel


class CapitalSplit(APIModel):
    """Total capital split between cost, equity, and borrowed amount."""
    total_cost: Decimal
    total_equity: Decimal
    total_borrowed: Decimal


class LotCapitalSplit(APIModel):
    """Capital split for a single lot."""
    cost: Decimal
    equity: Decimal
    borrowed: Decimal


class ReturnMetrics(APIModel):
    """High-level return percentages used in summaries."""
    return_on_total_assets_pct: Decimal | None = None
    return_on_equity_net_pct: Decimal | None = None
    annualized_return_on_equity_pct: Decimal | None = None
    annualized_return_on_cost_weighted_pct: Decimal | None = None


class ReturnSplitMetrics(APIModel):
    """Return amounts and percentages before and after interest costs."""
    gross_amount_nok: Decimal
    gross_pct: Decimal | None = None
    gross_annualized_pct: Decimal | None = None
    after_interest_amount_nok: Decimal
    after_interest_pct: Decimal | None = None
    after_interest_annualized_pct: Decimal | None = None


class PeriodMetrics(APIModel):
    """Detailed metric values for one analysis period."""
    start_date: date
    end_date: date
    days: int
    period_capital_base_nok: Decimal
    return_pct_fund: Decimal | None = None
    brutto_value_change_nok: Decimal
    allocated_interest_cost_nok: Decimal
    interest_tax_credit_nok: Decimal
    running_dividend_tax_nok: Decimal
    net_liquidity_margin_nok: Decimal
    net_value_margin_nok: Decimal
    return_split: ReturnSplitMetrics


class PeriodMetricsByWindow(APIModel):
    """Period metrics grouped by predefined time windows."""
    d1: PeriodMetrics = Field(serialization_alias="1d")
    d7: PeriodMetrics = Field(serialization_alias="7d")
    d30: PeriodMetrics = Field(serialization_alias="30d")
    d180: PeriodMetrics = Field(serialization_alias="180d")
    ytd: PeriodMetrics = Field(serialization_alias="YTD")
    m12: PeriodMetrics = Field(serialization_alias="12m")
    m24: PeriodMetrics = Field(serialization_alias="24m")
    total: PeriodMetrics = Field(serialization_alias="Total")


class FundPeriodReconciliationRow(APIModel):
    """One row in a fund period reconciliation table."""
    period_key: str
    start_date: date
    end_date: date
    days: int
    regime: str
    units_t0: Decimal
    units_t1: Decimal
    start_price: Decimal
    end_price: Decimal
    value_t0: Decimal
    value_t1: Decimal
    net_external_cashflow_nok: Decimal
    period_capital_base_nok: Decimal
    gross_value_change_nok: Decimal
    dividends_in_period_nok: Decimal
    running_dividend_tax_nok: Decimal
    allocated_interest_cost_nok: Decimal
    interest_tax_credit_nok: Decimal
    net_liquidity_margin_nok: Decimal
    net_value_margin_nok: Decimal
    return_pct_fund: Decimal | None = None


class FundPeriodReconciliation(APIModel):
    """Reconciliation payload for one fund across all windows."""
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    as_of_date: date
    rows: list[FundPeriodReconciliationRow]


class TaxSummary(APIModel):
    """Tax-related totals and regime details for a fund."""
    regime: str
    taxable_gain_base_nok: Decimal
    deferred_tax_nok: Decimal
    paid_dividend_tax_nok: Decimal
    interest_tax_credit_nok: Decimal


class TrueNetWorthBreakdown(APIModel):
    """Breakdown of true net worth components for a fund or portfolio."""
    total_invested_capital: Decimal
    total_market_value: Decimal
    total_allocated_debt: Decimal
    total_unrealized_gain_before_tax: Decimal
    total_accumulated_interest_cost: Decimal
    total_tax_credit_received: Decimal
    total_deferred_tax_accumulating: Decimal
    total_paid_tax_distributing: Decimal
    true_net_worth_nok: Decimal


class BorrowingCosts(APIModel):
    """Current monthly and annual borrowing cost estimates."""
    monthly_current: Decimal
    annual_current: Decimal


class PerformanceWindows(APIModel):
    """Price performance percentages for standard lookback windows."""
    d14_pct: Decimal | None = Field(default=None, serialization_alias="14d_pct")
    d30_pct: Decimal | None = Field(default=None, serialization_alias="30d_pct")
    d90_pct: Decimal | None = Field(default=None, serialization_alias="90d_pct")
    d180_pct: Decimal | None = Field(default=None, serialization_alias="180d_pct")
    y1_pct: Decimal | None = Field(default=None, serialization_alias="1y_pct")


class FundSummary(APIModel):
    """Complete analytics summary for one fund."""
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    as_of_date: date
    capital_split: CapitalSplit
    current_value: Decimal
    net_equity_value: Decimal
    total_dividend_reinvested: Decimal
    total_interest_paid: Decimal
    realized_profit_from_sold_positions: Decimal
    average_days_owned: Decimal
    profit_loss_gross: Decimal
    profit_loss_gross_including_realized: Decimal
    profit_loss_net: Decimal
    returns: ReturnMetrics
    borrowing_costs: BorrowingCosts
    performance_windows: PerformanceWindows
    period_metrics: PeriodMetricsByWindow
    total_return: ReturnSplitMetrics
    tax_summary: TaxSummary
    true_net_worth: TrueNetWorthBreakdown


class LotSummary(APIModel):
    """Analytics summary for one BUY lot."""
    lot_id: uuid.UUID
    purchase_date: date
    days_owned: int
    original_units: Decimal
    current_units: Decimal
    purchase_price_per_unit: Decimal
    capital_split: LotCapitalSplit
    current_value: Decimal
    allocated_interest_paid: Decimal
    profit_loss_net: Decimal
    returns: ReturnMetrics
    period_metrics: PeriodMetricsByWindow


class FundLotsSummary(APIModel):
    """Collection of lot summaries for one fund."""
    fund_id: uuid.UUID
    fund_name: str
    ticker: str
    market_price_per_unit: Decimal
    market_price_date: date | None
    lots: list[LotSummary]


class PortfolioTotals(APIModel):
    """Aggregated totals across all funds in the portfolio."""
    total_cost: Decimal
    total_market_value: Decimal
    current_value: Decimal
    net_equity_value: Decimal
    total_interest_paid: Decimal
    total_equity: Decimal
    total_borrowed: Decimal
    profit_loss_net: Decimal
    total_return: ReturnSplitMetrics
    true_net_worth_nok: Decimal
    true_net_worth: TrueNetWorthBreakdown


class PortfolioSummary(APIModel):
    """Portfolio-level summary with totals and period metrics."""
    as_of_date: date
    funds: list[FundSummary]
    totals: PortfolioTotals
    period_metrics: PeriodMetricsByWindow


class PortfolioHistoryPoint(APIModel):
    """One historical snapshot point for portfolio development over time."""
    date: date
    market_value: Decimal
    total_equity: Decimal
    total_borrowed: Decimal
    total_interest_paid: Decimal
    net_value: Decimal
