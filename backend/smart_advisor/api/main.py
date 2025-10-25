"""Entrypoint for the Smart Advisor FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .auth import get_auth_router
from .database import Database, database
from .schemas import HealthResponse


@asynccontextmanager
async def _lifespan(app: FastAPI, db: Database):
    await db.create_all()
    yield


def create_app(db: Database | None = None) -> FastAPI:
    database_instance = db or database

    app = FastAPI(
        title="Smart Advisor API",
        version="0.1.0",
        lifespan=lambda app: _lifespan(app, database_instance),
    )

    app.include_router(get_auth_router(database_instance))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="smart-advisor",
            database_status="connected",
        )

    return app


app = create_app()

