"""Recompute daily portfolio snapshots for a symbol."""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import _session_factory
from app.models import DailyBar, Transaction
from app.services.snapshots import TransactionInput, compute_daily


async def _run(symbol: str, method: str) -> None:
    async with _session_factory() as session:  # type: AsyncSession
        tx_rows = (
            await session.execute(
                select(Transaction).where(Transaction.symbol == symbol).order_by(Transaction.datetime)
            )
        ).scalars().all()
        price_rows = (
            await session.execute(
                select(DailyBar).where(DailyBar.symbol == symbol).order_by(DailyBar.date)
            )
        ).scalars().all()
        prices = {row.date: Decimal(str(row.adj_close)) for row in price_rows}
        transactions = [
            TransactionInput(
                id=str(tx.id),
                date=tx.datetime.date(),
                type=tx.type,
                quantity=Decimal(str(tx.qty)),
                price=Decimal(str(tx.price)),
                fee=Decimal(str(tx.fee or 0)),
                tax=Decimal(str(tx.tax or 0)),
            )
            for tx in tx_rows
        ]
        snapshots = compute_daily(symbol, transactions, prices, lot_method=method)
        print(f"Computed {len(snapshots)} snapshots for {symbol} using {method}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Recompute daily snapshots for a symbol")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--method", default="FIFO", choices=["FIFO", "LIFO", "SPEC_ID"])
    args = parser.parse_args()
    asyncio.run(_run(args.symbol, args.method))


if __name__ == "__main__":
    main()
