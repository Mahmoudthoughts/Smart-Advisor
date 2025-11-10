"""Proxy portfolio endpoints that delegate to the portfolio service."""

from __future__ import annotations

import logging
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.ingest.client import IngestServiceError, trigger_price_ingest
from app.config import get_settings
from app.models import DailyBar, DailyPortfolioSnapshot, Transaction
from app.providers.alpha_vantage import AlphaVantageError
from app.schemas import (
    PortfolioAccountCreateRequest,
    PortfolioAccountSchema,
    TransactionCreateRequest,
    TransactionSchema,
    TransactionUpdateRequest,
    WatchlistCreateRequest,
    WatchlistSymbolSchema,
)
from app.services import portfolio as portfolio_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/watchlist", response_model=list[WatchlistSymbolSchema])
async def get_watchlist() -> list[WatchlistSymbolSchema]:
    data = await portfolio_client.fetch_watchlist()
    return [WatchlistSymbolSchema(**item) for item in data]


@router.post("/watchlist", response_model=WatchlistSymbolSchema, status_code=status.HTTP_201_CREATED)
async def post_watchlist(
    payload: WatchlistCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> WatchlistSymbolSchema:
    try:
        record = await add_watchlist_symbol(payload.symbol, session, display_name=payload.name)
    except ValueError as exc:  # empty or invalid symbol
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        settings = get_settings()
        if not settings.ingest_base_url:
            logger.error("INGEST_BASE_URL not configured; cannot ingest %s via microservice", record.symbol)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ingest service not configured (INGEST_BASE_URL missing)",
            )
        logger.info(
            "Using ingest microservice for %s at %s (run_sync=True)",
            record.symbol,
            settings.ingest_base_url,
        )
        await trigger_price_ingest(record.symbol, settings.ingest_base_url, run_sync=True)
    except (AlphaVantageError, IngestServiceError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to fetch market data") from exc

    await recompute_snapshots_for_symbol(record.symbol, session)

    latest_stmt: Select = (
        select(DailyBar).where(DailyBar.symbol == record.symbol).order_by(DailyBar.date.desc()).limit(1)
    )
    latest = (await session.execute(latest_stmt)).scalars().first()
    return WatchlistSymbolSchema(
        id=record.id,
        symbol=record.symbol,
        created_at=record.created_at,
        latest_close=float(latest.adj_close) if latest else None,
        latest_close_date=latest.date if latest else None,
        previous_close=None,
        day_change=None,
        day_change_percent=None,
        position_qty=None,
        average_cost=None,
        unrealized_pl=None,
        name=record.display_name,
    )


@router.get("/transactions", response_model=list[TransactionSchema])
async def get_transactions() -> list[TransactionSchema]:
    data = await portfolio_client.list_transactions()
    return [TransactionSchema(**item) for item in data]


@router.post("/transactions", response_model=TransactionSchema, status_code=201)
async def post_transaction(payload: TransactionCreateRequest) -> TransactionSchema:
    data = await portfolio_client.create_transaction(payload.dict())
    return TransactionSchema(**data)


@router.put("/transactions/{transaction_id}", response_model=TransactionSchema)
async def put_transaction(transaction_id: int, payload: TransactionUpdateRequest) -> TransactionSchema:
    data = await portfolio_client.update_transaction(transaction_id, payload.dict())
    return TransactionSchema(**data)


@router.get("/accounts", response_model=list[PortfolioAccountSchema])
async def get_accounts() -> list[PortfolioAccountSchema]:
    data = await portfolio_client.list_accounts()
    return [PortfolioAccountSchema(**item) for item in data]


@router.post("/accounts", response_model=PortfolioAccountSchema, status_code=201)
async def post_account(payload: PortfolioAccountCreateRequest) -> PortfolioAccountSchema:
    data = await portfolio_client.create_account(payload.dict())
    return PortfolioAccountSchema(**data)


__all__ = ["router"]
