// ─── Domain types matching backend schemas ───────────────────────────────────

export interface Fund {
  id: string;
  name: string;
  ticker: string;
  is_distributing: boolean;
  manual_taxable_gain_override: number | null;
}

export interface FundCreate {
  name: string;
  ticker: string;
  is_distributing?: boolean;
  manual_taxable_gain_override?: number | null;
}

export interface FundTaxConfigUpdate {
  is_distributing?: boolean;
  manual_taxable_gain_override?: number | null;
}

export type TransactionType = "BUY" | "SELL" | "DIVIDEND_REINVEST";

export interface TransactionCreate {
  fund_id: string;
  lot_id?: string;
  date: string; // ISO date
  type: TransactionType;
  units: number;
  price_per_unit: number;
  total_amount: number;
  borrowed_amount: number;
}

export interface Transaction {
  id: string;
  fund_id: string;
  lot_id: string | null;
  date: string;
  type: TransactionType;
  units: number;
  price_per_unit: number;
  total_amount: number;
  borrowed_amount: number;
  equity_amount: number;
}

export interface DailyPriceCreate {
  date: string;
  price: number;
}

export interface DailyPrice {
  id: string;
  fund_id: string;
  date: string;
  price: number;
}

export interface LoanRateCreate {
  effective_date: string;
  nominal_rate: number;
}

export interface LoanRate {
  id: string;
  fund_id: string;
  effective_date: string;
  nominal_rate: number;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface CapitalSplit {
  total_cost: number;
  total_equity: number;
  total_borrowed: number;
}

export interface ReturnMetrics {
  return_on_total_assets_pct: number | null;
  return_on_equity_net_pct: number | null;
  annualized_return_on_equity_pct: number | null;
  annualized_return_on_cost_weighted_pct: number | null;
}

export interface ReturnSplitMetrics {
  gross_amount_nok: number;
  gross_pct: number | null;
  gross_annualized_pct: number | null;
  after_interest_amount_nok: number;
  after_interest_pct: number | null;
  after_interest_annualized_pct: number | null;
}

export interface PeriodMetrics {
  start_date: string;
  end_date: string;
  days: number;
  period_capital_base_nok: number;
  return_pct_fund: number | null;
  brutto_value_change_nok: number;
  allocated_interest_cost_nok: number;
  interest_tax_credit_nok: number;
  running_dividend_tax_nok: number;
  net_liquidity_margin_nok: number;
  net_value_margin_nok: number;
  return_split: ReturnSplitMetrics;
}

export interface PeriodMetricsByWindow {
  "1d": PeriodMetrics;
  "7d": PeriodMetrics;
  "30d": PeriodMetrics;
  "180d": PeriodMetrics;
  YTD: PeriodMetrics;
  "12m": PeriodMetrics;
  "24m": PeriodMetrics;
  Total: PeriodMetrics;
}

export interface FundPeriodReconciliationRow {
  period_key: string;
  start_date: string;
  end_date: string;
  days: number;
  regime: string;
  units_t0: number;
  units_t1: number;
  start_price: number;
  end_price: number;
  value_t0: number;
  value_t1: number;
  net_external_cashflow_nok: number;
  period_capital_base_nok: number;
  gross_value_change_nok: number;
  dividends_in_period_nok: number;
  running_dividend_tax_nok: number;
  allocated_interest_cost_nok: number;
  interest_tax_credit_nok: number;
  net_liquidity_margin_nok: number;
  net_value_margin_nok: number;
  return_pct_fund: number | null;
}

export interface FundPeriodReconciliation {
  fund_id: string;
  fund_name: string;
  ticker: string;
  as_of_date: string;
  rows: FundPeriodReconciliationRow[];
}

export interface TaxSummary {
  regime: string;
  taxable_gain_base_nok: number;
  deferred_tax_nok: number;
  paid_dividend_tax_nok: number;
  interest_tax_credit_nok: number;
}

export interface TrueNetWorthBreakdown {
  total_invested_capital: number;
  total_market_value: number;
  total_allocated_debt: number;
  total_unrealized_gain_before_tax: number;
  total_accumulated_interest_cost: number;
  total_tax_credit_received: number;
  total_deferred_tax_accumulating: number;
  total_paid_tax_distributing: number;
  true_net_worth_nok: number;
}

export interface BorrowingCosts {
  monthly_current: number;
  annual_current: number;
}

export interface PerformanceWindows {
  "14d_pct": number | null;
  "30d_pct": number | null;
  "90d_pct": number | null;
  "180d_pct": number | null;
  "1y_pct": number | null;
}

export interface FundSummary {
  fund_id: string;
  fund_name: string;
  ticker: string;
  as_of_date: string;
  capital_split: CapitalSplit;
  current_value: number;
  net_equity_value: number;
  total_dividend_reinvested: number;
  total_interest_paid: number;
  average_days_owned: number;
  profit_loss_gross: number;
  profit_loss_net: number;
  returns: ReturnMetrics;
  borrowing_costs: BorrowingCosts;
  performance_windows: PerformanceWindows;
  period_metrics: PeriodMetricsByWindow;
  total_return: ReturnSplitMetrics;
  tax_summary: TaxSummary;
  true_net_worth: TrueNetWorthBreakdown;
}

export interface LotCapitalSplit {
  cost: number;
  equity: number;
  borrowed: number;
}

export interface LotSummary {
  lot_id: string;
  purchase_date: string;
  days_owned: number;
  original_units: number;
  current_units: number;
  purchase_price_per_unit: number;
  capital_split: LotCapitalSplit;
  current_value: number;
  allocated_interest_paid: number;
  profit_loss_net: number;
  returns: ReturnMetrics;
  period_metrics: PeriodMetricsByWindow;
}

export interface FundLotsSummary {
  fund_id: string;
  fund_name: string;
  ticker: string;
  market_price_per_unit: number;
  market_price_date: string | null;
  lots: LotSummary[];
}

export interface PortfolioTotals {
  total_cost: number;
  total_market_value: number;
  current_value: number;
  net_equity_value: number;
  total_interest_paid: number;
  total_equity: number;
  total_borrowed: number;
  profit_loss_net: number;
  total_return: ReturnSplitMetrics;
  true_net_worth_nok: number;
  true_net_worth: TrueNetWorthBreakdown;
}

export interface PortfolioSummary {
  as_of_date: string;
  funds: FundSummary[];
  totals: PortfolioTotals;
  period_metrics: PeriodMetricsByWindow;
}

// ─── Sync ─────────────────────────────────────────────────────────────────────

export interface SyncResult {
  ticker: string;
  upserted: number;
  error: string | null;
}

// ─── Price period selector ────────────────────────────────────────────────────

export type PricePeriod = "7d" | "14d" | "30d" | "90d" | "180d" | "1y" | "all";
