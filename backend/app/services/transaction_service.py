import uuid
from decimal import Decimal

from app.domain.enums import TransactionType
from app.domain.exceptions import NotFoundError, ValidationError
from app.models.transaction import Transaction
from app.repositories.fund_repository import FundRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate


class TransactionService:
    def __init__(
        self,
        fund_repository: FundRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        self.fund_repository = fund_repository
        self.transaction_repository = transaction_repository

    def create_transaction(self, payload: TransactionCreate) -> Transaction:
        fund = self.fund_repository.get(payload.fund_id)
        if fund is None:
            raise NotFoundError("Fund not found")

        if payload.type is TransactionType.BUY and payload.lot_id is not None:
            raise ValidationError("BUY transactions cannot reference lot_id")

        if payload.lot_id is not None:
            lot = self.transaction_repository.get(payload.lot_id)
            if lot is None:
                raise ValidationError("Referenced lot was not found")
            if lot.fund_id != payload.fund_id:
                raise ValidationError("Referenced lot belongs to another fund")
            if lot.type is not TransactionType.BUY:
                raise ValidationError("lot_id must reference a BUY transaction")

        equity_amount = Decimal(payload.total_amount) - Decimal(payload.borrowed_amount)
        transaction = Transaction(
            fund_id=payload.fund_id,
            lot_id=payload.lot_id,
            date=payload.date,
            type=payload.type,
            units=payload.units,
            price_per_unit=payload.price_per_unit,
            total_amount=payload.total_amount,
            borrowed_amount=payload.borrowed_amount,
            equity_amount=equity_amount,
        )
        created = self.transaction_repository.add(transaction)
        self.transaction_repository.session.commit()
        return created

    def list_transactions(self, fund_id: uuid.UUID | None = None) -> list[Transaction]:
        if fund_id is None:
            return self.transaction_repository.list_all()
        return self.transaction_repository.list_for_fund(fund_id)
