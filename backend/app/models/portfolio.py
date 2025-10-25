"""Portfolio, transaction, and lot models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

TRANSACTION_TYPES = ("BUY", "SELL", "DIVIDEND", "FEE", "SPLIT")


class Portfolio(Base):
    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Dubai")

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    watchlist: Mapped[list["PortfolioSymbol"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "transaction"
    __table_args__ = (
        Index("ix_transaction_symbol_datetime", "symbol", "datetime"),
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
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="transactions")
    lots: Mapped[list["Lot"]] = relationship(back_populates="transaction")


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

    portfolio: Mapped[Portfolio] = relationship(back_populates="watchlist")


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


__all__ = ["Portfolio", "Transaction", "Lot", "PortfolioSymbol", "TRANSACTION_TYPES"]
