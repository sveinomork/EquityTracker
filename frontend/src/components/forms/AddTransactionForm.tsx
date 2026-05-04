import { useForm } from "react-hook-form";
import { useFunds } from "../../hooks/useFunds";
import { useCreateTransaction } from "../../hooks/useMutations";
import type { TransactionCreate } from "../../types/api";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";

export default function AddTransactionForm() {
  const { register, handleSubmit, reset, watch, formState } =
    useForm<TransactionCreate>({
      defaultValues: { type: "BUY", units: 1, borrowed_amount: 0 },
    });
  const { mutate, isPending, isError, error } = useCreateTransaction();
  const { data: funds, isLoading: fundsLoading } = useFunds();

  const totalAmount = watch("units") * watch("price_per_unit");

  const onSubmit = (data: TransactionCreate) => {
    mutate(
      { ...data, total_amount: totalAmount },
      {
        onSuccess: () => {
          reset();
          alert("✅ Transaksjon opprettet!");
        },
      },
    );
  };

  if (fundsLoading) return <LoadingSpinner label="Laster fond..." />;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
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
        {formState.errors.fund_id && (
          <span className="text-red-500 text-xs mt-1">
            {formState.errors.fund_id.message}
          </span>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Type
        </label>
        <select
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("type")}
        >
          <option value="BUY">Kjøp</option>
          <option value="SELL">Salg</option>
          <option value="DIVIDEND_REINVEST">Utbytte</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Dato
        </label>
        <input
          type="date"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("date", { required: "Dato er påkrevd" })}
        />
        {formState.errors.date && (
          <span className="text-red-500 text-xs mt-1">
            {formState.errors.date.message}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Andeler
          </label>
          <input
            type="number"
            step="0.0001"
            placeholder="1.00"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            {...register("units", {
              required: "Andeler er påkrevd",
              valueAsNumber: true,
            })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Pris per andel
          </label>
          <input
            type="number"
            step="0.01"
            placeholder="100.00"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            {...register("price_per_unit", {
              required: "Pris er påkrevd",
              valueAsNumber: true,
            })}
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Total beløp (NOK)
        </label>
        <input
          type="number"
          readOnly
          value={totalAmount.toFixed(2)}
          className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-lg text-gray-600"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Lånt beløp (NOK)
        </label>
        <input
          type="number"
          step="0.01"
          placeholder="0.00"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("borrowed_amount", { valueAsNumber: true })}
        />
      </div>

      {isError && <ErrorMessage message={String(error?.message)} />}

      <button
        type="submit"
        disabled={isPending}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
      >
        {isPending ? (
          <>
            <span className="animate-spin">⏳</span> Lagrer...
          </>
        ) : (
          "✅ Opprett transaksjon"
        )}
      </button>
    </form>
  );
}
