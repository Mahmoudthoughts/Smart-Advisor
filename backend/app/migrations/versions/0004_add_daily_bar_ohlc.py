"""Add OHLC columns to daily_bar.

Revision ID: 0004_add_daily_bar_ohlc
Revises: 0003_add_portfolio_account
Create Date: 2025-12-25 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0004_add_daily_bar_ohlc"
down_revision = "0003_add_portfolio_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("daily_bar", sa.Column("open", sa.Numeric(18, 6), nullable=True))
    op.add_column("daily_bar", sa.Column("high", sa.Numeric(18, 6), nullable=True))
    op.add_column("daily_bar", sa.Column("low", sa.Numeric(18, 6), nullable=True))
    op.add_column("daily_bar", sa.Column("close", sa.Numeric(18, 6), nullable=True))
    op.execute(
        "UPDATE daily_bar "
        "SET open = adj_close, high = adj_close, low = adj_close, close = adj_close "
        "WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL"
    )
    op.alter_column("daily_bar", "open", nullable=False)
    op.alter_column("daily_bar", "high", nullable=False)
    op.alter_column("daily_bar", "low", nullable=False)
    op.alter_column("daily_bar", "close", nullable=False)


def downgrade() -> None:
    op.drop_column("daily_bar", "close")
    op.drop_column("daily_bar", "low")
    op.drop_column("daily_bar", "high")
    op.drop_column("daily_bar", "open")
