"""Pydantic schemas for the portfolio service."""

from __future__ import annotations

from datetime import datetime, date

from pydantic import BaseModel, Field

from ..models.portfolio import TRANSACTION_TYPES


class WatchlistCreateRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to track", examples=["PATH"])
    name: str | None = Field(default=None, description="Optional display name for the symbol")


class WatchlistSymbolSchema(BaseModel):
    id: int
    symbol: str
    created_at: datetime
    latest_close: float | None = None
    latest_close_date: date | None = None
    previous_close: float | None = None
    day_change: float | None = None
    day_change_percent: float | None = None
    position_qty: float | None = None
    average_cost: float | None = None
    unrealized_pl: float | None = None
    name: str | None = None


class TransactionCreateRequest(BaseModel):
    symbol: str = Field(..., examples=["PATH"])
    type: str = Field(..., pattern="|".join(TRANSACTION_TYPES))
    quantity: float
    price: float
    trade_datetime: datetime
    fee: float = 0.0
    tax: float = 0.0
    currency: str = Field(default="USD", min_length=3, max_length=3)
    account_id: int | None = Field(default=None, description="Portfolio account identifier")
    account: str | None = Field(default=None, description="Account or broker reference")
    notes: str | None = None


class TransactionSchema(BaseModel):
    id: int
    symbol: str
    type: str
    quantity: float
    price: float
    fee: float
    tax: float
    currency: str
    trade_datetime: datetime
    account_id: int | None = None
    account: str | None = None
    notes: str | None = None
    notional_value: float


class PortfolioAccountCreateRequest(BaseModel):
    name: str = Field(..., description="Display name for the account", examples=["Interactive Brokers"])
    type: str | None = Field(default=None, description="Account type such as Brokerage or Retirement")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    notes: str | None = Field(default=None)
    is_default: bool = Field(default=False)


class PortfolioAccountSchema(BaseModel):
    id: int
    name: str
    type: str | None = None
    currency: str
    notes: str | None = None
    is_default: bool
    created_at: datetime


class TransactionUpdateRequest(BaseModel):
    symbol: str = Field(..., examples=["PATH"])
    type: str = Field(..., pattern="|".join(TRANSACTION_TYPES))
    quantity: float
    price: float
    trade_datetime: datetime
    fee: float = 0.0
    tax: float = 0.0
    currency: str = Field(default="USD", min_length=3, max_length=3)
    account_id: int | None = Field(default=None, description="Portfolio account identifier")
    account: str | None = Field(default=None)
    notes: str | None = None


__all__ = [
    "TransactionSchema",
    "TransactionCreateRequest",
    "TransactionUpdateRequest",
    "WatchlistSymbolSchema",
    "WatchlistCreateRequest",
    "PortfolioAccountSchema",
    "PortfolioAccountCreateRequest",
]
