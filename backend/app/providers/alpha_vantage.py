"""Alpha Vantage API client wrapper."""

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
        requests_per_minute: int | None = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.alphavantage_api_key
        self.requests_per_minute = requests_per_minute or settings.alphavantage_requests_per_minute
        self._client = client or httpx.AsyncClient()
        self._calls: Deque[float] = deque(maxlen=max(self.requests_per_minute, 1))
        self._lock = asyncio.Lock()

    async def _throttle(self) -> None:
        """Ensure requests do not exceed the configured rate limit."""

        async with self._lock:
            if self.requests_per_minute <= 0:
                return
            interval = 60.0 / self.requests_per_minute
            loop = asyncio.get_running_loop()
            now = loop.time()
            if self._calls and len(self._calls) == self._calls.maxlen:
                elapsed = now - self._calls[0]
                if elapsed < interval:
                    await asyncio.sleep(interval - elapsed)
                    now = loop.time()
                    self._calls.popleft()
            self._calls.append(now)

    async def _get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a GET request with API key injection and error handling."""

        query = dict(params)
        query["apikey"] = self.api_key
        await self._throttle()
        response = await self._client.get(BASE_URL, params=query, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        if any(key in data for key in ("Note", "Information")):
            message = data.get("Note") or data.get("Information")
            raise AlphaVantageError(message or "Alpha Vantage rate limited the request")
        return data

    async def daily_adjusted(self, symbol: str, *, output: str = "full") -> Dict[str, Any]:
        return await self._get({"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": output})

    async def fx_daily(self, from_ccy: str, to_ccy: str) -> Dict[str, Any]:
        return await self._get({"function": "FX_DAILY", "from_symbol": from_ccy, "to_symbol": to_ccy})

    async def tech_indicator(self, function: str, symbol: str, *, interval: str = "daily", **kwargs: Any) -> Dict[str, Any]:
        params = {"function": function, "symbol": symbol, "interval": interval}
        params.update(kwargs)
        return await self._get(params)

    async def news_sentiment(self, tickers: str, *, limit: int = 50, sort: str = "LATEST") -> Dict[str, Any]:
        return await self._get(
            {
                "function": "NEWS_SENTIMENT",
                "tickers": tickers,
                "limit": limit,
                "sort": sort,
            }
        )

    async def symbol_search(self, keywords: str) -> Dict[str, Any]:
        return await self._get({"function": "SYMBOL_SEARCH", "keywords": keywords})

    async def econ_indicator(self, function: str, **kwargs: Any) -> Dict[str, Any]:
        params = {"function": function}
        params.update(kwargs)
        return await self._get(params)

    async def aclose(self) -> None:
        await self._client.aclose()


_client: AlphaVantageClient | None = None


def get_alpha_vantage_client() -> AlphaVantageClient:
    """Return a process-wide Alpha Vantage client."""

    global _client
    if _client is None:
        _client = AlphaVantageClient()
    return _client


__all__ = [
    "AlphaVantageClient",
    "AlphaVantageError",
    "BASE_URL",
    "get_alpha_vantage_client",
]
