import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import TransactionType
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, numeric_column


class Transaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_fund_date", "fund_id", "date"),
        Index("ix_transactions_lot_id", "lot_id"),
    )

    fund_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("funds.id", ondelete="CASCADE"), index=True
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    date: Mapped[date]
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType, name="transaction_type"))
    units: Mapped[Decimal] = numeric_column()
    price_per_unit: Mapped[Decimal] = numeric_column()
    total_amount: Mapped[Decimal] = numeric_column(scale=2)
    borrowed_amount: Mapped[Decimal] = numeric_column(scale=2)
    equity_amount: Mapped[Decimal] = numeric_column(scale=2)

    fund = relationship("Fund", back_populates="transactions")
