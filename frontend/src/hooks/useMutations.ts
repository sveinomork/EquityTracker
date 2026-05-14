import { useMutation, useQueryClient } from "@tanstack/react-query";
import { addPrices } from "../api/prices";
import { createTransaction, updateTransaction } from "../api/transactions";
import { syncYahooPrices } from "../api/sync";
import type {
  DailyPriceCreate,
  Transaction,
  TransactionCreate,
  TransactionUpdate,
} from "../types/api";
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

export function useUpdateTransaction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { transactionId: string; payload: TransactionUpdate }) =>
      updateTransaction(args.transactionId, args.payload),
    onSuccess: (updated) => {
      qc.setQueriesData(
        { queryKey: ["transactions"] },
        (current: Transaction[] | unknown) => {
          if (!Array.isArray(current)) return current;
          return current.map((item) =>
            item.id === updated.id ? { ...item, ...updated } : item,
          );
        },
      );
      qc.invalidateQueries({ queryKey: ["transactions"] });
      qc.invalidateQueries({ queryKey: ["fund", updated.fund_id] });
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
