"""FastAPI application entrypoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.config import get_settings
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.db.init import init_database
from app.db.session import _engine
from smart_advisor.api.auth import get_auth_router
from smart_advisor.api.database import database as legacy_database

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
setup_logging()
setup_telemetry(app, settings, engine=_engine)

# Configure CORS
# Allow common local development origins (localhost and 127.0.0.1) on port 4200,
# plus same-origin without port to support different setups.
allowed_origins = [
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost",
    "http://127.0.0.1",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    """Initialise the database schema when the service boots."""

    await init_database()
    await legacy_database.create_all()


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
    app.include_router(get_auth_router(legacy_database))
    return app


configure_app()

__all__ = ["app", "configure_app"]
