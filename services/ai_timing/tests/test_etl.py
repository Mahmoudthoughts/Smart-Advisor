from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from services.ai_timing import etl


@pytest.fixture()
def sample_bars() -> pd.DataFrame:
    data_path = Path(__file__).parent / "data" / "tsla_intraday.json"
    with data_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return pd.DataFrame(payload)


def test_normalize_to_sessions(sample_bars: pd.DataFrame) -> None:
    sessions_df, per_bar_df = etl.normalize_to_sessions(sample_bars, tz="US/Eastern")

    assert len(sessions_df) == 2
    assert set(per_bar_df["session_date"].unique()) == {pd.to_datetime("2025-01-02").date(), pd.to_datetime("2025-01-03").date()}

    first_session = sessions_df.iloc[0]
    assert first_session["open"] == pytest.approx(240.0)
    assert first_session["midday_low"] == pytest.approx(237.5)
    assert first_session["close"] == pytest.approx(238.5)
    assert first_session["drawdown_pct"] == pytest.approx(-0.010416, rel=1e-3)
    assert first_session["recovery_pct"] == pytest.approx(0.00421, rel=1e-3)

    minute_marks = per_bar_df["minute_of_day"].tolist()
    assert minute_marks[:3] == [570, 575, 580]


def test_write_parquet(tmp_path: Path, sample_bars: pd.DataFrame) -> None:
    _, per_bar_df = etl.normalize_to_sessions(sample_bars, tz="US/Eastern")
    target = tmp_path / "bars-202501.parquet"
    etl.write_parquet(per_bar_df, target)

    assert target.exists()
    reloaded = pd.read_parquet(target)
    assert len(reloaded) == len(per_bar_df)
    assert "session_id" in reloaded.columns
