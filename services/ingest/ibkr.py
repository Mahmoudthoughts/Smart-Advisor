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
_ib: IB | None = None
_lock = asyncio.Lock()


async def _get_ib() -> IB:
    global _ib
    if _ib and _ib.isConnected():
        return _ib
    async with _lock:
        if _ib and _ib.isConnected():
            return _ib
        settings = get_settings()
        _ib = IB()
        await asyncio.to_thread(
            _ib.connect,
            settings.ibkr_host,
            settings.ibkr_port,
            clientId=settings.ibkr_client_id,
            timeout=5,
        )
        await asyncio.to_thread(_ib.reqMarketDataType, settings.ibkr_market_data_type)
        return _ib


def _to_date(raw) -> datetime.date:  # type: ignore[override]
    if hasattr(raw, "date"):
        return raw.date()
    return datetime.strptime(str(raw), "%Y%m%d").date()


async def ingest_prices_ibkr(symbol: str, session: AsyncSession) -> int:
    settings = get_settings()
    ib = await _get_ib()
    contract = Stock(symbol, "SMART", settings.base_currency)
    await asyncio.to_thread(ib.qualifyContracts, contract)
    bars: Iterable[BarData] = await asyncio.to_thread(
        ib.reqHistoricalData,
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


async def close_ib_client() -> None:
    global _ib
    if _ib:
        await asyncio.to_thread(_ib.disconnect)
        _ib = None
