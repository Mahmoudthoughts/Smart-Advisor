"""Sentiment routes."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import TickerSentimentDaily
from app.schemas import SentimentSeriesResponse, TickerSentimentDailySchema

router = APIRouter()


@router.get("/{symbol}", response_model=SentimentSeriesResponse)
async def get_sentiment_series(
    symbol: str,
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_db),
) -> SentimentSeriesResponse:
    stmt = select(TickerSentimentDaily).where(TickerSentimentDaily.symbol == symbol)
    if from_date:
        stmt = stmt.where(TickerSentimentDaily.date >= from_date)
    if to_date:
        stmt = stmt.where(TickerSentimentDaily.date <= to_date)
    stmt = stmt.order_by(TickerSentimentDaily.date)
    rows = (await session.execute(stmt)).scalars().all()
    return SentimentSeriesResponse(
        symbol=symbol,
        points=[
            TickerSentimentDailySchema(symbol=row.symbol, date=row.date, score=float(row.score))
            for row in rows
        ],
    )


__all__ = ["get_sentiment_series"]
