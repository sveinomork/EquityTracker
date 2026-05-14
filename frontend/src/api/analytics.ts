import client from "./client";
import type {
  FundLotsSummary,
  FundPeriodReconciliation,
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
