import client from "./client";
import type {
  FundLotsSummary,
  FundPeriodReconciliation,
  PortfolioPeriodReport,
  ReportPeriodOptions,
  ReportPeriodType,
  FundSummary,
  PortfolioHistoryPoint,
  PortfolioSummary,
} from "../types/api";

export const fetchPortfolioSummary = (
  asOfDate?: string,
): Promise<PortfolioSummary> =>
  client
    .get<PortfolioSummary>("/portfolio/summary", {
      params: asOfDate ? { as_of_date: asOfDate } : undefined,
    })
    .then((r) => r.data);

export const fetchPortfolioHistory = (
  asOfDate?: string,
): Promise<PortfolioHistoryPoint[]> =>
  client
    .get<PortfolioHistoryPoint[]>("/portfolio/history", {
      params: asOfDate ? { as_of_date: asOfDate } : undefined,
    })
    .then((r) => r.data);

export const fetchFundSummary = (
  fundId: string,
  asOfDate?: string,
): Promise<FundSummary> =>
  client
    .get<FundSummary>(`/funds/${fundId}/summary`, {
      params: asOfDate ? { as_of_date: asOfDate } : undefined,
    })
    .then((r) => r.data);

export const fetchFundLots = (fundId: string): Promise<FundLotsSummary> =>
  client.get<FundLotsSummary>(`/funds/${fundId}/lots`).then((r) => r.data);

export const fetchFundPeriodReconciliation = (
  ticker = "FHY",
  asOfDate?: string,
): Promise<FundPeriodReconciliation> =>
  client
    .get<FundPeriodReconciliation>("/portfolio/reconciliation/fund-period", {
      params: {
        ticker,
        ...(asOfDate ? { as_of_date: asOfDate } : {}),
      },
    })
    .then((r) => r.data);

export const fetchReportPeriodOptions = (
  periodType: ReportPeriodType,
  asOfDate?: string,
): Promise<ReportPeriodOptions> =>
  client
    .get<ReportPeriodOptions>("/reports/period-options", {
      params: {
        period_type: periodType,
        ...(asOfDate ? { as_of_date: asOfDate } : {}),
      },
    })
    .then((r) => r.data);

export const fetchPeriodReport = (
  periodType: ReportPeriodType,
  periodValue: string,
): Promise<PortfolioPeriodReport> =>
  client
    .get<PortfolioPeriodReport>("/reports/period", {
      params: {
        period_type: periodType,
        period_value: periodValue,
      },
    })
    .then((r) => r.data);
