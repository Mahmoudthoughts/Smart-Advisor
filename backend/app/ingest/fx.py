"""FX rate ingest job."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FXRate
from app.providers.alpha_vantage import AlphaVantageClient, get_alpha_vantage_client


async def ingest_fx_pair(
    from_ccy: str,
    to_ccy: str,
    session: AsyncSession,
    client: AlphaVantageClient | None = None,
) -> int:
    """Fetch FX_DAILY data and persist normalized FXRate rows."""

    client = client or get_alpha_vantage_client()
    payload = await client.fx_daily(from_ccy, to_ccy)
    series = payload.get("Time Series FX (Daily)", {})
    total = 0
    for day_str, values in series.items():
        day = datetime.strptime(day_str, "%Y-%m-%d").date()
        record = {
            "date": day,
            "from_ccy": from_ccy,
            "to_ccy": to_ccy,
            "rate_close": float(values["4. close"]),
        }
        stmt = (
            insert(FXRate)
            .values(**record)
            .on_conflict_do_update(
                index_elements=[FXRate.date, FXRate.from_ccy, FXRate.to_ccy],
                set_={"rate_close": record["rate_close"]},
            )
        )
        await session.execute(stmt)
        total += 1
    await session.commit()
    return total


__all__ = ["ingest_fx_pair"]
