from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime
from typing import Iterable, Any

from fastapi import FastAPI, HTTPException, Query
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


def _search_symbols_sync(query: str) -> list[dict[str, Any]]:
    settings = get_settings()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ib = IB()
    start = time.perf_counter()
    normalized = query.strip() or query
    try:
        log.info(
            "Connecting to IBKR host=%s port=%s clientId=%s for search",
            settings.ibkr_host,
            settings.ibkr_port,
            settings.ibkr_client_id,
        )
        ib.connect(settings.ibkr_host, settings.ibkr_port, clientId=settings.ibkr_client_id, timeout=10)
        log.info("Connected to IBKR in %.2fs for search", time.perf_counter() - start)
        matches = ib.reqMatchingSymbols(normalized)
        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for match in matches:
            contract = getattr(match, "contract", None)
            if contract is None:
                continue
            sec_type = str(getattr(contract, "secType", "") or "").upper()
            if sec_type and sec_type != "STK":
                continue
            symbol = (
                str(getattr(contract, "symbol", "") or getattr(contract, "localSymbol", "") or "").upper()
            )
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            name = (
                getattr(match, "description", None)
                or getattr(contract, "description", None)
                or getattr(contract, "localSymbol", None)
                or symbol
            )
            region = getattr(contract, "primaryExchange", None) or getattr(contract, "exchange", None)
            currency = getattr(contract, "currency", None) or settings.base_currency
            query_lower = normalized.lower()
            symbol_lower = symbol.lower()
            score: float | None = None
            if symbol_lower == query_lower:
                score = 1.0
            elif symbol_lower.startswith(query_lower):
                score = 0.9
            elif query_lower in symbol_lower:
                score = 0.75
            elif isinstance(name, str) and query_lower in name.lower():
                score = 0.5

            results.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "region": region,
                    "currency": currency,
                    "match_score": score,
                }
            )
            if len(results) >= 25:
                break
        return results
    except Exception as exc:  # noqa: BLE001
        log.error(
            "IBKR search failed after %.2fs for query %s: %s",
            time.perf_counter() - start,
            normalized,
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


async def _search_symbols_async(query: str) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_search_symbols_sync, query)


@app.post("/prices")
async def get_prices(req: PriceRequest):
    try:
        payload, currency = await _fetch_bars_async(req.symbol)
        return {"bars": payload}
    except Exception as exc:  # noqa: BLE001
        log.exception("IBKR fetch failed for %s", req.symbol)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/symbols/search")
async def search_symbols(query: str = Query(..., min_length=1, max_length=32)):
    try:
        results = await _search_symbols_async(query)
        return {"results": results}
    except Exception as exc:  # noqa: BLE001
        log.exception("IBKR symbol search failed for %s", query)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
