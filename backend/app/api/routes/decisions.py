"""Endpoints for tracking investor decisions and their outcomes."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import DailyBar, DecisionAction, DecisionStatus, InvestmentDecision
from app.schemas import (
    InvestmentDecisionCreateRequest,
    InvestmentDecisionOutcomeSchema,
    InvestmentDecisionResolveRequest,
    InvestmentDecisionSchema,
)

router = APIRouter()


async def _lookup_latest_close(
    session: AsyncSession, symbol: str, as_of_date: datetime | None
) -> float | None:
    stmt: Select = select(DailyBar).where(DailyBar.symbol == symbol)
    if as_of_date:
        stmt = stmt.where(DailyBar.date <= as_of_date.date())
    stmt = stmt.order_by(DailyBar.date.desc()).limit(1)
    row = (await session.execute(stmt)).scalar_one_or_none()
    return float(row.adj_close) if row else None


def _to_float(value: Decimal | float | None) -> float | None:
    if value is None:
        return None
    return float(Decimal(str(value)))


def _compute_outcome(decision: InvestmentDecision) -> InvestmentDecisionOutcomeSchema:
    decision_price = _to_float(decision.decision_price)
    terminal_price = _to_float(decision.outcome_price or decision.resolved_price)
    quantity = decision.actual_quantity if decision.actual_quantity is not None else decision.planned_quantity

    price_change = None
    price_change_pct = None
    projected_value_change = None

    if decision_price is not None and terminal_price is not None:
        price_change = terminal_price - decision_price
        if decision_price:
            price_change_pct = (price_change / decision_price) * 100
        if quantity is not None:
            direction = 1 if decision.action in (DecisionAction.BUY_MORE, DecisionAction.HOLD) else -1
            projected_value_change = price_change * float(quantity) * direction

    return InvestmentDecisionOutcomeSchema(
        price_change=price_change,
        price_change_pct=price_change_pct,
        projected_value_change=projected_value_change,
    )


def _serialize(decision: InvestmentDecision) -> InvestmentDecisionSchema:
    return InvestmentDecisionSchema(
        id=decision.id,
        portfolio_id=decision.portfolio_id,
        investor=decision.investor,
        symbol=decision.symbol,
        action=decision.action,
        planned_quantity=_to_float(decision.planned_quantity),
        decision_price=_to_float(decision.decision_price),
        decision_at=decision.decision_at,
        status=decision.status,
        resolved_at=decision.resolved_at,
        resolved_price=_to_float(decision.resolved_price),
        actual_quantity=_to_float(decision.actual_quantity),
        outcome_price=_to_float(decision.outcome_price),
        notes=decision.notes,
        outcome_notes=decision.outcome_notes,
        outcome=_compute_outcome(decision),
    )


async def _fetch_decisions(
    session: AsyncSession,
    *,
    symbol: str | None = None,
    investor: str | None = None,
    status: DecisionStatus | None = None,
) -> Iterable[InvestmentDecision]:
    stmt: Select = select(InvestmentDecision)
    if symbol:
        stmt = stmt.where(InvestmentDecision.symbol == symbol.strip().upper())
    if investor:
        stmt = stmt.where(InvestmentDecision.investor == investor.strip())
    if status:
        stmt = stmt.where(InvestmentDecision.status == status)
    stmt = stmt.order_by(desc(InvestmentDecision.decision_at))
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("", response_model=list[InvestmentDecisionSchema])
async def list_decisions(
    symbol: str | None = Query(default=None, description="Optional symbol filter"),
    investor: str | None = Query(default=None, description="Optional investor filter"),
    status_filter: DecisionStatus | None = Query(
        default=None, alias="status", description="Filter by decision status"
    ),
    session: AsyncSession = Depends(get_db),
) -> list[InvestmentDecisionSchema]:
    decisions = await _fetch_decisions(session, symbol=symbol, investor=investor, status=status_filter)
    return [_serialize(item) for item in decisions]


@router.post("", response_model=InvestmentDecisionSchema, status_code=status.HTTP_201_CREATED)
async def log_decision(
    payload: InvestmentDecisionCreateRequest, session: AsyncSession = Depends(get_db)
) -> InvestmentDecisionSchema:
    symbol = payload.symbol.strip().upper()
    decision_at = payload.decision_at or datetime.utcnow()
    decision_price = payload.decision_price
    if decision_price is None:
        decision_price = await _lookup_latest_close(session, symbol, decision_at)

    decision = InvestmentDecision(
        portfolio_id=payload.portfolio_id,
        investor=payload.investor.strip(),
        symbol=symbol,
        action=payload.action,
        planned_quantity=payload.planned_quantity,
        decision_price=decision_price,
        decision_at=decision_at,
        notes=payload.notes,
    )
    session.add(decision)
    await session.commit()
    await session.refresh(decision)
    return _serialize(decision)


@router.put("/{decision_id}", response_model=InvestmentDecisionSchema)
async def resolve_decision(
    decision_id: int,
    payload: InvestmentDecisionResolveRequest,
    session: AsyncSession = Depends(get_db),
) -> InvestmentDecisionSchema:
    decision = await session.get(InvestmentDecision, decision_id)
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    decision.status = payload.status
    decision.resolved_at = payload.resolved_at or decision.resolved_at or datetime.utcnow()

    if payload.actual_quantity is not None:
        decision.actual_quantity = payload.actual_quantity
    elif decision.actual_quantity is None and decision.planned_quantity is not None:
        decision.actual_quantity = decision.planned_quantity

    if payload.resolved_price is not None:
        decision.resolved_price = payload.resolved_price
    elif decision.resolved_price is None:
        decision.resolved_price = await _lookup_latest_close(session, decision.symbol, decision.resolved_at)

    if payload.outcome_price is not None:
        decision.outcome_price = payload.outcome_price
    elif decision.outcome_price is None:
        decision.outcome_price = decision.resolved_price

    if payload.outcome_notes is not None:
        decision.outcome_notes = payload.outcome_notes

    await session.commit()
    await session.refresh(decision)
    return _serialize(decision)


__all__ = ["router"]
