"""Application configuration and environment helpers."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings

DEFAULT_TIMEZONE = "Asia/Dubai"
DEFAULT_BASE_CURRENCY = "USD"


class AppSettings(BaseSettings):
    """Configuration options for the Smart Advisor service."""

    app_name: str = Field(default="Missed Opportunity Analyzer + Smart Advisor")
    timezone: str = Field(default=DEFAULT_TIMEZONE)
    base_currency: str = Field(default=DEFAULT_BASE_CURRENCY)

    database_url: str = Field(
        default="postgresql+asyncpg://smart_advisor:smart_advisor@localhost:5432/smart_advisor",
        description="SQLAlchemy database URL.",
    )
    alembic_ini_path: str = Field(default="app/migrations/alembic.ini")

    alphavantage_api_key: str = Field(default="W7NAEL9D8ERL47FW", env="ALPHAVANTAGE_API_KEY")
    alphavantage_requests_per_minute: int = Field(default=5)

    indicator_cache_ttl_minutes: int = Field(default=60)

    lot_allocation_method: Literal["FIFO", "LIFO", "SPEC_ID"] = Field(default="FIFO")
    lot_specific_map: dict[str, str] = Field(default_factory=dict)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def dict_for_logging(self) -> dict[str, Any]:
        """Return a sanitized dict for logging purposes."""

        hidden = {"alphavantage_api_key"}
        return {k: ("***" if k in hidden else v) for k, v in self.model_dump().items()}


@lru_cache(maxsize=1)
def get_settings(**overrides: Any) -> AppSettings:
    """Return cached application settings with optional overrides."""

    if overrides:
        return AppSettings(**overrides)
    return AppSettings()


__all__ = [
    "AppSettings",
    "DEFAULT_TIMEZONE",
    "DEFAULT_BASE_CURRENCY",
    "get_settings",
]
