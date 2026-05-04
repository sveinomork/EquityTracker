from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import yfinance as yf

from app.core.database import SessionLocal, create_db_and_tables
from app.models.daily_fund_price import DailyFundPrice
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.scripts.fund_identity import canonicalize_fund

LINE_PATTERN = re.compile(r"^(?P<name>.+?)\s*\((?P<symbol>[^()]+)\)\s*$")


@dataclass(frozen=True)
class TickerEntry:
    name: str
    symbol: str


def parse_ticker_file(ticker_file: Path) -> list[TickerEntry]:
    entries: list[TickerEntry] = []
    for raw_line in ticker_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = LINE_PATTERN.match(line)
        if match is None:
            continue

        entries.append(
            TickerEntry(
                name=match.group("name").strip(),
                symbol=match.group("symbol").strip(),
            )
        )
    return entries


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "unknown"


def _to_price_records(history_df: object) -> list[dict[str, object]]:
    if history_df is None or getattr(history_df, "empty", True):
        return []

    close_data = history_df["Close"]
    if getattr(close_data, "ndim", 1) == 2:
        close_series = close_data.iloc[:, 0].dropna()
    else:
        close_series = close_data.dropna()

    records: list[dict[str, object]] = []
    for idx, close in close_series.items():
        if hasattr(idx, "date"):
            day = idx.date().isoformat()
        else:
            day = str(idx)

        close_value = close.item() if hasattr(close, "item") else close
        records.append({"dato": day, "kurs": round(float(close_value), 4)})
    return records


def fetch_yahoo_prices(symbol: str, start_date: date, end_date: date) -> list[dict[str, object]]:
    # yfinance treats end as exclusive; add one day so the requested end date is included.
    history = yf.download(
        symbol,
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=False,
        actions=False,
    )
    return _to_price_records(history)


def write_price_file(
    output_dir: Path,
    entry: TickerEntry,
    records: list[dict[str, object]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{_slugify(entry.name)}-{_slugify(entry.symbol)}.json"
    output_path = output_dir / file_name
    output_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch historical close prices from Yahoo Finance for tickers in a text file "
            "and upsert them into the database. Funds that do not exist are created automatically."
        )
    )
    parser.add_argument(
        "--tickers-file",
        type=Path,
        default=Path("tiker.txt"),
        help="Text file containing lines like: Name (YAHOO_SYMBOL)",
    )
    parser.add_argument(
        "--start-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=date(2023, 1, 1),
        help="Start date in YYYY-MM-DD format. Default: 2023-01-01",
    )
    parser.add_argument(
        "--end-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=date.today(),
        help="End date in YYYY-MM-DD format. Default: today",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional: also write one JSON file per ticker to this directory",
    )
    return parser


def _upsert_to_db(
    fund_repo: FundRepository,
    price_repo: PriceRepository,
    entry: TickerEntry,
    records: list[dict[str, object]],
) -> int:
    canonical_name, ticker_key = canonicalize_fund(entry.name, entry.symbol)
    fund = fund_repo.get_by_ticker(ticker_key)
    if fund is None:
        fund = Fund(name=canonical_name, ticker=ticker_key)
        fund_repo.session.add(fund)
        fund_repo.session.flush()
        fund_repo.session.refresh(fund)
        print(f"  Created fund: {canonical_name} ({ticker_key})")
    elif fund.name != canonical_name:
        fund.name = canonical_name

    prices = [
        DailyFundPrice(
            fund_id=fund.id,
            date=date.fromisoformat(str(r["dato"])),
            price=Decimal(str(r["kurs"])),
        )
        for r in records
    ]
    upserted = price_repo.upsert_many(fund.id, prices)
    fund_repo.session.commit()
    return len(upserted)


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    entries = parse_ticker_file(args.tickers_file)
    if not entries:
        raise SystemExit(f"No valid ticker entries found in {args.tickers_file}")

    create_db_and_tables()

    with SessionLocal() as session:
        fund_repo = FundRepository(session)
        price_repo = PriceRepository(session)

        for entry in entries:
            records = fetch_yahoo_prices(
                entry.symbol, start_date=args.start_date, end_date=args.end_date
            )
            if not records:
                print(f"{entry.name} ({entry.symbol}): no data returned from Yahoo — skipped")
                continue

            count = _upsert_to_db(fund_repo, price_repo, entry, records)
            canonical_name, canonical_ticker = canonicalize_fund(entry.name, entry.symbol)
            print(
                f"{canonical_name} ({canonical_ticker}): {count} rows upserted into database"
            )

            if args.output_dir is not None:
                output_path = write_price_file(args.output_dir, entry, records)
                print(f"  -> also written to {output_path}")


if __name__ == "__main__":
    main()
