"""Monte Carlo risk analysis endpoints."""

from __future__ import annotations

import random
from math import ceil, floor

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import DailyBar
from app.schemas import MonteCarloPercentiles, MonteCarloRequest, MonteCarloResponse, MonteCarloSeries

try:  # pragma: no cover - optional dependency
    import numpy as np
except ImportError:  # pragma: no cover
    np = None

router = APIRouter()
MIN_HISTORY_DAYS = 30



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


def _run_simulation(
    request: MonteCarloRequest,
    *,
    runs: int,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    risk_multiplier: float,
) -> tuple[list[float], list[float], float, float]:
    if np is not None:
        rng = np.random.default_rng()
        wins = rng.random((runs, request.trades_per_run)) < win_rate
        trade_pl = np.where(wins, avg_win, -avg_loss)
        if risk_multiplier != 1.0:
            trade_pl = trade_pl * risk_multiplier
        trade_pl -= request.fee_per_trade
        if request.slippage_pct:
            trade_pl -= np.abs(trade_pl) * (request.slippage_pct / 100.0)
        equity = request.starting_capital + np.cumsum(trade_pl, axis=1)
        starting = np.full((runs, 1), request.starting_capital)
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
        return (
            final_returns.tolist(),
            max_drawdowns.tolist(),
            ruin_probability,
            max_dd_probability,
        )

    final_returns_list: list[float] = []
    max_drawdowns_list: list[float] = []
    ruin_events = 0
    max_dd_events = 0
    ruin_threshold = request.starting_capital * 0.5
    for _ in range(runs):
        equity = request.starting_capital
        peak = equity
        max_drawdown = 0.0
        ruined = False
        for _ in range(request.trades_per_run):
            win = random.random() < win_rate
            trade_pl = avg_win if win else -avg_loss
            trade_pl *= risk_multiplier
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
    ruin_probability = ruin_events / runs
    max_dd_probability = max_dd_events / runs
    return final_returns_list, max_drawdowns_list, ruin_probability, max_dd_probability


def _score_candidate(
    final_returns: list[float],
    max_drawdowns: list[float],
    ruin_probability: float,
) -> dict[str, float]:
    final_return_pct = _percentiles(final_returns)
    max_drawdown_pct = _percentiles(max_drawdowns)
    p50_return = final_return_pct.p50
    p75_drawdown = max_drawdown_pct.p75
    drawdown_penalty = p75_drawdown * 0.7
    ruin_penalty = ruin_probability * 100.0
    score = p50_return - drawdown_penalty - ruin_penalty
    return {
        "p50_final_return": p50_return,
        "p75_max_drawdown": p75_drawdown,
        "ruin_probability": ruin_probability,
        "drawdown_penalty": drawdown_penalty,
        "ruin_penalty": ruin_penalty,
        "score": score,
    }


def _derive_params_from_returns(
    request: MonteCarloRequest, returns_pct: list[float]
) -> tuple[float, float, float]:
    wins = [value for value in returns_pct if value > 0]
    losses = [-value for value in returns_pct if value < 0]
    if not wins or not losses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough mixed return history to derive win/loss stats.",
        )
    win_rate = len(wins) / len(returns_pct)
    avg_win_pct = sum(wins) / len(wins)
    avg_loss_pct = sum(losses) / len(losses)
    avg_win = (avg_win_pct / 100.0) * request.starting_capital
    avg_loss = (avg_loss_pct / 100.0) * request.starting_capital
    return win_rate, avg_win, avg_loss


async def _get_symbol_returns(
    session: AsyncSession,
    symbol: str,
    lookback_days: int,
) -> list[float]:
    stmt = (
        select(DailyBar)
        .where(DailyBar.symbol == symbol)
        .order_by(DailyBar.date.desc())
        .limit(lookback_days + 1)
    )
    rows = (await session.execute(stmt)).scalars().all()
    if len(rows) < 2:
        return []
    rows_sorted = sorted(rows, key=lambda row: row.date)
    prices = [float(row.adj_close) for row in rows_sorted if row.adj_close is not None]
    returns_pct: list[float] = []
    for index in range(1, len(prices)):
        prev = prices[index - 1]
        curr = prices[index]
        if prev <= 0 or curr <= 0:
            continue
        returns_pct.append((curr / prev - 1.0) * 100.0)
    return returns_pct


def _generate_candidates(
    *,
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    risk_multiplier: float,
) -> list[dict[str, float]]:
    candidate_count = random.randint(20, 50)
    candidates = [
        {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "risk_multiplier": risk_multiplier,
        }
    ]
    for _ in range(candidate_count - 1):
        candidates.append(
            {
                "win_rate": min(max(win_rate + random.uniform(-0.03, 0.03), 0.0), 1.0),
                "avg_win": max(avg_win * (1 + random.uniform(-0.1, 0.1)), 0.0),
                "avg_loss": max(avg_loss * (1 + random.uniform(-0.1, 0.1)), 0.0),
                "risk_multiplier": max(
                    risk_multiplier * (1 + random.uniform(-0.05, 0.05)),
                    0.01,
                ),
            }
        )
    return candidates


@router.post("/run", response_model=MonteCarloResponse)
async def run_monte_carlo(
    request: MonteCarloRequest,
    session: AsyncSession = Depends(get_db),
) -> MonteCarloResponse:
    """Run Monte Carlo risk simulations based on the provided assumptions."""

    selected_params: dict[str, float] | None = None
    score_breakdown: dict[str, float] | None = None
    win_rate = request.win_rate
    avg_win = request.avg_win
    avg_loss = request.avg_loss
    risk_multiplier = request.risk_multiplier

    if request.symbol:
        normalized = request.symbol.strip().upper()
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Symbol must not be empty.",
            )
        returns_pct = await _get_symbol_returns(session, normalized, request.lookback_days)
        if len(returns_pct) < MIN_HISTORY_DAYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Not enough price history to run symbol-driven simulation.",
            )
        win_rate, avg_win, avg_loss = _derive_params_from_returns(request, returns_pct)

    if request.use_ai:
        candidate_runs = min(800, request.runs)
        best_score = float("-inf")
        for candidate in _generate_candidates(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            risk_multiplier=risk_multiplier,
        ):
            final_returns_list, max_drawdowns_list, ruin_probability, _ = _run_simulation(
                request,
                runs=candidate_runs,
                win_rate=candidate["win_rate"],
                avg_win=candidate["avg_win"],
                avg_loss=candidate["avg_loss"],
                risk_multiplier=candidate["risk_multiplier"],
            )
            breakdown = _score_candidate(final_returns_list, max_drawdowns_list, ruin_probability)
            if breakdown["score"] > best_score:
                best_score = breakdown["score"]
                selected_params = candidate
                score_breakdown = breakdown
        if selected_params is not None:
            win_rate = selected_params["win_rate"]
            avg_win = selected_params["avg_win"]
            avg_loss = selected_params["avg_loss"]
            risk_multiplier = selected_params["risk_multiplier"]

    (
        final_returns_list,
        max_drawdowns_list,
        ruin_probability,
        max_dd_probability,
    ) = _run_simulation(
        request,
        runs=request.runs,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        risk_multiplier=risk_multiplier,
    )

    response = MonteCarloResponse(
        final_return_pct=_percentiles(final_returns_list),
        max_drawdown_pct=_percentiles(max_drawdowns_list),
        probability_ruin=ruin_probability,
        probability_max_drawdown_over_30=max_dd_probability,
        ai_selected_params=selected_params,
        ai_score_breakdown=score_breakdown,
    )

    if request.include_series:
        response.series = MonteCarloSeries(
            final_returns=final_returns_list,
            max_drawdowns=max_drawdowns_list,
        )

    return response


__all__ = ["run_monte_carlo"]
