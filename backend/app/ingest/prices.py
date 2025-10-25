"""Price ingest job for Alpha Vantage daily adjusted series."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import DailyBar
from app.providers.alpha_vantage import AlphaVantageClient, get_alpha_vantage_client


async def ingest_prices(symbol: str, session: AsyncSession, client: AlphaVantageClient | None = None) -> int:
    """Fetch and persist TIME_SERIES_DAILY_ADJUSTED data."""

    client = client or get_alpha_vantage_client()
    payload = await client.daily_adjusted(symbol)
    series = payload.get("Time Series (Daily)", {})
    total = 0
    settings = get_settings()
    for day_str, values in series.items():
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        record = {
            "symbol": symbol,
            "date": day,
            "adj_close": float(values["5. adjusted close"]),
            "volume": float(values["6. volume"]),
            "currency": payload.get("Meta Data", {}).get("7. Time Zone", settings.base_currency),
            "dividend_amount": float(values.get("7. dividend amount", 0.0)),
            "split_coefficient": float(values.get("8. split coefficient", 1.0)),
        }
        stmt = (
            insert(DailyBar)
            .values(**record)
            .on_conflict_do_update(
                index_elements=[DailyBar.symbol, DailyBar.date],
                set_={
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
