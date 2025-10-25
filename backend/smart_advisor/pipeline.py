"""Pipeline functions for building daily portfolio snapshots."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date
from typing import Deque, Dict, Iterable, List, Sequence

from .fx import FXRateProvider
from .models import DailySnapshot, PriceBar, Transaction


@dataclass
class _Lot:
    """Internal representation of an open lot."""

    quantity: float
    cost_per_share_base: float

    @property
    def cost_total(self) -> float:
        return self.quantity * self.cost_per_share_base


def _group_by_symbol(items: Iterable) -> Dict[str, List]:
    grouped: Dict[str, List] = {}
    for item in items:
        symbol = item.symbol
        grouped.setdefault(symbol, []).append(item)
    return grouped


def _get_price(price_map: Dict[date, PriceBar], d: date) -> PriceBar:
    if d not in price_map:
        raise KeyError(f"Missing price for {d}")
    return price_map[d]


def build_daily_snapshots(
    transactions: Sequence[Transaction],
    prices: Sequence[PriceBar],
    fx_provider: FXRateProvider | None = None,
    *,
    base_currency: str = "USD",
    estimated_sell_fee_bps: float = 0.0,
    estimated_sell_fee_flat: float = 0.0,
) -> List[DailySnapshot]:
    """Compute per-day analytics for each symbol in the provided data."""

    tx_by_symbol = _group_by_symbol(transactions)
    price_by_symbol = _group_by_symbol(prices)

    snapshots: List[DailySnapshot] = []

    for symbol, symbol_prices in price_by_symbol.items():
        price_map = {bar.date: bar for bar in symbol_prices}
        lots: Deque[_Lot] = deque()
        realized_pl = 0.0
        peak_hypo = float("-inf")

        symbol_transactions = sorted(
            tx_by_symbol.get(symbol, []), key=lambda tx: tx.date
        )
        tx_index = 0
        timeline_dates = sorted(
            set(price_map.keys())
            | {tx.date for tx in symbol_transactions}
        )
        if not timeline_dates:
            continue

        shares_open = 0.0
        cost_basis_open = 0.0
        for current_date in timeline_dates:
            # Process any transactions for the current day
            while tx_index < len(symbol_transactions) and symbol_transactions[
                tx_index
            ].date == current_date:
                tx = symbol_transactions[tx_index]
                tx_index += 1
                t_type = tx.normalized_type()
                qty = abs(tx.quantity)
                rate = 1.0
                if fx_provider:
                    rate = fx_provider.rate(tx.date, tx.currency, base_currency)
                total_fee_tax = (tx.fee + tx.tax) * rate
                if t_type == "BUY":
                    total_cost_base = (qty * tx.price) * rate + total_fee_tax
                    cost_per_share = total_cost_base / qty if qty else 0.0
                    lots.append(_Lot(quantity=qty, cost_per_share_base=cost_per_share))
                    shares_open += qty
                    cost_basis_open += total_cost_base
                elif t_type == "SELL":
                    proceeds_base = (qty * tx.price) * rate - total_fee_tax
                    qty_to_close = qty
                    cost_removed = 0.0
                    while qty_to_close > 0 and lots:
                        lot = lots[0]
                        close_qty = min(qty_to_close, lot.quantity)
                        cost_piece = close_qty * lot.cost_per_share_base
                        lot.quantity -= close_qty
                        cost_removed += cost_piece
                        qty_to_close -= close_qty
                        if lot.quantity == 0:
                            lots.popleft()
                    shares_open -= qty
                    cost_basis_open -= cost_removed
                    realized_pl += proceeds_base - cost_removed
                else:
                    # Non-trade events can be handled later; ignore for now
                    pass

            bar = _get_price(price_map, current_date)
            rate = 1.0
            if fx_provider:
                rate = fx_provider.rate(bar.date, bar.currency, base_currency)
            price_base = bar.adj_close * rate

            shares_open = max(shares_open, 0.0)
            cost_basis_open = max(cost_basis_open, 0.0)

            market_value = shares_open * price_base
            unrealized_pl = market_value - cost_basis_open
            if shares_open == 0:
                hypo_proceeds = 0.0
            else:
                hypo_proceeds = market_value * (1 - estimated_sell_fee_bps / 10000)
                hypo_proceeds = max(hypo_proceeds - estimated_sell_fee_flat, 0.0)
            hypo_pl = realized_pl + (hypo_proceeds - cost_basis_open)
            day_opportunity = max(0.0, hypo_pl - realized_pl)
            if peak_hypo == float("-inf"):
                peak_hypo = hypo_pl
            else:
                peak_hypo = max(peak_hypo, hypo_pl)
            if peak_hypo == 0:
                drawdown = 0.0
            else:
                drawdown = (hypo_pl - peak_hypo) / peak_hypo

            snapshots.append(
                DailySnapshot(
                    date=current_date,
                    symbol=symbol,
                    shares_open=shares_open,
                    market_value_base=market_value,
                    cost_basis_open_base=cost_basis_open,
                    unrealized_pl_base=unrealized_pl,
                    realized_pl_to_date_base=realized_pl,
                    hypo_liquidation_pl_base=hypo_pl,
                    day_opportunity_base=day_opportunity,
                    peak_hypo_pl_to_date_base=peak_hypo,
                    drawdown_from_peak_pct=drawdown,
                    fx_rate=rate,
                    price_base=price_base,
                    lot_count=len(lots),
                )
            )

    snapshots.sort(key=lambda s: (s.symbol, s.date))
    return snapshots
