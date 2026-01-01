"""Proxy AI timing requests to the ai_timing microservice."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.config import get_settings
from app.db.session import get_db
from app.models.ai_timing import AiTimingHistory
from smart_advisor.api.models import LlmProvider, User

router = APIRouter()
logger = logging.getLogger(__name__)


class IntradayBarPayload(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class SessionSummaryPayload(BaseModel):
    date: str
    bars: int
    open: float | None = None
    midday_low: float | None = None
    close: float | None = None
    drawdown_pct: float | None = None
    recovery_pct: float | None = None


class TimingRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    bar_size: str
    duration_days: int
    timezone: str | None = None
    use_rth: bool = True
    symbol_name: str | None = None
    session_summaries: list[SessionSummaryPayload] | None = None
    bars: list[IntradayBarPayload]
    force_refresh: bool | None = None
    llm_provider_id: UUID | None = None


class TimingHistoryEntry(BaseModel):
    id: int
    symbol: str
    symbol_name: str | None
    bar_size: str
    duration_days: int
    timezone: str
    use_rth: bool
    created_at: datetime
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]


class LlmProviderOption(BaseModel):
    id: UUID
    provider: str
    display_name: str
    model: str | None
    base_url: str | None
    is_default: bool


@router.post("/timing")
async def get_timing(
    payload: TimingRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    if not settings.ai_timing_base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI timing service is not configured (AI_TIMING_BASE_URL unset).",
        )

    url = f"{settings.ai_timing_base_url.rstrip('/')}/timing"
    headers = {"X-User-Id": str(current_user.id)}
    baggage = request.headers.get("baggage")
    if baggage:
        headers["baggage"] = baggage
    llm_provider = None
    if payload.llm_provider_id:
        llm_provider = await _get_llm_provider(db, payload.llm_provider_id)
        if not llm_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested LLM provider was not found or is inactive.",
            )
    else:
        llm_provider = await _get_default_llm_provider(db)
    proxy_payload: dict[str, Any] = payload.model_dump(mode="json")
    if llm_provider:
        proxy_payload["llm"] = {
            "provider": llm_provider.provider,
            "api_key": llm_provider.api_key,
            "base_url": llm_provider.base_url,
            "model": llm_provider.model,
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=proxy_payload, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI timing service failed with {resp.status_code}: {resp.text}",
            )
        response_data = resp.json()
        await _save_history(db, current_user, payload, response_data)
        return response_data
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to reach AI timing service at %s", url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach AI timing service: {exc}",
        ) from exc


@router.get("/timing/history", response_model=list[TimingHistoryEntry])
async def get_timing_history(
    symbol: str | None = Query(default=None, min_length=1),
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TimingHistoryEntry]:
    query = select(AiTimingHistory).where(AiTimingHistory.user_id == str(current_user.id))
    if symbol:
        query = query.where(AiTimingHistory.symbol == symbol.upper())
    start_dt = _parse_history_date(start_date)
    if start_dt:
        query = query.where(AiTimingHistory.created_at >= start_dt)
    end_dt = _parse_history_date(end_date)
    if end_dt:
        query = query.where(AiTimingHistory.created_at < end_dt + timedelta(days=1))

    query = query.order_by(AiTimingHistory.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        TimingHistoryEntry(
            id=entry.id,
            symbol=entry.symbol,
            symbol_name=entry.symbol_name,
            bar_size=entry.bar_size,
            duration_days=entry.duration_days,
            timezone=entry.timezone,
            use_rth=entry.use_rth,
            created_at=entry.created_at,
            request_payload=entry.request_payload,
            response_payload=entry.response_payload,
        )
        for entry in entries
    ]


@router.get("/llm-providers", response_model=list[LlmProviderOption])
async def list_llm_providers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LlmProviderOption]:
    _ = current_user
    result = await db.execute(select(LlmProvider).where(LlmProvider.is_active.is_(True)))
    providers = result.scalars().all()
    return [
        LlmProviderOption(
            id=provider.id,
            provider=provider.provider,
            display_name=provider.display_name,
            model=provider.model,
            base_url=provider.base_url,
            is_default=provider.is_default,
        )
        for provider in providers
    ]


def _parse_history_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def _save_history(
    db: AsyncSession,
    current_user: User,
    payload: TimingRequest,
    response_data: dict[str, Any],
) -> None:
    settings = get_settings()
    tz_name = payload.timezone or settings.timezone_default
    entry = AiTimingHistory(
        user_id=str(current_user.id),
        symbol=payload.symbol.upper(),
        symbol_name=payload.symbol_name,
        bar_size=payload.bar_size,
        duration_days=payload.duration_days,
        timezone=tz_name,
        use_rth=payload.use_rth,
        request_payload=payload.model_dump(mode="json"),
        response_payload=response_data,
    )
    try:
        db.add(entry)
        await db.commit()
    except Exception:  # pragma: no cover - defensive
        await db.rollback()
        logger.exception("Failed to persist AI timing history.")


async def _get_default_llm_provider(db: AsyncSession) -> LlmProvider | None:
    result = await db.execute(
        select(LlmProvider).where(LlmProvider.is_active.is_(True), LlmProvider.is_default.is_(True))
    )
    return result.scalar_one_or_none()


async def _get_llm_provider(db: AsyncSession, provider_id: UUID) -> LlmProvider | None:
    result = await db.execute(
        select(LlmProvider).where(LlmProvider.id == provider_id, LlmProvider.is_active.is_(True))
    )
    return result.scalar_one_or_none()


__all__ = ["router"]
