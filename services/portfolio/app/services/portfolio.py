"""Domain services backing the portfolio API."""

from __future__ import annotations

from decimal import Decimal
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.config import get_settings
from ..models import (
    DailyBar,
    DailyPortfolioSnapshot,
    Portfolio,
    PortfolioAccount,
    PortfolioOutbox,
    PortfolioSymbol,
    Transaction,
    TRANSACTION_TYPES,
)
from ..schemas import (
    PortfolioAccountCreateRequest,
    TransactionCreateRequest,
    TransactionUpdateRequest,
)
from .snapshots import DailySnapshot, TransactionInput, compute_daily


async def ensure_portfolio(session: AsyncSession) -> Portfolio:
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


async def add_watchlist_symbol(
    symbol: str,
    session: AsyncSession,
    *,
    display_name: str | None = None,
) -> PortfolioSymbol:
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
        if display_name and not existing.display_name:
            existing.display_name = display_name.strip()
            await session.commit()
            await session.refresh(existing)
        return existing
    record = PortfolioSymbol(
        portfolio_id=portfolio.id,
        symbol=normalized,
        display_name=display_name.strip() if display_name else None,
    )
    session.add(record)
    await session.flush()
    await enqueue_portfolio_event(
        session,
        "portfolio.watchlist.added",
        {"symbol": record.symbol, "display_name": record.display_name},
    )
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
        .options(selectinload(Transaction.account))
        .where(Transaction.portfolio_id == portfolio.id)
        .order_by(Transaction.datetime.desc())
    )
    return list(result.scalars().all())


async def _resolve_account(
    portfolio: Portfolio,
    session: AsyncSession,
    *,
    account_id: int | None,
    account_name: str | None,
) -> tuple[PortfolioAccount | None, str | None]:
    account_record: PortfolioAccount | None = None
    normalized = account_name.strip() if account_name else None
    if account_id is not None:
        account_record = await session.get(PortfolioAccount, account_id)
        if account_record is None or account_record.portfolio_id != portfolio.id:
            raise ValueError("Invalid account selected for transaction")
    elif normalized:
        existing_stmt = select(PortfolioAccount).where(
            PortfolioAccount.portfolio_id == portfolio.id,
            sa.func.lower(PortfolioAccount.name) == normalized.lower(),
        )
        account_record = (await session.execute(existing_stmt)).scalars().first()

    if account_record is None:
        default_stmt = select(PortfolioAccount).where(
            PortfolioAccount.portfolio_id == portfolio.id,
            PortfolioAccount.is_default.is_(True),
        )
        account_record = (await session.execute(default_stmt)).scalars().first()

    resolved_name = account_record.name if account_record else normalized
    return account_record, resolved_name


async def create_transaction(payload: TransactionCreateRequest, session: AsyncSession) -> Transaction:
    portfolio = await ensure_portfolio(session)
    await add_watchlist_symbol(payload.symbol, session)

    settings = get_settings()
    trade_dt = payload.trade_datetime
    if trade_dt.tzinfo is None:
        trade_dt = trade_dt.replace(tzinfo=ZoneInfo(settings.timezone))

    tx_type = payload.type.upper()
    if tx_type not in TRANSACTION_TYPES:
        raise ValueError("Unsupported transaction type")

    account_record, account_name = await _resolve_account(
        portfolio,
        session,
        account_id=payload.account_id,
        account_name=payload.account,
    )

    tx = Transaction(
        portfolio_id=portfolio.id,
        symbol=payload.symbol.strip().upper(),
        type=tx_type,
        qty=Decimal(str(payload.quantity)),
        price=Decimal(str(payload.price)),
        fee=Decimal(str(payload.fee)),
        tax=Decimal(str(payload.tax)),
        currency=payload.currency.upper(),
        datetime=trade_dt,
        broker_id=account_name,
        account_id=account_record.id if account_record else None,
        notes=payload.notes,
    )
    session.add(tx)
    await session.commit()
    await session.refresh(tx)
    await recompute_snapshots_for_symbol(tx.symbol, session)
    await enqueue_portfolio_event(
        session,
        "portfolio.transaction.created",
        {"transaction_id": tx.id, "symbol": tx.symbol, "type": tx.type},
    )
    await session.commit()
    return tx


async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdateRequest,
    session: AsyncSession,
) -> Transaction:
    portfolio = await ensure_portfolio(session)
    tx = await session.get(Transaction, transaction_id)
    if tx is None or tx.portfolio_id != portfolio.id:
        raise ValueError("Transaction not found for this portfolio")

    previous_symbol = tx.symbol
    await add_watchlist_symbol(payload.symbol, session)

    settings = get_settings()
    trade_dt = payload.trade_datetime
    if trade_dt.tzinfo is None:
        trade_dt = trade_dt.replace(tzinfo=ZoneInfo(settings.timezone))

    tx_type = payload.type.upper()
    if tx_type not in TRANSACTION_TYPES:
        raise ValueError("Unsupported transaction type")

    account_record, account_name = await _resolve_account(
        portfolio,
        session,
        account_id=payload.account_id,
        account_name=payload.account,
    )

    tx.symbol = payload.symbol.strip().upper()
    tx.type = tx_type
    tx.qty = Decimal(str(payload.quantity))
    tx.price = Decimal(str(payload.price))
    tx.fee = Decimal(str(payload.fee))
    tx.tax = Decimal(str(payload.tax))
    tx.currency = payload.currency.upper()
    tx.datetime = trade_dt
    tx.broker_id = account_name
    tx.account_id = account_record.id if account_record else None
    tx.notes = payload.notes

    await session.commit()
    await session.refresh(tx)

    if previous_symbol != tx.symbol:
        await recompute_snapshots_for_symbol(previous_symbol, session)
    await recompute_snapshots_for_symbol(tx.symbol, session)
    await enqueue_portfolio_event(
        session,
        "portfolio.transaction.updated",
        {"transaction_id": tx.id, "symbol": tx.symbol, "type": tx.type},
    )
    await session.commit()
    return tx


async def list_accounts(session: AsyncSession) -> list[PortfolioAccount]:
    portfolio = await ensure_portfolio(session)
    result = await session.execute(
        select(PortfolioAccount)
        .where(PortfolioAccount.portfolio_id == portfolio.id)
        .order_by(PortfolioAccount.is_default.desc(), PortfolioAccount.name)
    )
    return list(result.scalars().all())


async def create_account(
    payload: PortfolioAccountCreateRequest,
    session: AsyncSession,
) -> PortfolioAccount:
    portfolio = await ensure_portfolio(session)
    name = payload.name.strip()
    if not name:
        raise ValueError("Account name must not be empty")

    exists_stmt = select(PortfolioAccount).where(
        PortfolioAccount.portfolio_id == portfolio.id,
        sa.func.lower(PortfolioAccount.name) == name.lower(),
    )
    existing = (await session.execute(exists_stmt)).scalars().first()
    if existing:
        raise ValueError("An account with this name already exists")

    if payload.is_default:
        await session.execute(
            sa.update(PortfolioAccount)
            .where(PortfolioAccount.portfolio_id == portfolio.id)
            .values(is_default=False)
        )

    record = PortfolioAccount(
        portfolio_id=portfolio.id,
        name=name,
        type=payload.type.strip() if payload.type else None,
        currency=payload.currency.upper(),
        notes=payload.notes.strip() if payload.notes else None,
        is_default=payload.is_default,
    )
    session.add(record)
    await session.flush()
    await enqueue_portfolio_event(
        session,
        "portfolio.account.created",
        {"account_id": record.id, "name": record.name},
    )
    await session.commit()
    await session.refresh(record)
    return record


async def recompute_snapshots_for_symbol(
    symbol: str, session: AsyncSession
) -> list[DailySnapshot]:
    portfolio = await ensure_portfolio(session)
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
            .where(
                Transaction.symbol == normalized,
                Transaction.portfolio_id == portfolio.id,
            )
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
    snapshots = compute_daily(
        normalized,
        transactions,
        price_series,
        lot_method=settings.lot_allocation_method,
        estimated_sell_fee_bps=Decimal(str(settings.estimated_sell_fee_bps)),
        estimated_sell_fee_flat=Decimal(str(settings.estimated_sell_fee_flat)),
    )

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
    await enqueue_portfolio_event(
        session,
        "portfolio.snapshots.recomputed",
        {"symbol": normalized, "snapshots": len(snapshots)},
    )
    await session.commit()
    return snapshots


async def enqueue_portfolio_event(session: AsyncSession, event_type: str, payload: dict) -> None:
    event = PortfolioOutbox(event_type=event_type, payload=payload, status="pending")
    session.add(event)
    await session.flush()


__all__ = [
    "ensure_portfolio",
    "add_watchlist_symbol",
    "list_watchlist",
    "list_transactions",
    "create_transaction",
    "update_transaction",
    "list_accounts",
    "create_account",
    "recompute_snapshots_for_symbol",
    "enqueue_portfolio_event",
]
