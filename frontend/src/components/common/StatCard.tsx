interface Props {
  title: string;
  value: string;
  sub?: string;
  highlight?: "positive" | "negative" | "neutral";
}

const highlightClass: Record<NonNullable<Props["highlight"]>, string> = {
  positive: "text-green-600",
  negative: "text-red-500",
  neutral: "text-gray-800",
};

export default function StatCard({
  title,
  value,
  sub,
  highlight = "neutral",
}: Props) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm px-4 py-4">
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">
        {title}
      </p>
      <p className={`text-xl font-bold mt-1 ${highlightClass[highlight]}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}
