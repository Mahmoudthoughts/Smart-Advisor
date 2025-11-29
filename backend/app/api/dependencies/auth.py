"""Authentication helpers for API routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from smart_advisor.api.database import database as legacy_database
from smart_advisor.api.models import AuthToken, User


async def _get_legacy_session() -> AsyncSession:
    async for session in legacy_database.get_session():
        yield session


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(_get_legacy_session),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token_value = authorization.split(" ", 1)[1].strip()
    now = datetime.now(timezone.utc)
    stmt: Select[AuthToken] = select(AuthToken).where(
        AuthToken.token == token_value,
        AuthToken.is_active.is_(True),
        AuthToken.expires_at > now,
    )
    result = await session.execute(stmt)
    auth_token = result.scalar_one_or_none()
    if auth_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = await session.get(User, auth_token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


__all__ = ["get_current_user"]
