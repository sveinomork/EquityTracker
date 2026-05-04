import client from "./client";
import type { SyncResult } from "../types/api";

export const syncYahooPrices = (startDate?: string): Promise<SyncResult[]> =>
  client
    .post<SyncResult[]>("/sync/yahoo", null, {
      params: startDate ? { start_date: startDate } : undefined,
    })
    .then((r) => r.data);
