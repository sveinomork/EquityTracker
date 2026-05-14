"""Delete funds that have no market value as of a given date.

By default, runs in dry-run mode and only prints what would be deleted.

Run:
    uv run python -m app.scripts.cleanup_funds_without_market_value
    uv run python -m app.scripts.cleanup_funds_without_market_value --apply
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal, create_db_and_tables
from app.models.fund import Fund
from app.repositories.fund_repository import FundRepository
from app.repositories.price_repository import PriceRepository
from app.repositories.rate_repository import RateRepository
from app.repositories.transaction_repository import TransactionRepository
from app.services.interest_service import InterestService
from app.services.portfolio_analytics_service import PortfolioAnalyticsService

DECIMAL_ZERO = Decimal("0")


@dataclass(slots=True)
class CleanupCandidate:
    """Fund entry marked for optional deletion by cleanup script."""
    fund_id: str
    ticker: str
    name: str
    current_value: Decimal


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for cleanup execution."""
    parser = argparse.ArgumentParser(description="Delete funds with no market value")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete candidates. Without this flag the script is a dry-run.",
    )
    parser.add_argument(
        "--as-of-date",
        type=date.fromisoformat,
        default=date.today(),
        help="Evaluate market value on this date (YYYY-MM-DD). Default: today.",
    )
    return parser.parse_args()


def _find_candidates(as_of_date: date) -> list[CleanupCandidate]:
    """Find funds whose current market value is zero or negative."""
    with SessionLocal() as session:
        funds = list(session.scalars(select(Fund).order_by(Fund.ticker.asc())))
        service = PortfolioAnalyticsService(
            FundRepository(session),
            TransactionRepository(session),
            PriceRepository(session),
            RateRepository(session),
            InterestService(),
        )

        candidates: list[CleanupCandidate] = []
        for fund in funds:
            summary = service.get_fund_summary(fund.id, as_of_date=as_of_date)
            if summary.current_value <= DECIMAL_ZERO:
                candidates.append(
                    CleanupCandidate(
                        fund_id=str(fund.id),
                        ticker=fund.ticker,
                        name=fund.name,
                        current_value=summary.current_value,
                    )
                )
        return candidates


def _apply_deletions(candidates: list[CleanupCandidate]) -> int:
    """Delete all candidate funds and return the number removed."""
    if not candidates:
        return 0

    candidate_ids = {item.fund_id for item in candidates}

    with SessionLocal() as session:
        funds_to_delete = [
            fund
            for fund in session.scalars(select(Fund))
            if str(fund.id) in candidate_ids
        ]

        for fund in funds_to_delete:
            session.delete(fund)

        session.commit()
        return len(funds_to_delete)


def main() -> None:
    """Run dry-run or apply cleanup for funds without market value."""
    args = _parse_args()
    create_db_and_tables()

    candidates = _find_candidates(as_of_date=args.as_of_date)

    print(f"As-of date: {args.as_of_date.isoformat()}")
    print(f"Found {len(candidates)} fund(s) with no market value.")

    for item in candidates:
        print(
            f"  - {item.ticker} | {item.name} | current_value={item.current_value:,.2f}"
        )

    if not args.apply:
        print("Dry-run only. Re-run with --apply to delete these funds.")
        return

    deleted = _apply_deletions(candidates)
    print(f"Deleted {deleted} fund(s).")


if __name__ == "__main__":
    main()
