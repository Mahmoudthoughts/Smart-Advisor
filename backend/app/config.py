"""Settings and configuration for the application."""

from __future__ import annotations

from pydantic import BaseSettings


class Settings(BaseSettings):
    # ...existing settings...
    cors_origins: list[str] = ["http://localhost:4200"]

    class Config:
        env_file = ".env"