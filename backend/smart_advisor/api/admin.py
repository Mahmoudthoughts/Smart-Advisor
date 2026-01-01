from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Database
from .models import LlmProvider, StockListProvider, User
from .schemas import (
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    LlmProviderOut,
    LlmProviderUpsert,
    StockListProviderOut,
    StockListProviderUpsert,
    UserOut,
)
from .security import hash_password


def get_admin_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/admin", tags=["admin"])

    @router.get("/users", response_model=list[UserOut])
    async def list_users(session: AsyncSession = Depends(database.get_session)) -> list[UserOut]:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return [_to_user_out(user) for user in users]

    @router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
    async def create_user(
        payload: AdminCreateUserRequest, session: AsyncSession = Depends(database.get_session)
    ) -> UserOut:
        normalized_email = payload.email.strip().lower()
        existing = await session.execute(select(User).where(User.email == normalized_email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

        user = User(
            name=payload.name.strip(),
            email=normalized_email,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return _to_user_out(user)

    @router.patch("/users/{user_id}", response_model=UserOut)
    async def update_user(
        user_id: UUID, payload: AdminUpdateUserRequest, session: AsyncSession = Depends(database.get_session)
    ) -> UserOut:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if payload.name is not None:
            user.name = payload.name.strip()
        if payload.role is not None:
            user.role = payload.role
        if payload.password is not None:
            user.password_hash = hash_password(payload.password)

        await session.commit()
        await session.refresh(user)
        return _to_user_out(user)

    @router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_user(user_id: UUID, session: AsyncSession = Depends(database.get_session)) -> None:
        user = await session.get(User, user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        await session.delete(user)
        await session.commit()

    @router.get("/providers", response_model=list[StockListProviderOut])
    async def list_providers(
        session: AsyncSession = Depends(database.get_session),
    ) -> list[StockListProviderOut]:
        result = await session.execute(select(StockListProvider))
        providers = result.scalars().all()
        return [_to_provider_out(provider) for provider in providers]

    @router.post("/providers", response_model=StockListProviderOut, status_code=status.HTTP_201_CREATED)
    async def create_provider(
        payload: StockListProviderUpsert, session: AsyncSession = Depends(database.get_session)
    ) -> StockListProviderOut:
        provider = StockListProvider(
            provider=payload.provider.strip(),
            display_name=payload.display_name.strip(),
            api_key=payload.api_key,
            base_url=payload.base_url,
            is_active=payload.is_active,
            is_default=payload.is_default,
        )
        session.add(provider)
        await session.flush()

        if payload.is_default:
            await _reset_default_providers(session, provider.id)

        await session.commit()
        await session.refresh(provider)
        return _to_provider_out(provider)

    @router.patch("/providers/{provider_id}", response_model=StockListProviderOut)
    async def update_provider(
        provider_id: UUID,
        payload: StockListProviderUpsert,
        session: AsyncSession = Depends(database.get_session),
    ) -> StockListProviderOut:
        provider = await session.get(StockListProvider, provider_id)
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

        provider.provider = payload.provider.strip()
        provider.display_name = payload.display_name.strip()
        provider.api_key = payload.api_key
        provider.base_url = payload.base_url
        provider.is_active = payload.is_active
        provider.is_default = payload.is_default

        await session.flush()
        if payload.is_default:
            await _reset_default_providers(session, provider_id)

        await session.commit()
        await session.refresh(provider)
        return _to_provider_out(provider)

    @router.get("/llm-providers", response_model=list[LlmProviderOut])
    async def list_llm_providers(
        session: AsyncSession = Depends(database.get_session),
    ) -> list[LlmProviderOut]:
        result = await session.execute(select(LlmProvider))
        providers = result.scalars().all()
        return [_to_llm_provider_out(provider) for provider in providers]

    @router.post("/llm-providers", response_model=LlmProviderOut, status_code=status.HTTP_201_CREATED)
    async def create_llm_provider(
        payload: LlmProviderUpsert, session: AsyncSession = Depends(database.get_session)
    ) -> LlmProviderOut:
        provider = LlmProvider(
            provider=payload.provider.strip(),
            display_name=payload.display_name.strip(),
            api_key=payload.api_key,
            base_url=payload.base_url,
            model=payload.model,
            is_active=payload.is_active,
            is_default=payload.is_default,
        )
        session.add(provider)
        await session.flush()

        if payload.is_default:
            await _reset_default_llm_providers(session, provider.id)

        await session.commit()
        await session.refresh(provider)
        return _to_llm_provider_out(provider)

    @router.patch("/llm-providers/{provider_id}", response_model=LlmProviderOut)
    async def update_llm_provider(
        provider_id: UUID,
        payload: LlmProviderUpsert,
        session: AsyncSession = Depends(database.get_session),
    ) -> LlmProviderOut:
        provider = await session.get(LlmProvider, provider_id)
        if provider is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

        provider.provider = payload.provider.strip()
        provider.display_name = payload.display_name.strip()
        provider.api_key = payload.api_key
        provider.base_url = payload.base_url
        provider.model = payload.model
        provider.is_active = payload.is_active
        provider.is_default = payload.is_default

        await session.flush()
        if payload.is_default:
            await _reset_default_llm_providers(session, provider_id)

        await session.commit()
        await session.refresh(provider)
        return _to_llm_provider_out(provider)

    return router


async def _reset_default_providers(session: AsyncSession, keep_id: UUID) -> None:
    await session.execute(
        update(StockListProvider)
        .where(StockListProvider.id != keep_id)
        .values(is_default=False)
    )


async def _reset_default_llm_providers(session: AsyncSession, keep_id: UUID) -> None:
    await session.execute(
        update(LlmProvider)
        .where(LlmProvider.id != keep_id)
        .values(is_default=False)
    )


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
    )


def _to_provider_out(provider: StockListProvider) -> StockListProviderOut:
    return StockListProviderOut(
        id=provider.id,
        provider=provider.provider,
        display_name=provider.display_name,
        api_key=provider.api_key,
        base_url=provider.base_url,
        is_active=provider.is_active,
        is_default=provider.is_default,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _to_llm_provider_out(provider: LlmProvider) -> LlmProviderOut:
    return LlmProviderOut(
        id=provider.id,
        provider=provider.provider,
        display_name=provider.display_name,
        api_key=provider.api_key,
        base_url=provider.base_url,
        model=provider.model,
        is_active=provider.is_active,
        is_default=provider.is_default,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


__all__ = ["get_admin_router"]
