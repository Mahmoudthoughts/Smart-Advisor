"""Forecast daily model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ForecastDaily(Base):
    __tablename__ = "forecast_daily"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    horizon_days: Mapped[int] = mapped_column(default=30)
    prob_retake_peak_30d: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    expected_regret_delta: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


__all__ = ["ForecastDaily"]
