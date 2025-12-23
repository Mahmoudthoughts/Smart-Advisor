"""Schemas for Monte Carlo risk analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MonteCarloRequest(BaseModel):
    starting_capital: float = Field(..., gt=0)
    runs: int = Field(..., gt=0)
    trades_per_run: int = Field(..., gt=0)
    win_rate: float = Field(..., ge=0.0, le=1.0)
    avg_win: float = Field(..., ge=0.0)
    avg_loss: float = Field(..., ge=0.0)
    risk_multiplier: float = Field(1.0, gt=0.0)
    fee_per_trade: float = Field(0.0, ge=0.0)
    slippage_pct: float = Field(0.0, ge=0.0)
    include_series: bool = True
    use_ai: bool = False


class MonteCarloPercentiles(BaseModel):
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float


class MonteCarloSeries(BaseModel):
    final_returns: list[float]
    max_drawdowns: list[float]


class MonteCarloResponse(BaseModel):
    final_return_pct: MonteCarloPercentiles
    max_drawdown_pct: MonteCarloPercentiles
    probability_ruin: float
    probability_max_drawdown_over_30: float
    series: MonteCarloSeries | None = None
    ai_selected_params: dict[str, float] | None = None
    ai_score_breakdown: dict[str, float] | None = None


__all__ = [
    "MonteCarloPercentiles",
    "MonteCarloRequest",
    "MonteCarloResponse",
    "MonteCarloSeries",
]
