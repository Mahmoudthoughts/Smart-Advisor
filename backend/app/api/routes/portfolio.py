"""Portfolio watchlist and transaction endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.ingest.prices import ingest_prices
from app.models import DailyBar, DailyPortfolioSnapshot, Transaction
from app.providers.alpha_vantage import AlphaVantageError
from app.schemas import (
    TransactionCreateRequest,
    TransactionSchema,
    TransactionUpdateRequest,
    WatchlistCreateRequest,
    WatchlistSymbolSchema,
)
from app.services.portfolio import (
    add_watchlist_symbol,
    create_transaction,
    update_transaction,
    list_transactions,
    list_watchlist,
    recompute_snapshots_for_symbol,
)

router = APIRouter()


def _serialize_transaction(tx: Transaction) -> TransactionSchema:
    qty = float(Decimal(str(tx.qty)))
    price = float(Decimal(str(tx.price)))
    account_label = tx.account.name if tx.account else tx.broker_id
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
        account_id=tx.account_id,
        account=account_label,
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
            .limit(2)
        )
        latest_rows = (await session.execute(latest_stmt)).scalars().all()
        latest = latest_rows[0] if latest_rows else None
        previous = latest_rows[1] if len(latest_rows) > 1 else None
        snapshot_stmt: Select = (
            select(DailyPortfolioSnapshot)
            .where(DailyPortfolioSnapshot.symbol == item.symbol)
            .order_by(DailyPortfolioSnapshot.date.desc())
            .limit(1)
        )
        snapshot = (await session.execute(snapshot_stmt)).scalars().first()
        shares_open = float(snapshot.shares_open) if snapshot else None
        average_cost = None
        unrealized = None
        if snapshot and snapshot.shares_open:
            shares_val = float(snapshot.shares_open)
            cost_basis = float(snapshot.cost_basis_open_base)
            average_cost = cost_basis / shares_val if shares_val else None
            unrealized = float(snapshot.unrealized_pl_base)
        elif snapshot:
            shares_open = float(snapshot.shares_open)
            unrealized = float(snapshot.unrealized_pl_base)
        day_change = None
        day_change_pct = None
        if latest and previous:
            day_change = float(latest.adj_close - previous.adj_close)
            if previous.adj_close:
                day_change_pct = float((day_change / previous.adj_close) * 100)
        response.append(
            WatchlistSymbolSchema(
                id=item.id,
                symbol=item.symbol,
                created_at=item.created_at,
                latest_close=float(latest.adj_close) if latest else None,
                latest_close_date=latest.date if latest else None,
                previous_close=float(previous.adj_close) if previous else None,
                day_change=day_change,
                day_change_percent=day_change_pct,
                position_qty=shares_open,
                average_cost=average_cost,
                unrealized_pl=unrealized,
                name=item.display_name,
            )
        )
    return response


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
        previous_close=None,
        day_change=None,
        day_change_percent=None,
        position_qty=None,
        average_cost=None,
        unrealized_pl=None,
        name=record.display_name,
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
    try:
        tx = await create_transaction(payload, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_transaction(tx)


@router.put("/transactions/{transaction_id}", response_model=TransactionSchema)
async def put_transaction(
    transaction_id: int,
    payload: TransactionUpdateRequest,
    session: AsyncSession = Depends(get_db),
) -> TransactionSchema:
    try:
        tx = await update_transaction(transaction_id, payload, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_transaction(tx)


__all__ = ["router"]
