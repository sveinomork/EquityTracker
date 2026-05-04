import { useForm } from "react-hook-form";
import { useCreateFund } from "../../hooks/useFunds";
import type { FundCreate } from "../../types/api";

import ErrorMessage from "../common/ErrorMessage";

export default function AddFundForm() {
  const { register, handleSubmit, reset, formState } = useForm<FundCreate>();
  const { mutate, isPending, isError, error } = useCreateFund();

  const onSubmit = (data: FundCreate) => {
    mutate(data, {
      onSuccess: () => {
        reset();
        alert("✅ Fond opprettet!");
      },
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Navn
        </label>
        <input
          type="text"
          placeholder="f.eks. Heimdal Høyrente Plus"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("name", { required: "Navn er påkrevd" })}
        />
        {formState.errors.name && (
          <span className="text-red-500 text-xs mt-1">
            {formState.errors.name.message}
          </span>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Ticker
        </label>
        <input
          type="text"
          placeholder="f.eks. HHRP"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          {...register("ticker", { required: "Ticker er påkrevd" })}
        />
        {formState.errors.ticker && (
          <span className="text-red-500 text-xs mt-1">
            {formState.errors.ticker.message}
          </span>
        )}
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
          "➕ Opprett fond"
        )}
      </button>
    </form>
  );
}
