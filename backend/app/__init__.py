"""Missed Opportunity Analyzer + Smart Advisor service package."""

from .config.settings import AppSettings, get_settings  # noqa: F401

__all__ = ["AppSettings", "get_settings"]
