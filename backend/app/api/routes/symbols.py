"""Symbol timeline endpoints."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import DailyPortfolioSnapshot
from app.schemas.snapshots import DailyPortfolioSnapshotSchema, TimelineResponse, TopMissedDaySchema

router = APIRouter()


@router.get("/{symbol}/timeline", response_model=TimelineResponse)
async def get_symbol_timeline(
    symbol: str,
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    stmt: Select = select(DailyPortfolioSnapshot).where(DailyPortfolioSnapshot.symbol == symbol)
    if from_date:
        stmt = stmt.where(DailyPortfolioSnapshot.date >= from_date)
    if to_date:
        stmt = stmt.where(DailyPortfolioSnapshot.date <= to_date)
    stmt = stmt.order_by(DailyPortfolioSnapshot.date)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    snapshots = [
        DailyPortfolioSnapshotSchema(
            symbol=row.symbol,
            date=row.date,
            shares_open=float(row.shares_open),
            market_value_base=float(row.market_value_base),
            cost_basis_open_base=float(row.cost_basis_open_base),
            unrealized_pl_base=float(row.unrealized_pl_base),
            realized_pl_to_date_base=float(row.realized_pl_to_date_base),
            hypo_liquidation_pl_base=float(row.hypo_liquidation_pl_base),
            day_opportunity_base=float(row.day_opportunity_base),
            peak_hypo_pl_to_date_base=float(row.peak_hypo_pl_to_date_base),
            drawdown_from_peak_pct=float(row.drawdown_from_peak_pct),
        )
        for row in rows
    ]
    return TimelineResponse(symbol=symbol, snapshots=snapshots)


@router.get("/{symbol}/top-missed", response_model=list[TopMissedDaySchema])
async def get_top_missed_days(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> list[TopMissedDaySchema]:
    stmt = (
        select(DailyPortfolioSnapshot)
        .where(DailyPortfolioSnapshot.symbol == symbol)
        .order_by(DailyPortfolioSnapshot.day_opportunity_base.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    today_stmt = (
        select(DailyPortfolioSnapshot)
        .where(DailyPortfolioSnapshot.symbol == symbol)
        .order_by(DailyPortfolioSnapshot.date.desc())
        .limit(1)
    )
    today_row = (await session.execute(today_stmt)).scalars().first()
    delta_anchor = float(today_row.day_opportunity_base) if today_row else 0.0
    return [
        TopMissedDaySchema(
            date=row.date,
            symbol=row.symbol,
            day_opportunity_base=float(row.day_opportunity_base),
            delta_vs_today_base=float(row.day_opportunity_base) - delta_anchor,
        )
        for row in rows
    ]
