"""Configuration for the AI timing microservice."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str | None = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", env="OPENAI_MODEL")
    cache_ttl_seconds: int = Field(default=900, env="AI_TIMING_CACHE_TTL_SEC")
    timezone_default: str = Field(default="US/Eastern", env="AI_TIMING_DEFAULT_TZ")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["Settings", "get_settings"]
