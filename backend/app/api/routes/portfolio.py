"""Portfolio watchlist and transaction endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.ingest.prices import ingest_prices
from app.models import DailyBar, Transaction
from app.providers.alpha_vantage import AlphaVantageError
from app.schemas import (
    TransactionCreateRequest,
    TransactionSchema,
    WatchlistCreateRequest,
    WatchlistSymbolSchema,
)
from app.services.portfolio import (
    add_watchlist_symbol,
    create_transaction,
    list_transactions,
    list_watchlist,
    recompute_snapshots_for_symbol,
)

router = APIRouter()


def _serialize_transaction(tx: Transaction) -> TransactionSchema:
    qty = float(Decimal(str(tx.qty)))
    price = float(Decimal(str(tx.price)))
    return TransactionSchema(
        id=tx.id,
        symbol=tx.symbol,
        type=tx.type,
        quantity=qty,
        price=price,
        fee=float(Decimal(str(tx.fee))),
        tax=float(Decimal(str(tx.tax))),
        currency=tx.currency,
        trade_datetime=tx.datetime,
        account=tx.broker_id,
        notes=tx.notes,
        notional_value=qty * price,
    )


@router.get("/watchlist", response_model=list[WatchlistSymbolSchema])
async def get_watchlist(session: AsyncSession = Depends(get_db)) -> list[WatchlistSymbolSchema]:
    symbols = await list_watchlist(session)
    response: list[WatchlistSymbolSchema] = []
    for item in symbols:
        latest_stmt: Select = (
            select(DailyBar)
            .where(DailyBar.symbol == item.symbol)
            .order_by(DailyBar.date.desc())
            .limit(1)
        )
        latest = (await session.execute(latest_stmt)).scalars().first()
        response.append(
            WatchlistSymbolSchema(
                id=item.id,
                symbol=item.symbol,
                created_at=item.created_at,
                latest_close=float(latest.adj_close) if latest else None,
                latest_close_date=latest.date if latest else None,
            )
        )
    return response


@router.post("/watchlist", response_model=WatchlistSymbolSchema, status_code=status.HTTP_201_CREATED)
async def post_watchlist(
    payload: WatchlistCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> WatchlistSymbolSchema:
    try:
        record = await add_watchlist_symbol(payload.symbol, session)
    except ValueError as exc:  # empty or invalid symbol
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        await ingest_prices(record.symbol, session)
    except AlphaVantageError as exc:
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
    )


@router.get("/transactions", response_model=list[TransactionSchema])
async def get_transactions(session: AsyncSession = Depends(get_db)) -> list[TransactionSchema]:
    transactions = await list_transactions(session)
    return [_serialize_transaction(tx) for tx in transactions]


@router.post("/transactions", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
async def post_transaction(
    payload: TransactionCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> TransactionSchema:
    tx = await create_transaction(payload, session)
    return _serialize_transaction(tx)


__all__ = ["router"]
