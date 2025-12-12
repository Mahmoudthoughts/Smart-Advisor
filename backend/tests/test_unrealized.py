from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.services.unrealized import (
    CachingPriceSource,
    CostMode,
    InMemoryPriceSource,
    LotInput,
    LotStore,
    LotType,
    NonTradingDayPolicy,
    SimulationRequest,
    compute_target_from_point,
    simulate_unrealized_series,
)


def build_store_with_single_lot() -> LotStore:
    store = LotStore()
    store.add_lot(
        LotInput(
            lot_id="lot-1",
            ticker="AAPL",
            buy_date=date(2024, 1, 2),
            shares=Decimal("10"),
            buy_price=Decimal("100"),
            type=LotType.REAL,
        )
    )
    return store


def test_single_lot_series_matches_manual_profit():
    store = build_store_with_single_lot()
    prices = InMemoryPriceSource(
        {"AAPL": {date(2024, 1, 2): {"close": "100"}, date(2024, 1, 3): {"close": "110"}, date(2024, 1, 4): {"close": "90"}}}
    )
    response = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(ticker="AAPL", start_date=date(2024, 1, 2), end_date=date(2024, 1, 4)),
    )
    assert len(response.rows) == 3
    day_3 = next(r for r in response.rows if r.date == date(2024, 1, 3))
    assert day_3.unrealized_pnl_value == Decimal("100")
    assert day_3.unrealized_pnl_pct == Decimal("0.1")
    latest = response.summary.latest_value
    assert latest == Decimal("-100")


def test_multiple_lots_fifo_aggregation():
    store = LotStore()
    store.add_lot(
        LotInput(
            lot_id="lot-1",
            ticker="AAPL",
            buy_date=date(2024, 1, 2),
            shares=Decimal("10"),
            buy_price=Decimal("100"),
        )
    )
    store.add_lot(
        LotInput(
            lot_id="lot-2",
            ticker="AAPL",
            buy_date=date(2024, 1, 5),
            shares=Decimal("5"),
            buy_price=Decimal("80"),
            type=LotType.HYPOTHETICAL,
        )
    )
    prices = InMemoryPriceSource({"AAPL": {date(2024, 1, 10): {"close": "90"}}})
    response = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(ticker="AAPL", start_date=date(2024, 1, 10), end_date=date(2024, 1, 10)),
    )
    row = response.rows[0]
    assert row.total_shares == Decimal("15")
    # (90-100)*10 + (90-80)*5 = -50
    assert row.unrealized_pnl_value == Decimal("-50")


def test_filters_by_lot_ids_and_type():
    store = LotStore()
    real_lot = store.add_lot(
        LotInput(
            lot_id="real-1",
            ticker="AAPL",
            buy_date=date(2024, 1, 2),
            shares=Decimal("10"),
            buy_price=Decimal("100"),
        )
    )
    hypo_lot = store.add_lot(
        LotInput(
            lot_id="hypo-1",
            ticker="AAPL",
            buy_date=date(2024, 1, 3),
            shares=Decimal("4"),
            buy_price=Decimal("50"),
            type=LotType.HYPOTHETICAL,
        )
    )
    prices = InMemoryPriceSource({"AAPL": {date(2024, 1, 4): {"close": "75"}}})
    # Type filter should exclude hypothetical lot
    response_real_only = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(
            ticker="AAPL",
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 4),
            type_filter=[LotType.REAL],
        ),
    )
    assert response_real_only.rows[0].total_shares == real_lot.shares
    # Lot id filter should pick only the hypothetical lot
    response_hypo = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(
            ticker="AAPL",
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 4),
            lot_ids=[hypo_lot.lot_id],
        ),
    )
    assert response_hypo.rows[0].total_shares == hypo_lot.shares


def test_fees_and_tax_are_applied_to_unrealized_pl():
    store = build_store_with_single_lot()
    prices = InMemoryPriceSource({"AAPL": {date(2024, 1, 5): {"close": "120"}}})
    response = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(
            ticker="AAPL",
            start_date=date(2024, 1, 5),
            end_date=date(2024, 1, 5),
            buy_fee=Decimal("1"),
            sell_fee=Decimal("1"),
            tax_rate=Decimal("0.1"),
            cost_mode=CostMode.AVERAGE_COST,
        ),
    )
    row = response.rows[0]
    # Base profit: (120-100)*10 = 200; minus sell_fee 1 => 199; tax 10% => 179.1
    assert row.unrealized_pnl_value == Decimal("179.1")
    assert row.cost_value == Decimal("1001")


def test_non_trading_day_policy_snap_and_skip():
    store = build_store_with_single_lot()
    prices = InMemoryPriceSource(
        {
            "AAPL": {
                date(2024, 1, 1): {"close": "100"},
                date(2024, 1, 4): {"close": "110"},
            }
        }
    )
    snap_response = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(
            ticker="AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 4),
            non_trading_day_policy=NonTradingDayPolicy.SNAP_PREV_TRADING_DAY,
        ),
    )
    assert len(snap_response.rows) == 4
    # Jan 3 uses the Jan 1 price (snap prev)
    jan3 = next(r for r in snap_response.rows if r.date == date(2024, 1, 3))
    assert jan3.sell_price == Decimal("100")

    skip_response = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(
            ticker="AAPL",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 4),
            non_trading_day_policy=NonTradingDayPolicy.SKIP_DATE,
        ),
    )
    assert len(skip_response.rows) == 2


def test_last_n_trading_days_selection():
    store = build_store_with_single_lot()
    prices = InMemoryPriceSource(
        {
            "AAPL": {
                date(2024, 1, 1): {"close": "100"},
                date(2024, 1, 2): {"close": "101"},
                date(2024, 1, 3): {"close": "102"},
                date(2024, 1, 4): {"close": "103"},
                date(2024, 1, 5): {"close": "104"},
            }
        }
    )
    response = simulate_unrealized_series(
        prices,
        store,
        SimulationRequest(ticker="AAPL", last_n_trading_days=3),
    )
    assert [row.date for row in response.rows] == [
        date(2024, 1, 3),
        date(2024, 1, 4),
        date(2024, 1, 5),
    ]


def test_compute_target_from_point_matches_formula():
    store = LotStore()
    store.add_lot(
        LotInput(
            lot_id="lot-1",
            ticker="MSFT",
            buy_date=date(2024, 2, 1),
            shares=Decimal("10"),
            buy_price=Decimal("100"),
        )
    )
    store.add_lot(
        LotInput(
            lot_id="lot-2",
            ticker="MSFT",
            buy_date=date(2024, 3, 1),
            shares=Decimal("5"),
            buy_price=Decimal("80"),
        )
    )
    result = compute_target_from_point(store, "MSFT", Decimal("300"))
    # Avg cost = 1400/15; target price should equal avg cost + profit/share
    assert result["target_price"] == Decimal("113.3333333333333333333333333")
    assert result["avg_cost"] == Decimal("93.33333333333333333333333333")
    assert result["total_shares"] == Decimal("15")


def test_price_source_caching_reuses_delegate():
    class CountingSource(InMemoryPriceSource):
        def __init__(self, prices):
            super().__init__(prices)
            self.calls = 0

        def get_price_series(self, ticker, start_date, end_date, *, price_field):
            self.calls += 1
            return super().get_price_series(ticker, start_date, end_date, price_field=price_field)

    source = CountingSource({"AAPL": {date(2024, 1, 1): {"close": "10"}}})
    cached = CachingPriceSource(source)
    first = cached.get_price_series("AAPL", None, None)
    second = cached.get_price_series("AAPL", None, None)
    assert first == second
    assert source.calls == 1


def test_invalid_future_real_lot_rejected():
    store = LotStore()
    with pytest.raises(ValueError):
        store.add_lot(
            LotInput(
                lot_id="future",
                ticker="AAPL",
                buy_date=date.today().replace(year=date.today().year + 1),
                shares=Decimal("1"),
                buy_price=Decimal("1"),
            )
        )
