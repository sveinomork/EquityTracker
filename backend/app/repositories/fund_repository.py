import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fund import Fund


class FundRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, fund: Fund) -> Fund:
        self.session.add(fund)
        self.session.flush()
        self.session.refresh(fund)
        return fund

    def list_all(self) -> list[Fund]:
        statement = select(Fund).order_by(Fund.name.asc())
        return list(self.session.scalars(statement))

    def get(self, fund_id: uuid.UUID) -> Fund | None:
        return self.session.get(Fund, fund_id)

    def get_by_ticker(self, ticker: str) -> Fund | None:
        statement = select(Fund).where(Fund.ticker == ticker)
        return self.session.scalar(statement)
