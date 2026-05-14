from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal, create_db_and_tables
from app.models.fund import Fund
from app.models.loan_rate_history import LoanRateHistory
from app.repositories.rate_repository import RateRepository

LOAN_TICKERS = ("FHY", "HHR", "HHRP", "KNB", "KHD")


@dataclass(frozen=True)
class SeedRate:
    """Seed entry describing one effective loan rate."""
    effective_date: date
    nominal_rate: Decimal


SEED_RATES: list[SeedRate] = [
    SeedRate(effective_date=date(2024, 1, 1), nominal_rate=Decimal("5.50")),
    SeedRate(effective_date=date(2025, 8, 18), nominal_rate=Decimal("4.73")),
    SeedRate(effective_date=date(2025, 9, 26), nominal_rate=Decimal("4.48")),
]


def main() -> None:
    """Upsert predefined loan rates for selected funds."""
    create_db_and_tables()

    with SessionLocal() as session:
        funds = list(
            session.scalars(
                select(Fund).where(Fund.ticker.in_(LOAN_TICKERS)).order_by(Fund.name.asc())
            )
        )
        if not funds:
            print("No funds found. Seed transactions first.")
            return

        repo = RateRepository(session)
        total_upserted = 0

        for fund in funds:
            rates = [
                LoanRateHistory(
                    fund_id=fund.id,
                    effective_date=item.effective_date,
                    nominal_rate=item.nominal_rate,
                )
                for item in SEED_RATES
            ]
            upserted = repo.upsert_many(fund.id, rates)
            total_upserted += len(upserted)
            print(f"{fund.name} ({fund.ticker}) -> upserted rates: {len(upserted)}")

        session.commit()

    print(f"Total rate rows upserted: {total_upserted}")


if __name__ == "__main__":
    main()
