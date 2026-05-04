import { pct } from "../../utils/dates";

interface Props {
  value: number | null | undefined;
  decimals?: number;
}

export default function PnlBadge({ value, decimals = 2 }: Props) {
  if (value == null) return <span className="text-gray-400 text-sm">N/A</span>;
  const positive = value >= 0;
  return (
    <span
      className={`inline-block text-sm font-semibold ${positive ? "text-green-600" : "text-red-500"}`}
    >
      {pct(value, decimals)}
    </span>
  );
}
