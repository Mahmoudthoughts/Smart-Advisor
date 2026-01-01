"""
Add session_summary table for intraday ETL outputs.

Revision ID: 0007_add_session_summary
Revises: 0006_add_ai_timing_history
Create Date: 2025-01-05 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0007_add_session_summary"
down_revision = "0006_add_ai_timing_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_summary",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(18, 6), nullable=False),
        sa.Column("midday_low", sa.Numeric(18, 6), nullable=False),
        sa.Column("close", sa.Numeric(18, 6), nullable=False),
        sa.Column("drawdown_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("recovery_pct", sa.Numeric(10, 6), nullable=False),
        sa.Column("bars", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("symbol", "date", name="uq_session_summary_symbol_date"),
    )
    op.create_index(
        "ix_session_summary_symbol_date",
        "session_summary",
        ["symbol", "date"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_summary_symbol_date", table_name="session_summary")
    op.drop_table("session_summary")
