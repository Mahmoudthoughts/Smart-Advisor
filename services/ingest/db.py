"""Database session helpers for the ingest service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings

_settings = get_settings()
if not _settings.database_url:
    msg = "DATABASE_URL is required to create a database session"
    raise RuntimeError(msg)

_engine: AsyncEngine = create_async_engine(_settings.database_url, echo=False, future=True)
_session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession for use in async contexts."""

    async with _session_factory() as session:
        yield session


__all__ = ["get_session", "_engine", "_session_factory"]
