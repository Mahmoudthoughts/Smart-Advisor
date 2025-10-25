"""Pydantic schemas for portfolio watchlists and transactions."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.portfolio import TRANSACTION_TYPES


class WatchlistCreateRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol to track", examples=["PATH"])


class WatchlistSymbolSchema(BaseModel):
    id: int
    symbol: str
    created_at: datetime
    latest_close: float | None = None
    latest_close_date: date | None = None


class TransactionCreateRequest(BaseModel):
    symbol: str = Field(..., examples=["PATH"])
    type: str = Field(..., pattern="|".join(TRANSACTION_TYPES))
    quantity: float
    price: float
    trade_datetime: datetime
    fee: float = 0.0
    tax: float = 0.0
    currency: str = Field(default="USD", min_length=3, max_length=3)
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
    account: str | None = None
    notes: str | None = None
    notional_value: float

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "symbol": "PATH",
                "type": "BUY",
                "quantity": 100,
                "price": 10.5,
                "fee": 1.0,
                "tax": 0.0,
                "currency": "USD",
                "trade_datetime": "2024-03-01T10:00:00+04:00",
                "account": "Broker-1",
                "notes": "Initial position",
                "notional_value": 1050.0,
            }
        }


__all__ = [
    "TransactionSchema",
    "TransactionCreateRequest",
    "WatchlistSymbolSchema",
    "WatchlistCreateRequest",
]
