"""FX conversion helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Tuple


@dataclass
class FXRateProvider:
    """Look up FX conversion rates to the base currency."""

    rates: Dict[Tuple[date, str, str], float]
    base_currency: str = "USD"

    def rate(self, d: date, from_currency: str, to_currency: str | None = None) -> float:
        """Return the conversion rate from ``from_currency`` to ``to_currency``."""

        target = to_currency or self.base_currency
        if from_currency.upper() == target.upper():
            return 1.0
        key = (d, from_currency.upper(), target.upper())
        if key not in self.rates:
            raise KeyError(
                f"Missing FX rate for {from_currency}->{target} on {d.isoformat()}"
            )
        return self.rates[key]
