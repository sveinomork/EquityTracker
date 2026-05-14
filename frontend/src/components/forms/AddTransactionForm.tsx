import { useForm } from "react-hook-form";
import { isAxiosError } from "axios";
import { useFundLots } from "../../hooks/useFundAnalytics";
import { useFunds } from "../../hooks/useFunds";
import { useCreateTransaction } from "../../hooks/useMutations";
import type { TransactionCreate } from "../../types/api";
import LoadingSpinner from "../common/LoadingSpinner";
import ErrorMessage from "../common/ErrorMessage";

type TransactionFormValues = Omit<TransactionCreate, "price_per_unit"> & {
  price_per_unit?: number;
};

function extractApiErrorMessage(error: unknown): string {
  if (!isAxiosError(error)) return "Noe gikk galt.";

  const payload = error.response?.data as
    | { detail?: string | Array<{ msg?: string }> }
    | undefined;
  const detail = payload?.detail;

  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const first = detail.find(
      (entry) => typeof entry?.msg === "string" && entry.msg.trim(),
    );
    if (first?.msg) return first.msg;
  }

  return error.message || "Noe gikk galt.";
}

export default function AddTransactionForm() {
  const { register, handleSubmit, reset, watch, formState } =
    useForm<TransactionFormValues>({
      defaultValues: {
        type: "BUY",
        units: 1,
        total_amount: 0,
        borrowed_amount: 0,
      },
    });
  const { mutate, isPending, isError, error } = useCreateTransaction();
  const { data: funds, isLoading: fundsLoading } = useFunds();
  const selectedFundId = watch("fund_id");
  const transactionType = watch("type");
  const isBuy = transactionType === "BUY";
  const requiresLot = transactionType === "DIVIDEND_REINVEST";
  const { data: fundLots } = useFundLots(selectedFundId || "");

  const onSubmit = (data: TransactionFormValues) => {
    const units = data.units || 1;
    const totalAmount = data.total_amount || 0;
    const pricePerUnit = units > 0 ? totalAmount / units : 0;
    const borrowedAmount =
      isBuy && Number.isFinite(data.borrowed_amount) ? data.borrowed_amount : 0;
    mutate(
      {
        ...data,
        borrowed_amount: borrowedAmount,
        price_per_unit: pricePerUnit,
      } as TransactionCreate,
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

      {requiresLot && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Posisjon (lot)
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            {...register("lot_id", {
              required: "Velg posisjon for utbytte",
            })}
          >
            <option value="">-- Velg posisjon --</option>
            {fundLots?.lots.map((lot) => (
              <option key={lot.lot_id} value={lot.lot_id}>
                {lot.purchase_date} - {lot.current_units.toFixed(4)} andeler
              </option>
            ))}
          </select>
          {formState.errors.lot_id && (
            <span className="text-red-500 text-xs mt-1">
              {formState.errors.lot_id.message}
            </span>
          )}
        </div>
      )}

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
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Total beløp (NOK)
        </label>
        <input
          type="number"
          step="0.01"
          placeholder="1000.00"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("total_amount", {
            required: "Total beløp er påkrevd",
            valueAsNumber: true,
          })}
        />
      </div>

      {isBuy && (
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
      )}

      {isError && <ErrorMessage message={extractApiErrorMessage(error)} />}

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
