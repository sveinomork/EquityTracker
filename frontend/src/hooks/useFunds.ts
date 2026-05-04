import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFund, fetchFunds, updateFundTaxConfig } from "../api/funds";
import type { FundCreate, FundTaxConfigUpdate } from "../types/api";

export const FUNDS_KEY = ["funds"] as const;

export function useFunds() {
  return useQuery({ queryKey: FUNDS_KEY, queryFn: fetchFunds });
}

export function useCreateFund() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FundCreate) => createFund(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: FUNDS_KEY }),
  });
}

export function useUpdateFundTaxConfig(fundId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: FundTaxConfigUpdate) =>
      updateFundTaxConfig(fundId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: FUNDS_KEY });
      qc.invalidateQueries({ queryKey: ["fund", fundId] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}
