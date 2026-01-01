"""ORM models for the Smart Advisor API."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid_pk() -> UUID:
    return uuid4()


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), default="user")
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    tokens: Mapped[list["AuthToken"]] = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped[User] = relationship("User", back_populates="tokens")

    @classmethod
    def for_user(cls, user_id: UUID, lifetime: timedelta) -> "AuthToken":
        token_value = str(uuid4())
        now = datetime.utcnow()
        return cls(user_id=user_id, token=token_value, created_at=now, expires_at=now + lifetime, is_active=True)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    name: Mapped[str] = mapped_column(String(255))
    owner_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    timezone: Mapped[Optional[str]] = mapped_column(String(64), default="Asia/Dubai")
    base_currency: Mapped[Optional[str]] = mapped_column(String(8), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    owner: Mapped[User] = relationship("User")


class UserPortfolioAccess(Base):
    __tablename__ = "user_portfolio_access"
    __table_args__ = (UniqueConstraint("user_id", "portfolio_id", name="uq_user_portfolio"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    portfolio_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("portfolios.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(32), default="owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class StockListProvider(Base):
    __tablename__ = "stock_list_providers"
    __table_args__ = (UniqueConstraint("provider", name="uq_stock_list_provider"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    provider: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(255))
    api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class LlmProvider(Base):
    __tablename__ = "llm_providers"
    __table_args__ = (UniqueConstraint("provider", name="uq_llm_provider"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=_uuid_pk)
    provider: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(255))
    api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

