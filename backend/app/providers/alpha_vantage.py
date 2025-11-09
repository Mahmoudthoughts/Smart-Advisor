"""Backwards-compatible re-export of the ingest Alpha Vantage client."""

from services.ingest.alpha_vantage import (  # noqa: F401
    AlphaVantageClient,
    AlphaVantageError,
    BASE_URL,
    get_alpha_vantage_client,
)

__all__ = ["AlphaVantageClient", "AlphaVantageError", "BASE_URL", "get_alpha_vantage_client"]
