from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime
from typing import Iterable

from fastapi import FastAPI, HTTPException
from ib_insync import BarData, IB, Stock
from pydantic import BaseModel

from .settings import get_settings

app = FastAPI()
log = logging.getLogger("ibkr_service")


class PriceRequest(BaseModel):
    symbol: str


def _to_iso_date(raw: object) -> str:
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    try:
        return datetime.fromisoformat(str(raw)).date().isoformat()
    except Exception:
        try:
            return datetime.strptime(str(raw), "%Y%m%d").date().isoformat()
        except Exception:
            return str(raw)


def _fetch_bars_sync(symbol: str) -> tuple[list[dict], str]:
    settings = get_settings()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ib = IB()
    start = time.perf_counter()
    try:
        log.info(
            "Connecting to IBKR host=%s port=%s clientId=%s",
            settings.ibkr_host,
            settings.ibkr_port,
            settings.ibkr_client_id,
        )
        ib.connect(settings.ibkr_host, settings.ibkr_port, clientId=settings.ibkr_client_id, timeout=10)
        log.info("Connected to IBKR in %.2fs", time.perf_counter() - start)
        ib.reqMarketDataType(settings.ibkr_market_data_type)
        contract = Stock(symbol, "SMART", settings.base_currency)
        ib.qualifyContracts(contract)
        bars_iter: Iterable[BarData] = ib.reqHistoricalData(
            contract,
            "",
            f"{settings.ibkr_duration_days} D",
            settings.ibkr_bar_size,
            settings.ibkr_what_to_show,
            settings.ibkr_use_rth,
            1,
            False,
        )
        currency = contract.currency or settings.base_currency
        payload = [
            {
                "symbol": symbol,
                "date": _to_iso_date(bar.date),
                "adj_close": float(bar.close),
                "volume": float(bar.volume),
                "currency": currency,
                "dividend_amount": 0.0,
                "split_coefficient": 1.0,
            }
            for bar in bars_iter
        ]
        return payload, currency
    except Exception as exc:  # noqa: BLE001
        log.error(
            "IBKR connection/fetch failed after %.2fs for %s: %s",
            time.perf_counter() - start,
            symbol,
            exc,
        )
        raise
    finally:
        try:
            ib.disconnect()
        finally:
            try:
                loop.stop()
            finally:
                loop.close()


async def _fetch_bars_async(symbol: str) -> tuple[list[dict], str]:
    return await asyncio.to_thread(_fetch_bars_sync, symbol)


@app.post("/prices")
async def get_prices(req: PriceRequest):
    try:
        payload, currency = await _fetch_bars_async(req.symbol)
        return {"bars": payload}
    except Exception as exc:  # noqa: BLE001
        log.exception("IBKR fetch failed for %s", req.symbol)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
