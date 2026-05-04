import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { addRates, fetchRates } from "../api/rates";
import type { LoanRateCreate } from "../types/api";

export const FUND_RATES_KEY = (fundId: string) =>
  ["fund", fundId, "rates"] as const;

export function useFundRates(fundId: string) {
  return useQuery({
    queryKey: FUND_RATES_KEY(fundId),
    queryFn: () => fetchRates(fundId),
    enabled: !!fundId,
  });
}

export function useAddRates(fundId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: LoanRateCreate[]) => addRates(fundId, items),
    onSuccess: () => qc.invalidateQueries({ queryKey: FUND_RATES_KEY(fundId) }),
  });
}
