"""Database schema initialization helpers."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.db.session import _engine

# Import models so that SQLAlchemy is aware of all tables before create_all runs.
import app.models  # noqa: F401  # pylint: disable=unused-import

logger = logging.getLogger(__name__)


async def init_database() -> None:
    """Ensure all database tables exist for the running application."""

    try:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text("ALTER TABLE IF EXISTS portfolio ADD COLUMN IF NOT EXISTS owner_id VARCHAR(64)")
            )
            await conn.execute(
                text(
                    "ALTER TABLE IF EXISTS daily_portfolio_snapshot "
                    "ADD COLUMN IF NOT EXISTS portfolio_id INTEGER"
                )
            )
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_portfolio_owner_id "
                    "ON portfolio(owner_id)"
                )
            )
            await conn.execute(
                text("ALTER TABLE IF EXISTS daily_portfolio_snapshot DROP CONSTRAINT IF EXISTS uq_snapshot_symbol_date")
            )
            await conn.execute(text("DROP INDEX IF EXISTS ix_snapshot_symbol_date"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_snapshot_portfolio_symbol_date "
                    "ON daily_portfolio_snapshot (portfolio_id, symbol, date)"
                )
            )
            await conn.execute(text("UPDATE portfolio SET owner_id = COALESCE(owner_id, 'system')"))
            await conn.execute(
                text(
                    "UPDATE daily_portfolio_snapshot "
                    "SET portfolio_id = COALESCE("
                    "portfolio_id, (SELECT id FROM portfolio WHERE owner_id = 'system' LIMIT 1)"
                    ")"
                )
            )
    except SQLAlchemyError:
        logger.exception("Failed to initialise database schema")
        raise


__all__ = ["init_database"]
