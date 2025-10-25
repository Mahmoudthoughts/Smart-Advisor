"""Schemas for signal events and rule upserts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SignalEventSchema(BaseModel):
    id: int
    symbol: str
    date: date
    rule_id: str
    signal_type: str
    severity: Optional[str] = None
    payload: Optional[dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "symbol": "PATH",
                "date": "2024-09-10",
                "rule_id": "path_breakout",
                "signal_type": "TECH_RULE",
                "severity": "medium",
                "payload": {"price": 17.45},
            }
        }


class SignalRuleDefinition(BaseModel):
    rule_id: str
    name: str
    description: Optional[str] = None
    expression: dict[str, Any]
    cooldown_days: int = Field(default=0, ge=0)


class SignalRuleUpsertRequest(BaseModel):
    rules: list[SignalRuleDefinition]

    class Config:
        json_schema_extra = {
            "example": {
                "rules": [
                    {
                        "rule_id": "path_breakout",
                        "name": "PATH breakout",
                        "description": "Close above resistance with volume surge",
                        "expression": {
                            "all": [
                                {"indicator": "close", "op": ">", "value": 17.20},
                                {"indicator": "volume_multiple_20d", "op": ">=", "value": 1.5},
                            ]
                        },
                        "cooldown_days": 2,
                    }
                ]
            }
        }


__all__ = ["SignalEventSchema", "SignalRuleDefinition", "SignalRuleUpsertRequest"]
