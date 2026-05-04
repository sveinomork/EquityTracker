import { useQuery } from "@tanstack/react-query";
import { fetchPortfolioSummary } from "../api/analytics";

export const PORTFOLIO_SUMMARY_KEY = (asOfDate?: string) =>
  ["portfolio", "summary", asOfDate ?? "today"] as const;

export function usePortfolioSummary(asOfDate?: string) {
  return useQuery({
    queryKey: PORTFOLIO_SUMMARY_KEY(asOfDate),
    queryFn: () => fetchPortfolioSummary(asOfDate),
  });
}
