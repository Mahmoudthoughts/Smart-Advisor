"""Gap down signal tests."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from app.indicators.gap_down import backtest_gap_down, compute_gap_down_signal


def _make_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date")


def test_compute_gap_down_signal():
    df = _make_df(
        [
            {"Date": "2024-01-02", "Open": 105, "High": 110, "Low": 100, "Close": 108},
            {"Date": "2024-01-03", "Open": 99, "High": 103, "Low": 98, "Close": 101},
        ]
    )
    signal = compute_gap_down_signal(df, "SPY")
    assert signal.symbol == "SPY"
    assert signal.date == "2024-01-03"
    assert signal.is_gap_down is True
    assert signal.is_up_close is True
    assert signal.open == 99.0
    assert signal.prev_low == 100.0
    assert signal.close == 101.0
    assert signal.gap_pct_vs_prev_low == pytest.approx(-0.01)
    assert signal.oc_return == pytest.approx((101 - 99) / 99)


def test_backtest_gap_down():
    df = _make_df(
        [
            {"Date": "2024-01-01", "Open": 110, "High": 115, "Low": 95, "Close": 112},
            {"Date": "2024-01-02", "Open": 100, "High": 104, "Low": 97, "Close": 102},
            {"Date": "2024-01-03", "Open": 94, "High": 100, "Low": 93, "Close": 96},
            {"Date": "2024-01-04", "Open": 92, "High": 97, "Low": 90, "Close": 91},
        ]
    )
    stats = backtest_gap_down(df)
    assert stats["total_signals"] == 2
    assert stats["win_signals"] == 1
    assert stats["win_rate"] == pytest.approx(0.5)
    assert stats["avg_oc_return"] == pytest.approx(((96 - 94) / 94 + (91 - 92) / 92) / 2)
    assert stats["median_oc_return"] == pytest.approx(((96 - 94) / 94 + (91 - 92) / 92) / 2)
    assert stats["worst_oc_return"] == pytest.approx((91 - 92) / 92)
    assert stats["best_oc_return"] == pytest.approx((96 - 94) / 94)
