"""Schemas for scenario simulator stubs."""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class WhatIfAction(BaseModel):
    type: Literal["BUY", "SELL", "HEDGE"]
    date: date
    qty_pct: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    price: str | float


class SimulationRequest(BaseModel):
    symbol: str
    base_timeline_id: str = Field(default="current")
    what_if: list[WhatIfAction]
    assumptions: dict[str, float] | None = None


class SimulationResponse(BaseModel):
    timeline_id: str
    diff_vs_base: dict[str, float]


__all__ = ["SimulationRequest", "SimulationResponse", "WhatIfAction"]
