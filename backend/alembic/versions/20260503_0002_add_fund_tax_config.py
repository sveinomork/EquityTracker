"""Add fund tax configuration fields.

Revision ID: 20260503_0002
Revises: 20260501_0001
Create Date: 2026-05-03 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260503_0002"
down_revision: str | None = "20260501_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("funds")}

    added_is_distributing = False
    if "is_distributing" not in existing_columns:
        op.add_column(
            "funds",
            sa.Column("is_distributing", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        added_is_distributing = True

    if "manual_taxable_gain_override" not in existing_columns:
        op.add_column(
            "funds",
            sa.Column("manual_taxable_gain_override", sa.Numeric(18, 2), nullable=True),
        )

    # SQLite does not support ALTER COLUMN ... DROP DEFAULT.
    if added_is_distributing and bind.dialect.name != "sqlite":
        op.alter_column("funds", "is_distributing", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("funds")}

    if "manual_taxable_gain_override" in existing_columns:
        op.drop_column("funds", "manual_taxable_gain_override")

    if "is_distributing" in existing_columns:
        op.drop_column("funds", "is_distributing")
