"""Client helpers for interacting with the ingest microservice."""

from __future__ import annotations

import httpx

from ..core.config import get_settings


async def ingest_prices(symbol: str) -> dict:
    settings = get_settings()
    url = f"{settings.ingest_service_url.rstrip('/')}/jobs/prices"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json={"symbol": symbol}, params={"run_sync": "true"})
        response.raise_for_status()
        return response.json()


__all__ = ["ingest_prices"]
