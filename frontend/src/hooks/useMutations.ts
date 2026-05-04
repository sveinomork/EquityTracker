import { useMutation, useQueryClient } from "@tanstack/react-query";
import { addPrices } from "../api/prices";
import { createTransaction } from "../api/transactions";
import { syncYahooPrices } from "../api/sync";
import type { DailyPriceCreate, TransactionCreate } from "../types/api";
import { FUNDS_KEY } from "./useFunds";

export function useCreateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: TransactionCreate) => createTransaction(payload),
    onSuccess: (_data, variables) => {
      // Invalidate fund summary and portfolio so they refresh
      qc.invalidateQueries({ queryKey: ["fund", variables.fund_id] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}

export function useAddPrices(fundId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (items: DailyPriceCreate[]) => addPrices(fundId, items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fund", fundId, "prices"] });
    },
  });
}

export function useSyncYahoo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (startDate: string | undefined = undefined) =>
      syncYahooPrices(startDate),
    onSuccess: () => {
      // Prices changed for multiple funds — invalidate all price queries
      qc.invalidateQueries({ queryKey: ["fund"] });
      qc.invalidateQueries({ queryKey: ["portfolio"] });
      qc.invalidateQueries({ queryKey: FUNDS_KEY });
    },
  });
}
