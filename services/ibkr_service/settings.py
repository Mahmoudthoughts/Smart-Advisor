from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ibkr_host: str = "192.168.100.178"
    ibkr_port: int = 4001
    ibkr_client_id: int = 1
    ibkr_market_data_type: int = 3
    ibkr_duration_days: int = 365
    ibkr_bar_size: str = "1 day"
    ibkr_what_to_show: str = "TRADES"
    ibkr_use_rth: bool = True
    base_currency: str = "USD"
    ibkr_timeout_seconds: int = 20
    ibkr_max_retries: int = 1

    # Read environment variables as IBKR_HOST, IBKR_PORT, etc. directly
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False)


def get_settings() -> Settings:
    return Settings()
