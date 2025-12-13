"""Configuration helpers for the ingest service."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestSettings(BaseSettings):
    """Settings for the standalone ingest worker."""

    database_url: str | None = Field(None, description="SQLAlchemy database URL for PostgreSQL")
    price_provider: str = Field("alpha_vantage", description="alpha_vantage|ibkr")
    alphavantage_api_key: str = Field(..., description="Alpha Vantage API key")
    alphavantage_requests_per_minute: int = Field(5, description="Throttle for Alpha Vantage requests")
    base_currency: str = Field("USD", description="Fallback currency for price records")
    ibkr_host: str = Field("127.0.0.1", description="IBKR gateway/TWS host")
    ibkr_port: int = Field(4001, description="IBKR live gateway port (paper=4003)")
    ibkr_client_id: int = Field(1, description="Stable client ID per app")
    ibkr_market_data_type: int = Field(3, description="1=real-time,3=delayed")
    ibkr_use_rth: bool = Field(True, description="Use regular trading hours")
    ibkr_duration_days: int = Field(365, description="Historical lookback days")
    ibkr_bar_size: str = Field("1 day", description="IB bar size setting")
    ibkr_what_to_show: str = Field("TRADES", description="TRADES/ADJUSTED_LAST/etc")
    ibkr_service_url: str = Field("http://ibkr:8110", description="IBKR microservice base URL")
    ibkr_http_timeout_seconds: int = Field(30, description="HTTP timeout when calling IBKR microservice")

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache()
def get_settings() -> IngestSettings:
    """Return cached ingest settings."""

    return IngestSettings()


__all__ = ["IngestSettings", "get_settings"]
