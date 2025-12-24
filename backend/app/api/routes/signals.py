"""Signal endpoints for Smart Advisor."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.indicators.gap_down import backtest_gap_down, compute_gap_down_signal
from app.models import SignalEvent
from app.providers.alpha_vantage import AlphaVantageError, get_alpha_vantage_client
from app.schemas import (
    GapDownBacktestStatsSchema,
    GapDownSignalSchema,
    SignalEventSchema,
    SignalRuleDefinition,
    SignalRuleUpsertRequest,
)
from app.services.market_data import load_ohlc

router = APIRouter()
_RULE_DEFINITIONS: dict[str, SignalRuleDefinition] = {}


@router.get("/{symbol}", response_model=list[SignalEventSchema])
async def list_signals(
    symbol: str,
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_db),
) -> list[SignalEventSchema]:
    stmt = select(SignalEvent).where(SignalEvent.symbol == symbol)
    if from_date:
        stmt = stmt.where(SignalEvent.date >= from_date)
    if to_date:
        stmt = stmt.where(SignalEvent.date <= to_date)
    stmt = stmt.order_by(SignalEvent.date)
    rows = (await session.execute(stmt)).scalars().all()
    return [
        SignalEventSchema(
            id=row.id,
            symbol=row.symbol,
            date=row.date,
            rule_id=row.rule_id,
            signal_type=row.signal_type,
            severity=row.severity,
            payload=row.payload,
        )
        for row in rows
    ]


@router.post("/rules", response_model=list[SignalRuleDefinition])
async def upsert_rules(payload: SignalRuleUpsertRequest) -> list[SignalRuleDefinition]:
    for rule in payload.rules:
        _RULE_DEFINITIONS[rule.rule_id] = rule
    return list(_RULE_DEFINITIONS.values())


@router.get("/gap-down", response_model=GapDownSignalSchema)
async def gap_down_signal(
    symbol: str = Query(..., min_length=1, max_length=16),
    client=Depends(get_alpha_vantage_client),
) -> GapDownSignalSchema:
    try:
        df = await load_ohlc(symbol, client, min_rows=2)
        signal = compute_gap_down_signal(df, symbol.strip().upper())
        return GapDownSignalSchema(**signal.__dict__)
    except AlphaVantageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Alpha Vantage error: {exc}",
        ) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "No data" in message else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get("/gap-down/backtest", response_model=GapDownBacktestStatsSchema)
async def gap_down_backtest(
    symbol: str = Query(..., min_length=1, max_length=16),
    start: date = Query(default=date(2000, 1, 1)),
    client=Depends(get_alpha_vantage_client),
) -> GapDownBacktestStatsSchema:
    try:
        df = await load_ohlc(symbol, client, start=start, min_rows=3)
        stats = backtest_gap_down(df)
        return GapDownBacktestStatsSchema(symbol=symbol.strip().upper(), start=start, **stats)
    except AlphaVantageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Alpha Vantage error: {exc}",
        ) from exc
    except ValueError as exc:
        message = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if "No data" in message else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=status_code, detail=message) from exc


__all__ = ["list_signals", "upsert_rules", "gap_down_signal", "gap_down_backtest"]
