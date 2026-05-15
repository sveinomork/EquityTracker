import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.enums import TransactionType
from app.models.transaction import Transaction


class TransactionRepository:
    """Data-access operations for portfolio transactions."""
    def __init__(self, session: Session) -> None:
        """Initialize the repository with an active database session."""
        self.session = session

    def add(self, transaction: Transaction) -> Transaction:
        """Persist a transaction and return the refreshed entity."""
        self.session.add(transaction)
        self.session.flush()
        self.session.refresh(transaction)
        return transaction

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        """Return a transaction by id, or None if it does not exist."""
        return self.session.get(Transaction, transaction_id)

    def list_all(self) -> list[Transaction]:
        """List all transactions sorted by date and creation time."""
        statement = select(Transaction).order_by(
            Transaction.date.asc(),
            Transaction.created_at.asc(),
        )
        return list(self.session.scalars(statement))

    def list_for_fund(self, fund_id: uuid.UUID) -> list[Transaction]:
        """List all transactions for one fund sorted chronologically."""
        statement = (
            select(Transaction)
            .where(Transaction.fund_id == fund_id)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def list_buy_lots_for_fund(self, fund_id: uuid.UUID) -> list[Transaction]:
        """List BUY transactions for one fund in chronological order."""
        statement = (
            select(Transaction)
            .where(Transaction.fund_id == fund_id, Transaction.type == TransactionType.BUY)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def get_date_range(self, fund_id: uuid.UUID | None = None) -> tuple[date, date] | None:
        """Return earliest and latest transaction dates, optionally for a specific fund."""
        statement = select(func.min(Transaction.date), func.max(Transaction.date))
        if fund_id is not None:
            statement = statement.where(Transaction.fund_id == fund_id)

        min_date, max_date = self.session.execute(statement).one()
        if min_date is None or max_date is None:
            return None

        return min_date, max_date
