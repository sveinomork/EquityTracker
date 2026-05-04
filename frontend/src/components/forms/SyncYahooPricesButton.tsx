import { useSyncYahoo } from "../../hooks/useMutations";
import ErrorMessage from "../common/ErrorMessage";

export default function SyncYahooPricesButton() {
  const { mutate, isPending, isError, error, data } = useSyncYahoo();

  const handleSync = () => {
    if (
      confirm(
        "Henter priser fra Yahoo Finance for FHY, HHR, KNB, KHD. Fortsett?",
      )
    ) {
      mutate(undefined);
    }
  };

  return (
    <div className="space-y-3">
      <button
        onClick={handleSync}
        disabled={isPending}
        className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
      >
        {isPending ? (
          <>
            <span className="animate-spin">⏳</span> Synkroniserer...
          </>
        ) : (
          <>🔄 Synk fra Yahoo Finance</>
        )}
      </button>

      {isError && <ErrorMessage message={String(error?.message)} />}

      {data && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <p className="text-sm font-medium text-green-900 mb-2">Resultat:</p>
          <ul className="text-xs text-green-700 space-y-1">
            {data.map((r) => (
              <li key={r.ticker}>
                {r.ticker}:{" "}
                {r.error ? `❌ ${r.error}` : `✅ ${r.upserted} rader`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
