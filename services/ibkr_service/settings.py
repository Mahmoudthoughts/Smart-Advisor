from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ibkr_host: str = "192.168.1.193"
    ibkr_port: int = 4001
    ibkr_client_id: int = 1
    ibkr_market_data_type: int = 3
    ibkr_duration_days: int = 365
    ibkr_bar_size: str = "1 day"
    ibkr_what_to_show: str = "TRADES"
    ibkr_use_rth: bool = True
    base_currency: str = "USD"

    model_config = SettingsConfigDict(env_prefix="IBKR_", case_sensitive=False)


def get_settings() -> Settings:
    return Settings()
