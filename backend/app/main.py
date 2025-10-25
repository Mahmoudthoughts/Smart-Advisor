"""FastAPI application entrypoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI

from app.api.routes import api_router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Return service readiness metadata."""

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "timezone": settings.timezone,
    }


def configure_app() -> FastAPI:
    """Attach routes and dependencies."""

    app.include_router(api_router)
    return app


configure_app()

__all__ = ["app", "configure_app"]
