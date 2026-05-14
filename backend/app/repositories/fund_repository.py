import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.fund import Fund


class FundRepository:
    """Data-access operations for fund entities."""
    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self.session = session

    def add(self, fund: Fund) -> Fund:
        """Persist a fund and return the refreshed entity."""
        self.session.add(fund)
        self.session.flush()
        self.session.refresh(fund)
        return fund

    def list_all(self) -> list[Fund]:
        """Return all funds ordered by name."""
        statement = select(Fund).order_by(Fund.name.asc())
        return list(self.session.scalars(statement))

    def get(self, fund_id: uuid.UUID) -> Fund | None:
        """Return a fund by id, or None if it does not exist."""
        return self.session.get(Fund, fund_id)

    def get_by_ticker(self, ticker: str) -> Fund | None:
        """Return a fund by ticker, or None if it does not exist."""
        statement = select(Fund).where(Fund.ticker == ticker)
        return self.session.scalar(statement)
