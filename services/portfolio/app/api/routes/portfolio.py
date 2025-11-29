"""Portfolio watchlist, transactions, and accounts endpoints."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import DailyBar, DailyPortfolioSnapshot, Transaction
from ...schemas import (
    PortfolioAccountCreateRequest,
    PortfolioAccountSchema,
    TransactionCreateRequest,
    TransactionSchema,
    TransactionUpdateRequest,
    WatchlistCreateRequest,
    WatchlistSymbolSchema,
)
from ...services import portfolio as portfolio_service
from ...services.ingest_client import ingest_prices
from ..dependencies import InternalAuth, RequestContext, get_db_session, get_request_context

router = APIRouter(dependencies=[InternalAuth])


def _serialize_transaction(tx: Transaction) -> TransactionSchema:
    qty = float(Decimal(str(tx.qty)))
    price = float(Decimal(str(tx.price)))
    fee = float(Decimal(str(tx.fee)))
    tax = float(Decimal(str(tx.tax)))
    # Fetch relationship via __dict__ to avoid lazy-load in async context
    account = tx.__dict__.get("account")
    account_label = account.name if account else tx.broker_id
    return TransactionSchema(
        id=tx.id,
        symbol=tx.symbol,
        type=tx.type,
        quantity=qty,
        price=price,
        fee=fee,
        tax=tax,
        currency=tx.currency,
        trade_datetime=tx.datetime,
        account_id=tx.account_id,
        account=account_label,
        notes=tx.notes,
        notional_value=qty * price,
    )


@router.get("/watchlist", response_model=list[WatchlistSymbolSchema])
async def get_watchlist(
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> list[WatchlistSymbolSchema]:
    symbols = await portfolio_service.list_watchlist(session, owner_id=context.user_id)
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
            .where(
                DailyPortfolioSnapshot.symbol == item.symbol,
                DailyPortfolioSnapshot.portfolio_id == item.portfolio_id,
            )
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
        latest_close = float(latest.adj_close) if latest else None
        previous_close = float(previous.adj_close) if previous else None
        if latest_close is not None and previous_close is not None:
            day_change = latest_close - previous_close
            if previous_close:
                day_change_pct = (day_change / previous_close) * 100
        response.append(
            WatchlistSymbolSchema(
                id=item.id,
                symbol=item.symbol,
                created_at=item.created_at,
                latest_close=latest_close,
                latest_close_date=latest.date if latest else None,
                previous_close=previous_close,
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
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> WatchlistSymbolSchema:
    try:
        record = await portfolio_service.add_watchlist_symbol(
            payload.symbol, session, owner_id=context.user_id, display_name=payload.name
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        await ingest_prices(record.symbol)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to fetch market data") from exc

    await portfolio_service.recompute_snapshots_for_symbol(record.symbol, session, owner_id=context.user_id)

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
async def get_transactions(
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> list[TransactionSchema]:
    transactions = await portfolio_service.list_transactions(session, owner_id=context.user_id)
    return [_serialize_transaction(tx) for tx in transactions]


@router.post("/transactions", response_model=TransactionSchema, status_code=status.HTTP_201_CREATED)
async def post_transaction(
    payload: TransactionCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> TransactionSchema:
    try:
        tx = await portfolio_service.create_transaction(payload, session, owner_id=context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_transaction(tx)


@router.put("/transactions/{transaction_id}", response_model=TransactionSchema)
async def put_transaction(
    transaction_id: int,
    payload: TransactionUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> TransactionSchema:
    try:
        tx = await portfolio_service.update_transaction(transaction_id, payload, session, owner_id=context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_transaction(tx)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> Response:
    try:
        await portfolio_service.delete_transaction(transaction_id, session, owner_id=context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/accounts", response_model=list[PortfolioAccountSchema])
async def get_accounts(
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> list[PortfolioAccountSchema]:
    records = await portfolio_service.list_accounts(session, owner_id=context.user_id)
    return [
        PortfolioAccountSchema(
            id=record.id,
            name=record.name,
            type=record.type,
            currency=record.currency,
            notes=record.notes,
            is_default=record.is_default,
            created_at=record.created_at,
        )
        for record in records
    ]


@router.post("/accounts", response_model=PortfolioAccountSchema, status_code=status.HTTP_201_CREATED)
async def post_account(
    payload: PortfolioAccountCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> PortfolioAccountSchema:
    try:
        record = await portfolio_service.create_account(payload, session, owner_id=context.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PortfolioAccountSchema(
        id=record.id,
        name=record.name,
        type=record.type,
        currency=record.currency,
        notes=record.notes,
        is_default=record.is_default,
        created_at=record.created_at,
    )


@router.post("/snapshots/{symbol}/recompute")
async def post_recompute_snapshots(
    symbol: str,
    session: AsyncSession = Depends(get_db_session),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, str | int]:
    snapshots = await portfolio_service.recompute_snapshots_for_symbol(symbol, session, owner_id=context.user_id)
    return {"symbol": symbol.strip().upper(), "snapshots_rebuilt": len(snapshots)}


__all__ = ["router"]

