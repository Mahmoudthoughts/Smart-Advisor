"""Price ingest job for Alpha Vantage or IBKR daily price series.

This implementation performs incremental upserts:
- On first run (no existing rows), it fetches the full series.
- On subsequent runs, it fetches the compact series and only upserts a small
  backfill window plus new days to capture restatements/dividends/splits.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyBar

from .alpha_vantage import AlphaVantageClient, get_alpha_vantage_client
from .config import get_settings
from .ibkr import ingest_prices_ibkr


async def ingest_prices(symbol: str, session: AsyncSession, client: AlphaVantageClient | None = None) -> int:
    """Fetch and persist daily data using the configured price provider."""

    settings = get_settings()
    if settings.price_provider == "ibkr":
        return await ingest_prices_ibkr(symbol, session)

    client = client or get_alpha_vantage_client()
    # Determine last ingested date for incremental fetch
    latest_stmt: Select = select(func.max(DailyBar.date)).where(DailyBar.symbol == symbol)
    latest_date = (await session.execute(latest_stmt)).scalar()

    # Use compact for incremental updates, full for initial load or long gaps
    output_size = "compact" if latest_date else "full"
    if latest_date:
        try:
            from datetime import date as _date

            if (_date.today() - latest_date).days > 90:
                output_size = "full"
        except Exception:
            # Fallback to compact on any unexpected date issues
            output_size = output_size
    payload = await client.daily_adjusted(symbol, output=output_size)
    series = payload.get("Time Series (Daily)", {})
    total = 0
    metadata = payload.get("Meta Data", {})
    currency_hint = metadata.get("7. Time Zone") or metadata.get("6. Time Zone") or metadata.get("5. Time Zone")
    currency = (
        currency_hint
        if isinstance(currency_hint, str) and len(currency_hint) == 3 and currency_hint.isalpha()
        else settings.base_currency
    )

    # Backfill to capture restatements/splits around the last known date
    backfill_days = 5
    cutoff_date = (latest_date - timedelta(days=backfill_days)) if latest_date else None

    for day_str, values in series.items():
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        if cutoff_date and day < cutoff_date:
            # Skip historical rows beyond the backfill window
            continue
        adj_close_value = values.get("5. adjusted close") or values.get("4. close")
        volume_value = values.get("6. volume") or values.get("5. volume")
        if adj_close_value is None or volume_value is None:
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
