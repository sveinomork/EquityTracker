import client from "./client";
import type { LoanRate, LoanRateCreate } from "../types/api";

export const fetchRates = (fundId: string): Promise<LoanRate[]> =>
  client.get<LoanRate[]>(`/funds/${fundId}/rates`).then((r) => r.data);

export const addRates = (
  fundId: string,
  items: LoanRateCreate[],
): Promise<LoanRate[]> =>
  client
    .post<LoanRate[]>(`/funds/${fundId}/rates`, { items })
    .then((r) => r.data);
