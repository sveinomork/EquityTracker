import { useQuery } from "@tanstack/react-query";
import { subDays, format } from "../utils/dates";
import { fetchPrices } from "../api/prices";
import type { PricePeriod } from "../types/api";

export const FUND_PRICES_KEY = (fundId: string, period: PricePeriod) =>
  ["fund", fundId, "prices", period] as const;

function periodToParams(period: PricePeriod): {
  from_date?: string;
  limit?: number;
} {
  const today = new Date();
  if (period === "total") return { limit: 1500 };
  const days: Record<Exclude<PricePeriod, "total">, number> = {
    "1d": 1,
    "7d": 7,
    "14d": 14,
    "90d": 90,
  };
  return { from_date: format(subDays(today, days[period])) };
}

export function useFundPrices(fundId: string, period: PricePeriod) {
  const params = periodToParams(period);
  return useQuery({
    queryKey: FUND_PRICES_KEY(fundId, period),
    queryFn: () => fetchPrices(fundId, params),
    enabled: !!fundId,
  });
}
