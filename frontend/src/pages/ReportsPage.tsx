import { useEffect, useMemo, useState } from "react";
import * as XLSX from "xlsx";
import ErrorMessage from "../components/common/ErrorMessage";
import LoadingSpinner from "../components/common/LoadingSpinner";
import SectionHeader from "../components/common/SectionHeader";
import { usePeriodReport, useReportPeriodOptions } from "../hooks/useReports";
import type { PortfolioPeriodReport, ReportPeriodType } from "../types/api";
import { nok, pct } from "../utils/dates";

const PERIOD_TYPES: { value: ReportPeriodType; label: string }[] = [
  { value: "monthly", label: "Maaned" },
  { value: "quarterly", label: "Kvartal" },
  { value: "yearly", label: "Aar" },
];

function buildReportFilename(
  report: PortfolioPeriodReport,
  extension: string,
): string {
  return `fundtracker-report-${report.period_type}-${report.period_value}.${extension}`;
}

export default function ReportsPage() {
  const [periodType, setPeriodType] = useState<ReportPeriodType>("monthly");
  const [periodValue, setPeriodValue] = useState<string>("");
  const [fundFilter, setFundFilter] = useState("");
  const [sortBy, setSortBy] = useState<
    "current_value" | "profit_loss_net" | "gross_pct" | "units"
  >("current_value");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  const {
    data: optionsData,
    isLoading: optionsLoading,
    isError: optionsError,
  } = useReportPeriodOptions(periodType);

  const availableOptions = optionsData?.options ?? [];
  const selectedOption = useMemo(
    () => availableOptions.find((item) => item.value === periodValue),
    [availableOptions, periodValue],
  );

  useEffect(() => {
    if (availableOptions.length === 0) {
      setPeriodValue("");
      return;
    }

    const hasCurrentSelection = availableOptions.some(
      (item) => item.value === periodValue,
    );
    if (hasCurrentSelection) {
      return;
    }

    setPeriodValue(availableOptions[availableOptions.length - 1].value);
  }, [availableOptions, periodValue]);

  const {
    data: report,
    isLoading: reportLoading,
    isError: reportError,
  } = usePeriodReport(periodType, periodValue);

  const previousPeriodValue = useMemo(() => {
    const currentIndex = availableOptions.findIndex(
      (item) => item.value === periodValue,
    );
    if (currentIndex <= 0) {
      return undefined;
    }
    return availableOptions[currentIndex - 1].value;
  }, [availableOptions, periodValue]);

  const { data: previousReport } = usePeriodReport(
    periodType,
    previousPeriodValue,
  );

  const filteredFunds = useMemo(() => {
    if (!report) {
      return [];
    }

    const normalizedFilter = fundFilter.trim().toLowerCase();
    const visibleFunds = report.funds.filter((item) => {
      if (!normalizedFilter) {
        return true;
      }
      return (
        item.ticker.toLowerCase().includes(normalizedFilter) ||
        item.fund_name.toLowerCase().includes(normalizedFilter)
      );
    });

    const sorted = [...visibleFunds].sort((left, right) => {
      let leftValue = 0;
      let rightValue = 0;

      if (sortBy === "current_value") {
        leftValue = left.end_value;
        rightValue = right.end_value;
      } else if (sortBy === "profit_loss_net") {
        leftValue = left.summary.profit_loss_net;
        rightValue = right.summary.profit_loss_net;
      } else if (sortBy === "gross_pct") {
        leftValue =
          left.summary.period_metrics.Total.return_split.gross_pct ??
          Number.NEGATIVE_INFINITY;
        rightValue =
          right.summary.period_metrics.Total.return_split.gross_pct ??
          Number.NEGATIVE_INFINITY;
      } else {
        leftValue = left.end_units;
        rightValue = right.end_units;
      }

      return sortDirection === "asc"
        ? leftValue - rightValue
        : rightValue - leftValue;
    });

    return sorted;
  }, [fundFilter, report, sortBy, sortDirection]);

  const fundComparisonRows = useMemo(() => {
    if (!report) {
      return [];
    }

    // Calculate period delta for each fund (end - start within the same period)
    return report.funds.map((item) => {
      return {
        ticker: item.ticker,
        fund_name: item.fund_name,
        start_value: item.start_value,
        end_value: item.end_value,
        value_delta: item.end_value - item.start_value,
        start_cost: item.start_cost,
        end_cost: item.end_cost,
        cost_delta: item.end_cost - item.start_cost,
        profit: item.summary.profit_loss_net,
        return_pct: item.summary.period_metrics.Total.return_split.gross_pct,
      };
    });
  }, [report]);

  const handleExportExcel = () => {
    if (!report) {
      return;
    }

    const workbook = XLSX.utils.book_new();

    const metadataRows = [
      {
        period_type: report.period_type,
        period_value: report.period_value,
        period_start: report.period_start,
        period_end: report.period_end,
        as_of_date: report.portfolio_end.as_of_date,
        data_start_date: report.data_start_date,
        data_end_date: report.data_end_date,
        generated_at: new Date().toISOString(),
      },
    ];
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(metadataRows),
      "Metadata",
    );

    const portfolioRows = [
      {
        period_start_value: report.portfolio_start.totals.current_value,
        period_end_value: report.portfolio_end.totals.current_value,
        value_delta:
          report.portfolio_end.totals.current_value -
          report.portfolio_start.totals.current_value,
        start_cost: report.portfolio_start.totals.total_cost,
        end_cost: report.portfolio_end.totals.total_cost,
        cost_delta:
          report.portfolio_end.totals.total_cost -
          report.portfolio_start.totals.total_cost,
        start_profit: report.portfolio_start.totals.profit_loss_net,
        end_profit: report.portfolio_end.totals.profit_loss_net,
        profit_delta:
          report.portfolio_end.totals.profit_loss_net -
          report.portfolio_start.totals.profit_loss_net,
        start_return_pct:
          report.portfolio_start.period_metrics.Total.return_split.gross_pct,
        end_return_pct:
          report.portfolio_end.period_metrics.Total.return_split.gross_pct,
      },
    ];
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(portfolioRows),
      "Portfolio",
    );

    const fundRows = report.funds.map((item) => ({
      ticker: item.ticker,
      fund_name: item.fund_name,
      start_units: item.start_units,
      end_units: item.end_units,
      units_delta: item.end_units - item.start_units,
      start_price: item.start_price,
      end_price: item.end_price,
      start_value: item.start_value,
      end_value: item.end_value,
      value_delta: item.end_value - item.start_value,
      start_cost: item.start_cost,
      end_cost: item.end_cost,
      cost_delta: item.end_cost - item.start_cost,
      profit_loss_net: item.summary.profit_loss_net,
      total_return_gross_pct:
        item.summary.period_metrics.Total.return_split.gross_pct,
      latest_price_date: item.latest_price_date,
    }));
    XLSX.utils.book_append_sheet(
      workbook,
      XLSX.utils.json_to_sheet(fundRows),
      "Funds",
    );

    if (previousReport) {
      const comparisonRows = [
        {
          previous_period: previousReport.period_value,
          current_value_delta:
            report.portfolio_end.totals.current_value -
            previousReport.portfolio_end.totals.current_value,
          profit_loss_delta:
            report.portfolio_end.totals.profit_loss_net -
            previousReport.portfolio_end.totals.profit_loss_net,
        },
      ];
      XLSX.utils.book_append_sheet(
        workbook,
        XLSX.utils.json_to_sheet(comparisonRows),
        "Comparison",
      );
    }

    if (fundComparisonRows.length > 0) {
      XLSX.utils.book_append_sheet(
        workbook,
        XLSX.utils.json_to_sheet(fundComparisonRows),
        "PeriodDelta",
      );
    }

    XLSX.writeFile(workbook, buildReportFilename(report, "xlsx"));
  };

  const handleExportPdf = () => {
    if (!report) {
      return;
    }

    const rowsHtml = report.funds
      .map(
        (item) => `
          <tr>
            <td>${item.ticker}</td>
            <td>${item.fund_name}</td>
            <td style="text-align:right;">${item.start_units.toLocaleString("nb-NO", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</td>
            <td style="text-align:right;">${item.end_units.toLocaleString("nb-NO", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}</td>
            <td style="text-align:right;">${nok(item.start_value)}</td>
            <td style="text-align:right;">${nok(item.end_value)}</td>
            <td style="text-align:right;">${nok(item.end_cost)}</td>
            <td style="text-align:right;">${nok(item.summary.profit_loss_net)}</td>
            <td style="text-align:right;">${pct(item.summary.period_metrics.Total.return_split.gross_pct)}</td>
            <td>${item.latest_price_date ?? "-"}</td>
          </tr>
        `,
      )
      .join("");

    const comparisonHtml = previousReport
      ? `
          <h2>Sammenligning mot forrige periode (${previousReport.period_value})</h2>
          <p>Endring markedsverdi: ${nok(
            report.portfolio_end.totals.current_value -
              previousReport.portfolio_end.totals.current_value,
          )}</p>
          <p>Endring netto avkastning: ${nok(
            report.portfolio_end.totals.profit_loss_net -
              previousReport.portfolio_end.totals.profit_loss_net,
          )}</p>
        `
      : "";

    const fundComparisonRowsHtml = fundComparisonRows
      .map(
        (item) => `
          <tr>
            <td>${item.ticker}</td>
            <td>${item.fund_name}</td>
            <td style="text-align:right;">${nok(item.start_value)}</td>
            <td style="text-align:right;">${nok(item.end_value)}</td>
            <td style="text-align:right;">${nok(item.value_delta)}</td>
            <td style="text-align:right;">${nok(item.end_cost)}</td>
            <td style="text-align:right;">${nok(item.profit)}</td>
            <td style="text-align:right;">${pct(item.return_pct)}</td>
          </tr>
        `,
      )
      .join("");

    const fundComparisonHtml =
      fundComparisonRows.length > 0
        ? `
          <h2>Per fond periode endring</h2>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Fond</th>
                <th>Start verdi</th>
                <th>Slutt verdi</th>
                <th>Endring verdi</th>
                <th>Kostpris</th>
                <th>Netto avkastning</th>
                <th>Avkastning %</th>
              </tr>
            </thead>
            <tbody>
              ${fundComparisonRowsHtml}
            </tbody>
          </table>
        `
        : "";

    const printWindow = window.open("", "_blank", "width=1200,height=900");
    if (!printWindow) {
      alert("Kunne ikke apne utskriftsvindu. Sjekk popup-innstillinger.");
      return;
    }

    printWindow.document.write(`
      <html>
        <head>
          <title>${buildReportFilename(report, "pdf")}</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 24px; color: #222; }
            h1, h2 { margin: 0 0 12px; }
            p { margin: 4px 0; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; }
            th, td { border: 1px solid #d1d5db; padding: 8px; font-size: 12px; }
            th { background: #f3f4f6; text-align: left; }
          </style>
        </head>
        <body>
          <h1>FundTracker Rapport</h1>
          <p>Periode: ${report.period_type} ${report.period_value}</p>
          <p>Fra ${report.period_start} til ${report.period_end}</p>
          <p>As of: ${report.portfolio_end.as_of_date}</p>

          <h2>Portefolje</h2>
          <p>Markedsverdi START: ${nok(report.portfolio_start.totals.current_value)}</p>
          <p>Markedsverdi SLUTT: ${nok(report.portfolio_end.totals.current_value)}</p>
          <p>Endring markedsverdi: ${nok(
            report.portfolio_end.totals.current_value -
              report.portfolio_start.totals.current_value,
          )}</p>
          <p>Kostpris: ${nok(report.portfolio_end.totals.total_cost)}</p>
          <p>Netto avkastning: ${nok(report.portfolio_end.totals.profit_loss_net)}</p>
          <p>Total avkastning %: ${pct(report.portfolio_end.period_metrics.Total.return_split.gross_pct)}</p>

          ${comparisonHtml}

          <h2>Per fond</h2>
          <table>
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Fond</th>
                <th>Andeler START</th>
                <th>Andeler SLUTT</th>
                <th>Verdi START</th>
                <th>Verdi SLUTT</th>
                <th>Kostpris</th>
                <th>Netto avkastning</th>
                <th>Total %</th>
                <th>Siste kursdato</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml}
            </tbody>
          </table>

          ${fundComparisonHtml}
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Rapporter</h1>
          <p className="text-sm text-gray-500">
            Samme rapportstruktur for total portefolje og hvert fond, med
            andeler per fond.
          </p>
        </div>
        <div className="grid gap-2 grid-cols-1 md:grid-cols-2">
          <label className="text-sm text-gray-600">
            Periode type
            <select
              className="mt-1 w-full rounded-md border border-gray-300 px-2 py-2 text-sm"
              value={periodType}
              onChange={(event) =>
                setPeriodType(event.target.value as ReportPeriodType)
              }
            >
              {PERIOD_TYPES.map((type) => (
                <option key={type.value} value={type.value}>
                  {type.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm text-gray-600">
            Periode
            <select
              className="mt-1 w-full rounded-md border border-gray-300 px-2 py-2 text-sm"
              value={periodValue}
              onChange={(event) => setPeriodValue(event.target.value)}
              disabled={availableOptions.length === 0}
            >
              {availableOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {optionsLoading && <LoadingSpinner label="Laster perioder..." />}
      {optionsError && (
        <ErrorMessage message="Kunne ikke laste tilgjengelige rapportperioder." />
      )}

      {!optionsLoading && !optionsError && availableOptions.length === 0 && (
        <ErrorMessage message="Ingen rapportperioder funnet for valgt type." />
      )}

      {!optionsLoading && !optionsError && availableOptions.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 text-sm text-gray-600">
          <p>
            Dataintervall: {optionsData?.data_start_date} til{" "}
            {optionsData?.data_end_date}
          </p>
          {selectedOption && (
            <p>
              Valgt periode: {selectedOption.start_date} til{" "}
              {selectedOption.end_date}
            </p>
          )}
        </div>
      )}

      {reportLoading && periodValue && (
        <LoadingSpinner label="Laster rapport..." />
      )}
      {reportError && <ErrorMessage message="Kunne ikke laste rapport." />}

      {report && (
        <>
          <div className="flex justify-end gap-2">
            <button
              onClick={handleExportExcel}
              className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-700"
            >
              Eksporter Excel
            </button>
            <button
              onClick={handleExportPdf}
              className="rounded-md bg-slate-700 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Eksporter PDF
            </button>
          </div>

          <div className="grid gap-3 grid-cols-2 md:grid-cols-4">
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Markedsverdi START
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-800">
                {nok(report.portfolio_start.totals.current_value)}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Markedsverdi SLUTT
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-800">
                {nok(report.portfolio_end.totals.current_value)}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Endring markedsverdi
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-800">
                {nok(
                  report.portfolio_end.totals.current_value -
                    report.portfolio_start.totals.current_value,
                )}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-gray-500">
                Kostpris (slutt)
              </p>
              <p className="mt-1 text-lg font-semibold text-gray-800">
                {nok(report.portfolio_end.totals.total_cost)}
              </p>
            </div>
          </div>

          {previousReport && (
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
              <p className="font-semibold">
                Sammenlignet med forrige periode ({previousReport.period_value})
              </p>
              <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                <p>
                  Endring markedsverdi samlet:{" "}
                  {nok(
                    report.portfolio_end.totals.current_value -
                      previousReport.portfolio_end.totals.current_value,
                  )}
                </p>
                <p>
                  Endring netto avkastning samlet:{" "}
                  {nok(
                    report.portfolio_end.totals.profit_loss_net -
                      previousReport.portfolio_end.totals.profit_loss_net,
                  )}
                </p>
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <SectionHeader title="Per fond" />
            <div className="mb-3 grid grid-cols-1 gap-2 md:grid-cols-4">
              <input
                type="text"
                value={fundFilter}
                onChange={(event) => setFundFilter(event.target.value)}
                placeholder="Sok ticker eller fond"
                className="rounded-md border border-gray-300 px-2 py-2 text-sm"
              />
              <select
                value={sortBy}
                onChange={(event) =>
                  setSortBy(
                    event.target.value as
                      | "current_value"
                      | "profit_loss_net"
                      | "gross_pct"
                      | "units",
                  )
                }
                className="rounded-md border border-gray-300 px-2 py-2 text-sm"
              >
                <option value="current_value">Sorter: Markedsverdi</option>
                <option value="profit_loss_net">
                  Sorter: Netto avkastning
                </option>
                <option value="gross_pct">Sorter: Total %</option>
                <option value="units">Sorter: Andeler</option>
              </select>
              <select
                value={sortDirection}
                onChange={(event) =>
                  setSortDirection(event.target.value as "asc" | "desc")
                }
                className="rounded-md border border-gray-300 px-2 py-2 text-sm"
              >
                <option value="desc">Rekkefolge: Hoyest forst</option>
                <option value="asc">Rekkefolge: Lavest forst</option>
              </select>
              <div className="text-sm text-gray-500 flex items-center">
                Viser {filteredFunds.length} av {report.funds.length} fond
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50">
                    <th className="px-3 py-2 text-left">Ticker</th>
                    <th className="px-3 py-2 text-left">Fond</th>
                    <th className="px-3 py-2 text-right">Andeler START</th>
                    <th className="px-3 py-2 text-right">Andeler SLUTT</th>
                    <th className="px-3 py-2 text-right">Verdi START</th>
                    <th className="px-3 py-2 text-right">Verdi SLUTT</th>
                    <th className="px-3 py-2 text-right">Kostpris</th>
                    <th className="px-3 py-2 text-right">Netto avkastning</th>
                    <th className="px-3 py-2 text-right">Total %</th>
                    <th className="px-3 py-2 text-left">Siste kursdato</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFunds.map((item) => {
                    return (
                      <tr key={item.fund_id} className="border-b">
                        <td className="px-3 py-2 font-medium text-gray-800">
                          {item.ticker}
                        </td>
                        <td className="px-3 py-2 text-gray-700">
                          {item.fund_name}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {item.start_units.toLocaleString("nb-NO", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 4,
                          })}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {item.end_units.toLocaleString("nb-NO", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 4,
                          })}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {nok(item.start_value)}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {nok(item.end_value)}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {nok(item.end_cost)}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {nok(item.summary.profit_loss_net)}
                        </td>
                        <td className="px-3 py-2 text-right text-gray-700">
                          {pct(
                            item.summary.period_metrics.Total.return_split
                              .gross_pct,
                          )}
                        </td>
                        <td className="px-3 py-2 text-gray-700">
                          {item.latest_price_date ?? "-"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
