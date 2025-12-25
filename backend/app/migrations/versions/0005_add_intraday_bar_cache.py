"""Add intraday bar cache table.

Revision ID: 0005_add_intraday_bar_cache
Revises: 0004_add_daily_bar_ohlc
Create Date: 2025-12-25 03:18:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0005_add_intraday_bar_cache"
down_revision = "0004_add_daily_bar_ohlc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intraday_bar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("bar_size", sa.String(length=16), nullable=False),
        sa.Column("use_rth", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("high", sa.Numeric(18, 6), nullable=False),
        sa.Column("low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("volume", sa.Numeric(20, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.UniqueConstraint("symbol", "bar_size", "use_rth", "timestamp", name="uq_intraday_bar_key"),
    )
    op.create_index(
        "ix_intraday_bar_symbol_ts",
        "intraday_bar",
        ["symbol", "bar_size", "use_rth", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_intraday_bar_symbol_ts", table_name="intraday_bar")
    op.drop_table("intraday_bar")
