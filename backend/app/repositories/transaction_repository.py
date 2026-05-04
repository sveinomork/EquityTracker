import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.enums import TransactionType
from app.models.transaction import Transaction


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, transaction: Transaction) -> Transaction:
        self.session.add(transaction)
        self.session.flush()
        self.session.refresh(transaction)
        return transaction

    def get(self, transaction_id: uuid.UUID) -> Transaction | None:
        return self.session.get(Transaction, transaction_id)

    def list_all(self) -> list[Transaction]:
        statement = select(Transaction).order_by(
            Transaction.date.asc(),
            Transaction.created_at.asc(),
        )
        return list(self.session.scalars(statement))

    def list_for_fund(self, fund_id: uuid.UUID) -> list[Transaction]:
        statement = (
            select(Transaction)
            .where(Transaction.fund_id == fund_id)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
        )
        return list(self.session.scalars(statement))

    def list_buy_lots_for_fund(self, fund_id: uuid.UUID) -> list[Transaction]:
        statement = (
            select(Transaction)
            .where(Transaction.fund_id == fund_id, Transaction.type == TransactionType.BUY)
            .order_by(Transaction.date.asc(), Transaction.created_at.asc())
        )
        return list(self.session.scalars(statement))
