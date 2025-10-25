"""Golden tests for lot math from AGENT.md §16."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.snapshots import DailySnapshot, TransactionInput, compute_daily


def build_transactions():
    return [
        TransactionInput(
            id="tx1",
            date=date(2024, 3, 1),
            type="BUY",
            quantity=Decimal("100"),
            price=Decimal("10.00"),
            fee=Decimal("5"),
        ),
        TransactionInput(
            id="tx2",
            date=date(2024, 7, 1),
            type="BUY",
            quantity=Decimal("50"),
            price=Decimal("12.00"),
            fee=Decimal("5"),
        ),
        TransactionInput(
            id="tx3",
            date=date(2024, 9, 15),
            type="SELL",
            quantity=Decimal("-50"),
            price=Decimal("15.00"),
            fee=Decimal("5"),
        ),
    ]


def build_prices():
    return {
        date(2024, 3, 1): Decimal("10.00"),
        date(2024, 7, 1): Decimal("12.00"),
        date(2024, 9, 10): Decimal("14.00"),
        date(2024, 9, 15): Decimal("15.00"),
    }


def test_compute_daily_fifo_snapshot_matches_spec():
    snapshots = compute_daily("PATH", build_transactions(), build_prices())
    snapshot_map = {snap.date: snap for snap in snapshots}
    sept_10 = snapshot_map[date(2024, 9, 10)]
    assert sept_10.shares_open == Decimal("150")
    assert sept_10.market_value_base == Decimal("2100")
    assert sept_10.cost_basis_open_base == Decimal("1610")
    assert sept_10.unrealized_pl_base == Decimal("490")
    assert sept_10.realized_pl_to_date_base == Decimal("0")
    assert sept_10.hypo_liquidation_pl_base == Decimal("485")
    assert sept_10.day_opportunity_base == Decimal("485")


def test_realized_pl_after_sell():
    snapshots = compute_daily("PATH", build_transactions(), build_prices())
    snapshot_map = {snap.date: snap for snap in snapshots}
    sell_day = snapshot_map[date(2024, 9, 15)]
    # Realized P&L should reflect 50 shares sold FIFO
    expected_cost_basis = Decimal("10.10") * Decimal("50")  # First lot cost per share 10.10
    proceeds = Decimal("50") * Decimal("15.00") - Decimal("5")
    assert sell_day.realized_pl_to_date_base == proceeds - expected_cost_basis
