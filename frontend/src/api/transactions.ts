import client from "./client";
import type { Transaction, TransactionCreate } from "../types/api";

interface ListTransactionsParams {
  fund_id?: string;
}

export const createTransaction = (
  payload: TransactionCreate,
): Promise<Transaction> =>
  client.post<Transaction>("/transactions", payload).then((r) => r.data);

export const fetchTransactions = (
  params?: ListTransactionsParams,
): Promise<Transaction[]> =>
  client.get<Transaction[]>("/transactions", { params }).then((r) => r.data);
