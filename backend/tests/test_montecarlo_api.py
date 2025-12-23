"""Monte Carlo API tests."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.routes.montecarlo import router as montecarlo_router


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(montecarlo_router, prefix="/risk/montecarlo", tags=["risk"])
    return app


async def test_montecarlo_run_percentile_bounds():
    request_payload = {
        "starting_capital": 10_000,
        "runs": 250,
        "trades_per_run": 20,
        "win_rate": 1.0,
        "avg_win": 25.0,
        "avg_loss": 0.0,
        "fee_per_trade": 0.0,
        "slippage_pct": 0.0,
        "include_series": False,
    }

    transport = ASGITransport(app=_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/risk/montecarlo/run", json=request_payload)

    assert response.status_code == 200
    payload = response.json()

    final_returns = payload["final_return_pct"]
    max_drawdowns = payload["max_drawdown_pct"]

    for percentile in ("p5", "p25", "p50", "p75", "p95"):
        assert final_returns[percentile] >= 0
        assert 0 <= max_drawdowns[percentile] <= 100
