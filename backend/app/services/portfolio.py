"""Portfolio and transaction orchestration helpers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import (
    DailyBar,
    DailyPortfolioSnapshot,
    Portfolio,
    PortfolioSymbol,
    Transaction,
)
from app.schemas.portfolio import TransactionCreateRequest
from app.services.snapshots import TransactionInput, compute_daily


async def ensure_portfolio(session: AsyncSession) -> Portfolio:
    """Return the single demo portfolio, creating it if needed."""

    result = await session.execute(select(Portfolio).limit(1))
    portfolio = result.scalars().first()
    if portfolio is not None:
        return portfolio
    settings = get_settings()
    portfolio = Portfolio(base_currency=settings.base_currency, timezone=settings.timezone)
    session.add(portfolio)
    await session.commit()
    await session.refresh(portfolio)
    return portfolio


async def add_watchlist_symbol(symbol: str, session: AsyncSession) -> PortfolioSymbol:
    """Ensure a symbol exists on the portfolio watchlist."""

    portfolio = await ensure_portfolio(session)
    normalized = symbol.strip().upper()
    if not normalized:
        raise ValueError("Symbol must not be empty")
    result = await session.execute(
        select(PortfolioSymbol).where(
            PortfolioSymbol.portfolio_id == portfolio.id,
            PortfolioSymbol.symbol == normalized,
        )
    )
    existing = result.scalars().first()
    if existing:
        return existing
    record = PortfolioSymbol(portfolio_id=portfolio.id, symbol=normalized)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def list_watchlist(session: AsyncSession) -> list[PortfolioSymbol]:
    portfolio = await ensure_portfolio(session)
    result = await session.execute(
        select(PortfolioSymbol).where(PortfolioSymbol.portfolio_id == portfolio.id).order_by(PortfolioSymbol.symbol)
    )
    return list(result.scalars().all())


async def list_transactions(session: AsyncSession) -> list[Transaction]:
    portfolio = await ensure_portfolio(session)
    result = await session.execute(
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio.id)
        .order_by(Transaction.datetime.desc())
    )
    return list(result.scalars().all())


async def create_transaction(payload: TransactionCreateRequest, session: AsyncSession) -> Transaction:
    """Persist a manual transaction and recompute snapshots."""

    portfolio = await ensure_portfolio(session)
    await add_watchlist_symbol(payload.symbol, session)

    settings = get_settings()
    trade_dt = payload.trade_datetime
    if trade_dt.tzinfo is None:
        trade_dt = trade_dt.replace(tzinfo=ZoneInfo(settings.timezone))

    tx = Transaction(
        portfolio_id=portfolio.id,
        symbol=payload.symbol.strip().upper(),
        type=payload.type.upper(),
        qty=Decimal(str(payload.quantity)),
        price=Decimal(str(payload.price)),
        fee=Decimal(str(payload.fee)),
        tax=Decimal(str(payload.tax)),
        currency=payload.currency.upper(),
        datetime=trade_dt,
        broker_id=payload.account,
        notes=payload.notes,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    await recompute_snapshots_for_symbol(tx.symbol, session)
    return tx


async def recompute_snapshots_for_symbol(symbol: str, session: AsyncSession) -> list:
    """Rebuild daily snapshots for a symbol based on current trades and prices."""

    normalized = symbol.strip().upper()
    price_rows = (
        await session.execute(
            select(DailyBar).where(DailyBar.symbol == normalized).order_by(DailyBar.date)
        )
    ).scalars().all()
    if not price_rows:
        return []

    tx_rows = (
        await session.execute(
            select(Transaction)
            .where(Transaction.symbol == normalized)
            .order_by(Transaction.datetime)
        )
    ).scalars().all()

    price_series = {row.date: Decimal(str(row.adj_close)) for row in price_rows}
    transactions = [
        TransactionInput(
            id=str(tx.id),
            date=tx.datetime.date(),
            type=tx.type,
            quantity=Decimal(str(tx.qty)),
            price=Decimal(str(tx.price)),
            fee=Decimal(str(tx.fee)),
            tax=Decimal(str(tx.tax)),
        )
        for tx in tx_rows
    ]

    settings = get_settings()
    snapshots = compute_daily(normalized, transactions, price_series, lot_method=settings.lot_allocation_method)

    await session.execute(
        delete(DailyPortfolioSnapshot).where(DailyPortfolioSnapshot.symbol == normalized)
    )
    for snap in snapshots:
        session.add(
            DailyPortfolioSnapshot(
                symbol=snap.symbol,
                date=snap.date,
                shares_open=snap.shares_open,
                market_value_base=snap.market_value_base,
                cost_basis_open_base=snap.cost_basis_open_base,
                unrealized_pl_base=snap.unrealized_pl_base,
                realized_pl_to_date_base=snap.realized_pl_to_date_base,
                hypo_liquidation_pl_base=snap.hypo_liquidation_pl_base,
                day_opportunity_base=snap.day_opportunity_base,
                peak_hypo_pl_to_date_base=snap.peak_hypo_pl_to_date_base,
                drawdown_from_peak_pct=snap.drawdown_from_peak_pct,
            )
        )
    await session.commit()
    return snapshots


__all__ = [
    "ensure_portfolio",
    "add_watchlist_symbol",
    "list_watchlist",
    "list_transactions",
    "create_transaction",
    "recompute_snapshots_for_symbol",
]
