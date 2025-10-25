"""Schemas for forecast API stubs."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class ForecastResponse(BaseModel):
    symbol: str
    as_of: date
    prob_retake_peak_30d: Optional[float] = None
    expected_regret_delta: Optional[float] = None
    drivers: list[str] = Field(default_factory=list)


__all__ = ["ForecastResponse"]
