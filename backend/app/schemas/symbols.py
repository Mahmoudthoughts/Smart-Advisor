from pydantic import BaseModel, Field
from typing import Optional


class SymbolSearchResultSchema(BaseModel):
    symbol: str = Field(..., examples=["PATH"])
    name: str
    region: Optional[str] = None
    currency: Optional[str] = None
    match_score: Optional[float] = None

    class Config:
        schema_extra = {
            "example": {
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "region": "United States",
                "currency": "USD",
                "match_score": 1.0,
            }
        }


class SymbolRefreshResponse(BaseModel):
    symbol: str
    prices_ingested: int
    snapshots_rebuilt: int


class IntradayBarSchema(BaseModel):
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


__all__ = [
    "SymbolSearchResultSchema",
    "SymbolRefreshResponse",
    "IntradayBarSchema",
]
