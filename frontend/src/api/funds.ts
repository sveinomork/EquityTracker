import client from "./client";
import type { Fund, FundCreate, FundTaxConfigUpdate } from "../types/api";

export const fetchFunds = (): Promise<Fund[]> =>
  client.get<Fund[]>("/funds").then((r) => r.data);

export const createFund = (payload: FundCreate): Promise<Fund> =>
  client.post<Fund>("/funds", payload).then((r) => r.data);

export const updateFundTaxConfig = (
  fundId: string,
  payload: FundTaxConfigUpdate,
): Promise<Fund> =>
  client
    .patch<Fund>(`/funds/${fundId}/tax-config`, payload)
    .then((r) => r.data);
