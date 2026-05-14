from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, create_db_and_tables
from app.domain.enums import TransactionType
from app.models.fund import Fund
from app.models.transaction import Transaction
from app.scripts.fund_identity import canonicalize_fund


@dataclass(frozen=True)
class SeedTransaction:
    """Seed entry describing one BUY transaction to import."""
    fund_name: str
    fund_ticker: str
    trade_date: date
    total_amount: Decimal
    units: Decimal


SEED_TRANSACTIONS: list[SeedTransaction] = [
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2026, 1, 14), Decimal("10000.00"), Decimal("0.9332")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 10, 21), Decimal("50000.00"), Decimal("4.34")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 8, 27), Decimal("50000.00"), Decimal("4.40")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 6, 3), Decimal("100000.00"), Decimal("9.03")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 5, 27), Decimal("150000.00"), Decimal("13.54")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 5, 15), Decimal("150000.00"), Decimal("13.57")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 5, 6), Decimal("200000.00"), Decimal("18.14")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 4, 29), Decimal("100000.00"), Decimal("9.10")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 4, 22), Decimal("200000.00"), Decimal("18.23")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 4, 16), Decimal("200000.00"), Decimal("18.22")),
    SeedTransaction("Fondsfinans High Yield", "FHY", date(2024, 4, 9), Decimal("300000.00"), Decimal("27.38")),
    SeedTransaction("Heimdal Høyrente", "HHR", date(2024, 6, 10), Decimal("100000.00"), Decimal("795.62")),
    SeedTransaction("Heimdal Høyrente", "HHR", date(2024, 8, 7), Decimal("100000.00"), Decimal("786.71")),
    SeedTransaction("Heimdal Høyrente", "HHR", date(2024, 7, 30), Decimal("100000.00"), Decimal("779.23")),
    SeedTransaction("Heimdal Høyrente", "HHR", date(2024, 8, 27), Decimal("50000.00"), Decimal("387.23")),
    SeedTransaction("Heimdal Høyrente", "HHR", date(2024, 9, 3), Decimal("100000.00"), Decimal("770.64")),
    SeedTransaction("Heimdal Høyrente", "HHR", date(2024, 10, 21), Decimal("150000.00"), Decimal("1140.93")),
    SeedTransaction("Heimdal Høyrente Plus", "HHRP", date(2025, 9, 30), Decimal("100000.00"), Decimal("1000.00")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 1, 9), Decimal("25000.00"), Decimal("169.078")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 1, 10), Decimal("11956.00"), Decimal("80.941")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 2, 6), Decimal("20000.00"), Decimal("133.6")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 2, 12), Decimal("50000.00"), Decimal("332.314")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 2, 19), Decimal("30000.00"), Decimal("197.993")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 2, 25), Decimal("20000.00"), Decimal("131.544")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 2, 27), Decimal("20077.20"), Decimal("131.844")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 3, 3), Decimal("12153.83"), Decimal("79.962")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 3, 6), Decimal("50000.00"), Decimal("327.976")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 6, 17), Decimal("20000.00"), Decimal("128.932")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 7, 1), Decimal("30000.00"), Decimal("192.283")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 7, 24), Decimal("50000.00"), Decimal("317.561")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 7, 29), Decimal("20000.00"), Decimal("126.823")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 8, 1), Decimal("30000.00"), Decimal("189.334")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 8, 4), Decimal("40000.00"), Decimal("252.509")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 8, 19), Decimal("40000.00"), Decimal("249.953")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 8, 28), Decimal("3000.00"), Decimal("18.723")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 9, 11), Decimal("12000.00"), Decimal("74.538")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 9, 24), Decimal("60000.00"), Decimal("368.958")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2025, 10, 2), Decimal("50000.00"), Decimal("307.012")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2026, 1, 20), Decimal("11000.00"), Decimal("65.25")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2026, 1, 27), Decimal("30000.00"), Decimal("176.855")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2026, 2, 6), Decimal("40000.00"), Decimal("234.068")),
    SeedTransaction("Kraft Nordic Bonds B", "KNB", date(2026, 2, 13), Decimal("50000.00"), Decimal("291.562")),

    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 1, 9), Decimal("25000.00"), Decimal("209.52")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 1, 16), Decimal("12000.00"), Decimal("100.062")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 2, 6), Decimal("20000.00"), Decimal("165.521")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 2, 12), Decimal("50000.00"), Decimal("412.507")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 2, 19), Decimal("30000.00"), Decimal("246.487")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 3, 6), Decimal("50000.00"), Decimal("408.296")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 4, 30), Decimal("10000.00"), Decimal("82.189")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 6, 10), Decimal("35000.00"), Decimal("280.022")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 6, 17), Decimal("30000.00"), Decimal("239.52")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 7, 1), Decimal("30000.00"), Decimal("237.83")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 7, 14), Decimal("15000.00"), Decimal("118.221")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 7, 24), Decimal("50000.00"), Decimal("393.019")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 7, 29), Decimal("22000.00"), Decimal("172.75")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 8, 1), Decimal("31000.00"), Decimal("242.832")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 8, 4), Decimal("30000.00"), Decimal("234.999")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 8, 19), Decimal("35000.00"), Decimal("271.802")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 9, 11), Decimal("8000.00"), Decimal("61.857")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 9, 24), Decimal("45000.00"), Decimal("346.100")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2025, 10, 2), Decimal("20000.00"), Decimal("153.633")),
    SeedTransaction("Kraft Høyrente D", "KHD", date(2026, 1, 14), Decimal("50000.00"), Decimal("376.166")),
]


def _get_or_create_fund(session: Session, name: str, ticker: str) -> Fund:
    """Return an existing canonical fund or create it when missing."""
    canonical_name, canonical_ticker = canonicalize_fund(name, ticker)
    statement = select(Fund).where(Fund.ticker == canonical_ticker)
    fund = session.scalar(statement)
    if fund is not None:
        if fund.name != canonical_name:
            fund.name = canonical_name
        return fund

    fund = Fund(name=canonical_name, ticker=canonical_ticker)
    session.add(fund)
    session.flush()
    session.refresh(fund)
    return fund


def _get_existing_transaction(
    session: Session, fund_id: object, tx: SeedTransaction
) -> Transaction | None:
    """Find an existing BUY transaction matching seed identity fields."""
    statement = select(Transaction).where(
        Transaction.fund_id == fund_id,
        Transaction.date == tx.trade_date,
        Transaction.type == TransactionType.BUY,
        Transaction.units == tx.units,
        Transaction.total_amount == tx.total_amount,
    )
    return session.scalar(statement)


def _price_per_unit(total_amount: Decimal, units: Decimal) -> Decimal:
    """Calculate and quantize unit price from total amount and units."""
    return (total_amount / units).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def main() -> None:
    """Upsert seeded BUY transactions and print processing totals."""
    create_db_and_tables()

    inserted = 0
    updated = 0

    with SessionLocal() as session:
        for tx in SEED_TRANSACTIONS:
            fund = _get_or_create_fund(session, tx.fund_name, tx.fund_ticker)
            existing = _get_existing_transaction(session, fund.id, tx)

            if existing is not None:
                existing.price_per_unit = _price_per_unit(tx.total_amount, tx.units)
                existing.borrowed_amount = tx.total_amount
                existing.equity_amount = Decimal("0.00")
                updated += 1
                continue

            transaction = Transaction(
                fund_id=fund.id,
                lot_id=None,
                date=tx.trade_date,
                type=TransactionType.BUY,
                units=tx.units,
                price_per_unit=_price_per_unit(tx.total_amount, tx.units),
                total_amount=tx.total_amount,
                borrowed_amount=tx.total_amount,
                equity_amount=Decimal("0.00"),
            )
            session.add(transaction)
            inserted += 1

        session.commit()

    print(f"Transactions processed: {len(SEED_TRANSACTIONS)}")
    print(f"Inserted: {inserted}")
    print(f"Updated existing: {updated}")


if __name__ == "__main__":
    main()
