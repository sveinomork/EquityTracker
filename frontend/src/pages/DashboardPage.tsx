import { usePortfolioSummary } from "../hooks/usePortfolioSummary";
import { useNavigate } from "react-router-dom";
import StatCard from "../components/common/StatCard";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import EmptyState from "../components/common/EmptyState";
import SectionHeader from "../components/common/SectionHeader";
import PnlBadge from "../components/common/PnlBadge";
import { nok, pct } from "../utils/dates";

export default function DashboardPage() {
  const { data: portfolio, isLoading, isError } = usePortfolioSummary();
  const navigate = useNavigate();

  if (isLoading) return <LoadingSpinner label="Laster portefølje..." />;
  if (isError) return <ErrorMessage message="Kunne ikke laste portefølje." />;
  if (!portfolio) return <EmptyState message="Ingen data." />;

  const { funds, totals } = portfolio;
  const portfolioTotal = totals.total_return;
  const periodOrder: Array<keyof typeof portfolio.period_metrics> = [
    "1d",
    "7d",
    "30d",
    "180d",
    "12m",
    "24m",
    "Total",
  ];
  const periodLabel: Record<keyof typeof portfolio.period_metrics, string> = {
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
      <div>
        <h1 className="text-2xl font-bold text-gray-800">
          Portefølje Oversikt
        </h1>
        <p className="text-sm text-gray-500 mt-1">Per {portfolio.as_of_date}</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          title="Investert"
          value={nok(totals.total_equity + totals.total_borrowed)}
          highlight="neutral"
        />
        <StatCard
          title="Markedsverdi"
          value={nok(totals.current_value)}
          highlight="neutral"
        />
        <StatCard
          title="Netto egenkapital"
          value={nok(totals.net_equity_value)}
          highlight={totals.net_equity_value >= 0 ? "positive" : "negative"}
        />
        <StatCard
          title="True Net Worth"
          value={nok(totals.true_net_worth_nok)}
          highlight={totals.true_net_worth_nok >= 0 ? "positive" : "negative"}
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <p className="text-sm font-semibold text-gray-700 mb-3">
          Portefølje Total (uten skatt)
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm mb-4">
          <div>
            <span className="text-gray-500">Kostpris</span>
            <div className="font-semibold">{nok(totals.total_cost)}</div>
          </div>
          <div>
            <span className="text-gray-500">Markedsverdi</span>
            <div className="font-semibold">
              {nok(totals.total_market_value)}
            </div>
          </div>
          <div>
            <span className="text-gray-500">Betalt rente</span>
            <div className="font-semibold">
              {nok(totals.total_interest_paid)}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
            <p className="font-semibold text-gray-700 mb-2">
              Totalavkastning uten rentekost
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-600">Belop</span>
                <span className="font-semibold">
                  {nok(portfolioTotal.gross_amount_nok)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Prosent</span>
                <PnlBadge value={portfolioTotal.gross_pct} />
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Annualisert</span>
                <span className="font-semibold">
                  {pct(portfolioTotal.gross_annualized_pct)}
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 p-3 bg-gray-50">
            <p className="font-semibold text-gray-700 mb-2">
              Totalavkastning med rentekost
            </p>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-gray-600">Belop</span>
                <span className="font-semibold">
                  {nok(portfolioTotal.after_interest_amount_nok)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Prosent</span>
                <PnlBadge value={portfolioTotal.after_interest_pct} />
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Annualisert</span>
                <span className="font-semibold">
                  {pct(portfolioTotal.after_interest_annualized_pct)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">Periode</th>
                <th className="px-3 py-2 text-right">Uten rente belop</th>
                <th className="px-3 py-2 text-right">Uten rente %</th>
                <th className="px-3 py-2 text-right">Uten rente ann.</th>
                <th className="px-3 py-2 text-right">Med rente belop</th>
                <th className="px-3 py-2 text-right">Med rente %</th>
                <th className="px-3 py-2 text-right">Med rente ann.</th>
              </tr>
            </thead>
            <tbody>
              {periodOrder.map((key) => {
                const metric = portfolio.period_metrics[key];
                const split = metric.return_split;
                return (
                  <tr key={key} className="border-b">
                    <td className="px-3 py-2">{periodLabel[key]}</td>
                    <td className="px-3 py-2 text-right">
                      {nok(split.gross_amount_nok)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <PnlBadge value={split.gross_pct} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      {pct(split.gross_annualized_pct)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {nok(split.after_interest_amount_nok)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <PnlBadge value={split.after_interest_pct} />
                    </td>
                    <td className="px-3 py-2 text-right">
                      {pct(split.after_interest_annualized_pct)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <SectionHeader title="Fond" description="Klikk på et fond for detaljer" />

      {funds.length === 0 ? (
        <EmptyState message="Ingen fond. Opprett ditt første fond i 'Legg til data'." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {funds.map((fund) => {
            const totalReturn = fund.total_return;
            return (
              <button
                key={fund.fund_id}
                onClick={() => navigate(`/fund/${fund.fund_id}`)}
                className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 hover:shadow-md hover:border-blue-300 transition-all text-left"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <p className="font-bold text-gray-800">{fund.ticker}</p>
                    <p className="text-xs text-gray-500">{fund.fund_name}</p>
                  </div>
                </div>

                <div className="space-y-2 text-sm border-t pt-2 mt-2">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Markedsverdi</span>
                    <span className="font-semibold">
                      {nok(fund.current_value)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Kostpris total</span>
                    <span className="font-semibold">
                      {nok(fund.capital_split.total_cost)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Betalt rente</span>
                    <span className="font-semibold">
                      {nok(fund.total_interest_paid)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Vektet ann. avkast.</span>
                    <PnlBadge
                      value={
                        fund.returns.annualized_return_on_cost_weighted_pct
                      }
                    />
                  </div>

                  <div className="pt-1 mt-1 border-t border-gray-100">
                    <p className="text-xs font-semibold text-gray-600 mb-1">
                      Total uten rentekost
                    </p>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Belop</span>
                      <span className="font-semibold">
                        {nok(totalReturn.gross_amount_nok)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Prosent</span>
                      <PnlBadge value={totalReturn.gross_pct} />
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Annualisert</span>
                      <span className="font-semibold">
                        {pct(totalReturn.gross_annualized_pct)}
                      </span>
                    </div>
                  </div>

                  <div className="pt-1 mt-1 border-t border-gray-100">
                    <p className="text-xs font-semibold text-gray-600 mb-1">
                      Total med rentekost
                    </p>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Belop</span>
                      <span className="font-semibold">
                        {nok(totalReturn.after_interest_amount_nok)}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Prosent</span>
                      <PnlBadge value={totalReturn.after_interest_pct} />
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">Annualisert</span>
                      <span className="font-semibold">
                        {pct(totalReturn.after_interest_annualized_pct)}
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
