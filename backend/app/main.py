"""FastAPI application entrypoint."""

from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.baggage import get_baggage

from app.api.routes import api_router
from app.config import get_settings
from app.core.logging import setup_logging
from app.core.telemetry import setup_telemetry
from app.db.init import init_database
from app.db.session import _engine
from smart_advisor.api.admin import get_admin_router
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
    expose_headers=[
        # Expose tracing/debug headers for end-to-end propagation debugging
        "traceparent",
        "tracestate",
        "baggage",
        "x-trace-id",
        "x-request-id",
    ],
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
    app.include_router(get_admin_router(legacy_database))
    return app


configure_app()


# Attach end-user attributes from W3C Baggage to the active server span
@app.middleware("http")
async def _attach_user_baggage(request, call_next):  # type: ignore[no-redef]
    span = trace.get_current_span()
    try:
        for key in ("enduser.id", "enduser.role", "enduser.email"):
            val = get_baggage(key)
            if val:
                span.set_attribute(key, val)
    except Exception:  # best-effort only
        pass
    response = await call_next(request)
    return response

__all__ = ["app", "configure_app"]
