"""Service that fetches current prices from Yahoo Finance and upserts them into the DB."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.daily_fund_price import DailyFundPrice
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.scripts.fund_identity import CANONICAL_BY_SYMBOL

# Yahoo symbol → canonical ticker map (same source as fetch_yahoo_prices.py)
YAHOO_SYMBOLS: dict[str, str] = {
    symbol: ticker for symbol, (_name, ticker) in CANONICAL_BY_SYMBOL.items()
}


@dataclass(frozen=True)
class SyncResult:
    ticker: str
    upserted: int
    error: str | None = None


def sync_yahoo_prices(
    session: Session,
    start_date: date | None = None,
) -> list[SyncResult]:
    """Fetch prices from Yahoo Finance for all known symbols and upsert into DB."""
    try:
        import yfinance as yf  # imported here so import error is local
    except ImportError:
        return [SyncResult(ticker="*", upserted=0, error="yfinance is not installed")]

    import pandas as pd  # noqa: PLC0415

    fund_repo = FundRepository(session)
    price_repo = PriceRepository(session)

    effective_start = start_date or date(2023, 1, 1)
    results: list[SyncResult] = []

    for symbol, ticker in YAHOO_SYMBOLS.items():
        fund = fund_repo.get_by_ticker(ticker)
        if fund is None:
            results.append(SyncResult(ticker=ticker, upserted=0, error="Fund not in DB"))
            continue

        try:
            history = yf.download(
                symbol,
                start=effective_start.isoformat(),
                auto_adjust=False,
                actions=False,
                progress=False,
            )
            if history is None or history.empty:
                results.append(SyncResult(ticker=ticker, upserted=0, error="No data from Yahoo"))
                continue

            close = history["Close"]
            if getattr(close, "ndim", 1) == 2:
                close = close.iloc[:, 0]
            close = close.dropna()

            prices: list[DailyFundPrice] = [
                DailyFundPrice(
                    fund_id=fund.id,
                    date=idx.date() if isinstance(idx, pd.Timestamp) else idx,
                    price=Decimal(str(round(float(val), 6))),
                )
                for idx, val in close.items()
            ]

            upserted = price_repo.upsert_many(fund.id, prices)
            results.append(SyncResult(ticker=ticker, upserted=len(upserted)))
        except Exception as exc:  # noqa: BLE001
            results.append(SyncResult(ticker=ticker, upserted=0, error=str(exc)))

    session.commit()
    return results
