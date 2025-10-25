"""Add portfolio accounts and transaction linkage

Revision ID: 0003_add_portfolio_account
Revises: 0002_add_portfolio_symbol
Create Date: 2025-02-17 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_add_portfolio_account"
down_revision = "0002_add_portfolio_symbol"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("portfolio_id", "name", name="uq_portfolio_account_name"),
    )
    op.create_index(
        "ix_portfolio_account_portfolio",
        "portfolio_account",
        ["portfolio_id"],
    )

    op.add_column(
        "transaction",
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("portfolio_account.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_transaction_account", "transaction", ["account_id"])

    op.add_column(
        "portfolio_symbol",
        sa.Column("display_name", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portfolio_symbol", "display_name")
    op.drop_index("ix_transaction_account", table_name="transaction")
    op.drop_column("transaction", "account_id")
    op.drop_index("ix_portfolio_account_portfolio", table_name="portfolio_account")
    op.drop_table("portfolio_account")
