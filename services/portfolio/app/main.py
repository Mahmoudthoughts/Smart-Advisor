"""Entry point for the portfolio microservice."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from .api.routes.portfolio import router as portfolio_router
from .core.config import get_settings
from .core.telemetry import setup_telemetry
from .db.session import get_engine

logger = logging.getLogger("services.portfolio")
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.on_event("startup")
async def startup_event() -> None:
    engine = get_engine()
    setup_telemetry(app, settings, engine)
    logger.info("Portfolio service configuration", extra=settings.dict_for_logging())


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(portfolio_router, prefix=settings.api_prefix, tags=["portfolio"])


__all__ = ["app"]
