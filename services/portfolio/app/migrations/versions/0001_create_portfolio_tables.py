"""Initial portfolio tables and outbox."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision = "0001_create_portfolio_tables"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "portfolio"):
        op.create_table(
            "portfolio",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("base_currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Dubai"),
        )

    if not _has_table(bind, "portfolio_account"):
        op.create_table(
            "portfolio_account",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("portfolio_id", sa.Integer, sa.ForeignKey("portfolio.id", ondelete="CASCADE")),
            sa.Column("name", sa.String(length=64), nullable=False),
            sa.Column("type", sa.String(length=32)),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("notes", sa.String(length=255)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
            sa.UniqueConstraint("portfolio_id", "name", name="uq_portfolio_account_name"),
            sa.Index("ix_portfolio_account_portfolio", "portfolio_id"),
        )

    if not _has_table(bind, "portfolio_symbol"):
        op.create_table(
            "portfolio_symbol",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("portfolio_id", sa.Integer, sa.ForeignKey("portfolio.id", ondelete="CASCADE")),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("display_name", sa.String(length=128)),
            sa.UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),
            sa.Index("ix_portfolio_symbol_symbol", "symbol"),
        )

    if not _has_table(bind, "transaction"):
        op.create_table(
            "transaction",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("portfolio_id", sa.Integer, sa.ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=False),
            sa.Column("symbol", sa.String(length=20), nullable=False, index=True),
            sa.Column("type", sa.Enum("BUY", "SELL", "DIVIDEND", "FEE", "SPLIT", name="transaction_type"), nullable=False),
            sa.Column("qty", sa.Numeric(18, 4), nullable=False),
            sa.Column("price", sa.Numeric(18, 6), nullable=False),
            sa.Column("fee", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("tax", sa.Numeric(18, 6), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
            sa.Column("datetime", sa.DateTime(timezone=True), nullable=False, index=True),
            sa.Column("broker_id", sa.String(length=64)),
            sa.Column("account_id", sa.Integer, sa.ForeignKey("portfolio_account.id", ondelete="SET NULL")),
            sa.Column("notes", sa.String(length=255)),
            sa.Index("ix_transaction_symbol_datetime", "symbol", "datetime"),
            sa.Index("ix_transaction_account", "account_id"),
        )

    if not _has_table(bind, "daily_portfolio_snapshot"):
        op.create_table(
            "daily_portfolio_snapshot",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("symbol", sa.String(length=20), nullable=False),
            sa.Column("date", sa.Date, nullable=False),
            sa.Column("shares_open", sa.Numeric(18, 6), nullable=False),
            sa.Column("market_value_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("cost_basis_open_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("unrealized_pl_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("realized_pl_to_date_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("hypo_liquidation_pl_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("day_opportunity_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("peak_hypo_pl_to_date_base", sa.Numeric(18, 6), nullable=False),
            sa.Column("drawdown_from_peak_pct", sa.Numeric(10, 4), nullable=False),
            sa.UniqueConstraint("symbol", "date", name="uq_snapshot_symbol_date"),
            sa.Index("ix_snapshot_symbol_date", "symbol", "date"),
        )

    if not _has_table(bind, "portfolio_outbox"):
        op.create_table(
            "portfolio_outbox",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("event_type", sa.String(length=128), nullable=False),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("available_at", sa.DateTime(timezone=True)),
            sa.Column("processed_at", sa.DateTime(timezone=True)),
            sa.Index("ix_portfolio_outbox_status", "status", "created_at"),
        )


def downgrade() -> None:
    op.drop_table("portfolio_outbox")
    op.drop_table("daily_portfolio_snapshot")
    op.drop_table("transaction")
    op.drop_table("portfolio_symbol")
    op.drop_table("portfolio_account")
    op.drop_table("portfolio")
