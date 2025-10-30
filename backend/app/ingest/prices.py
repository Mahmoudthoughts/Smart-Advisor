"""Price ingest job for Alpha Vantage daily price series."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import DailyBar
from app.providers.alpha_vantage import AlphaVantageClient, get_alpha_vantage_client


async def ingest_prices(symbol: str, session: AsyncSession, client: AlphaVantageClient | None = None) -> int:
    """Fetch and persist Alpha Vantage TIME_SERIES_DAILY data."""

    client = client or get_alpha_vantage_client()
    payload = await client.daily_adjusted(symbol)
    series = payload.get("Time Series (Daily)", {})
    total = 0
    settings = get_settings()
    metadata = payload.get("Meta Data", {})
    currency_hint = metadata.get("7. Time Zone") or metadata.get("6. Time Zone") or metadata.get("5. Time Zone")
    currency = (
        currency_hint
        if isinstance(currency_hint, str) and len(currency_hint) == 3 and currency_hint.isalpha()
        else settings.base_currency
    )

    for day_str, values in series.items():
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        adj_close_value = values.get("5. adjusted close") or values.get("4. close")
        volume_value = values.get("6. volume") or values.get("5. volume")
        if adj_close_value is None or volume_value is None:
            # Skip malformed entries instead of raising to allow partial ingest.
            continue
        record = {
            "symbol": symbol,
            "date": day,
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
