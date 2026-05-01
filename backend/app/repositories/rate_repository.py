import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.loan_rate_history import LoanRateHistory


class RateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_many(
        self, fund_id: uuid.UUID, rates: list[LoanRateHistory]
    ) -> list[LoanRateHistory]:
        stored: list[LoanRateHistory] = []
        for rate in rates:
            statement = select(LoanRateHistory).where(
                LoanRateHistory.fund_id == fund_id,
                LoanRateHistory.effective_date == rate.effective_date,
            )
            existing = self.session.scalar(statement)
            if existing is None:
                self.session.add(rate)
                stored.append(rate)
            else:
                existing.nominal_rate = rate.nominal_rate
                stored.append(existing)

        self.session.flush()
        for item in stored:
            self.session.refresh(item)
        return stored

    def list_for_fund(self, fund_id: uuid.UUID) -> list[LoanRateHistory]:
        statement = (
            select(LoanRateHistory)
            .where(LoanRateHistory.fund_id == fund_id)
            .order_by(LoanRateHistory.effective_date.asc())
        )
        return list(self.session.scalars(statement))

    def active_rate_on(self, fund_id: uuid.UUID, value_date: date) -> LoanRateHistory | None:
        statement = (
            select(LoanRateHistory)
            .where(LoanRateHistory.fund_id == fund_id, LoanRateHistory.effective_date <= value_date)
            .order_by(LoanRateHistory.effective_date.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
