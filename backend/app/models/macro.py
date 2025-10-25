"""Macro event model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MacroEvent(Base):
    __tablename__ = "macro_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(128))
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    importance: Mapped[str | None] = mapped_column(String(16), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    impact_score: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)


__all__ = ["MacroEvent"]
