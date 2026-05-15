import { useQuery } from "@tanstack/react-query";
import { fetchPeriodReport, fetchReportPeriodOptions } from "../api/analytics";
import type { ReportPeriodType } from "../types/api";

export const REPORT_OPTIONS_KEY = (
  periodType: ReportPeriodType,
  asOfDate?: string,
) => ["reports", "period-options", periodType, asOfDate ?? "latest"] as const;

export const REPORT_PERIOD_KEY = (
  periodType: ReportPeriodType,
  periodValue?: string,
) => ["reports", "period", periodType, periodValue ?? ""] as const;

export function useReportPeriodOptions(
  periodType: ReportPeriodType,
  asOfDate?: string,
) {
  return useQuery({
    queryKey: REPORT_OPTIONS_KEY(periodType, asOfDate),
    queryFn: () => fetchReportPeriodOptions(periodType, asOfDate),
  });
}

export function usePeriodReport(
  periodType: ReportPeriodType,
  periodValue?: string,
) {
  return useQuery({
    queryKey: REPORT_PERIOD_KEY(periodType, periodValue),
    queryFn: () => fetchPeriodReport(periodType, periodValue as string),
    enabled: !!periodValue,
  });
}
