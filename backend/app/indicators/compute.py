"""Technical indicator computation helpers with simple caching."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict

import numpy as np
import pandas as pd

from app.config import get_settings


@dataclass
class CachedIndicators:
    symbol: str
    as_of: datetime
    data: pd.DataFrame


class IndicatorCache:
    """In-memory cache for per-symbol indicator dataframes."""

    def __init__(self) -> None:
        self._store: Dict[str, CachedIndicators] = {}

    def get(self, symbol: str) -> CachedIndicators | None:
        settings = get_settings()
        cached = self._store.get(symbol)
        if not cached:
            return None
        ttl = timedelta(minutes=settings.indicator_cache_ttl_minutes)
        if datetime.utcnow() - cached.as_of > ttl:
            self._store.pop(symbol, None)
            return None
        return cached

    def set(self, symbol: str, df: pd.DataFrame) -> None:
        self._store[symbol] = CachedIndicators(symbol=symbol, as_of=datetime.utcnow(), data=df)


_cache = IndicatorCache()


def _ensure_dataframe(symbol: str, df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "close" not in df:
        if "adj_close" in df:
            df["close"] = df["adj_close"]
        else:
            raise ValueError("DataFrame must contain a close or adj_close column")
    if "volume" not in df:
        df["volume"] = np.nan
    return df


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, periods: int = 14) -> pd.Series:
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain, index=series.index).rolling(window=periods).mean()
    avg_loss = pd.Series(loss, index=series.index).rolling(window=periods).mean()
    rs = avg_gain / avg_loss
    rsi_series = 100 - (100 / (1 + rs))
    return rsi_series.fillna(0)


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    if not {"high", "low"}.issubset(df.columns):
        # Fallback using close-only data
        true_range = df["close"].diff().abs()
    else:
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift()).abs()
        lc = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return true_range.rolling(window=period, min_periods=period).mean()


def volume_multiple_20d(series: pd.Series) -> pd.Series:
    avg_volume = series.rolling(window=20, min_periods=20).mean()
    return series / avg_volume


def compute_indicators(symbol: str, df: pd.DataFrame) -> pd.DataFrame:
    """Compute indicator columns and store them in the cache."""

    df = _ensure_dataframe(symbol, df)
    df = df.sort_index()
    df["sma_20"] = sma(df["close"], 20)
    df["ema_20"] = ema(df["close"], 20)
    df["rsi_14"] = rsi(df["close"], 14)
    macd_df = macd(df["close"])
    df = df.join(macd_df)
    df["atr_14"] = atr(df)
    df["volume_multiple_20d"] = volume_multiple_20d(df["volume"])
    _cache.set(symbol, df)
    return df


def get_cached_indicators(symbol: str) -> pd.DataFrame | None:
    cached = _cache.get(symbol)
    return cached.data if cached else None


__all__ = [
    "compute_indicators",
    "get_cached_indicators",
    "sma",
    "ema",
    "rsi",
    "macd",
    "atr",
    "volume_multiple_20d",
]
