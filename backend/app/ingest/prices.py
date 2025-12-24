"""Price ingest job for Alpha Vantage daily price series.

This module provides a local implementation so the backend container does not
depend on the external `services.ingest` package at import time.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyBar
from app.providers.alpha_vantage import AlphaVantageClient, get_alpha_vantage_client
from app.config import get_settings


async def ingest_prices(
    symbol: str,
    session: AsyncSession,
    client: AlphaVantageClient | None = None,
) -> int:
    """Fetch and persist Alpha Vantage TIME_SERIES_DAILY data.

    Mirrors the standalone ingest service logic but runs within the backend.
    """

    client = client or get_alpha_vantage_client()
    payload = await client.daily_adjusted(symbol)
    series = payload.get("Time Series (Daily)", {})
    total = 0

    settings = get_settings()
    # Alpha Vantage daily payload does not reliably include currency; default to base.
    currency = settings.base_currency

    for day_str, values in series.items():
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        open_value = values.get("1. open")
        high_value = values.get("2. high")
        low_value = values.get("3. low")
        close_value = values.get("4. close")
        adj_close_value = values.get("5. adjusted close") or values.get("4. close")
        volume_value = values.get("6. volume") or values.get("5. volume")
        if adj_close_value is None or volume_value is None:
            continue

        record = {
            "symbol": symbol,
            "date": day,
            "open": float(open_value) if open_value is not None else float(adj_close_value),
            "high": float(high_value) if high_value is not None else float(adj_close_value),
            "low": float(low_value) if low_value is not None else float(adj_close_value),
            "close": float(close_value) if close_value is not None else float(adj_close_value),
            "adj_close": float(adj_close_value),
            "volume": float(volume_value),
            "currency": currency,
            "dividend_amount": float(values.get("7. dividend amount", values.get("6. dividend amount", 0.0))),
            "split_coefficient": float(values.get("8. split coefficient", values.get("7. split coefficient", 1.0))),
        }

        stmt = (
            insert(DailyBar)
            .values(**record)
            .on_conflict_do_update(
                index_elements=[DailyBar.symbol, DailyBar.date],
                set_={
                    "open": record["open"],
                    "high": record["high"],
                    "low": record["low"],
                    "close": record["close"],
                    "adj_close": record["adj_close"],
                    "volume": record["volume"],
                    "currency": record["currency"],
                    "dividend_amount": record["dividend_amount"],
                    "split_coefficient": record["split_coefficient"],
                },
            )
        )
        await session.execute(stmt)
        total += 1

    await session.commit()
    return total


__all__ = ["ingest_prices"]
