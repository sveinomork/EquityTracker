import { useQuery } from "@tanstack/react-query";
import { fetchPortfolioHistory } from "../api/analytics";

export const PORTFOLIO_HISTORY_KEY = (asOfDate?: string) =>
  ["portfolio", "history", asOfDate ?? "today"] as const;

export function usePortfolioHistory(asOfDate?: string) {
  return useQuery({
    queryKey: PORTFOLIO_HISTORY_KEY(asOfDate),
    queryFn: () => fetchPortfolioHistory(asOfDate),
  });
}
