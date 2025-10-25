"""Dashboard KPI model."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DashboardKPI(Base):
    __tablename__ = "dashboard_kpi"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Numeric(18, 6))
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)


__all__ = ["DashboardKPI"]
