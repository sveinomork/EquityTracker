import uuid
from decimal import Decimal

from app.domain.enums import TransactionType
from app.domain.exceptions import NotFoundError, ValidationError
from app.models.transaction import Transaction
from app.repositories.fund_repository import FundRepository
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.transaction import TransactionCreate, TransactionUpdate


class TransactionService:
    """Business operations for portfolio transactions."""
    def __init__(
        self,
        fund_repository: FundRepository,
        transaction_repository: TransactionRepository,
    ) -> None:
        """Initialize the service with fund and transaction repositories."""
        self.fund_repository = fund_repository
        self.transaction_repository = transaction_repository

    def create_transaction(self, payload: TransactionCreate) -> Transaction:
        """Create a transaction and apply type-specific validation rules."""
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

        if payload.type is TransactionType.SELL and payload.lot_id is None:
            return self._create_fifo_sell_transactions(payload)

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

    def update_transaction(
        self,
        transaction_id: uuid.UUID,
        payload: TransactionUpdate,
    ) -> Transaction:
        """Update an existing transaction with normalized values."""
        transaction = self.transaction_repository.get(transaction_id)
        if transaction is None:
            raise NotFoundError("Transaction not found")

        next_type = payload.type or transaction.type
        next_date = payload.date or transaction.date
        next_units_raw = Decimal(payload.units) if payload.units is not None else Decimal(transaction.units)
        next_units = -abs(next_units_raw) if next_type is TransactionType.SELL else abs(next_units_raw)
        next_total_amount = (
            Decimal(payload.total_amount)
            if payload.total_amount is not None
            else Decimal(transaction.total_amount)
        )
        next_borrowed_amount = (
            Decimal(payload.borrowed_amount)
            if payload.borrowed_amount is not None
            else Decimal(transaction.borrowed_amount)
        )
        next_lot_id = transaction.lot_id
        if "lot_id" in payload.model_fields_set:
            next_lot_id = payload.lot_id

        if next_borrowed_amount > next_total_amount:
            raise ValidationError("borrowed_amount cannot exceed total_amount")

        if next_type is TransactionType.BUY and next_lot_id is not None:
            raise ValidationError("BUY transactions cannot reference lot_id")
        if next_type is TransactionType.DIVIDEND_REINVEST and next_lot_id is None:
            raise ValidationError("DIVIDEND_REINVEST transactions must reference a lot_id")

        if next_lot_id is not None:
            lot = self.transaction_repository.get(next_lot_id)
            if lot is None:
                raise ValidationError("Referenced lot was not found")
            if lot.fund_id != transaction.fund_id:
                raise ValidationError("Referenced lot belongs to another fund")
            if lot.type is not TransactionType.BUY:
                raise ValidationError("lot_id must reference a BUY transaction")

        if payload.price_per_unit is not None:
            next_price_per_unit = Decimal(payload.price_per_unit)
        else:
            next_price_per_unit = (
                next_total_amount / abs(next_units)
                if abs(next_units) > Decimal("0")
                else Decimal(transaction.price_per_unit)
            )

        transaction.type = next_type
        transaction.date = next_date
        transaction.units = next_units
        transaction.lot_id = next_lot_id
        transaction.total_amount = next_total_amount
        transaction.borrowed_amount = next_borrowed_amount
        transaction.price_per_unit = next_price_per_unit
        transaction.equity_amount = next_total_amount - next_borrowed_amount

        self.transaction_repository.session.commit()
        self.transaction_repository.session.refresh(transaction)
        return transaction

    def _create_fifo_sell_transactions(self, payload: TransactionCreate) -> Transaction:
        """Split a SELL transaction across BUY lots using FIFO allocation."""
        transactions = self.transaction_repository.list_for_fund(payload.fund_id)
        buy_lots = [
            transaction
            for transaction in transactions
            if transaction.type is TransactionType.BUY and transaction.date <= payload.date
        ]
        if not buy_lots:
            raise ValidationError("No BUY lots available for SELL transaction")

        total_requested_units = abs(Decimal(payload.units))
        remaining_to_sell = total_requested_units
        available_by_lot: list[tuple[Transaction, Decimal]] = []

        for lot in buy_lots:
            related_units = sum(
                (
                    Decimal(item.units)
                    for item in transactions
                    if item.lot_id == lot.id and item.date <= payload.date
                ),
                start=Decimal("0"),
            )
            available_units = Decimal(lot.units) + related_units
            if available_units > Decimal("0"):
                available_by_lot.append((lot, available_units))

        total_available = sum((units for _, units in available_by_lot), start=Decimal("0"))
        if total_available < total_requested_units:
            raise ValidationError("Not enough available units across lots for SELL transaction")

        remaining_total_amount = Decimal(payload.total_amount)
        remaining_borrowed_amount = Decimal(payload.borrowed_amount)
        created_transactions: list[Transaction] = []

        for index, (lot, available_units) in enumerate(available_by_lot):
            if remaining_to_sell <= Decimal("0"):
                break

            sell_units = min(available_units, remaining_to_sell)
            is_last_split = index == len(available_by_lot) - 1 or (remaining_to_sell - sell_units) <= Decimal(
                "0"
            )

            if is_last_split:
                split_total_amount = remaining_total_amount
                split_borrowed_amount = remaining_borrowed_amount
            else:
                split_total_amount = (
                    (Decimal(payload.total_amount) * sell_units / total_requested_units)
                    .quantize(Decimal("0.01"))
                )
                split_borrowed_amount = (
                    (Decimal(payload.borrowed_amount) * sell_units / total_requested_units)
                    .quantize(Decimal("0.01"))
                )

            equity_amount = split_total_amount - split_borrowed_amount
            transaction = Transaction(
                fund_id=payload.fund_id,
                lot_id=lot.id,
                date=payload.date,
                type=payload.type,
                units=-sell_units,
                price_per_unit=payload.price_per_unit,
                total_amount=split_total_amount,
                borrowed_amount=split_borrowed_amount,
                equity_amount=equity_amount,
            )
            created_transactions.append(self.transaction_repository.add(transaction))

            remaining_to_sell -= sell_units
            remaining_total_amount -= split_total_amount
            remaining_borrowed_amount -= split_borrowed_amount

        self.transaction_repository.session.commit()
        return created_transactions[0]

    def list_transactions(self, fund_id: uuid.UUID | None = None) -> list[Transaction]:
        """List transactions globally or for a specific fund."""
        if fund_id is None:
            return self.transaction_repository.list_all()
        return self.transaction_repository.list_for_fund(fund_id)
