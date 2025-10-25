"""Signal endpoints for Smart Advisor."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import SignalEvent
from app.schemas import SignalEventSchema, SignalRuleDefinition, SignalRuleUpsertRequest

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


__all__ = ["list_signals", "upsert_rules"]
