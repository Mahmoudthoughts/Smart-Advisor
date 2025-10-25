"""Add portfolio_symbol table."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_add_portfolio_symbol"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_symbol",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolio.id", ondelete="CASCADE")),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),
    )
    op.create_index("ix_portfolio_symbol_symbol", "portfolio_symbol", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_symbol_symbol", table_name="portfolio_symbol")
    op.drop_table("portfolio_symbol")
