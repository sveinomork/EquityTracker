import type { PeriodMetricsByWindow } from "../../types/api";
import PnlBadge from "../common/PnlBadge";

interface Props {
  periodMetrics: PeriodMetricsByWindow;
}

const WINDOW_LABELS: { key: keyof PeriodMetricsByWindow; label: string }[] = [
  { key: "1d", label: "1 dag" },
  { key: "7d", label: "7 dager" },
  { key: "14d", label: "14 dager" },
  { key: "90d", label: "90 dager" },
  { key: "Total", label: "Total" },
];

export default function PerformanceBars({ periodMetrics }: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Avkastning per periode
      </h3>
      <div className="space-y-2">
        {WINDOW_LABELS.map(({ key, label }) => {
          const value = periodMetrics[key]?.return_split?.gross_pct ?? null;
          const barWidth =
            value == null ? 0 : Math.min(Math.abs(value) * 4, 100);
          const positive = value == null || value >= 0;
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-xs text-gray-500 w-20 shrink-0">
                {label}
              </span>
              <div className="flex-1 h-4 bg-gray-100 rounded overflow-hidden">
                <div
                  className={`h-full rounded transition-all ${positive ? "bg-green-400" : "bg-red-400"}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <span className="w-20 text-right">
                <PnlBadge value={value} />
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
