import client from "./client";
import type {
  Transaction,
  TransactionCreate,
  TransactionUpdate,
} from "../types/api";

interface ListTransactionsParams {
  fund_id?: string;
}

export const createTransaction = (
  payload: TransactionCreate,
): Promise<Transaction> =>
  client.post<Transaction>("/transactions", payload).then((r) => r.data);

export const updateTransaction = (
  transactionId: string,
  payload: TransactionUpdate,
): Promise<Transaction> =>
  client
    .patch<Transaction>(`/transactions/${transactionId}`, payload)
    .then((r) => r.data);

export const fetchTransactions = (
  params?: ListTransactionsParams,
): Promise<Transaction[]> =>
  client.get<Transaction[]>("/transactions", { params }).then((r) => r.data);
