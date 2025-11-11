"""Entry point for the portfolio microservice."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.baggage import get_baggage
from opentelemetry.propagate import extract
from opentelemetry import context as otel_context

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


# Attach end-user attributes from W3C Baggage and ensure incoming trace context is active
@app.middleware("http")
async def _attach_user_baggage_and_context(request, call_next):  # type: ignore[no-redef]
    token = None
    try:
        # Extract upstream context so spans in this request join the caller's trace
        extracted = extract(request.headers)  # type: ignore[arg-type]
        token = otel_context.attach(extracted)
    except Exception:
        token = None
    # Best-effort to annotate the active span with end-user attributes
    span = trace.get_current_span()
    try:
        for key in ("enduser.id", "enduser.role", "enduser.email"):
            val = get_baggage(key)
            if val:
                span.set_attribute(key, val)
    except Exception:
        pass
    try:
        response = await call_next(request)
    finally:
        if token is not None:
            try:
                otel_context.detach(token)
            except Exception:
                pass
    return response


app.include_router(portfolio_router, prefix=settings.api_prefix, tags=["portfolio"])


__all__ = ["app"]
