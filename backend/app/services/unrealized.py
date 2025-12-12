"""Unrealized gain/loss calculator and profit-target helpers.

This module keeps state-light helpers for adding lots, fetching prices via a
pluggable price source, and producing unrealized P/L series suitable for
tables or charting. It is intentionally self contained so it can be reused in
API handlers or background jobs without database coupling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, DivisionByZero, getcontext
from enum import Enum
from typing import Dict, Iterable, Mapping, MutableMapping, Protocol, Sequence

getcontext().prec = 28


class LotType(str, Enum):
    REAL = "REAL"
    HYPOTHETICAL = "HYPOTHETICAL"
    ASSUMED = "ASSUMED"


class CostMode(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    AVERAGE_COST = "AVERAGE_COST"


class PriceField(str, Enum):
    CLOSE = "close"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    VWAP = "vwap"


class NonTradingDayPolicy(str, Enum):
    SNAP_PREV_TRADING_DAY = "SNAP_PREV_TRADING_DAY"
    SNAP_NEXT_TRADING_DAY = "SNAP_NEXT_TRADING_DAY"
    SKIP_DATE = "SKIP_DATE"


@dataclass
class LotInput:
    lot_id: str
    ticker: str
    buy_date: date
    shares: Decimal
    buy_price: Decimal
    currency: str | None = None
    type: LotType = LotType.REAL
    notes: str | None = None
    tags: Sequence[str] | None = None


@dataclass
class Lot:
    lot_id: str
    ticker: str
    buy_date: date
    shares: Decimal
    buy_price: Decimal
    currency: str | None = None
    type: LotType = LotType.REAL
    notes: str | None = None
    tags: list[str] | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class PriceSource(Protocol):
    """Pluggable price provider."""

    def get_price_series(
        self,
        ticker: str,
        start_date: date | None,
        end_date: date | None,
        *,
        price_field: PriceField = PriceField.CLOSE,
    ) -> dict[date, Decimal]:
        ...

    def get_latest_price(
        self,
        ticker: str,
        *,
        price_field: PriceField = PriceField.CLOSE,
    ) -> Decimal:
        ...


class InMemoryPriceSource:
    """Simple price source for tests and examples."""

    def __init__(self, prices: Mapping[str, Mapping[date, Mapping[str, Decimal | str | float]]]):
        self._prices: dict[str, dict[date, dict[str, Decimal]]] = {}
        for ticker, date_map in prices.items():
            normalized_dates: dict[date, dict[str, Decimal]] = {}
            for d, values in date_map.items():
                normalized_dates[d] = {field: Decimal(str(v)) for field, v in values.items()}
            self._prices[ticker] = normalized_dates

    def get_price_series(
        self,
        ticker: str,
        start_date: date | None,
        end_date: date | None,
        *,
        price_field: PriceField = PriceField.CLOSE,
    ) -> dict[date, Decimal]:
        series = self._prices.get(ticker, {})
        result: dict[date, Decimal] = {}
        for d, values in series.items():
            if start_date and d < start_date:
                continue
            if end_date and d > end_date:
                continue
            if price_field.value not in values and "close" not in values:
                continue
            result[d] = values.get(price_field.value, values.get("close"))  # type: ignore[assignment]
        return dict(sorted(result.items()))

    def get_latest_price(
        self,
        ticker: str,
        *,
        price_field: PriceField = PriceField.CLOSE,
    ) -> Decimal:
        series = self.get_price_series(ticker, None, None, price_field=price_field)
        if not series:
            raise ValueError(f"No prices for ticker {ticker}")
        last_date = max(series.keys())
        return series[last_date]


class CachingPriceSource:
    """Cache wrapper to avoid refetching the same price ranges."""

    def __init__(self, delegate: PriceSource):
        self.delegate = delegate
        self._range_cache: MutableMapping[tuple, dict[date, Decimal]] = {}
        self._latest_cache: MutableMapping[tuple, Decimal] = {}

    def get_price_series(
        self,
        ticker: str,
        start_date: date | None,
        end_date: date | None,
        *,
        price_field: PriceField = PriceField.CLOSE,
    ) -> dict[date, Decimal]:
        key = (ticker, price_field, start_date, end_date)
        if key not in self._range_cache:
            self._range_cache[key] = self.delegate.get_price_series(
                ticker, start_date, end_date, price_field=price_field
            )
        return dict(self._range_cache[key])

    def get_latest_price(
        self,
        ticker: str,
        *,
        price_field: PriceField = PriceField.CLOSE,
    ) -> Decimal:
        key = (ticker, price_field, "latest")
        if key not in self._latest_cache:
            self._latest_cache[key] = self.delegate.get_latest_price(ticker, price_field=price_field)
        return self._latest_cache[key]


@dataclass
class SeriesRow:
    date: date
    ticker: str
    sell_price: Decimal
    total_shares: Decimal
    cost_value: Decimal
    market_value: Decimal
    unrealized_pnl_value: Decimal
    unrealized_pnl_pct: Decimal


@dataclass
class SeriesSummary:
    best_date: date | None = None
    best_value: Decimal | None = None
    worst_date: date | None = None
    worst_value: Decimal | None = None
    latest_date: date | None = None
    latest_value: Decimal | None = None
    max_drawdown_pct: Decimal | None = None


@dataclass
class SeriesResponse:
    rows: list[SeriesRow]
    summary: SeriesSummary


@dataclass
class SimulationRequest:
    ticker: str
    start_date: date | None = None
    end_date: date | None = None
    last_n_trading_days: int | None = None
    specific_dates: Sequence[date] | None = None
    lot_ids: Sequence[str] | None = None
    type_filter: Sequence[LotType] | None = None
    cost_mode: CostMode = CostMode.FIFO
    price_field: PriceField = PriceField.CLOSE
    non_trading_day_policy: NonTradingDayPolicy = NonTradingDayPolicy.SNAP_PREV_TRADING_DAY
    buy_fee: Decimal = Decimal("0")
    sell_fee: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("0")


class LotStore:
    """Minimal in-memory lot repository."""

    def __init__(self):
        self._lots: Dict[str, Lot] = {}

    def add_lot(self, lot: LotInput) -> Lot:
        _validate_lot_input(lot)
        if lot.lot_id in self._lots:
            raise ValueError(f"Lot {lot.lot_id} already exists")
        created = datetime.utcnow()
        stored = Lot(
            lot_id=lot.lot_id,
            ticker=lot.ticker,
            buy_date=lot.buy_date,
            shares=Decimal(lot.shares),
            buy_price=Decimal(lot.buy_price),
            currency=lot.currency,
            type=lot.type,
            notes=lot.notes,
            tags=list(lot.tags) if lot.tags else None,
            created_at=created,
            updated_at=created,
        )
        self._lots[stored.lot_id] = stored
        return stored

    def list_lots(
        self,
        *,
        ticker: str | None = None,
        lot_ids: Sequence[str] | None = None,
        type_filter: Sequence[LotType] | None = None,
    ) -> list[Lot]:
        selected = list(self._lots.values())
        if ticker:
            selected = [lot for lot in selected if lot.ticker == ticker]
        if lot_ids:
            allowed = set(lot_ids)
            selected = [lot for lot in selected if lot.lot_id in allowed]
        if type_filter:
            allowed_types = {LotType(t) for t in type_filter}
            selected = [lot for lot in selected if lot.type in allowed_types]
        return sorted(selected, key=lambda l: (l.buy_date, l.lot_id))


def _validate_lot_input(lot: LotInput) -> None:
    if lot.shares <= 0:
        raise ValueError("shares must be > 0")
    if lot.buy_price <= 0:
        raise ValueError("buy_price must be > 0")
    if lot.type == LotType.REAL and lot.buy_date > date.today():
        raise ValueError("future buy_date only allowed for hypothetical/assumed lots")


def _ensure_dates(request: SimulationRequest) -> None:
    if request.last_n_trading_days is not None and request.last_n_trading_days <= 0:
        raise ValueError("last_n_trading_days must be positive")
    if request.start_date and request.end_date and request.start_date > request.end_date:
        raise ValueError("start_date cannot be after end_date")
    if (
        request.start_date is None
        and request.last_n_trading_days is None
        and not request.specific_dates
    ):
        raise ValueError("Provide start/end, last_n_trading_days, or specific_dates")


def _resolve_price_for_date(
    valuation_date: date,
    price_series: Mapping[date, Decimal],
    policy: NonTradingDayPolicy,
) -> Decimal | None:
    if valuation_date in price_series:
        return price_series[valuation_date]
    sorted_dates = sorted(price_series.keys())
    if not sorted_dates:
        return None
    if policy == NonTradingDayPolicy.SNAP_PREV_TRADING_DAY:
        for d in reversed(sorted_dates):
            if d < valuation_date:
                return price_series[d]
    elif policy == NonTradingDayPolicy.SNAP_NEXT_TRADING_DAY:
        for d in sorted_dates:
            if d > valuation_date:
                return price_series[d]
    return None


def _build_date_window(request: SimulationRequest, price_series: Mapping[date, Decimal]) -> list[date]:
    if request.specific_dates:
        return sorted(set(request.specific_dates))
    if request.last_n_trading_days:
        available = sorted(price_series.keys())
        return available[-request.last_n_trading_days :] if request.last_n_trading_days <= len(available) else available
    end_date = request.end_date or request.start_date
    assert request.start_date is not None
    assert end_date is not None
    days = (end_date - request.start_date).days
    return [request.start_date + timedelta(days=i) for i in range(days + 1)]


def _compute_unrealized_values(
    sell_price: Decimal,
    lots: Iterable[Lot],
    *,
    cost_mode: CostMode,
    buy_fee: Decimal,
    sell_fee: Decimal,
    tax_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    total_shares = sum(Decimal(l.shares) for l in lots)
    cost_value = sum(Decimal(l.buy_price) * Decimal(l.shares) for l in lots) + Decimal(buy_fee)
    if total_shares == 0:
        return Decimal("0"), cost_value, Decimal("0")
    if cost_mode == CostMode.AVERAGE_COST:
        avg_cost = cost_value / total_shares
        base_unrealized = (sell_price - avg_cost) * total_shares
    else:
        base_unrealized = sum((sell_price - Decimal(l.buy_price)) * Decimal(l.shares) for l in lots)
    net_unrealized = base_unrealized - Decimal(sell_fee)
    if tax_rate:
        taxable = max(Decimal("0"), net_unrealized)
        net_unrealized = taxable * (Decimal("1") - Decimal(tax_rate)) + min(Decimal("0"), net_unrealized)
    market_value = sell_price * total_shares
    try:
        pct = net_unrealized / cost_value if cost_value != 0 else Decimal("0")
    except DivisionByZero:
        pct = Decimal("0")
    return net_unrealized, cost_value, market_value


def simulate_unrealized_series(
    price_source: PriceSource,
    lot_store: LotStore,
    request: SimulationRequest,
) -> SeriesResponse:
    _ensure_dates(request)
    lots = lot_store.list_lots(
        ticker=request.ticker,
        lot_ids=request.lot_ids,
        type_filter=request.type_filter,
    )
    if not lots:
        return SeriesResponse(rows=[], summary=SeriesSummary())
    total_shares = sum(Decimal(l.shares) for l in lots)
    if total_shares == 0:
        return SeriesResponse(rows=[], summary=SeriesSummary())
    price_series = price_source.get_price_series(
        request.ticker, request.start_date, request.end_date, price_field=request.price_field
    )
    if not price_series:
        return SeriesResponse(rows=[], summary=SeriesSummary())
    valuation_dates = _build_date_window(request, price_series)
    rows: list[SeriesRow] = []
    for valuation_date in valuation_dates:
        sell_price = _resolve_price_for_date(valuation_date, price_series, request.non_trading_day_policy)
        if sell_price is None:
            continue
        unrealized, cost_value, market_value = _compute_unrealized_values(
            sell_price,
            lots,
            cost_mode=request.cost_mode,
            buy_fee=request.buy_fee,
            sell_fee=request.sell_fee,
            tax_rate=request.tax_rate,
        )
        row = SeriesRow(
            date=valuation_date,
            ticker=request.ticker,
            sell_price=sell_price,
            total_shares=total_shares,
            cost_value=cost_value,
            market_value=market_value,
            unrealized_pnl_value=unrealized,
            unrealized_pnl_pct=unrealized / cost_value if cost_value else Decimal("0"),
        )
        rows.append(row)
    summary = _summarize(rows)
    return SeriesResponse(rows=rows, summary=summary)


def _summarize(rows: Sequence[SeriesRow]) -> SeriesSummary:
    if not rows:
        return SeriesSummary()
    best_row = max(rows, key=lambda r: r.unrealized_pnl_value)
    worst_row = min(rows, key=lambda r: r.unrealized_pnl_value)
    latest_row = max(rows, key=lambda r: r.date)
    peak = Decimal("-Infinity")
    max_drawdown = Decimal("0")
    for row in sorted(rows, key=lambda r: r.date):
        if peak == Decimal("-Infinity"):
            peak = row.unrealized_pnl_value
        peak = max(peak, row.unrealized_pnl_value)
        if peak != 0:
            drawdown = (row.unrealized_pnl_value - peak) / peak * Decimal("100")
            max_drawdown = min(max_drawdown, drawdown)
    return SeriesSummary(
        best_date=best_row.date,
        best_value=best_row.unrealized_pnl_value,
        worst_date=worst_row.date,
        worst_value=worst_row.unrealized_pnl_value,
        latest_date=latest_row.date,
        latest_value=latest_row.unrealized_pnl_value,
        max_drawdown_pct=max_drawdown,
    )


def compute_target_from_point(
    lot_store: LotStore,
    ticker: str,
    target_profit: Decimal,
    *,
    lot_ids: Sequence[str] | None = None,
    type_filter: Sequence[LotType] | None = None,
) -> dict[str, Decimal | str | None]:
    lots = lot_store.list_lots(ticker=ticker, lot_ids=lot_ids, type_filter=type_filter)
    if not lots:
        raise ValueError("No lots available for target computation")
    total_shares = sum(Decimal(l.shares) for l in lots)
    if total_shares == 0:
        raise ValueError("Total shares is zero; cannot compute target price")
    cost_value = sum(Decimal(l.buy_price) * Decimal(l.shares) for l in lots)
    avg_cost = cost_value / total_shares
    target_price = avg_cost + (Decimal(target_profit) / total_shares)
    return {
        "ticker": ticker,
        "total_shares": total_shares,
        "avg_cost": avg_cost,
        "target_profit": Decimal(target_profit),
        "target_price": target_price,
    }


__all__ = [
    "Lot",
    "LotInput",
    "LotStore",
    "LotType",
    "CostMode",
    "PriceField",
    "NonTradingDayPolicy",
    "PriceSource",
    "InMemoryPriceSource",
    "CachingPriceSource",
    "SimulationRequest",
    "SeriesResponse",
    "SeriesRow",
    "SeriesSummary",
    "simulate_unrealized_series",
    "compute_target_from_point",
]
