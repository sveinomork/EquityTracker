import { useState } from "react";
import { useForm } from "react-hook-form";
import { useFunds } from "../../hooks/useFunds";
import { useAddPrices } from "../../hooks/useMutations";
import type { DailyPriceCreate } from "../../types/api";
import LoadingSpinner from "../common/LoadingSpinner";

export default function ManualPriceEntryForm() {
  const { register, handleSubmit, reset, watch } = useForm<{
    fund_id: string;
    date: string;
    price: number;
  }>();
  const { data: funds, isLoading: fundsLoading } = useFunds();
  const [entries, setEntries] = useState<DailyPriceCreate[]>([]);
  const fundId = watch("fund_id");
  const { mutate: addPrices, isPending } = useAddPrices(fundId);

  const fundName = funds?.find((f) => f.id === fundId)?.ticker;

  const onAdd = (data: { date: string; price: number }) => {
    setEntries([...entries, { date: data.date, price: data.price }]);
    reset((prev) => ({ ...prev, date: "", price: 0 }));
  };

  const onSubmit = () => {
    if (!entries.length) {
      alert("Legg til minst en pris.");
      return;
    }
    addPrices(entries, {
      onSuccess: () => {
        setEntries([]);
        alert("✅ Priser lagret!");
      },
    });
  };

  if (fundsLoading) return <LoadingSpinner label="Laster fond..." />;

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Fond
        </label>
        <select
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("fund_id", { required: "Velg fond" })}
        >
          <option value="">-- Velg fond --</option>
          {funds?.map((f) => (
            <option key={f.id} value={f.id}>
              {f.ticker} – {f.name}
            </option>
          ))}
        </select>
      </div>

      {fundId && (
        <form
          onSubmit={handleSubmit(onAdd)}
          className="border-t pt-4 mt-4 space-y-3"
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Dato
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                {...register("date", { required: true })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Kurs
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="100.00"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                {...register("price", { required: true, valueAsNumber: true })}
              />
            </div>
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 text-sm"
          >
            + Legg til pris
          </button>
        </form>
      )}

      {entries.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm font-medium text-blue-900 mb-2">
            {fundName} – {entries.length} pris{entries.length !== 1 ? "er" : ""}
          </p>
          <ul className="space-y-1">
            {entries.map((e, i) => (
              <li key={i} className="text-sm text-blue-700">
                {e.date}: {Number(e.price).toFixed(2)} kr
              </li>
            ))}
          </ul>
          <button
            onClick={onSubmit}
            disabled={isPending}
            className="mt-3 w-full px-3 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {isPending ? "Lagrer..." : "💾 Lagre all priser"}
          </button>
        </div>
      )}
    </div>
  );
}
