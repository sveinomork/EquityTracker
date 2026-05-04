import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../api/transactions";

export const TRANSACTIONS_KEY = (fundId?: string) =>
  ["transactions", fundId ?? "all"] as const;

export function useTransactions(fundId?: string) {
  return useQuery({
    queryKey: TRANSACTIONS_KEY(fundId),
    queryFn: () => fetchTransactions(fundId ? { fund_id: fundId } : undefined),
  });
}
