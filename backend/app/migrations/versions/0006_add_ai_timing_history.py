"""Add AI timing history table.

Revision ID: 0006_add_ai_timing_history
Revises: 0005_add_intraday_bar_cache
Create Date: 2025-12-29 21:30:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0006_add_ai_timing_history"
down_revision = "0005_add_intraday_bar_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_timing_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("symbol_name", sa.String(length=128), nullable=True),
        sa.Column("bar_size", sa.String(length=16), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("use_rth", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("request_payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("response_payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_ai_timing_history_user_symbol_created",
        "ai_timing_history",
        ["user_id", "symbol", "created_at"],
    )
    op.create_index(
        "ix_ai_timing_history_user_id",
        "ai_timing_history",
        ["user_id"],
    )
    op.create_index(
        "ix_ai_timing_history_symbol",
        "ai_timing_history",
        ["symbol"],
    )
    op.create_index(
        "ix_ai_timing_history_created_at",
        "ai_timing_history",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_timing_history_created_at", table_name="ai_timing_history")
    op.drop_index("ix_ai_timing_history_symbol", table_name="ai_timing_history")
    op.drop_index("ix_ai_timing_history_user_id", table_name="ai_timing_history")
    op.drop_index("ix_ai_timing_history_user_symbol_created", table_name="ai_timing_history")
    op.drop_table("ai_timing_history")
