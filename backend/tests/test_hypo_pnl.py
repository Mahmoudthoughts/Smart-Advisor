"""Hypothetical liquidation P&L regression tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.services.snapshots import TransactionInput, compute_daily


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
            quantity=Decimal("-150"),
            price=Decimal("16.00"),
            fee=Decimal("5"),
        ),
    ]


def build_prices():
    return {
        date(2024, 3, 1): Decimal("10.00"),
        date(2024, 7, 1): Decimal("12.00"),
        date(2024, 9, 10): Decimal("14.00"),
        date(2024, 9, 15): Decimal("16.00"),
    }


def test_day_opportunity_zero_when_no_open_position():
    snapshots = compute_daily("PATH", build_transactions(), build_prices())
    final_day = snapshots[-1]
    assert final_day.shares_open == Decimal("0")
    assert final_day.day_opportunity_base == Decimal("0")
    assert final_day.hypo_liquidation_pl_base == final_day.realized_pl_to_date_base
