"""Nightly ETL for AI timing intraday sessions."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date, datetime, time, timezone
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_PATH = BASE_DIR / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))
SERVICE_PATH = BASE_DIR / "services" / "ai_timing"
if str(SERVICE_PATH) not in sys.path:
    sys.path.append(str(SERVICE_PATH))

from backend.app.config import get_settings as get_backend_settings
from backend.app.models import IntradayBar, SessionSummary
from services.ai_timing.config import get_settings as get_timing_settings
from services.ai_timing.main import minutes_since_midnight

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    settings = get_backend_settings()
    return create_async_engine(settings.database_url, echo=False, future=True)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_intraday_bars(
    symbol: str,
    start: date,
    end: date,
    use_rth: bool = True,
    engine: AsyncEngine | None = None,
) -> pd.DataFrame:
    """Load intraday bars for the requested range into a DataFrame."""

    async def _fetch(target_engine: AsyncEngine) -> pd.DataFrame:
        start_dt = _as_utc(datetime.combine(start, time.min))
        end_dt = _as_utc(datetime.combine(end, time.max))
        async with target_engine.connect() as conn:
            stmt = (
                select(
                    IntradayBar.symbol,
                    IntradayBar.bar_size,
                    IntradayBar.use_rth,
                    IntradayBar.timestamp,
                    IntradayBar.open,
                    IntradayBar.high,
                    IntradayBar.low,
                    IntradayBar.close,
                    IntradayBar.volume,
                    IntradayBar.currency,
                )
                .where(
                    IntradayBar.symbol == symbol,
                    IntradayBar.use_rth == use_rth,
                    IntradayBar.timestamp >= start_dt,
                    IntradayBar.timestamp <= end_dt,
                )
                .order_by(IntradayBar.timestamp)
            )
            result = await conn.execute(stmt)
            rows = result.fetchall()
            payload = [
                {
                    "symbol": row.symbol,
                    "bar_size": row.bar_size,
                    "use_rth": row.use_rth,
                    "timestamp": row.timestamp,
                    "open": float(row.open),
                    "high": float(row.high),
                    "low": float(row.low),
                    "close": float(row.close),
                    "volume": float(row.volume),
                    "currency": row.currency,
                }
                for row in rows
            ]
            return pd.DataFrame(payload)

    target_engine = engine or get_engine()
    return asyncio.run(_fetch(target_engine))


def _session_rows_from_group(symbol: str, session_id: str, group: pd.DataFrame) -> dict:
    open_price = float(group.iloc[0]["open"])
    midday_low = float(group["low"].min())
    close_price = float(group.iloc[-1]["close"])
    drawdown_pct = (midday_low - open_price) / open_price if open_price else 0.0
    recovery_pct = (close_price - midday_low) / midday_low if midday_low else 0.0
    return {
        "session_id": session_id,
        "symbol": symbol.upper(),
        "date": group.iloc[0]["session_date"],
        "open": open_price,
        "midday_low": midday_low,
        "close": close_price,
        "drawdown_pct": drawdown_pct,
        "recovery_pct": recovery_pct,
        "bars": int(len(group)),
    }


def normalize_to_sessions(df_bars: pd.DataFrame, tz: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize raw bars to session-level and per-bar DataFrames."""

    if df_bars.empty:
        return pd.DataFrame(), pd.DataFrame()

    tzinfo = ZoneInfo(tz)
    df = df_bars.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(tzinfo)
    df["session_date"] = df["timestamp"].dt.date
    df.sort_values("timestamp", inplace=True)
    df["minute_of_day"] = df["timestamp"].apply(minutes_since_midnight)
    df["session_id"] = df["symbol"].str.upper() + "-" + df["session_date"].astype(str)

    session_rows: list[dict] = []
    for session_id, group in df.groupby("session_id"):
        session_rows.append(_session_rows_from_group(group.iloc[0]["symbol"], session_id, group))

    sessions_df = pd.DataFrame(session_rows).sort_values(["symbol", "date"])
    per_bar_df = df.copy()
    return sessions_df, per_bar_df


def _session_upsert_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


def write_session_summary(summary_row: dict, engine: AsyncEngine | None = None) -> None:
    """Persist or update a session summary row."""

    async def _upsert(target_engine: AsyncEngine) -> None:
        session_maker = _session_upsert_factory(target_engine)
        async with session_maker() as session:
            existing = await session.scalar(
                select(SessionSummary).where(
                    SessionSummary.symbol == summary_row["symbol"],
                    SessionSummary.date == summary_row["date"],
                )
            )
            if existing:
                existing.open = summary_row["open"]
                existing.midday_low = summary_row["midday_low"]
                existing.close = summary_row["close"]
                existing.drawdown_pct = summary_row["drawdown_pct"]
                existing.recovery_pct = summary_row["recovery_pct"]
                existing.bars = summary_row["bars"]
            else:
                session.add(SessionSummary(**summary_row))
            await session.commit()

    target_engine = engine or get_engine()
    asyncio.run(_upsert(target_engine))


def write_parquet(per_bar_df: pd.DataFrame, path: Path | str) -> None:
    """Write per-bar features to Parquet."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    per_bar_df.to_parquet(output_path, index=False)
    logger.info("Wrote %s rows to %s", len(per_bar_df), output_path)


def _month_key(value: date) -> str:
    return value.strftime("%Y%m")


def run_etl(
    symbols: Iterable[str],
    start: date,
    end: date,
    use_rth: bool = True,
    tz_name: str | None = None,
) -> None:
    tz = tz_name or get_timing_settings().timezone_default
    engine = get_engine()

    for symbol in symbols:
        logger.info("Processing %s from %s to %s", symbol, start, end)
        bars_df = fetch_intraday_bars(symbol, start, end, use_rth=use_rth, engine=engine)
        if bars_df.empty:
            logger.warning("No bars found for %s", symbol)
            continue

        sessions_df, per_bar_df = normalize_to_sessions(bars_df, tz)
        for _, row in sessions_df.iterrows():
            payload = {**row.to_dict()}
            payload.pop("session_id", None)
            write_session_summary(payload, engine=engine)

        per_bar_df["year_month"] = per_bar_df["session_date"].apply(_month_key)
        for month_key, month_df in per_bar_df.groupby("year_month"):
            parquet_path = Path("data/training") / symbol.upper() / f"bars-{month_key}.parquet"
            write_parquet(month_df, parquet_path)

    asyncio.run(engine.dispose())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI timing nightly ETL")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols to process")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--use-rth",
        dest="use_rth",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Restrict to regular trading hours (default: true)",
    )
    parser.add_argument("--timezone", default=None, help="Target timezone (defaults to AI timing config)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    run_etl(
        symbols=symbols,
        start=date.fromisoformat(args.start),
        end=date.fromisoformat(args.end),
        use_rth=args.use_rth,
        tz_name=args.timezone,
    )


if __name__ == "__main__":
    main()
