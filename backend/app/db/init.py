"""Database schema initialization helpers."""

from __future__ import annotations

import logging

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
    except SQLAlchemyError:
        logger.exception("Failed to initialise database schema")
        raise


__all__ = ["init_database"]
