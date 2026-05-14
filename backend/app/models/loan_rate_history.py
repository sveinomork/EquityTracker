import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, numeric_column


class LoanRateHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ORM model storing historical borrowing rates per fund."""
    __tablename__ = "loan_rate_history"
    __table_args__ = (
        UniqueConstraint(
            "fund_id", "effective_date", name="uq_loan_rate_history_fund_id_effective_date"
        ),
        Index("ix_loan_rate_history_fund_effective_date", "fund_id", "effective_date"),
    )

    fund_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("funds.id", ondelete="CASCADE"), index=True
    )
    effective_date: Mapped[date]
    nominal_rate: Mapped[Decimal] = numeric_column()

    fund = relationship("Fund", back_populates="loan_rates")
