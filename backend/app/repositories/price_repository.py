import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.daily_fund_price import DailyFundPrice


class PriceRepository:
    """Data-access operations for daily fund prices."""
    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self.session = session

    def upsert_many(self, fund_id: uuid.UUID, prices: list[DailyFundPrice]) -> list[DailyFundPrice]:
        """Insert or update many prices for a fund and return stored rows."""
        stored: list[DailyFundPrice] = []
        for price in prices:
            statement = select(DailyFundPrice).where(
                DailyFundPrice.fund_id == fund_id,
                DailyFundPrice.date == price.date,
            )
            existing = self.session.scalar(statement)
            if existing is None:
                self.session.add(price)
                stored.append(price)
            else:
                existing.price = price.price
                stored.append(existing)

        self.session.flush()
        for item in stored:
            self.session.refresh(item)
        return stored

    def list_for_fund(
        self,
        fund_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int | None = None,
    ) -> list[DailyFundPrice]:
        """List prices for a fund with optional date filtering and limit."""
        statement = select(DailyFundPrice).where(DailyFundPrice.fund_id == fund_id)

        if from_date is not None:
            statement = statement.where(DailyFundPrice.date >= from_date)
        if to_date is not None:
            statement = statement.where(DailyFundPrice.date <= to_date)

        statement = statement.order_by(DailyFundPrice.date.asc())
        if limit is not None:
            statement = statement.limit(limit)

        return list(self.session.scalars(statement))

    def latest_on_or_before(self, fund_id: uuid.UUID, value_date: date) -> DailyFundPrice | None:
        """Return the latest price on or before a date."""
        statement = (
            select(DailyFundPrice)
            .where(DailyFundPrice.fund_id == fund_id, DailyFundPrice.date <= value_date)
            .order_by(DailyFundPrice.date.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def earliest_on_or_after(self, fund_id: uuid.UUID, value_date: date) -> DailyFundPrice | None:
        """Return the earliest price on or after a date."""
        statement = (
            select(DailyFundPrice)
            .where(DailyFundPrice.fund_id == fund_id, DailyFundPrice.date >= value_date)
            .order_by(DailyFundPrice.date.asc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def latest_on_or_before_with_max_staleness(
        self,
        fund_id: uuid.UUID,
        value_date: date,
        max_staleness_days: int,
    ) -> DailyFundPrice | None:
        """Return the latest price only if it is within the allowed staleness window."""
        latest = self.latest_on_or_before(fund_id, value_date)
        if latest is None:
            return None

        staleness = (value_date - latest.date).days
        if staleness > max_staleness_days:
            return None

        return latest

    def get_date_range(self, fund_id: uuid.UUID | None = None) -> tuple[date, date] | None:
        """Return earliest and latest price dates, optionally for a specific fund."""
        statement = select(func.min(DailyFundPrice.date), func.max(DailyFundPrice.date))
        if fund_id is not None:
            statement = statement.where(DailyFundPrice.fund_id == fund_id)

        min_date, max_date = self.session.execute(statement).one()
        if min_date is None or max_date is None:
            return None

        return min_date, max_date
