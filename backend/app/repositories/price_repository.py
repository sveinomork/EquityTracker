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

    def list_for_fund(self, fund_id: uuid.UUID) -> list[DailyFundPrice]:
        statement = (
            select(DailyFundPrice)
            .where(DailyFundPrice.fund_id == fund_id)
            .order_by(DailyFundPrice.date.asc())
        )
        return list(self.session.scalars(statement))

    def latest_on_or_before(self, fund_id: uuid.UUID, value_date: date) -> DailyFundPrice | None:
        statement = (
            select(DailyFundPrice)
            .where(DailyFundPrice.fund_id == fund_id, DailyFundPrice.date <= value_date)
            .order_by(DailyFundPrice.date.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
