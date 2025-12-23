"""Monte Carlo risk analysis endpoints."""

from __future__ import annotations

import random
from math import ceil, floor

from fastapi import APIRouter

from app.schemas import MonteCarloPercentiles, MonteCarloRequest, MonteCarloResponse, MonteCarloSeries

try:  # pragma: no cover - optional dependency
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

router = APIRouter()


def _percentiles(values: list[float]) -> MonteCarloPercentiles:
    if np is not None:
        percentiles = np.percentile(values, [5, 25, 50, 75, 95]).tolist()
        return MonteCarloPercentiles(
            p5=percentiles[0],
            p25=percentiles[1],
            p50=percentiles[2],
            p75=percentiles[3],
            p95=percentiles[4],
        )

    sorted_values = sorted(values)
    count = len(sorted_values)

    def percentile(q: float) -> float:
        if count == 1:
            return sorted_values[0]
        position = (count - 1) * (q / 100)
        lower = floor(position)
        upper = ceil(position)
        if lower == upper:
            return sorted_values[int(position)]
        fraction = position - lower
        return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction

    return MonteCarloPercentiles(
        p5=percentile(5),
        p25=percentile(25),
        p50=percentile(50),
        p75=percentile(75),
        p95=percentile(95),
    )


@router.post("/run", response_model=MonteCarloResponse)
async def run_monte_carlo(request: MonteCarloRequest) -> MonteCarloResponse:
    """Run Monte Carlo risk simulations based on the provided assumptions."""

    if np is not None:
        rng = np.random.default_rng()
        wins = rng.random((request.runs, request.trades_per_run)) < request.win_rate
        trade_pl = np.where(wins, request.avg_win, -request.avg_loss)
        trade_pl -= request.fee_per_trade
        if request.slippage_pct:
            trade_pl -= np.abs(trade_pl) * (request.slippage_pct / 100.0)
        equity = request.starting_capital + np.cumsum(trade_pl, axis=1)
        starting = np.full((request.runs, 1), request.starting_capital)
        equity_path = np.concatenate([starting, equity], axis=1)
        peaks = np.maximum.accumulate(equity_path, axis=1)
        drawdowns = (peaks - equity_path) / peaks
        max_drawdowns = np.max(drawdowns, axis=1) * 100.0
        final_equity = equity[:, -1]
        final_returns = (final_equity / request.starting_capital - 1.0) * 100.0
        ruin_threshold = request.starting_capital * 0.5
        ruin_events = np.any(equity_path < ruin_threshold, axis=1)
        max_dd_events = max_drawdowns > 30.0
        ruin_probability = float(np.mean(ruin_events))
        max_dd_probability = float(np.mean(max_dd_events))
        final_returns_list = final_returns.tolist()
        max_drawdowns_list = max_drawdowns.tolist()
    else:
        final_returns_list = []
        max_drawdowns_list = []
        ruin_events = 0
        max_dd_events = 0
        ruin_threshold = request.starting_capital * 0.5
        for _ in range(request.runs):
            equity = request.starting_capital
            peak = equity
            max_drawdown = 0.0
            ruined = False
            for _ in range(request.trades_per_run):
                win = random.random() < request.win_rate
                trade_pl = request.avg_win if win else -request.avg_loss
                trade_pl -= request.fee_per_trade
                if request.slippage_pct:
                    trade_pl -= abs(trade_pl) * (request.slippage_pct / 100.0)
                equity += trade_pl
                if equity > peak:
                    peak = equity
                drawdown = (peak - equity) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                if equity < ruin_threshold:
                    ruined = True
            final_returns_list.append((equity / request.starting_capital - 1.0) * 100.0)
            max_drawdowns_list.append(max_drawdown * 100.0)
            if ruined:
                ruin_events += 1
            if max_drawdown * 100.0 > 30.0:
                max_dd_events += 1
        ruin_probability = ruin_events / request.runs
        max_dd_probability = max_dd_events / request.runs

    response = MonteCarloResponse(
        final_return_pct=_percentiles(final_returns_list),
        max_drawdown_pct=_percentiles(max_drawdowns_list),
        probability_ruin=ruin_probability,
        probability_max_drawdown_over_30=max_dd_probability,
    )

    if request.include_series:
        response.series = MonteCarloSeries(
            final_returns=final_returns_list,
            max_drawdowns=max_drawdowns_list,
        )

    return response


__all__ = ["run_monte_carlo"]
