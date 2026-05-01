from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Fund(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "funds"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    transactions = relationship("Transaction", back_populates="fund", cascade="all, delete-orphan")
    prices = relationship("DailyFundPrice", back_populates="fund", cascade="all, delete-orphan")
    loan_rates = relationship(
        "LoanRateHistory",
        back_populates="fund",
        cascade="all, delete-orphan",
    )
