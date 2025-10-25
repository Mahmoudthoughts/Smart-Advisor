"""Entrypoint for the Smart Advisor FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .auth import get_auth_router
from .database import Database, database
from .schemas import HealthResponse
from typing import List
import os
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def _lifespan(app: FastAPI, db: Database):
    await db.create_all()
    yield

def _get_allowed_origins() -> List[str]:
    """
    Read allowed origins from env (comma-separated), falling back to localhost:4200 for dev.
    Example:
      BACKEND_CORS_ORIGINS=http://localhost:4200,https://api.smart-advisor.local
    """
    env_val = os.getenv("BACKEND_CORS_ORIGINS")
    if not env_val:
        return ["http://localhost:4200"]
    return [o.strip() for o in env_val.split(",") if o.strip()]


def create_app(db: Database | None = None) -> FastAPI:
    database_instance = db or database

    app = FastAPI(
        title="Smart Advisor API",
        version="0.1.0",
        lifespan=lambda app: _lifespan(app, database_instance),
    )
    # ✅ CORS goes here (in the factory, before routers)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(get_auth_router(database_instance))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="smart-advisor", database_url=database_instance.url)

    return app


app = create_app()

