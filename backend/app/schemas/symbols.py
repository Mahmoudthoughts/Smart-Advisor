from pydantic import BaseModel, Field


class SymbolSearchResultSchema(BaseModel):
    symbol: str = Field(..., examples=["PATH"])
    name: str
    region: str | None = None
    currency: str | None = None
    match_score: float | None = None


class SymbolRefreshResponse(BaseModel):
    symbol: str
    prices_ingested: int
    snapshots_rebuilt: int


__all__ = [
    "SymbolSearchResultSchema",
    "SymbolRefreshResponse",
]
