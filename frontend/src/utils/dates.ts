/** Returns a new Date with `days` subtracted. */
export function subDays(d: Date, days: number): Date {
  const result = new Date(d);
  result.setDate(result.getDate() - days);
  return result;
}

/** Formats a Date as "YYYY-MM-DD". */
export function format(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/** Formats a number as Norwegian NOK string. */
export function nok(value: number, decimals = 0): string {
  return new Intl.NumberFormat("nb-NO", {
    style: "currency",
    currency: "NOK",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/** Formats a number as a percentage string with sign. */
export function pct(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "N/A";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)} %`;
}
