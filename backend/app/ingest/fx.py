"""Compatibility wrapper for ingest FX job."""

from services.ingest.fx import ingest_fx_pair  # noqa: F401

__all__ = ["ingest_fx_pair"]
