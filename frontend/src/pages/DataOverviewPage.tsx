import { useMemo, useState } from "react";
import { useQueries } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import * as XLSX from "xlsx";
import LoadingSpinner from "../components/common/LoadingSpinner";
import ErrorMessage from "../components/common/ErrorMessage";
import EmptyState from "../components/common/EmptyState";
import SectionHeader from "../components/common/SectionHeader";
import { useFunds } from "../hooks/useFunds";
import { useUpdateTransaction } from "../hooks/useMutations";
import { useTransactions } from "../hooks/useTransactions";
import { fetchPrices } from "../api/prices";
import { fetchRates } from "../api/rates";
import { nok } from "../utils/dates";
import type { DailyPrice, LoanRate, Transaction } from "../types/api";

type PriceRow = DailyPrice & { fund_name: string; ticker: string };
type RateRow = LoanRate & { fund_name: string; ticker: string };

function parseLocalizedNumber(input: string): number {
  const normalized = input
    .trim()
    .replace(/\s/g, "")
    .replace(/kr/gi, "")
    .replace(/,/g, ".");
  return Number(normalized);
}

export default function DataOverviewPage() {
  const [selectedFundId, setSelectedFundId] = useState<string>("all");
  const {
    data: funds = [],
    isLoading: fundsLoading,
    isError: fundsError,
  } = useFunds();

  const activeFundId = selectedFundId === "all" ? undefined : selectedFundId;
  const fundById = useMemo(
    () => new Map(funds.map((fund) => [fund.id, fund])),
    [funds],
  );
  const {
    data: transactions = [],
    isLoading: transactionsLoading,
    isError: transactionsError,
  } = useTransactions(activeFundId);
  const { mutate: updateTransaction } = useUpdateTransaction();

  const fundsForMarketData = useMemo(
    () =>
      activeFundId ? funds.filter((item) => item.id === activeFundId) : funds,
    [activeFundId, funds],
  );

  const priceQueries = useQueries({
    queries: fundsForMarketData.map((fund) => ({
      queryKey: ["overview", "prices", fund.id],
      queryFn: () => fetchPrices(fund.id, { limit: 5000 }),
      enabled: !!fund.id,
    })),
  });

  const rateQueries = useQueries({
    queries: fundsForMarketData.map((fund) => ({
      queryKey: ["overview", "rates", fund.id],
      queryFn: () => fetchRates(fund.id),
      enabled: !!fund.id,
    })),
  });

  const marketDataLoading =
    priceQueries.some((query) => query.isLoading) ||
    rateQueries.some((query) => query.isLoading);
  const marketDataError =
    priceQueries.some((query) => query.isError) ||
    rateQueries.some((query) => query.isError);

  const priceRows: PriceRow[] = useMemo(() => {
    const rows: PriceRow[] = [];
    fundsForMarketData.forEach((fund, index) => {
      const prices = (priceQueries[index]?.data ?? []) as DailyPrice[];
      prices.forEach((price) => {
        rows.push({
          ...price,
          fund_name: fund.name,
          ticker: fund.ticker,
        });
      });
    });

    return rows.sort((left, right) =>
      `${right.date}-${right.ticker}`.localeCompare(
        `${left.date}-${left.ticker}`,
      ),
    );
  }, [fundsForMarketData, priceQueries]);

  const rateRows: RateRow[] = useMemo(() => {
    const rows: RateRow[] = [];
    fundsForMarketData.forEach((fund, index) => {
      const rates = (rateQueries[index]?.data ?? []) as LoanRate[];
      rates.forEach((rate) => {
        rows.push({
          ...rate,
          fund_name: fund.name,
          ticker: fund.ticker,
        });
      });
    });

    return rows.sort((left, right) =>
      `${right.effective_date}-${right.ticker}`.localeCompare(
        `${left.effective_date}-${left.ticker}`,
      ),
    );
  }, [fundsForMarketData, rateQueries]);

  const handleEditTransaction = (transaction: Transaction) => {
    const borrowedDefault =
      transaction.type === "BUY" ? String(transaction.borrowed_amount) : "0";
    const borrowedInput = window.prompt("Laan", borrowedDefault);
    if (borrowedInput === null) return;
    const equityInput = window.prompt(
      "Egenkapital",
      String(transaction.equity_amount),
    );
    if (equityInput === null) return;

    const borrowedAmountRaw = parseLocalizedNumber(borrowedInput);
    const equityAmount = parseLocalizedNumber(equityInput);
    if (!Number.isFinite(equityAmount) || equityAmount <= 0) {
      alert("Egenkapital ma vaere et positivt tall.");
      return;
    }

    const borrowedAmount = transaction.type === "BUY" ? borrowedAmountRaw : 0;
    if (!Number.isFinite(borrowedAmount) || borrowedAmount < 0) {
      alert("Laan ma vaere et gyldig tall.");
      return;
    }

    const totalAmount = equityAmount + borrowedAmount;

    updateTransaction(
      {
        transactionId: transaction.id,
        payload: {
          date: transaction.date,
          type: transaction.type,
          units: Math.abs(transaction.units),
          total_amount: totalAmount,
          borrowed_amount: borrowedAmount,
        },
      },
      {
        onSuccess: () => alert("Transaksjon oppdatert."),
        onError: (error) => {
          if (isAxiosError(error)) {
            const detail = (error.response?.data as { detail?: unknown })
              ?.detail;
            if (typeof detail === "string") {
              alert(`Kunne ikke oppdatere transaksjonen: ${detail}`);
              return;
            }
          }
          alert("Kunne ikke oppdatere transaksjonen.");
        },
      },
    );
  };

  const handleExportToExcel = () => {
    const workbook = XLSX.utils.book_new();

    const metadataRows = [
      {
        generated_at: new Date().toISOString(),
        selected_fund:
          selectedFundId === "all"
            ? "Alle fond"
            : `${fundById.get(selectedFundId)?.ticker ?? "Ukjent"} - ${fundById.get(selectedFundId)?.name ?? "Ukjent"}`,
      },
      {
        funds_count: funds.length,
        transactions_count: transactions.length,
        prices_count: priceRows.length,
        rates_count: rateRows.length,
      },
    ];
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(metadataRows),
      "Metadata",
    );

    const fundRows = funds.map((fund) => ({
      id: fund.id,
      ticker: fund.ticker,
      name: fund.name,
      is_distributing: fund.is_distributing,
      manual_taxable_gain_override: fund.manual_taxable_gain_override,
    }));
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(fundRows),
      "Fond",
    );

    const transactionRows = transactions.map((transaction) => ({
      id: transaction.id,
      date: transaction.date,
      ticker: fundById.get(transaction.fund_id)?.ticker ?? "Ukjent",
      fund_name: fundById.get(transaction.fund_id)?.name ?? "Ukjent",
      type: transaction.type,
      units: transaction.units,
      price_per_unit: transaction.price_per_unit,
      total_amount: transaction.total_amount,
      borrowed_amount: transaction.borrowed_amount,
      equity_amount: transaction.equity_amount,
      lot_id: transaction.lot_id,
    }));
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(transactionRows),
      "Transaksjoner",
    );

    const pricesSheetRows = priceRows.map((price) => ({
      id: price.id,
      date: price.date,
      ticker: price.ticker,
      fund_name: price.fund_name,
      price: price.price,
    }));
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(pricesSheetRows),
      "Priser",
    );

    const ratesSheetRows = rateRows.map((rate) => ({
      id: rate.id,
      effective_date: rate.effective_date,
      ticker: rate.ticker,
      fund_name: rate.fund_name,
      nominal_rate: rate.nominal_rate,
    }));
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(ratesSheetRows),
      "Renter",
    );

    const fileSuffix =
      selectedFundId === "all"
        ? "alle-fond"
        : (fundById.get(selectedFundId)?.ticker ?? selectedFundId);
    XLSX.writeFile(workbook, `dataoversikt-${fileSuffix}.xlsx`);
  };

  if (fundsLoading) return <LoadingSpinner label="Laster dataoversikt..." />;
  if (fundsError) return <ErrorMessage message="Kunne ikke laste fond." />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dataoversikt</h1>
          <p className="text-sm text-gray-500 mt-1">
            Se alle registrerte fond, transaksjoner, priser og renter.
          </p>
        </div>
        <button
          type="button"
          onClick={handleExportToExcel}
          disabled={fundsLoading || transactionsLoading || marketDataLoading}
          className="inline-flex items-center justify-center rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
        >
          Eksporter til Excel
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Filter på fond
        </label>
        <select
          value={selectedFundId}
          onChange={(event) => setSelectedFundId(event.target.value)}
          className="w-full md:w-80 border border-gray-300 rounded-md px-3 py-2 text-sm"
        >
          <option value="all">Alle fond</option>
          {funds.map((fund) => (
            <option key={fund.id} value={fund.id}>
              {fund.ticker} - {fund.name}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-x-auto">
        <SectionHeader title={`Fond (${funds.length})`} />
        {funds.length === 0 ? (
          <EmptyState message="Ingen fond registrert." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">Ticker</th>
                <th className="px-3 py-2 text-left">Navn</th>
                <th className="px-3 py-2 text-left">Distribuerende</th>
                <th className="px-3 py-2 text-right">Manuell skattebase</th>
              </tr>
            </thead>
            <tbody>
              {funds.map((fund) => (
                <tr key={fund.id} className="border-b">
                  <td className="px-3 py-2 font-medium">{fund.ticker}</td>
                  <td className="px-3 py-2">{fund.name}</td>
                  <td className="px-3 py-2">
                    {fund.is_distributing ? "Ja" : "Nei"}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {fund.manual_taxable_gain_override == null
                      ? "-"
                      : nok(fund.manual_taxable_gain_override, 2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-x-auto">
        <SectionHeader title={`Transaksjoner (${transactions.length})`} />
        {transactionsLoading ? (
          <LoadingSpinner label="Laster transaksjoner..." />
        ) : transactionsError ? (
          <ErrorMessage message="Kunne ikke laste transaksjoner." />
        ) : transactions.length === 0 ? (
          <EmptyState message="Ingen transaksjoner funnet for valgt filter." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">Dato</th>
                <th className="px-3 py-2 text-left">Ticker</th>
                <th className="px-3 py-2 text-left">Fond</th>
                <th className="px-3 py-2 text-left">Type</th>
                <th className="px-3 py-2 text-right">Units</th>
                <th className="px-3 py-2 text-right">Pris per unit</th>
                <th className="px-3 py-2 text-right">Belop</th>
                <th className="px-3 py-2 text-right">Laan</th>
                <th className="px-3 py-2 text-right">Egenkapital</th>
                <th className="px-3 py-2 text-right">Handling</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((transaction) => (
                <tr key={transaction.id} className="border-b">
                  <td className="px-3 py-2">{transaction.date}</td>
                  <td className="px-3 py-2 font-medium">
                    {fundById.get(transaction.fund_id)?.ticker ?? "Ukjent"}
                  </td>
                  <td className="px-3 py-2">
                    {fundById.get(transaction.fund_id)?.name ?? "Ukjent"}
                  </td>
                  <td className="px-3 py-2">{transaction.type}</td>
                  <td className="px-3 py-2 text-right">{transaction.units}</td>
                  <td className="px-3 py-2 text-right">
                    {nok(transaction.price_per_unit, 2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {nok(transaction.total_amount, 2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {nok(transaction.borrowed_amount, 2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {nok(transaction.equity_amount, 2)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => handleEditTransaction(transaction)}
                      className="px-2 py-1 text-xs font-medium rounded border border-gray-300 hover:bg-gray-100"
                    >
                      Rediger
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-x-auto">
        <SectionHeader title={`Priser (${priceRows.length})`} />
        {marketDataLoading ? (
          <LoadingSpinner label="Laster priser og renter..." />
        ) : marketDataError ? (
          <ErrorMessage message="Kunne ikke laste priser/renter." />
        ) : priceRows.length === 0 ? (
          <EmptyState message="Ingen priser funnet for valgt filter." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">Dato</th>
                <th className="px-3 py-2 text-left">Ticker</th>
                <th className="px-3 py-2 text-left">Fond</th>
                <th className="px-3 py-2 text-right">Kurs</th>
              </tr>
            </thead>
            <tbody>
              {priceRows.map((price) => (
                <tr key={price.id} className="border-b">
                  <td className="px-3 py-2">{price.date}</td>
                  <td className="px-3 py-2 font-medium">{price.ticker}</td>
                  <td className="px-3 py-2">{price.fund_name}</td>
                  <td className="px-3 py-2 text-right">
                    {nok(price.price, 3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 overflow-x-auto">
        <SectionHeader title={`Renter (${rateRows.length})`} />
        {marketDataLoading ? (
          <LoadingSpinner label="Laster priser og renter..." />
        ) : marketDataError ? (
          <ErrorMessage message="Kunne ikke laste priser/renter." />
        ) : rateRows.length === 0 ? (
          <EmptyState message="Ingen renter funnet for valgt filter." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th className="px-3 py-2 text-left">Effektiv dato</th>
                <th className="px-3 py-2 text-left">Ticker</th>
                <th className="px-3 py-2 text-left">Fond</th>
                <th className="px-3 py-2 text-right">Nom. rente %</th>
              </tr>
            </thead>
            <tbody>
              {rateRows.map((rate) => (
                <tr key={rate.id} className="border-b">
                  <td className="px-3 py-2">{rate.effective_date}</td>
                  <td className="px-3 py-2 font-medium">{rate.ticker}</td>
                  <td className="px-3 py-2">{rate.fund_name}</td>
                  <td className="px-3 py-2 text-right">{rate.nominal_rate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
