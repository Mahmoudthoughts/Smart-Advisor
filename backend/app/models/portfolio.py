"""Portfolio, transaction, decision, and lot models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TRANSACTION_TYPES = ("BUY", "SELL", "DIVIDEND", "FEE", "SPLIT")


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Dubai")

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    watchlist: Mapped[list["PortfolioSymbol"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    accounts: Mapped[list["PortfolioAccount"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["InvestmentDecision"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        Index("ix_transaction_symbol_datetime", "symbol", "datetime"),
        Index("ix_transaction_account", "account_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    type: Mapped[str] = mapped_column(Enum(*TRANSACTION_TYPES, name="transaction_type"))
    qty: Mapped[float] = mapped_column(Numeric(18, 4))
    price: Mapped[float] = mapped_column(Numeric(18, 6))
    fee: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    tax: Mapped[float] = mapped_column(Numeric(18, 6), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    broker_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("portfolio_account.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="transactions")
    lots: Mapped[list["Lot"]] = relationship(back_populates="transaction")
    account: Mapped[Optional["PortfolioAccount"]] = relationship(back_populates="transactions")


class PortfolioSymbol(Base):
    __tablename__ = "portfolio_symbol"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),
        Index("ix_portfolio_symbol_symbol", "symbol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="watchlist")


class PortfolioAccount(Base):
    __tablename__ = "portfolio_account"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "name", name="uq_portfolio_account_name"),
        Index("ix_portfolio_account_portfolio", "portfolio_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolio.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship(back_populates="account")


class DecisionAction(str, enum.Enum):
    BUY_MORE = "BUY_MORE"
    TRIM = "TRIM"
    EXIT = "EXIT"
    HOLD = "HOLD"


class DecisionStatus(str, enum.Enum):
    OPEN = "OPEN"
    EXECUTED = "EXECUTED"
    SKIPPED = "SKIPPED"


class InvestmentDecision(Base):
    __tablename__ = "investment_decision"
    __table_args__ = (
        Index("ix_investment_decision_symbol_status", "symbol", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int | None] = mapped_column(
        ForeignKey("portfolio.id", ondelete="SET NULL"), nullable=True
    )
    investor: Mapped[str] = mapped_column(String(128))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    action: Mapped[DecisionAction] = mapped_column(
        Enum(DecisionAction, name="decision_action"), default=DecisionAction.BUY_MORE
    )
    planned_quantity: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    decision_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    decision_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    status: Mapped[DecisionStatus] = mapped_column(
        Enum(DecisionStatus, name="decision_status"), default=DecisionStatus.OPEN
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    actual_quantity: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    outcome_price: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    outcome_notes: Mapped[str | None] = mapped_column(String(512), nullable=True)

    portfolio: Mapped[Optional[Portfolio]] = relationship(back_populates="decisions")


class Lot(Base):
    __tablename__ = "lot"
    __table_args__ = (
        Index("ix_lot_symbol_open", "symbol", "open_datetime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transaction.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    open_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    qty_open: Mapped[float] = mapped_column(Numeric(18, 4))
    cost_per_share_adj: Mapped[float] = mapped_column(Numeric(18, 6))
    fees_alloc: Mapped[float] = mapped_column(Numeric(18, 6), default=0)

    transaction: Mapped[Transaction] = relationship(back_populates="lots")


__all__ = [
    "Portfolio",
    "Transaction",
    "Lot",
    "PortfolioSymbol",
    "PortfolioAccount",
    "InvestmentDecision",
    "DecisionAction",
    "DecisionStatus",
    "TRANSACTION_TYPES",
]
