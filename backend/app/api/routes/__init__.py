"""Route registration helpers."""

from __future__ import annotations

from fastapi import APIRouter

from .accounts import router as accounts_router
from .forecast import router as forecast_router
from .portfolio import router as portfolio_router
from .debug import router as debug_router
from .ingest import router as ingest_router
from .ai_timing import router as ai_timing_router
from .sentiment import router as sentiment_router
from .signals import router as signals_router
from .simulate import router as simulate_router
from .symbols import router as symbols_router
from .decisions import router as decisions_router
from .montecarlo import router as montecarlo_router

api_router = APIRouter()
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(decisions_router, prefix="/decisions", tags=["decisions"])
api_router.include_router(debug_router, prefix="/debug", tags=["debug"])
api_router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
api_router.include_router(accounts_router, prefix="/accounts", tags=["accounts"])
api_router.include_router(symbols_router, prefix="/symbols", tags=["symbols"])
api_router.include_router(signals_router, prefix="/signals", tags=["signals"])
api_router.include_router(sentiment_router, prefix="/sentiment", tags=["sentiment"])
api_router.include_router(forecast_router, prefix="/forecast", tags=["forecast"])
api_router.include_router(simulate_router, prefix="/simulate", tags=["simulate"])
api_router.include_router(montecarlo_router, prefix="/risk/montecarlo", tags=["risk"])
api_router.include_router(ai_timing_router, prefix="/ai", tags=["ai"])

__all__ = ["api_router"]
