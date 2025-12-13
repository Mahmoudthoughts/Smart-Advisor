from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ibkr_host: str = Field(default="192.168.100.178", validation_alias=AliasChoices("IBKR_HOST"))
    ibkr_port: int = Field(default=4001, validation_alias=AliasChoices("IBKR_PORT"))
    ibkr_client_id: int = Field(default=1, validation_alias=AliasChoices("IBKR_CLIENT_ID"))
    ibkr_market_data_type: int = Field(default=3, validation_alias=AliasChoices("IBKR_MARKET_DATA_TYPE"))
    ibkr_duration_days: int = Field(default=365, validation_alias=AliasChoices("IBKR_DURATION_DAYS"))
    ibkr_bar_size: str = Field(default="1 day", validation_alias=AliasChoices("IBKR_BAR_SIZE"))
    ibkr_what_to_show: str = Field(default="TRADES", validation_alias=AliasChoices("IBKR_WHAT_TO_SHOW"))
    ibkr_use_rth: bool = Field(default=True, validation_alias=AliasChoices("IBKR_USE_RTH"))
    base_currency: str = Field(
        default="USD",
        validation_alias=AliasChoices("IBKR_BASE_CURRENCY", "BASE_CURRENCY"),
    )
    ibkr_timeout_seconds: int = Field(default=20, validation_alias=AliasChoices("IBKR_TIMEOUT_SECONDS"))
    ibkr_max_retries: int = Field(default=1, validation_alias=AliasChoices("IBKR_MAX_RETRIES"))

    # Read environment variables as IBKR_HOST, IBKR_PORT, etc. directly
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
