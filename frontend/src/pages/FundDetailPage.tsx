import { useParams, useNavigate } from "react-router-dom";
import { useFundLots, useFundSummary } from "../hooks/useFundAnalytics";
import StatCard from "../components/common/StatCard";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import SectionHeader from "../components/common/SectionHeader";
import PriceChart from "../components/charts/PriceChart";
import PerformanceBars from "../components/charts/PerformanceBars";
import PnlBadge from "../components/common/PnlBadge";
import { nok, pct } from "../utils/dates";

function ThWithTooltip({
  label,
  tip,
  className,
}: {
  label: string;
  tip: string;
  className?: string;
}) {
  return (
    <th className={className ?? "px-3 py-2 text-right"}>
      <span
        title={tip}
        className="cursor-help border-b border-dotted border-gray-400"
      >
        {label}
      </span>
    </th>
  );
}

export default function FundDetailPage() {
  const { fundId } = useParams<{ fundId: string }>();
  const safeFundId = fundId ?? "";
  const navigate = useNavigate();

  const {
    data: summary,
    isLoading: sumLoading,
    isError: sumError,
  } = useFundSummary(safeFundId);
  const { data: lotsData, isLoading: lotsLoading } = useFundLots(safeFundId);

  if (!fundId) return <ErrorMessage message="Fond-ID mangler." />;

  if (sumLoading) return <LoadingSpinner label="Laster fond..." />;
  if (sumError) return <ErrorMessage message="Kunne ikke laste fond." />;
  if (!summary) return <ErrorMessage message="Fond ikke funnet." />;

  const lots = lotsData?.lots ?? [];

  const periodOrder: Array<keyof typeof summary.period_metrics> = [
    "1d",
    "7d",
    "30d",
    "180d",
    "YTD",
    "12m",
    "24m",
    "Total",
  ];
  const periodLabel: Record<keyof typeof summary.period_metrics, string> = {
    "1d": "1d",
    "7d": "7d",
    "30d": "30d",
    "180d": "180d",
    YTD: "YTD",
    "12m": "1y",
    "24m": "2y",
    Total: "Total",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate("/")}
          className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
        >
          ← Tilbake
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{summary.ticker}</h1>
          <p className="text-sm text-gray-500">{summary.fund_name}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard title="Markedsverdi" value={nok(summary.current_value)} />
        <StatCard
          title="Kostpris total"
          value={nok(summary.capital_split.total_cost)}
        />
        <StatCard
          title="Betalt rente"
          value={nok(summary.total_interest_paid)}
        />
        <StatCard
          title="True Net Worth"
          value={nok(summary.true_net_worth.true_net_worth_nok)}
          highlight={
            summary.true_net_worth.true_net_worth_nok >= 0
              ? "positive"
              : "negative"
          }
        />
        <StatCard
          title="Vektet ann. avkastning (%)"
          value={pct(summary.returns.annualized_return_on_cost_weighted_pct)}
          highlight={
            summary.returns.annualized_return_on_cost_weighted_pct == null
              ? "neutral"
              : summary.returns.annualized_return_on_cost_weighted_pct >= 0
                ? "positive"
                : "negative"
          }
        />
      </div>

      <PriceChart fundId={fundId} fundName={summary.fund_name} />

      <PerformanceBars periodMetrics={summary.period_metrics} />

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <SectionHeader title="Rullerende perioder" />
        <p className="text-xs text-gray-500 mb-3">
          For 1d-2y justeres verdiendring for kjøp/salg og utbytte-reinvestering
          i perioden. Total viser markedsverdi minus kostpris (kjøp). Visning er
          uten skatt.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <ThWithTooltip
                  className="px-3 py-2 text-left"
                  label="Periode"
                  tip="Tidsvindu for beregning (1d, 7d, 30d, 180d, YTD, 1y, 2y, Total)."
                />
                <ThWithTooltip
                  label="Brutto %"
                  tip="Brutto verdiendring delt på kapitalbase i perioden, i prosent."
                />
                <ThWithTooltip
                  label="Brutto verdiendring"
                  tip="For 1d-2y: (verdi slutt - verdi start) justert for netto kjøp/salg og utbytte-reinvestering. For Total: markedsverdi minus kostpris (kjøp)."
                />
                <ThWithTooltip
                  label="Rentekost"
                  tip="Allokert rentekostnad i perioden."
                />
                <ThWithTooltip
                  label="Brutto verdiendring inkl. rentekost"
                  tip="Brutto verdiendring minus allokert rentekost i perioden (uten skatt)."
                />
              </tr>
            </thead>
            <tbody>
              {periodOrder.map((key) => {
                const metric = summary.period_metrics[key];
                const isNotApplicable = metric.return_pct_fund == null;
                return (
                  <tr key={key} className="border-b">
                    <td className="px-3 py-2">{periodLabel[key]}</td>
                    <td className="px-3 py-2 text-right">
                      <PnlBadge value={metric.return_split.gross_pct} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isNotApplicable ? (
                        <span className="text-gray-400 text-sm">N/A</span>
                      ) : (
                        nok(metric.brutto_value_change_nok)
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isNotApplicable ? (
                        <span className="text-gray-400 text-sm">N/A</span>
                      ) : (
                        nok(metric.allocated_interest_cost_nok)
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isNotApplicable ? (
                        <span className="text-gray-400 text-sm">N/A</span>
                      ) : (
                        nok(metric.return_split.after_interest_amount_nok)
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <SectionHeader title="Posisjoner (Lot)" />
          {lotsData && (
            <div className="text-xs text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              Siste kurs:{" "}
              <span className="font-semibold text-gray-700">
                {nok(lotsData.market_price_per_unit)}
              </span>
              {lotsData.market_price_date && (
                <span className="ml-1 text-gray-400">
                  ({lotsData.market_price_date})
                </span>
              )}
            </div>
          )}
        </div>
        {lotsLoading ? (
          <LoadingSpinner />
        ) : lots.length === 0 ? (
          <p className="text-gray-500 text-sm">Ingen posisjoner.</p>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50">
                  <ThWithTooltip
                    className="px-4 py-3 text-left font-semibold text-gray-700"
                    label="Dato kjøp"
                    tip="Dato loten ble kjøpt."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Kostpris total"
                    tip="Total kjøpskost for loten."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Rentekostnad"
                    tip="Akkumulert allokert rentekostnad for loten."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Kurs (kr/andel)"
                    tip="Siste registrerte andelskurs brukt i verdiestimatet."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-left font-semibold text-gray-700"
                    label="Kursdato"
                    tip="Dato for siste kurs i beregningen."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Andeler kjøpt"
                    tip="Antall andeler i opprinnelig kjøpstransaksjon."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Andeler nå"
                    tip="Nåværende antall andeler i loten etter salg/utbytte-reinvestering."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Verdi (NOK)"
                    tip="Nåverdi av loten basert på siste kurs."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Avkastning NOK"
                    tip="Nåverdi minus kostpris for loten."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Avkastning mot kostpris (%)"
                    tip="(Nåverdi - kostpris) / kostpris, i prosent."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Avkastning ann. mot kostpris (%)"
                    tip="Annualisert avkastning basert på kostpris og eiertid i dager."
                  />
                  <ThWithTooltip
                    className="px-4 py-3 text-right font-semibold text-gray-700"
                    label="Dager"
                    tip="Antall dager loten har vært eid."
                  />
                </tr>
              </thead>
              <tbody>
                {lots.map((lot) => (
                  <tr key={lot.lot_id} className="border-b hover:bg-gray-50">
                    {(() => {
                      const lotCost = lot.capital_split.cost;
                      const returnOnCostPct =
                        lotCost > 0
                          ? ((lot.current_value - lotCost) / lotCost) * 100
                          : null;
                      const annualizedReturnOnCostPct =
                        lotCost > 0 &&
                        lot.current_value > 0 &&
                        lot.days_owned > 0
                          ? (Math.pow(
                              lot.current_value / lotCost,
                              365 / lot.days_owned,
                            ) -
                              1) *
                            100
                          : null;

                      return (
                        <>
                          <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                            {lot.purchase_date}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {nok(lot.capital_split.cost)}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {nok(lot.allocated_interest_paid)}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {lotsData?.market_price_per_unit.toLocaleString(
                              "nb-NO",
                              {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                              },
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                            {lotsData?.market_price_date ?? "-"}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {lot.original_units.toFixed(4)}
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">
                            {lot.current_units.toFixed(4)}
                          </td>
                          <td className="px-4 py-3 text-right font-semibold text-gray-800">
                            {nok(lot.current_value)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            {nok(lot.current_value - lot.capital_split.cost)}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <PnlBadge value={returnOnCostPct} />
                          </td>
                          <td className="px-4 py-3 text-right">
                            <PnlBadge value={annualizedReturnOnCostPct} />
                          </td>
                          <td className="px-4 py-3 text-right text-gray-500">
                            {lot.days_owned}
                          </td>
                        </>
                      );
                    })()}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
