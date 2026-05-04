import client from "./client";
import type { Transaction, TransactionCreate } from "../types/api";

export const createTransaction = (
  payload: TransactionCreate,
): Promise<Transaction> =>
  client.post<Transaction>("/transactions", payload).then((r) => r.data);
