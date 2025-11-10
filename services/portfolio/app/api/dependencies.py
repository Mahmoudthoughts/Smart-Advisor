"""Shared FastAPI dependencies for the portfolio service."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..db.session import get_session


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in get_session():  # pragma: no cover - FastAPI dependency wrapper
        yield session


def verify_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if settings.internal_auth_token is None:
        return
    if x_internal_token != settings.internal_auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal token")


InternalAuth = Depends(verify_internal_token)

__all__ = ["get_db_session", "InternalAuth"]
