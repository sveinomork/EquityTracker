from decimal import Decimal

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, numeric_column


class Fund(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """ORM model representing an investment fund."""
    __tablename__ = "funds"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    is_distributing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    manual_taxable_gain_override: Mapped[Decimal | None] = numeric_column(scale=2)

    transactions = relationship("Transaction", back_populates="fund", cascade="all, delete-orphan")
    prices = relationship("DailyFundPrice", back_populates="fund", cascade="all, delete-orphan")
    loan_rates = relationship(
        "LoanRateHistory",
        back_populates="fund",
        cascade="all, delete-orphan",
    )
