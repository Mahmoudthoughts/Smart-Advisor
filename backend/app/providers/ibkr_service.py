"""Client helpers for the IBKR microservice."""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.schemas.symbols import SymbolSearchResultSchema


class IBKRServiceError(RuntimeError):
    """Raised when the IBKR microservice returns an error."""


async def search_symbols(
    query: str,
    *,
    base_url: str | None = None,
    timeout_seconds: float = 15.0,
) -> list[SymbolSearchResultSchema]:
    """Call the IBKR service search endpoint and normalize results."""

    settings = get_settings()
    url_base = (base_url or settings.ibkr_service_url or "").rstrip("/")
    if not url_base:
        raise IBKRServiceError("IBKR service URL is not configured")
    url = f"{url_base}/symbols/search"
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, params={"query": query})
    except httpx.HTTPError as exc:  # pragma: no cover - network failure handling
        raise IBKRServiceError(f"Failed to reach IBKR service: {exc}") from exc

    if response.status_code >= 400:
        detail: Any
        try:
            payload = response.json()
            detail = payload.get("detail", payload)
        except Exception:  # pragma: no cover - defensive parsing
            detail = response.text
        raise IBKRServiceError(f"IBKR service error {response.status_code}: {detail}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise IBKRServiceError("IBKR service returned invalid JSON payload") from exc

    matches: Any
    if isinstance(payload, dict):
        matches = payload.get("results", [])
    else:
        matches = payload

    if not isinstance(matches, list):
        raise IBKRServiceError("IBKR service response is not a list of results")

    results: list[SymbolSearchResultSchema] = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        raw_symbol = item.get("symbol") or item.get("ticker") or ""
        symbol = str(raw_symbol).strip().upper()
        if not symbol:
            continue
        name_value = item.get("name") or raw_symbol or symbol
        schema = SymbolSearchResultSchema(
            symbol=symbol,
            name=str(name_value),
            region=item.get("region"),
            currency=item.get("currency"),
            match_score=item.get("match_score"),
        )
        results.append(schema)
    return results


async def fetch_price_bars(
    symbol: str,
    *,
    base_url: str | None = None,
    bar_size: str | None = None,
    duration_days: int | None = None,
    use_rth: bool | None = None,
    timeout_seconds: float = 15.0,
) -> list[dict[str, Any]]:
    """Fetch raw bar payloads from the IBKR bridge."""

    settings = get_settings()
    url_base = (base_url or settings.ibkr_service_url or "").rstrip("/")
    if not url_base:
        raise IBKRServiceError("IBKR service URL is not configured")
    url = f"{url_base}/prices"
    params: dict[str, Any] = {}
    if bar_size:
        params["bar_size"] = bar_size
    if duration_days:
        params["duration_days"] = duration_days
    if use_rth is not None:
        params["use_rth"] = use_rth
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(url, params=params, json={"symbol": symbol})
    except httpx.HTTPError as exc:  # pragma: no cover - network failure handling
        raise IBKRServiceError(f"Failed to reach IBKR service: {exc}") from exc

    if response.status_code >= 400:
        detail: Any
        try:
            payload = response.json()
            detail = payload.get("detail", payload)
        except Exception:  # pragma: no cover - defensive parsing
            detail = response.text
        raise IBKRServiceError(f"IBKR service error {response.status_code}: {detail}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise IBKRServiceError("IBKR service returned invalid JSON payload") from exc

    bars: Any
    if isinstance(payload, dict):
        bars = payload.get("bars", [])
    else:
        bars = payload

    if not isinstance(bars, list):
        raise IBKRServiceError("IBKR service response is not a list of bars")
    return bars


__all__ = ["IBKRServiceError", "search_symbols", "fetch_price_bars"]
