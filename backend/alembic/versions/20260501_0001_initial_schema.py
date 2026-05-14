"""Initial schema.

Revision ID: 20260501_0001
Revises:
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260501_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    transaction_type = sa.Enum("BUY", "SELL", "DIVIDEND_REINVEST", name="transaction_type")
    transaction_type.create(op.get_bind(), checkfirst=True)
    transaction_type_for_table = postgresql.ENUM(
        "BUY",
        "SELL",
        "DIVIDEND_REINVEST",
        name="transaction_type",
        create_type=False,
    )

    op.create_table(
        "funds",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_funds"),
    )
    op.create_index(op.f("ix_funds_ticker"), "funds", ["ticker"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("fund_id", sa.Uuid(), nullable=False),
        sa.Column("lot_id", sa.Uuid(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("type", transaction_type_for_table, nullable=False),
        sa.Column("units", sa.Numeric(18, 6), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("borrowed_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("equity_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], name="fk_transactions_fund_id_funds", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["transactions.id"], name="fk_transactions_lot_id_transactions", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_transactions"),
    )
    op.create_index(op.f("ix_transactions_fund_date"), "transactions", ["fund_id", "date"], unique=False)
    op.create_index(op.f("ix_transactions_fund_id"), "transactions", ["fund_id"], unique=False)
    op.create_index(op.f("ix_transactions_lot_id"), "transactions", ["lot_id"], unique=False)

    op.create_table(
        "daily_fund_prices",
        sa.Column("fund_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], name="fk_daily_fund_prices_fund_id_funds", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_daily_fund_prices"),
        sa.UniqueConstraint("fund_id", "date", name="uq_daily_fund_prices_fund_id_date"),
    )
    op.create_index(op.f("ix_daily_fund_prices_fund_date"), "daily_fund_prices", ["fund_id", "date"], unique=False)
    op.create_index(op.f("ix_daily_fund_prices_fund_id"), "daily_fund_prices", ["fund_id"], unique=False)

    op.create_table(
        "loan_rate_history",
        sa.Column("fund_id", sa.Uuid(), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("nominal_rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["fund_id"], ["funds.id"], name="fk_loan_rate_history_fund_id_funds", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_loan_rate_history"),
        sa.UniqueConstraint("fund_id", "effective_date", name="uq_loan_rate_history_fund_id_effective_date"),
    )
    op.create_index(
        op.f("ix_loan_rate_history_fund_effective_date"),
        "loan_rate_history",
        ["fund_id", "effective_date"],
        unique=False,
    )
    op.create_index(op.f("ix_loan_rate_history_fund_id"), "loan_rate_history", ["fund_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_loan_rate_history_fund_id"), table_name="loan_rate_history")
    op.drop_index(op.f("ix_loan_rate_history_fund_effective_date"), table_name="loan_rate_history")
    op.drop_table("loan_rate_history")
    op.drop_index(op.f("ix_daily_fund_prices_fund_id"), table_name="daily_fund_prices")
    op.drop_index(op.f("ix_daily_fund_prices_fund_date"), table_name="daily_fund_prices")
    op.drop_table("daily_fund_prices")
    op.drop_index(op.f("ix_transactions_lot_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_fund_id"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_fund_date"), table_name="transactions")
    op.drop_table("transactions")
    op.drop_index(op.f("ix_funds_ticker"), table_name="funds")
    op.drop_table("funds")
    sa.Enum("BUY", "SELL", "DIVIDEND_REINVEST", name="transaction_type").drop(op.get_bind(), checkfirst=True)
