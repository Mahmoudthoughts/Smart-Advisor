"""AI timing history model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AiTimingHistory(Base):
    __tablename__ = "ai_timing_history"
    __table_args__ = (
        Index("ix_ai_timing_history_user_symbol_created", "user_id", "symbol", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    symbol_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bar_size: Mapped[str] = mapped_column(String(16))
    duration_days: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(64))
    use_rth: Mapped[bool] = mapped_column(Boolean, default=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


__all__ = ["AiTimingHistory"]
