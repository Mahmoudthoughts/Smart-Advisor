"""Settings for the standalone portfolio service."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class PortfolioSettings(BaseSettings):
    """Runtime configuration for the portfolio microservice."""

    app_name: str = Field(default="Smart Advisor Portfolio Service")
    api_prefix: str = Field(default="/portfolio")

    timezone: str = Field(default="Asia/Dubai")
    base_currency: str = Field(default="USD")
    lot_allocation_method: str = Field(default="FIFO")

    database_url: str = Field(
        default="postgresql+asyncpg://smart_advisor:smart_advisor@localhost:5432/smart_advisor",
        description="Database URL for async SQLAlchemy sessions.",
    )

    ingest_service_url: str = Field(
        default="http://localhost:8100",
        description="Base URL for the ingest service used to fetch price history.",
    )

    internal_auth_token: str | None = Field(
        default=None,
        description="Optional shared secret used to authenticate internal callers.",
    )

    estimated_sell_fee_bps: float = Field(
        default=0.0,
        description="Estimated basis points charged when liquidating a position.",
    )
    estimated_sell_fee_flat: float = Field(
        default=5.0,
        description="Estimated flat fee charged when liquidating a position.",
    )

    telemetry_enabled: bool = Field(default=False)
    telemetry_service_name: str = Field(default="portfolio-service")
    telemetry_otlp_endpoint: str | None = Field(default=None)
    telemetry_otlp_insecure: bool = Field(default=True)
    telemetry_sample_ratio: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def dict_for_logging(self) -> dict[str, Any]:
        """Return a sanitised representation safe for structured logging."""

        hidden = {"internal_auth_token"}
        return {k: ("***" if k in hidden and v else v) for k, v in self.model_dump().items()}


@lru_cache(maxsize=1)
def get_settings(**overrides: Any) -> PortfolioSettings:
    """Return cached settings, optionally overriding values for tests."""

    if overrides:
        return PortfolioSettings(**overrides)
    return PortfolioSettings()


__all__ = ["PortfolioSettings", "get_settings"]
