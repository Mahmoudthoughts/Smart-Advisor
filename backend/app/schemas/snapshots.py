"""Pydantic schemas for timeline and snapshots."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class DailyPortfolioSnapshotSchema(BaseModel):
    symbol: str = Field(..., examples=["PATH"])
    date: date
    shares_open: float
    market_value_base: float
    cost_basis_open_base: float
    unrealized_pl_base: float
    realized_pl_to_date_base: float
    hypo_liquidation_pl_base: float
    day_opportunity_base: float
    peak_hypo_pl_to_date_base: float
    drawdown_from_peak_pct: float

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "PATH",
                "date": "2024-09-10",
                "shares_open": 150,
                "market_value_base": 2100,
                "cost_basis_open_base": 1610,
                "unrealized_pl_base": 490,
                "realized_pl_to_date_base": 0,
                "hypo_liquidation_pl_base": 485,
                "day_opportunity_base": 485,
                "peak_hypo_pl_to_date_base": 485,
                "drawdown_from_peak_pct": 0.0,
            }
        }


class TimelinePricePointSchema(BaseModel):
    date: date
    adj_close: float


class TimelineTransactionSchema(BaseModel):
    id: int
    symbol: str
    type: str
    quantity: float
    price: float
    trade_datetime: datetime
    fee: float
    tax: float
    account_id: int | None = None
    account: str | None = None
    notes: str | None = None
    notional_value: float


class TimelineResponse(BaseModel):
    symbol: str
    snapshots: list[DailyPortfolioSnapshotSchema]
    prices: list[TimelinePricePointSchema]
    transactions: list[TimelineTransactionSchema]


class TopMissedDaySchema(BaseModel):
    date: date
    symbol: str
    day_opportunity_base: float
    delta_vs_today_base: Optional[float] = None


__all__ = [
    "DailyPortfolioSnapshotSchema",
    "TimelinePricePointSchema",
    "TimelineTransactionSchema",
    "TimelineResponse",
    "TopMissedDaySchema",
]
