"""Daily market data and portfolio snapshot models."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyBar(Base):
    __tablename__ = "daily_bar"
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_daily_bar_symbol_date"),
        Index("ix_daily_bar_symbol_date", "symbol", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20))
    date: Mapped[date] = mapped_column(Date)
    open: Mapped[float] = mapped_column(Numeric(18, 6))
    high: Mapped[float] = mapped_column(Numeric(18, 6))
    low: Mapped[float] = mapped_column(Numeric(18, 6))
    close: Mapped[float] = mapped_column(Numeric(18, 6))
    adj_close: Mapped[float] = mapped_column(Numeric(18, 6))
    volume: Mapped[float] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    split_coefficient: Mapped[float | None] = mapped_column(Float, nullable=True)
    dividend_amount: Mapped[float | None] = mapped_column(Float, nullable=True)


class FXRate(Base):
    __tablename__ = "fx_rate"
    __table_args__ = (
        UniqueConstraint("date", "from_ccy", "to_ccy", name="uq_fx_rate_date_pair"),
        Index("ix_fx_rate_pair", "from_ccy", "to_ccy", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    from_ccy: Mapped[str] = mapped_column(String(3))
    to_ccy: Mapped[str] = mapped_column(String(3))
    rate_close: Mapped[float] = mapped_column(Numeric(18, 8))


class DailyPortfolioSnapshot(Base):
    __tablename__ = "daily_portfolio_snapshot"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", "date", name="uq_snapshot_symbol_date"),
        Index("ix_snapshot_symbol_date", "portfolio_id", "symbol", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int | None] = mapped_column(ForeignKey("portfolio.id", ondelete="CASCADE"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20))
    date: Mapped[date] = mapped_column(Date)
    shares_open: Mapped[float] = mapped_column(Numeric(18, 6))
    market_value_base: Mapped[float] = mapped_column(Numeric(18, 6))
    cost_basis_open_base: Mapped[float] = mapped_column(Numeric(18, 6))
    unrealized_pl_base: Mapped[float] = mapped_column(Numeric(18, 6))
    realized_pl_to_date_base: Mapped[float] = mapped_column(Numeric(18, 6))
    hypo_liquidation_pl_base: Mapped[float] = mapped_column(Numeric(18, 6))
    day_opportunity_base: Mapped[float] = mapped_column(Numeric(18, 6))
    peak_hypo_pl_to_date_base: Mapped[float] = mapped_column(Numeric(18, 6))
    drawdown_from_peak_pct: Mapped[float] = mapped_column(Numeric(10, 4))


__all__ = ["DailyBar", "FXRate", "DailyPortfolioSnapshot"]
