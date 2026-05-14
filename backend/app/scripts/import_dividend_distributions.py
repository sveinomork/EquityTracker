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
class DividendSeed:
    """Seed entry describing one annual dividend distribution."""
    fund_ticker: str
    year: int
    total_dividend: Decimal
    total_reinvested_units: Decimal


DIVIDEND_DISTRIBUTIONS: list[DividendSeed] = [
    DividendSeed(
        fund_ticker="FHY",
        year=2024,
        total_dividend=Decimal("135686.69"),
        total_reinvested_units=Decimal("12.67"),
    ),
    DividendSeed(
        fund_ticker="HHR",
        year=2024,
        total_dividend=Decimal("58250.25"),
        total_reinvested_units=Decimal("481.56"),
    ),
    DividendSeed(
        fund_ticker="FHY",
        year=2025,
        total_dividend=Decimal("170420.31"),
        total_reinvested_units=Decimal("16.0127"),
    ),
    DividendSeed(
        fund_ticker="HHR",
        year=2025,
        total_dividend=Decimal("80757.88"),
        total_reinvested_units=Decimal("683.3748"),
    ),
    DividendSeed(
        fund_ticker="HHRP",
        year=2025,
        total_dividend=Decimal("1392.90"),
        total_reinvested_units=Decimal("13.8787"),
    ),

]


def _get_fund(session: Session, fund_ticker: str) -> Fund:
    """Fetch a fund by canonical ticker and normalize its name."""
    canonical_name, canonical_ticker = canonicalize_fund("", fund_ticker)
    statement = select(Fund).where(Fund.ticker == canonical_ticker)
    fund = session.scalar(statement)
    if fund is None:
        raise ValueError(f"Fund not found: {canonical_ticker}")
    if fund.name != canonical_name:
        fund.name = canonical_name
    return fund


def _get_eligible_lots(session: Session, fund_id: object, year: int) -> list[Transaction]:
    """Return BUY lots eligible for annual dividend allocation."""
    distribution_date = date(year, 12, 31)
    statement = (
        select(Transaction)
        .where(
            Transaction.fund_id == fund_id,
            Transaction.type == TransactionType.BUY,
            Transaction.date <= distribution_date,
        )
        .order_by(Transaction.date.asc(), Transaction.created_at.asc())
    )
    return list(session.scalars(statement))


def _already_exists(session: Session, lot_id: object, distribution_date: date) -> bool:
    """Check whether a dividend reinvest transaction already exists for a lot/date."""
    statement = select(Transaction).where(
        Transaction.lot_id == lot_id,
        Transaction.type == TransactionType.DIVIDEND_REINVEST,
        Transaction.date == distribution_date,
    )
    return session.scalar(statement) is not None


def _quantize_units(value: Decimal) -> Decimal:
    """Quantize units to six decimal places using half-up rounding."""
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def _quantize_amount(value: Decimal) -> Decimal:
    """Quantize amount to two decimal places using half-up rounding."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _insert_dividends_for_seed(session: Session, seed: DividendSeed) -> tuple[int, int]:
    """Insert dividend reinvest rows for one seed and return inserted/skipped counts."""
    fund = _get_fund(session, seed.fund_ticker)
    lots = _get_eligible_lots(session, fund.id, seed.year)
    if not lots:
        raise ValueError(
            f"No eligible BUY lots found for {seed.fund_ticker} in year {seed.year}"
        )

    distribution_date = date(seed.year, 12, 31)
    total_lot_units = sum((Decimal(lot.units) for lot in lots), start=Decimal("0"))
    if total_lot_units <= Decimal("0"):
        raise ValueError(f"Total units are zero for {seed.fund_ticker} in year {seed.year}")

    inserted = 0
    skipped = 0

    allocated_units_sum = Decimal("0")
    allocated_amount_sum = Decimal("0")

    for idx, lot in enumerate(lots):
        if _already_exists(session, lot.id, distribution_date):
            skipped += 1
            continue

        is_last = idx == len(lots) - 1

        if is_last:
            units = _quantize_units(seed.total_reinvested_units - allocated_units_sum)
            amount = _quantize_amount(seed.total_dividend - allocated_amount_sum)
        else:
            ratio = Decimal(lot.units) / total_lot_units
            units = _quantize_units(seed.total_reinvested_units * ratio)
            amount = _quantize_amount(seed.total_dividend * ratio)
            allocated_units_sum += units
            allocated_amount_sum += amount

        if units <= Decimal("0") or amount <= Decimal("0"):
            continue

        price_per_unit = _quantize_units(amount / units)
        dividend_tx = Transaction(
            fund_id=fund.id,
            lot_id=lot.id,
            date=distribution_date,
            type=TransactionType.DIVIDEND_REINVEST,
            units=units,
            price_per_unit=price_per_unit,
            total_amount=amount,
            borrowed_amount=Decimal("0.00"),
            equity_amount=amount,
        )
        session.add(dividend_tx)
        inserted += 1

    return inserted, skipped


def main() -> None:
    """Import annual dividend distributions into transaction data."""
    create_db_and_tables()

    with SessionLocal() as session:
        total_inserted = 0
        total_skipped = 0

        for seed in DIVIDEND_DISTRIBUTIONS:
            inserted, skipped = _insert_dividends_for_seed(session, seed)
            total_inserted += inserted
            total_skipped += skipped
            print(
                f"{seed.fund_ticker} ({seed.year}) -> inserted: {inserted}, skipped: {skipped}"
            )

        session.commit()

    print(f"Total inserted dividend rows: {total_inserted}")
    print(f"Total skipped existing rows: {total_skipped}")


if __name__ == "__main__":
    main()
