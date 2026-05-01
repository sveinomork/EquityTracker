import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.daily_fund_price import DailyFundPrice


class PriceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(self, fund_id: uuid.UUID, prices: list[DailyFundPrice]) -> list[DailyFundPrice]:
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
        statement = (
            select(DailyFundPrice)
            .where(DailyFundPrice.fund_id == fund_id, DailyFundPrice.date <= value_date)
            .order_by(DailyFundPrice.date.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def latest_on_or_before_with_max_staleness(
        self,
        fund_id: uuid.UUID,
        value_date: date,
        max_staleness_days: int,
    ) -> DailyFundPrice | None:
        latest = self.latest_on_or_before(fund_id, value_date)
        if latest is None:
            return None

        staleness = (value_date - latest.date).days
        if staleness > max_staleness_days:
            return None

        return latest
