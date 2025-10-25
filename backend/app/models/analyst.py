"""Analyst snapshot model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalystSnapshot(Base):
    __tablename__ = "analyst_snapshot"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    as_of: Mapped[date] = mapped_column(Date, index=True)
    rating: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    horizon_days: Mapped[int | None] = mapped_column(nullable=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verified: Mapped[bool] = mapped_column(default=False)


__all__ = ["AnalystSnapshot"]
