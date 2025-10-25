"""Configuration helpers for the Smart Advisor backend."""

from __future__ import annotations

import os
from functools import lru_cache


DEFAULT_ALPHA_VANTAGE_API_KEY = "W7NAEL9D8ERL47FW"


@lru_cache()
def get_alpha_vantage_api_key() -> str:
    """Return the Alpha Vantage API key available to the backend."""

    return os.getenv("ALPHAVANTAGE_API_KEY", DEFAULT_ALPHA_VANTAGE_API_KEY)


__all__ = ["get_alpha_vantage_api_key", "DEFAULT_ALPHA_VANTAGE_API_KEY"]

