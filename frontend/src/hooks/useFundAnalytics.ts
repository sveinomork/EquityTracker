import { useQuery } from "@tanstack/react-query";
import {
  fetchFundLots,
  fetchFundPeriodReconciliation,
  fetchFundSummary,
} from "../api/analytics";

export const FUND_SUMMARY_KEY = (fundId: string, asOfDate?: string) =>
  ["fund", fundId, "summary", asOfDate ?? "today"] as const;

export const FUND_LOTS_KEY = (fundId: string) =>
  ["fund", fundId, "lots"] as const;

export const FUND_PERIOD_RECONCILIATION_KEY = (
  ticker: string,
  asOfDate?: string,
) => ["fund", ticker, "period-reconciliation", asOfDate ?? "today"] as const;

export function useFundSummary(fundId: string, asOfDate?: string) {
  return useQuery({
    queryKey: FUND_SUMMARY_KEY(fundId, asOfDate),
    queryFn: () => fetchFundSummary(fundId, asOfDate),
    enabled: !!fundId,
  });
}

export function useFundLots(fundId: string) {
  return useQuery({
    queryKey: FUND_LOTS_KEY(fundId),
    queryFn: () => fetchFundLots(fundId),
    enabled: !!fundId,
  });
}

export function useFundPeriodReconciliation(ticker: string, asOfDate?: string) {
  return useQuery({
    queryKey: FUND_PERIOD_RECONCILIATION_KEY(ticker, asOfDate),
    queryFn: () => fetchFundPeriodReconciliation(ticker, asOfDate),
    enabled: !!ticker,
  });
}
