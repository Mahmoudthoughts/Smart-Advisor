"""Forecast route stubs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas import ForecastResponse

router = APIRouter()


@router.get("/{symbol}", response_model=ForecastResponse)
async def get_forecast(symbol: str, as_of: Optional[date] = Query(default=None, alias="asof")) -> ForecastResponse:
    """Return stubbed forecast response."""

    as_of = as_of or date.today()
    return ForecastResponse(symbol=symbol, as_of=as_of, prob_retake_peak_30d=None, expected_regret_delta=None)


__all__ = ["get_forecast"]
