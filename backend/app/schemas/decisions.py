"""Pydantic schemas for investor decision tracking."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, validator

from app.models.portfolio import DecisionAction, DecisionStatus


class InvestmentDecisionOutcomeSchema(BaseModel):
    """Summarised outcome metrics for a decision."""

    price_change: float | None = Field(
        default=None, description="Absolute price change between decision and outcome"
    )
    price_change_pct: float | None = Field(
        default=None, description="Percentage price change between decision and outcome"
    )
    projected_value_change: float | None = Field(
        default=None,
        description=(
            "Hypothetical value delta if the suggested quantity was applied "
            "(positive favours the proposed action, negative indicates regret)."
        ),
    )


class InvestmentDecisionSchema(BaseModel):
    """Full representation of a logged decision."""

    id: int
    portfolio_id: int | None
    investor: str
    symbol: str
    action: DecisionAction
    planned_quantity: float | None
    decision_price: float | None
    decision_at: datetime
    status: DecisionStatus
    resolved_at: datetime | None
    resolved_price: float | None
    actual_quantity: float | None
    outcome_price: float | None
    notes: str | None
    outcome_notes: str | None
    outcome: InvestmentDecisionOutcomeSchema


class InvestmentDecisionCreateRequest(BaseModel):
    """Payload to capture a new potential move for a symbol."""

    investor: str = Field(..., min_length=1, max_length=128, description="Investor name or identifier")
    symbol: str = Field(..., min_length=1, max_length=20, description="Ticker symbol under consideration")
    action: DecisionAction = Field(default=DecisionAction.BUY_MORE)
    planned_quantity: float | None = Field(
        default=None, description="Quantity the investor intends to add or trim"
    )
    decision_price: float | None = Field(
        default=None,
        description="Reference price at the time of logging the decision (defaults to latest close if omitted)",
    )
    decision_at: datetime | None = Field(
        default=None, description="Timestamp the decision was considered (defaults to now if omitted)"
    )
    notes: str | None = Field(default=None, max_length=512)
    portfolio_id: int | None = Field(
        default=None, description="Optional portfolio linkage for the investor"
    )


class InvestmentDecisionResolveRequest(BaseModel):
    """Update payload once the investor acts or chooses to skip the decision."""

    status: DecisionStatus = Field(..., description="Final status such as EXECUTED or SKIPPED")
    resolved_at: datetime | None = Field(
        default=None, description="When the decision was closed (defaults to now if omitted)"
    )
    resolved_price: float | None = Field(
        default=None, description="Execution price if the decision was actioned"
    )
    actual_quantity: float | None = Field(
        default=None, description="Quantity actually executed; defaults to planned quantity if missing"
    )
    outcome_price: float | None = Field(
        default=None,
        description="Price to measure the outcome against; falls back to resolved price or latest close",
    )
    outcome_notes: str | None = Field(default=None, max_length=512)

    @validator("status")
    def _status_must_close_decision(cls, value: DecisionStatus) -> DecisionStatus:  # noqa: B902
        if value == DecisionStatus.OPEN:
            raise ValueError("Resolution status cannot remain OPEN")
        return value


__all__ = [
    "InvestmentDecisionOutcomeSchema",
    "InvestmentDecisionSchema",
    "InvestmentDecisionCreateRequest",
    "InvestmentDecisionResolveRequest",
]
