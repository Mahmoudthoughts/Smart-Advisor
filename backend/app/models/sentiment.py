"""Signal and sentiment models."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SignalEvent(Base):
    __tablename__ = "signal_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    signal_type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TickerSentimentDaily(Base):
    __tablename__ = "ticker_sentiment_daily"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    score: Mapped[float] = mapped_column(Numeric(6, 4))


__all__ = ["SignalEvent", "TickerSentimentDaily"]
