"""Portfolio snapshot computation services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, getcontext
from typing import Iterable, List, Sequence

getcontext().prec = 28


@dataclass
class TransactionInput:
    """Normalized transaction input for lot building."""

    id: str
    date: date
    type: str
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")
    specific_lot_ids: Sequence[str] | None = None


@dataclass
class LotPosition:
    lot_id: str
    quantity: Decimal
    cost_per_share: Decimal


@dataclass
class DailySnapshot:
    symbol: str
    date: date
    shares_open: Decimal
    market_value_base: Decimal
    cost_basis_open_base: Decimal
    unrealized_pl_base: Decimal
    realized_pl_to_date_base: Decimal
    hypo_liquidation_pl_base: Decimal
    day_opportunity_base: Decimal
    peak_hypo_pl_to_date_base: Decimal
    drawdown_from_peak_pct: Decimal


def _pop_lot(lots: list[LotPosition], method: str) -> LotPosition:
    if method == "FIFO":
        return lots.pop(0)
    if method == "LIFO":
        return lots.pop()
    return lots.pop(0)


def compute_daily(
    symbol: str,
    transactions: Iterable[TransactionInput],
    price_series: dict[date, Decimal],
    *,
    lot_method: str = "FIFO",
) -> List[DailySnapshot]:
    """Compute daily portfolio snapshots according to §3–§4."""

    lots: list[LotPosition] = []
    realized_pl = Decimal("0")
    snapshots: list[DailySnapshot] = []
    transactions_by_date: dict[date, list[TransactionInput]] = {}
    for tx in sorted(transactions, key=lambda t: (t.date, t.id)):
        transactions_by_date.setdefault(tx.date, []).append(tx)
    peak_hypo = Decimal("-Infinity")

    for day in sorted(price_series.keys()):
        day_price = price_series[day]
        for tx in transactions_by_date.get(day, []):
            if tx.type == "BUY":
                cost = tx.quantity * tx.price + tx.fee + tx.tax
                lot = LotPosition(lot_id=tx.id, quantity=tx.quantity, cost_per_share=cost / tx.quantity)
                lots.append(lot)
            elif tx.type == "SELL":
                qty_to_close = -tx.quantity if tx.quantity < 0 else tx.quantity
                qty_to_close = abs(qty_to_close)
                remaining = qty_to_close
                proceeds = qty_to_close * tx.price - tx.fee - tx.tax
                lot_cost_total = Decimal("0")
                while remaining > 0 and lots:
                    lot = _pop_lot(lots, lot_method)
                    take_qty = min(lot.quantity, remaining)
                    lot_cost_total += take_qty * lot.cost_per_share
                    lot.quantity -= take_qty
                    remaining -= take_qty
                    if lot.quantity > 0:
                        if lot_method == "FIFO":
                            lots.insert(0, lot)
                        else:
                            lots.append(lot)
                realized_pl += proceeds - lot_cost_total
            # TODO: handle DIVIDEND/FEE/SPLIT events as needed
        shares_open = sum(lot.quantity for lot in lots)
        cost_basis_open = sum(lot.quantity * lot.cost_per_share for lot in lots)
        market_value = shares_open * day_price
        unrealized = market_value - cost_basis_open
        hypo_liquidation = realized_pl + (market_value - cost_basis_open)
        if shares_open == 0:
            hypo_liquidation = realized_pl
            day_opp = Decimal("0")
        else:
            day_opp = max(Decimal("0"), hypo_liquidation - realized_pl)
        if peak_hypo == Decimal("-Infinity"):
            peak_hypo = hypo_liquidation
        peak_hypo = max(peak_hypo, hypo_liquidation)
        drawdown = Decimal("0")
        if peak_hypo != 0:
            drawdown = (hypo_liquidation - peak_hypo) / peak_hypo * Decimal("100")
        snapshots.append(
            DailySnapshot(
                symbol=symbol,
                date=day,
                shares_open=shares_open,
                market_value_base=market_value,
                cost_basis_open_base=cost_basis_open,
                unrealized_pl_base=unrealized,
                realized_pl_to_date_base=realized_pl,
                hypo_liquidation_pl_base=hypo_liquidation,
                day_opportunity_base=day_opp,
                peak_hypo_pl_to_date_base=peak_hypo,
                drawdown_from_peak_pct=drawdown,
            )
        )
    return snapshots


__all__ = [
    "TransactionInput",
    "DailySnapshot",
    "compute_daily",
]
