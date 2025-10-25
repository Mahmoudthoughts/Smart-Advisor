"""Database engine and session utilities."""

from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_settings = get_settings()
_engine: AsyncEngine = create_async_engine(_settings.database_url, echo=False, future=True)
_session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an AsyncSession for FastAPI dependency usage."""

    async with _session_factory() as session:
        yield session


__all__ = ["get_db", "_engine", "_session_factory"]
