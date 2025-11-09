"""Alpha Vantage client used by the backend service."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any, Deque, Dict, Optional

import httpx

from app.config import get_settings

BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageError(RuntimeError):
    """Raised when Alpha Vantage returns an error payload."""


class AlphaVantageClient:
    """Throttled Alpha Vantage client with convenience helpers."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
