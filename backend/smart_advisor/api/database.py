"""Database utilities for the Smart Advisor API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DEFAULT_DATABASE_URL = "postgresql+asyncpg://smart_advisor:smart_advisor@db:5432/smart_advisor"


class Base(AsyncAttrs, DeclarativeBase):
    """Declarative base for ORM models."""


class Database:
    """Configure an async SQLAlchemy engine and session factory."""

    def __init__(self, url: str | None = None):
        self._url = url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
        self._engine = create_async_engine(self._url, future=True, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def url(self) -> str:
        return self._url

    @property
    def engine(self):
        return self._engine

    async def create_all(self) -> None:
        """Create all tables defined on the declarative metadata."""

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def ensure_user_role_column(self) -> None:
        """Backfill missing role column on legacy user table if needed."""

        async with self._engine.begin() as connection:
            await connection.execute(
                text("ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS role VARCHAR(32) DEFAULT 'user'")
            )
            await connection.execute(text("UPDATE users SET role = 'user' WHERE role IS NULL"))

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session

    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with self._session_factory() as session:
            yield session


# Shared database instance for the production application.
database = Database()


__all__ = ["Base", "Database", "database", "DEFAULT_DATABASE_URL"]
