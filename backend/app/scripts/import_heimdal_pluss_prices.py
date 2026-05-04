"""
Import historical prices for Heimdal Høyrente Plus (HHRP) into the database.

Reads price data from heimdal.json located in the backend root directory.

Run:
    uv run python -m app.scripts.import_heimdal_pluss_prices
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.core.database import SessionLocal, create_db_and_tables
from app.models.daily_fund_price import DailyFundPrice
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.scripts.fund_identity import CANONICAL_BY_TICKER

FUND_TICKER = "HHRP"
FUND_NAME = CANONICAL_BY_TICKER[FUND_TICKER]

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
HEIMDAL_JSON = _BACKEND_ROOT / "heimdal.json"



def main() -> None:
    create_db_and_tables()

    if not HEIMDAL_JSON.exists():
        print(f"ERROR: {HEIMDAL_JSON} not found.")
        return

    raw = json.loads(HEIMDAL_JSON.read_text(encoding="utf-8"))
    entries: list[tuple[date, Decimal]] = [
        (date.fromisoformat(item["dato"]), Decimal(str(item["kurs"])))
        for item in raw
    ]
    print(f"Loaded {len(entries)} price entries from {HEIMDAL_JSON.name}")

    with SessionLocal() as session:
        fund_repo = FundRepository(session)
        price_repo = PriceRepository(session)

        fund = fund_repo.get_by_ticker(FUND_TICKER)
        if fund is None:
            fund = Fund(name=FUND_NAME, ticker=FUND_TICKER)
            session.add(fund)
            session.flush()
            session.refresh(fund)
            print(f"Created fund: {FUND_NAME} ({FUND_TICKER})")
        else:
            print(f"Found existing fund: {fund.name} ({fund.ticker})")

        prices = [
            DailyFundPrice(
                fund_id=fund.id,
                date=dato,
                price=kurs,
            )
            for dato, kurs in entries
        ]

        upserted = price_repo.upsert_many(fund.id, prices)
        session.commit()
        print(f"Upserted {len(upserted)} price records into database")


if __name__ == "__main__":
    main()
