import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.loan_rate_history import LoanRateHistory


class RateRepository:
    """Data-access operations for borrowing rate history."""
    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self.session = session

    def upsert_many(
        self, fund_id: uuid.UUID, rates: list[LoanRateHistory]
    ) -> list[LoanRateHistory]:
        """Insert or update many rates for a fund and return stored rows."""
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

    def list_for_fund(
        self,
        fund_id: uuid.UUID,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int | None = None,
    ) -> list[LoanRateHistory]:
        """List rates for a fund with optional date filtering and limit."""
        statement = select(LoanRateHistory).where(LoanRateHistory.fund_id == fund_id)

        if from_date is not None:
            statement = statement.where(LoanRateHistory.effective_date >= from_date)
        if to_date is not None:
            statement = statement.where(LoanRateHistory.effective_date <= to_date)

        statement = statement.order_by(LoanRateHistory.effective_date.asc())
        if limit is not None:
            statement = statement.limit(limit)

        return list(self.session.scalars(statement))

    def active_rate_on(self, fund_id: uuid.UUID, value_date: date) -> LoanRateHistory | None:
        """Return the active nominal rate on a specific date."""
        statement = (
            select(LoanRateHistory)
            .where(LoanRateHistory.fund_id == fund_id, LoanRateHistory.effective_date <= value_date)
            .order_by(LoanRateHistory.effective_date.desc())
            .limit(1)
        )
        return self.session.scalar(statement)
