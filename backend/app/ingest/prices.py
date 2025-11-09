"""Compatibility wrapper for ingest price job."""

from services.ingest.prices import ingest_prices  # noqa: F401

__all__ = ["ingest_prices"]
