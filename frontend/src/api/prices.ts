import client from "./client";
import type { DailyPrice, DailyPriceCreate } from "../types/api";

interface ListPricesParams {
  from_date?: string;
  to_date?: string;
  limit?: number;
}

export const fetchPrices = (
  fundId: string,
  params?: ListPricesParams,
): Promise<DailyPrice[]> =>
  client
    .get<DailyPrice[]>(`/funds/${fundId}/prices`, { params })
    .then((r) => r.data);

export const addPrices = (
  fundId: string,
  items: DailyPriceCreate[],
): Promise<DailyPrice[]> =>
  client
    .post<DailyPrice[]>(`/funds/${fundId}/prices`, { items })
    .then((r) => r.data);
