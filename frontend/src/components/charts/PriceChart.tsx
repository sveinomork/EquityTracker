import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useFundPrices } from "../../hooks/useFundPrices";
import type { PricePeriod } from "../../types/api";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";
import EmptyState from "../common/EmptyState";

const PERIODS: { label: string; value: PricePeriod }[] = [
  { label: "1d", value: "1d" },
  { label: "7d", value: "7d" },
  { label: "14d", value: "14d" },
  { label: "90d", value: "90d" },
  { label: "Total", value: "total" },
];

interface Props {
  fundId: string;
  fundName?: string;
}

export default function PriceChart({ fundId, fundName }: Props) {
  const [period, setPeriod] = useState<PricePeriod>("90d");
  const { data: prices, isLoading, isError } = useFundPrices(fundId, period);

  const chartData = (prices ?? []).map((p) => ({
    date: p.date,
    kurs: Number(p.price),
  }));

  const minPrice = chartData.length
    ? Math.min(...chartData.map((d) => d.kurs)) * 0.998
    : 0;
  const maxPrice = chartData.length
    ? Math.max(...chartData.map((d) => d.kurs)) * 1.002
    : 100;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700">
          {fundName ? `Kursutvikling – ${fundName}` : "Kursutvikling"}
        </h3>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={[
                "px-2 py-1 text-xs rounded font-medium transition-colors",
                period === p.value
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200",
              ].join(" ")}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <LoadingSpinner />}
      {isError && <ErrorMessage message="Kunne ikke laste kurser." />}
      {!isLoading && !isError && chartData.length === 0 && (
        <EmptyState message="Ingen kursdata for valgt periode." />
      )}
      {!isLoading && !isError && chartData.length > 0 && (
        <ResponsiveContainer width="100%" height={260}>
          <LineChart
            data={chartData}
            margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickFormatter={(v: string) => v.slice(5)} // MM-DD
              interval="preserveStartEnd"
            />
            <YAxis
              domain={[minPrice, maxPrice]}
              tick={{ fontSize: 11 }}
              tickFormatter={(v: number) => v.toFixed(2)}
              width={55}
            />
            <Tooltip
              formatter={(v: number) => [v.toFixed(4), "Kurs"]}
              labelFormatter={(l: string) => `Dato: ${l}`}
            />
            <Line
              type="monotone"
              dataKey="kurs"
              stroke="#2563eb"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
