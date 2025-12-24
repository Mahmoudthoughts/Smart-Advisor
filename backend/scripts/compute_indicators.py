"""Compute indicator cache for a symbol using stored prices."""

from __future__ import annotations

import argparse

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import _session_factory
from app.indicators.compute import compute_indicators
from app.models import DailyBar


async def _run(symbol: str) -> None:
    async with _session_factory() as session:  # type: AsyncSession
        result = await session.execute(
            select(DailyBar).where(DailyBar.symbol == symbol).order_by(DailyBar.date)
        )
        rows = result.scalars().all()
        if not rows:
            print(f"No price history for {symbol}")
            return
        df = pd.DataFrame(
            {
                "open": [float(r.open) if r.open is not None else float(r.adj_close) for r in rows],
                "high": [float(r.high) if r.high is not None else float(r.adj_close) for r in rows],
                "low": [float(r.low) if r.low is not None else float(r.adj_close) for r in rows],
                "close": [float(r.close) if r.close is not None else float(r.adj_close) for r in rows],
                "adj_close": [float(r.adj_close) for r in rows],
                "volume": [float(r.volume) for r in rows],
            },
            index=[r.date for r in rows],
        )
        df["prev_low"] = df["low"].shift()
        compute_indicators(symbol, df)
        print(f"Cached indicators for {symbol} ({len(df)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compute indicator cache for a symbol")
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    import asyncio

    asyncio.run(_run(args.symbol))


if __name__ == "__main__":
    main()
