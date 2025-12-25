"""Intraday bar cache model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IntradayBar(Base):
    __tablename__ = "intraday_bar"
    __table_args__ = (
        UniqueConstraint("symbol", "bar_size", "use_rth", "timestamp", name="uq_intraday_bar_key"),
        Index("ix_intraday_bar_symbol_ts", "symbol", "bar_size", "use_rth", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20))
    bar_size: Mapped[str] = mapped_column(String(16))
    use_rth: Mapped[bool] = mapped_column(Boolean, default=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[float] = mapped_column(Numeric(18, 6))
    high: Mapped[float] = mapped_column(Numeric(18, 6))
    low: Mapped[float] = mapped_column(Numeric(18, 6))
    close: Mapped[float] = mapped_column(Numeric(18, 6))
    volume: Mapped[float] = mapped_column(Numeric(20, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")


__all__ = ["IntradayBar"]
