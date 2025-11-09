"""FastAPI entrypoint for the ingest service."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from .alpha_vantage import AlphaVantageError, get_alpha_vantage_client
from .config import get_settings
from .db import _session_factory, _engine
from .fx import ingest_fx_pair
from .prices import ingest_prices
from .telemetry import setup_telemetry

logger = logging.getLogger("services.ingest")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Smart Advisor Ingest Service", version="0.1.0")
setup_telemetry(app, engine=_engine)


class PriceIngestRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Ticker symbol to ingest")


class FXIngestRequest(BaseModel):
    from_ccy: str = Field(..., min_length=3, max_length=3, description="Source currency code")
    to_ccy: str = Field(..., min_length=3, max_length=3, description="Target currency code")


async def _run_price_job(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()
    logger.info("Starting price ingest for %s", symbol)
    try:
        async with _session_factory() as session:
            inserted = await ingest_prices(symbol, session)
    except Exception:
        logger.exception("Price ingest for %s failed", symbol)
        raise
    logger.info("Price ingest for %s completed (%d rows)", symbol, inserted)
    return {"symbol": symbol, "rows": inserted}


async def _run_fx_job(from_ccy: str, to_ccy: str) -> dict[str, Any]:
    pair = f"{from_ccy.upper()}/{to_ccy.upper()}"
    logger.info("Starting FX ingest for %s", pair)
    try:
        async with _session_factory() as session:
            inserted = await ingest_fx_pair(from_ccy.upper(), to_ccy.upper(), session)
    except Exception:
        logger.exception("FX ingest for %s failed", pair)
        raise
    logger.info("FX ingest for %s completed (%d rows)", pair, inserted)
    return {"pair": pair, "rows": inserted}


@app.get("/health", tags=["system"])
async def health() -> dict[str, Any]:
    """Lightweight health probe."""

    settings = get_settings()
    return {
        "status": "ok",
        "rate_limit": settings.alphavantage_requests_per_minute,
        "base_currency": settings.base_currency,
    }


async def _schedule(
    background_tasks: BackgroundTasks,
    coro_fn: Callable[..., Awaitable[dict[str, Any]]],
    *args: Any,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        background_tasks.add_task(coro_fn, *args)
    except RuntimeError:
        # Fallback when BackgroundTasks has already been awaited.
        asyncio.create_task(coro_fn(*args))
    response = {"status": "scheduled"}
    if metadata:
        response.update(metadata)
    return response


@app.post("/jobs/prices", status_code=status.HTTP_202_ACCEPTED, tags=["jobs"])
async def trigger_price_ingest(
    payload: PriceIngestRequest,
    background_tasks: BackgroundTasks,
    run_sync: bool = False,
) -> dict[str, Any]:
    """Schedule or run a price ingest job for the requested symbol."""

    try:
        if run_sync:
            return await _run_price_job(payload.symbol)
        return await _schedule(
            background_tasks,
            _run_price_job,
            payload.symbol,
            metadata={"symbol": payload.symbol.upper()},
        )
    except AlphaVantageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/jobs/fx", status_code=status.HTTP_202_ACCEPTED, tags=["jobs"])
async def trigger_fx_ingest(
    payload: FXIngestRequest,
    background_tasks: BackgroundTasks,
    run_sync: bool = False,
) -> dict[str, Any]:
    """Schedule or run an FX ingest job for the requested currency pair."""

    try:
        if run_sync:
            return await _run_fx_job(payload.from_ccy, payload.to_ccy)
        return await _schedule(
            background_tasks,
            _run_fx_job,
            payload.from_ccy,
            payload.to_ccy,
            metadata={"pair": f"{payload.from_ccy.upper()}/{payload.to_ccy.upper()}"},
        )
    except AlphaVantageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Ensure the API client is closed when the service stops."""

    client = get_alpha_vantage_client()
    await client.aclose()
