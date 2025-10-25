"""Authentication routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Database
from .models import AuthToken, User
from .schemas import AuthResponse, LoginRequest, RegisterRequest, UserOut
from .security import hash_password, token_lifetime, verify_password


def get_auth_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
    async def register(payload: RegisterRequest, session: AsyncSession = Depends(database.get_session)) -> AuthResponse:
        normalized_email = payload.email.strip().lower()
        existing = await session.execute(select(User).where(User.email == normalized_email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

        user = User(name=payload.name.strip(), email=normalized_email, password_hash=hash_password(payload.password))
        session.add(user)
        await session.flush()

        token = AuthToken.for_user(user.id, token_lifetime())
        session.add(token)
        await session.commit()
        await session.refresh(user)

        return AuthResponse(access_token=token.token, user=_to_user_out(user))

    @router.post("/login", response_model=AuthResponse)
    async def login(payload: LoginRequest, session: AsyncSession = Depends(database.get_session)) -> AuthResponse:
        normalized_email = payload.email.strip().lower()
        query = await session.execute(select(User).where(User.email == normalized_email))
        user = query.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        token = AuthToken.for_user(user.id, token_lifetime())
        session.add(token)
        await session.commit()
        await session.refresh(user)

        return AuthResponse(access_token=token.token, user=_to_user_out(user))

    return router


def _to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email, created_at=user.created_at or datetime.utcnow())

