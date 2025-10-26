"""FastAPI application entrypoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import get_settings
from app.core.logging import setup_logging

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
setup_logging()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
