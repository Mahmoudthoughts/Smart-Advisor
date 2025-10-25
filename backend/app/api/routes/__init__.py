"""Route registration helpers."""

from __future__ import annotations

from fastapi import APIRouter

from .forecast import router as forecast_router
from .sentiment import router as sentiment_router
from .signals import router as signals_router
from .simulate import router as simulate_router
from .symbols import router as symbols_router

api_router = APIRouter()
api_router.include_router(symbols_router, prefix="/symbols", tags=["symbols"])
api_router.include_router(signals_router, prefix="/signals", tags=["signals"])
api_router.include_router(sentiment_router, prefix="/sentiment", tags=["sentiment"])
api_router.include_router(forecast_router, prefix="/forecast", tags=["forecast"])
api_router.include_router(simulate_router, prefix="/simulate", tags=["simulate"])

__all__ = ["api_router"]
