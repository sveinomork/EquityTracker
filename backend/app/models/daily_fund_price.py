import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, numeric_column


class DailyFundPrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "daily_fund_prices"
    __table_args__ = (
        UniqueConstraint("fund_id", "date", name="uq_daily_fund_prices_fund_id_date"),
        Index("ix_daily_fund_prices_fund_date", "fund_id", "date"),
    )

    fund_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("funds.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date]
    price: Mapped[Decimal] = numeric_column()

    fund = relationship("Fund", back_populates="prices")
