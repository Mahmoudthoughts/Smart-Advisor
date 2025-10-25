"""CLI wrapper for price ingest."""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import _session_factory
from app.ingest.prices import ingest_prices


async def _run(symbol: str) -> None:
    async with _session_factory() as session:  # type: AsyncSession
        count = await ingest_prices(symbol, session)
        print(f"Upserted {count} price rows for {symbol}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest TIME_SERIES_DAILY_ADJUSTED data")
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()
    asyncio.run(_run(args.symbol))


if __name__ == "__main__":
    main()
