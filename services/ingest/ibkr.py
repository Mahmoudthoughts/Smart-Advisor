from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Iterable

from ib_insync import BarData, IB, Stock
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailyBar
from .config import get_settings

log = logging.getLogger("services.ingest.ibkr")


async def _get_ib() -> IB:
    """Create a fresh IB client on the current asyncio loop."""
    settings = get_settings()
    ib = IB()
    await ib.connectAsync(
        settings.ibkr_host,
        settings.ibkr_port,
        clientId=settings.ibkr_client_id,
        timeout=5,
    )
    ib.reqMarketDataType(settings.ibkr_market_data_type)
    return ib


def _to_date(raw) -> datetime.date:  # type: ignore[override]
    if hasattr(raw, "date"):
        return raw.date()
    return datetime.strptime(str(raw), "%Y%m%d").date()


async def ingest_prices_ibkr(symbol: str, session: AsyncSession) -> int:
    settings = get_settings()
    ib = await _get_ib()
    try:
        contract = Stock(symbol, "SMART", settings.base_currency)
        qualified = await ib.qualifyContractsAsync(contract)
        contract = qualified[0] if qualified else contract
        bars: Iterable[BarData] = await ib.reqHistoricalDataAsync(
            contract,
            "",
            f"{settings.ibkr_duration_days} D",
            settings.ibkr_bar_size,
            settings.ibkr_what_to_show,
            settings.ibkr_use_rth,
            1,
            False,
        )
        total = 0
        currency = contract.currency or settings.base_currency
        for bar in bars:
            day = _to_date(bar.date)
            record = {
                "symbol": symbol,
                "date": day,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "adj_close": float(bar.close),
                "volume": float(bar.volume),
                "currency": currency,
                "dividend_amount": 0.0,
                "split_coefficient": 1.0,
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
        log.info("IBKR ingest for %s completed (%d rows)", symbol, total)
        return total
    finally:
        ib.disconnect()


async def close_ib_client() -> None:
    # No-op with per-call clients
    return None
