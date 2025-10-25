"""Schemas for ticker sentiment responses."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class TickerSentimentDailySchema(BaseModel):
    symbol: str
    date: date
    score: float = Field(..., ge=-1.0, le=1.0)


class SentimentSeriesResponse(BaseModel):
    symbol: str
    points: list[TickerSentimentDailySchema]


__all__ = ["TickerSentimentDailySchema", "SentimentSeriesResponse"]
