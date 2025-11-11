"""HTTP client for the dedicated portfolio microservice."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from opentelemetry.propagate import inject
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _request(method: str, path: str, json: Any | None = None) -> Any:
    settings = get_settings()
    base_url = settings.portfolio_service_url.rstrip("/")
    url = f"{base_url}{path}"
    headers: dict[str, str] = {}
    if settings.portfolio_service_token:
        headers["X-Internal-Token"] = settings.portfolio_service_token
    # Inject current trace context so downstream spans link to the backend request
    try:
        inject(headers)
    except Exception:
        # Best-effort; keep request functional even if tracing is unavailable
        pass
    timeout = settings.portfolio_service_timeout_seconds
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, json=json, headers=headers)
    if response.status_code >= 400:
        logger.warning("Portfolio service error %s for %s", response.status_code, url)
        detail: Any
        try:
            payload = response.json()
            detail = payload.get("detail", payload)
        except Exception:  # pragma: no cover - defensive
            detail = response.text
        raise HTTPException(status_code=response.status_code, detail=detail)
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    return response.content


async def fetch_watchlist() -> Any:
    return await _request("GET", "/watchlist")


async def add_watchlist(payload: dict[str, Any]) -> Any:
    return await _request("POST", "/watchlist", json=payload)


async def list_transactions() -> Any:
    return await _request("GET", "/transactions")


async def create_transaction(payload: dict[str, Any]) -> Any:
    return await _request("POST", "/transactions", json=payload)


async def update_transaction(transaction_id: int, payload: dict[str, Any]) -> Any:
    return await _request("PUT", f"/transactions/{transaction_id}", json=payload)


async def list_accounts() -> Any:
    return await _request("GET", "/accounts")


async def create_account(payload: dict[str, Any]) -> Any:
    return await _request("POST", "/accounts", json=payload)


async def recompute_snapshots(symbol: str) -> Any:
    return await _request("POST", f"/snapshots/{symbol}/recompute")


__all__ = [
    "fetch_watchlist",
    "add_watchlist",
    "list_transactions",
    "create_transaction",
    "update_transaction",
    "list_accounts",
    "create_account",
    "recompute_snapshots",
]
