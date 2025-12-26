"""Proxy AI timing requests to the ai_timing microservice."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.config import get_settings
from smart_advisor.api.models import User

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


@router.post("/timing")
async def get_timing(
    payload: TimingRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
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

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload.model_dump(mode="json"), headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI timing service failed with {resp.status_code}: {resp.text}",
            )
        return resp.json()
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to reach AI timing service at %s", url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach AI timing service: {exc}",
        ) from exc


__all__ = ["router"]
