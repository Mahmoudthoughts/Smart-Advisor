"""Session-level summaries for intraday bars."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SessionSummary(Base):
    """Aggregated intraday metrics per symbol and trading session."""

    __tablename__ = "session_summary"
    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_session_summary_symbol_date"),
        Index("ix_session_summary_symbol_date", "symbol", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    midday_low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    drawdown_pct: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    recovery_pct: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    bars: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


__all__ = ["SessionSummary"]
