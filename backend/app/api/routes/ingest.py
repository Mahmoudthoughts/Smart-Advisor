"""Endpoints related to the ingest microservice connectivity."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def ingest_health() -> dict:
    """Proxy health endpoint for the ingest microservice.

    Returns a small JSON payload from the upstream service if configured.
    If not configured, returns a simple status indicating it is disabled.
    """

    settings = get_settings()
    if not settings.ingest_base_url:
        logger.info("Ingest microservice not configured (INGEST_BASE_URL unset)")
        return {"status": "disabled", "detail": "INGEST_BASE_URL not configured"}

    url = f"{settings.ingest_base_url.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream ingest health failed with {resp.status_code}: {resp.text}",
            )
        payload = resp.json()
        return {"status": "ok", "upstream": payload}
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to reach ingest microservice health at %s", url)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach ingest microservice: {exc}",
        ) from exc


__all__ = ["router"]

