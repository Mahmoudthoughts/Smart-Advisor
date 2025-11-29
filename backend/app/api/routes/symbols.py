"""Symbol-centric endpoints: search, timeline, and refresh helpers."""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.ingest.client import IngestServiceError, trigger_price_ingest
from app.models import DailyBar, DailyPortfolioSnapshot, Transaction
from app.providers.alpha_vantage import AlphaVantageError, get_alpha_vantage_client
from app.providers.ibkr_service import IBKRServiceError, search_symbols as search_ibkr_service
from app.schemas.snapshots import (
    DailyPortfolioSnapshotSchema,
    TimelinePricePointSchema,
    TimelineResponse,
    TimelineTransactionSchema,
    TopMissedDaySchema,
)
from app.schemas.symbols import SymbolRefreshResponse, SymbolSearchResultSchema
from app.services import portfolio as portfolio_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search", response_model=list[SymbolSearchResultSchema])
async def search_symbols(
    query: str = Query(..., min_length=1, max_length=32, description="Ticker or company keywords"),
    client=Depends(get_alpha_vantage_client),
) -> list[SymbolSearchResultSchema]:
    logger.info(f"Searching symbols with query: {query}")
    settings = get_settings()
    if settings.ibkr_service_url:
        try:
            results = await search_ibkr_service(query, base_url=settings.ibkr_service_url)
            logger.info("Returning %d IBKR matches for query: %s", len(results), query)
            return results
        except IBKRServiceError as exc:
            logger.error(f"IBKR search failed: {exc}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    try:
        payload = await client.symbol_search(query)
        logger.debug(f"Raw AlphaVantage response: {payload}")
        
        if not isinstance(payload, dict):
            logger.error(f"Unexpected payload type: {type(payload)}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Invalid response from data provider")
            
        matches = payload.get("bestMatches", [])
        logger.debug(f"Found {len(matches)} raw matches")
        
        results: list[SymbolSearchResultSchema] = []
        for match in matches:
            try:
                logger.debug(f"Processing match: {match}")
                score = float(match.get("9. matchScore")) if match.get("9. matchScore") is not None else None
                symbol = (match.get("1. symbol") or "").upper()
                name = match.get("2. name") or match.get("1. symbol") or ""
                region = match.get("4. region")
                currency = match.get("8. currency")
                
                # Validate all required fields are present
                if not symbol:
                    logger.warning("Skipping match with empty symbol")
                    continue
                    
                result = SymbolSearchResultSchema(
                    symbol=symbol,
                    name=name,
                    region=region,
                    currency=currency,
                    match_score=score,
                )
                logger.debug(f"Created result schema: {result.dict()}")
                results.append(result)
                
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to process match {match}: {e}")
                continue
                
        logger.info(f"Returning {len(results)} processed matches for query: {query}")
        return results
        
    except AlphaVantageError as exc:
        logger.error(f"AlphaVantage search failed: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except Exception as e:
        logger.error(f"Unexpected error in symbol search: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/{symbol}/timeline", response_model=TimelineResponse)
async def get_symbol_timeline(
    symbol: str,
    from_date: Optional[date] = Query(default=None, alias="from"),
    to_date: Optional[date] = Query(default=None, alias="to"),
    session: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    logger.info(f"Getting timeline for {symbol} from {from_date} to {to_date}")
    normalized = symbol.strip().upper()
    stmt: Select = select(DailyPortfolioSnapshot).where(DailyPortfolioSnapshot.symbol == normalized)
    if from_date:
        stmt = stmt.where(DailyPortfolioSnapshot.date >= from_date)
    if to_date:
        stmt = stmt.where(DailyPortfolioSnapshot.date <= to_date)
    stmt = stmt.order_by(DailyPortfolioSnapshot.date)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    snapshots = [
        DailyPortfolioSnapshotSchema(
            symbol=row.symbol,
            date=row.date,
            shares_open=float(row.shares_open),
            market_value_base=float(row.market_value_base),
            cost_basis_open_base=float(row.cost_basis_open_base),
            unrealized_pl_base=float(row.unrealized_pl_base),
            realized_pl_to_date_base=float(row.realized_pl_to_date_base),
            hypo_liquidation_pl_base=float(row.hypo_liquidation_pl_base),
            day_opportunity_base=float(row.day_opportunity_base),
            peak_hypo_pl_to_date_base=float(row.peak_hypo_pl_to_date_base),
            drawdown_from_peak_pct=float(row.drawdown_from_peak_pct),
        )
        for row in rows
    ]
    price_stmt: Select = select(DailyBar).where(DailyBar.symbol == normalized)
    if from_date:
        price_stmt = price_stmt.where(DailyBar.date >= from_date)
    if to_date:
        price_stmt = price_stmt.where(DailyBar.date <= to_date)
    price_stmt = price_stmt.order_by(DailyBar.date)
    price_rows = (await session.execute(price_stmt)).scalars().all()
    prices = [
        TimelinePricePointSchema(date=row.date, adj_close=float(row.adj_close))
        for row in price_rows
    ]

    settings = get_settings()
    tz = ZoneInfo(settings.timezone)
    tx_stmt: Select = select(Transaction).where(Transaction.symbol == normalized)
    if from_date:
        start_dt = datetime.combine(from_date, time.min, tzinfo=tz)
        tx_stmt = tx_stmt.where(Transaction.datetime >= start_dt)
    if to_date:
        end_dt = datetime.combine(to_date, time.max, tzinfo=tz)
        tx_stmt = tx_stmt.where(Transaction.datetime <= end_dt)
    tx_stmt = tx_stmt.order_by(Transaction.datetime)
    tx_rows = (await session.execute(tx_stmt)).scalars().all()
    transactions = [
        TimelineTransactionSchema(
            id=tx.id,
            symbol=tx.symbol,
            type=tx.type,
            quantity=float(Decimal(str(tx.qty))),
            price=float(Decimal(str(tx.price))),
            trade_datetime=tx.datetime,
            fee=float(Decimal(str(tx.fee))),
            tax=float(Decimal(str(tx.tax))),
            account_id=tx.account_id,
            account=(tx.__dict__.get("account").name if tx.__dict__.get("account") else tx.broker_id),
            notes=tx.notes,
            notional_value=float(Decimal(str(tx.qty)) * Decimal(str(tx.price))),
        )
        for tx in tx_rows
    ]
    logger.debug(f"Retrieved timeline for {symbol}: {len(snapshots)} snapshots, {len(prices)} prices, {len(transactions)} transactions")
    return TimelineResponse(symbol=normalized, snapshots=snapshots, prices=prices, transactions=transactions)


@router.post("/{symbol}/refresh", response_model=SymbolRefreshResponse)
async def refresh_symbol(
    symbol: str,
    session: AsyncSession = Depends(get_db),
    client=Depends(get_alpha_vantage_client),
) -> SymbolRefreshResponse:
    logger.info(f"Refreshing symbol: {symbol}")
    normalized = symbol.strip().upper()
    if not normalized:
        logger.error("Empty symbol provided")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol must not be empty")
    try:
        settings = get_settings()
        if not settings.ingest_base_url:
            logger.error("INGEST_BASE_URL not configured; cannot ingest %s via microservice", normalized)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Ingest service not configured (INGEST_BASE_URL missing)",
            )
        logger.info(
            "Calling ingest microservice for %s at %s (run_sync=True)",
            normalized,
            settings.ingest_base_url,
        )
        resp = await trigger_price_ingest(normalized, settings.ingest_base_url, run_sync=True)
        ingested = int(resp.get("rows", 0))
    except (AlphaVantageError, IngestServiceError) as exc:
        logger.error(f"Ingest refresh failed for {symbol}: {exc}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    response = await portfolio_client.recompute_snapshots(normalized)
    snapshots_rebuilt = response.get("snapshots_rebuilt", 0) if isinstance(response, dict) else 0
    logger.info(
        "Refreshed %s: ingested %s prices, rebuilt %s snapshots",
        symbol,
        ingested,
        snapshots_rebuilt,
    )
    return SymbolRefreshResponse(
        symbol=normalized,
        prices_ingested=ingested,
        snapshots_rebuilt=snapshots_rebuilt,
    )


@router.get("/{symbol}/top-missed", response_model=list[TopMissedDaySchema])
async def get_top_missed_days(
    symbol: str,
    limit: int = Query(default=5, ge=1, le=50),
    session: AsyncSession = Depends(get_db),
) -> list[TopMissedDaySchema]:
    logger.info(f"Getting top {limit} missed days for {symbol}")
    stmt = (
        select(DailyPortfolioSnapshot)
        .where(DailyPortfolioSnapshot.symbol == symbol)
        .order_by(DailyPortfolioSnapshot.day_opportunity_base.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    today_stmt = (
        select(DailyPortfolioSnapshot)
        .where(DailyPortfolioSnapshot.symbol == symbol)
        .order_by(DailyPortfolioSnapshot.date.desc())
        .limit(1)
    )
    today_row = (await session.execute(today_stmt)).scalars().first()
    delta_anchor = float(today_row.day_opportunity_base) if today_row else 0.0
    logger.debug(f"Retrieved {len(rows)} top missed days for {symbol}")
    return [
        TopMissedDaySchema(
            date=row.date,
            symbol=row.symbol,
            day_opportunity_base=float(row.day_opportunity_base),
            delta_vs_today_base=float(row.day_opportunity_base) - delta_anchor,
        )
        for row in rows
    ]
