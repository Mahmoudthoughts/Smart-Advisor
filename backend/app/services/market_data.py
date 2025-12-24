"""Market data helpers for loading OHLC series."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

import pandas as pd

from app.config import get_settings
from app.providers.alpha_vantage import AlphaVantageClient


def _parse_series(payload: dict[str, Any]) -> pd.DataFrame:
    series = payload.get("Time Series (Daily)", {})
    rows: list[dict[str, Any]] = []
    for day_str, values in series.items():
        try:
            day = datetime.strptime(day_str, "%Y-%m-%d")
        except ValueError:
            continue
        open_value = values.get("1. open")
        high_value = values.get("2. high")
        low_value = values.get("3. low")
        close_value = values.get("4. close")
        adj_close_value = values.get("5. adjusted close") or values.get("4. close")
        volume_value = values.get("6. volume") or values.get("5. volume")
        if None in (open_value, high_value, low_value, close_value, adj_close_value, volume_value):
            continue
        rows.append(
            {
                "Date": day,
                "Open": float(open_value),
                "High": float(high_value),
                "Low": float(low_value),
                "Close": float(close_value),
                "Adj Close": float(adj_close_value),
                "Volume": float(volume_value),
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("Date").sort_index()
    df.index = pd.to_datetime(df.index)
    return df


def _parse_ibkr_bars(payload: dict[str, Any]) -> pd.DataFrame:
    bars = payload.get("bars", [])
    rows: list[dict[str, Any]] = []
    for bar in bars:
        if not isinstance(bar, dict):
            continue
        raw_date = bar.get("date")
        if raw_date is None:
            continue
        try:
            day = pd.to_datetime(raw_date)
        except Exception:
            continue
        open_value = bar.get("open")
        high_value = bar.get("high")
        low_value = bar.get("low")
        close_value = bar.get("close")
        volume_value = bar.get("volume")
        if None in (open_value, high_value, low_value, close_value, volume_value):
            continue
        rows.append(
            {
                "Date": day,
                "Open": float(open_value),
                "High": float(high_value),
                "Low": float(low_value),
                "Close": float(close_value),
                "Adj Close": float(close_value),
                "Volume": float(volume_value),
            }
        )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).set_index("Date").sort_index()
    df.index = pd.to_datetime(df.index)
    return df


def _select_output_size(start: date | None) -> str:
    if not start:
        return "compact"
    days = (date.today() - start).days
    return "compact" if days <= 120 else "full"


async def _load_ibkr_ohlc(
    symbol: str,
    *,
    base_url: str,
    start: date | None = None,
    min_rows: int = 2,
) -> pd.DataFrame:
    url = base_url.rstrip("/") + "/prices"
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(url, json={"symbol": symbol})
        except httpx.HTTPError as exc:  # pragma: no cover - network failure handling
            raise ValueError(f"IBKR service error: {exc}") from exc
    if response.status_code >= 400:
        detail = response.text
        raise ValueError(f"IBKR service error {response.status_code}: {detail}")
    df = _parse_ibkr_bars(response.json())
    if start and not df.empty:
        df = df.loc[pd.Timestamp(start) :]
    if df.empty:
        raise ValueError("No data returned for symbol.")
    if len(df) < min_rows:
        raise ValueError(f"Need at least {min_rows} rows of daily OHLC data.")
    return df


async def load_ohlc(
    symbol: str,
    client: AlphaVantageClient,
    *,
    start: date | None = None,
    min_rows: int = 2,
) -> pd.DataFrame:
    settings = get_settings()
    if settings.ibkr_service_url:
        try:
            return await _load_ibkr_ohlc(
                symbol,
                base_url=settings.ibkr_service_url,
                start=start,
                min_rows=min_rows,
            )
        except ValueError:
            pass

    output_size = _select_output_size(start)
    payload = await client.daily_adjusted(symbol, output=output_size)
    df = _parse_series(payload)
    if start and not df.empty:
        df = df.loc[pd.Timestamp(start) :]
    if len(df) < min_rows and output_size == "compact":
        payload = await client.daily_adjusted(symbol, output="full")
        df = _parse_series(payload)
        if start and not df.empty:
            df = df.loc[pd.Timestamp(start) :]
    if df.empty:
        raise ValueError("No data returned for symbol.")
    if len(df) < min_rows:
        raise ValueError(f"Need at least {min_rows} rows of daily OHLC data.")
    return df


__all__ = ["load_ohlc"]
