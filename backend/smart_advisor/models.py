"""Domain models used by the Smart Advisor analytics pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class Transaction:
    """A normalized trade or cash flow event."""

    date: date
    symbol: str
    type: str
    quantity: float
    price: float
    fee: float = 0.0
    tax: float = 0.0
    currency: str = "USD"

    def normalized_type(self) -> str:
        """Return the upper-cased transaction type for consistent comparisons."""

        return self.type.upper()


@dataclass(frozen=True)
class PriceBar:
    """Daily market data used to price the portfolio."""

    date: date
    symbol: str
    adj_close: float
    currency: str = "USD"


@dataclass(frozen=True)
class DailySnapshot:
    """Per-day portfolio analytics for a single symbol."""

    date: date
    symbol: str
    shares_open: float
    market_value_base: float
    cost_basis_open_base: float
    unrealized_pl_base: float
    realized_pl_to_date_base: float
    hypo_liquidation_pl_base: float
    day_opportunity_base: float
    peak_hypo_pl_to_date_base: float
    drawdown_from_peak_pct: float
    fx_rate: float
    price_base: float
    lot_count: int
    notes: Optional[str] = None
