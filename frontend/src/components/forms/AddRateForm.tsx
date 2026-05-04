import { useState } from "react";
import { useForm } from "react-hook-form";
import { useFunds } from "../../hooks/useFunds";
import { useAddRates } from "../../hooks/useFundRates";
import type { LoanRateCreate } from "../../types/api";
import LoadingSpinner from "../common/LoadingSpinner";

export default function AddRateForm() {
  const { register, handleSubmit, reset, watch } = useForm<{
    fund_id: string;
    effective_date: string;
    nominal_rate: number;
  }>();
  const { data: funds, isLoading: fundsLoading } = useFunds();
  const [entries, setEntries] = useState<LoanRateCreate[]>([]);
  const fundId = watch("fund_id");
  const { mutate: addRates, isPending } = useAddRates(fundId);

  const fundName = funds?.find((f) => f.id === fundId)?.ticker;

  const onAdd = (data: { effective_date: string; nominal_rate: number }) => {
    setEntries([
      ...entries,
      {
        effective_date: data.effective_date,
        nominal_rate: data.nominal_rate,
      },
    ]);
    reset((prev) => ({ ...prev, effective_date: "", nominal_rate: 0 }));
  };

  const onSubmit = () => {
    if (!entries.length) {
      alert("Legg til minst en rente.");
      return;
    }
    addRates(entries, {
      onSuccess: () => {
        setEntries([]);
        alert("✅ Renter lagret!");
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
                Gjeldig fra
              </label>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                {...register("effective_date", { required: true })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Rente (%)
              </label>
              <input
                type="number"
                step="0.01"
                placeholder="4.48"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                {...register("nominal_rate", {
                  required: true,
                  valueAsNumber: true,
                })}
              />
            </div>
          </div>
          <button
            type="submit"
            className="px-3 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 text-sm"
          >
            + Legg til rente
          </button>
        </form>
      )}

      {entries.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm font-medium text-blue-900 mb-2">
            {fundName} – {entries.length} rente{entries.length !== 1 ? "r" : ""}
          </p>
          <ul className="space-y-1">
            {entries.map((e, i) => (
              <li key={i} className="text-sm text-blue-700">
                Fra {e.effective_date}: {Number(e.nominal_rate).toFixed(2)}%
              </li>
            ))}
          </ul>
          <button
            onClick={onSubmit}
            disabled={isPending}
            className="mt-3 w-full px-3 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 text-sm"
          >
            {isPending ? "Lagrer..." : "💾 Lagre alle renter"}
          </button>
        </div>
      )}
    </div>
  );
}
