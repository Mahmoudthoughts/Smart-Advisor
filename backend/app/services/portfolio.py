"""HTTP client for the dedicated portfolio microservice."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from opentelemetry.propagate import inject
from fastapi import HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _request(method: str, path: str, json: Any | None = None, *, user_id: str | None = None) -> Any:
    settings = get_settings()
    base_url = settings.portfolio_service_url.rstrip("/")
    url = f"{base_url}{path}"
    headers: dict[str, str] = {}
    if settings.portfolio_service_token:
        headers["X-Internal-Token"] = settings.portfolio_service_token
    if user_id:
        headers["X-User-Id"] = str(user_id)
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


async def fetch_watchlist(user_id: str) -> Any:
    return await _request("GET", "/watchlist", user_id=user_id)


async def add_watchlist(payload: dict[str, Any], user_id: str) -> Any:
    return await _request("POST", "/watchlist", json=payload, user_id=user_id)


async def list_transactions(user_id: str) -> Any:
    return await _request("GET", "/transactions", user_id=user_id)


async def create_transaction(payload: dict[str, Any], user_id: str) -> Any:
    return await _request("POST", "/transactions", json=payload, user_id=user_id)


async def update_transaction(transaction_id: int, payload: dict[str, Any], user_id: str) -> Any:
    return await _request("PUT", f"/transactions/{transaction_id}", json=payload, user_id=user_id)


async def delete_transaction(transaction_id: int, user_id: str) -> None:
    await _request("DELETE", f"/transactions/{transaction_id}", user_id=user_id)


async def list_accounts(user_id: str) -> Any:
    return await _request("GET", "/accounts", user_id=user_id)


async def create_account(payload: dict[str, Any], user_id: str) -> Any:
    return await _request("POST", "/accounts", json=payload, user_id=user_id)


async def recompute_snapshots(symbol: str, user_id: str) -> Any:
    return await _request("POST", f"/snapshots/{symbol}/recompute", user_id=user_id)


__all__ = [
    "fetch_watchlist",
    "add_watchlist",
    "list_transactions",
    "create_transaction",
    "update_transaction",
    "delete_transaction",
    "list_accounts",
    "create_account",
    "recompute_snapshots",
]
