"""Gap down (open < previous low) signal helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

import pandas as pd


@dataclass
class GapDownSignal:
    symbol: str
    date: str
    open: float
    prev_low: float
    close: Optional[float]
    is_gap_down: bool
    is_up_close: Optional[bool]
    gap_pct_vs_prev_low: float
    oc_return: Optional[float]


def compute_gap_down_signal(df: pd.DataFrame, symbol: str) -> GapDownSignal:
    """
    df must have columns: Open, High, Low, Close and a DatetimeIndex (daily).
    Uses the last row as 'today' and the previous row as 'yesterday'.
    """
    df = df.dropna().copy()
    if len(df) < 2:
        raise ValueError("Need at least 2 rows of daily OHLC data.")

    today = df.iloc[-1]
    yday = df.iloc[-2]

    open_ = float(today["Open"])
    prev_low = float(yday["Low"])
    close_ = float(today["Close"]) if "Close" in df.columns and pd.notna(today["Close"]) else None

    is_gap_down = open_ < prev_low
    is_up_close = (close_ > open_) if close_ is not None else None

    gap_pct = (open_ - prev_low) / prev_low
    oc_ret = ((close_ - open_) / open_) if close_ is not None else None

    return GapDownSignal(
        symbol=symbol,
        date=str(df.index[-1].date()),
        open=open_,
        prev_low=prev_low,
        close=close_,
        is_gap_down=is_gap_down,
        is_up_close=is_up_close,
        gap_pct_vs_prev_low=gap_pct,
        oc_return=oc_ret,
    )


def backtest_gap_down(df: pd.DataFrame) -> Dict[str, Any]:
    df = df.dropna().copy()
    if len(df) < 3:
        raise ValueError("Need enough history to backtest.")

    df["PrevLow"] = df["Low"].shift(1)
    df["GapDown"] = df["Open"] < df["PrevLow"]
    df["UpClose"] = df["Close"] > df["Open"]
    df["OC_Return"] = (df["Close"] - df["Open"]) / df["Open"]

    sample = df[df["GapDown"]]
    total = int(sample.shape[0])
    wins = int(sample["UpClose"].sum())

    return {
        "total_signals": total,
        "win_signals": wins,
        "win_rate": (wins / total) if total else None,
        "avg_oc_return": float(sample["OC_Return"].mean()) if total else None,
        "median_oc_return": float(sample["OC_Return"].median()) if total else None,
        "worst_oc_return": float(sample["OC_Return"].min()) if total else None,
        "best_oc_return": float(sample["OC_Return"].max()) if total else None,
    }


__all__ = ["GapDownSignal", "compute_gap_down_signal", "backtest_gap_down"]
