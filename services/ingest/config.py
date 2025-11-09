"""Configuration helpers for the ingest service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestSettings(BaseSettings):
    """Settings for the standalone ingest worker."""

    database_url: str | None = Field(None, description="SQLAlchemy database URL for PostgreSQL")
    alphavantage_api_key: str = Field(..., description="Alpha Vantage API key")
    alphavantage_requests_per_minute: int = Field(5, description="Throttle for Alpha Vantage requests")
    base_currency: str = Field("USD", description="Fallback currency for price records")

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> IngestSettings:
    """Return cached ingest settings."""

    return IngestSettings()


__all__ = ["IngestSettings", "get_settings"]
