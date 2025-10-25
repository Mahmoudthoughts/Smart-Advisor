from datetime import date

import pytest

from smart_advisor import PriceBar, Transaction, build_daily_snapshots
from smart_advisor.fx import FXRateProvider


def _make_transactions():
    return [
        Transaction(
            date=date(2024, 3, 1),
            symbol="PATH",
            type="BUY",
            quantity=100,
            price=10.0,
            fee=5,
            tax=0,
            currency="USD",
        ),
        Transaction(
            date=date(2024, 7, 1),
            symbol="PATH",
            type="BUY",
            quantity=50,
            price=12.0,
            fee=5,
            tax=0,
            currency="USD",
        ),
        Transaction(
            date=date(2024, 9, 15),
            symbol="PATH",
            type="SELL",
            quantity=-50,
            price=15.0,
            fee=5,
            tax=0,
            currency="USD",
        ),
    ]


def _make_prices():
    return [
        PriceBar(date=date(2024, 3, 1), symbol="PATH", adj_close=10.0),
        PriceBar(date=date(2024, 7, 1), symbol="PATH", adj_close=12.0),
        PriceBar(date=date(2024, 9, 10), symbol="PATH", adj_close=14.0),
        PriceBar(date=date(2024, 9, 15), symbol="PATH", adj_close=15.0),
    ]


def test_example_day_matches_spec():
    snapshots = build_daily_snapshots(
        transactions=_make_transactions(),
        prices=_make_prices(),
        estimated_sell_fee_flat=5.0,
    )
    target = [s for s in snapshots if s.date == date(2024, 9, 10)][0]
    assert target.shares_open == pytest.approx(150)
    assert target.cost_basis_open_base == pytest.approx(1610)
    assert target.realized_pl_to_date_base == pytest.approx(0)
    assert target.hypo_liquidation_pl_base == pytest.approx(485)
    assert target.day_opportunity_base == pytest.approx(485)


def test_realized_pl_after_sale_fifo():
    snapshots = build_daily_snapshots(
        transactions=_make_transactions(),
        prices=_make_prices(),
        estimated_sell_fee_flat=5.0,
    )
    last = snapshots[-1]
    # Sell 50 shares from first lot @ 15 minus fee 5
    expected_realized = (50 * 15 - 5) - (50 * (1000 + 5) / 100)
    assert last.realized_pl_to_date_base == pytest.approx(expected_realized)
    assert last.shares_open == pytest.approx(100)


def test_fx_conversion_is_applied():
    transactions = [
        Transaction(
            date=date(2024, 3, 1),
            symbol="SHOP",
            type="BUY",
            quantity=10,
            price=90.0,
            fee=0,
            currency="CAD",
        ),
    ]
    prices = [
        PriceBar(date=date(2024, 3, 1), symbol="SHOP", adj_close=90.0, currency="CAD"),
    ]
    fx = FXRateProvider({(date(2024, 3, 1), "CAD", "USD"): 0.75})
    snapshots = build_daily_snapshots(transactions, prices, fx_provider=fx)
    snap = snapshots[0]
    assert snap.cost_basis_open_base == pytest.approx(10 * 90 * 0.75)
    assert snap.price_base == pytest.approx(90 * 0.75)
