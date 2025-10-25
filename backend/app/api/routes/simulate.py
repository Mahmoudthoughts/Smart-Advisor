"""Scenario simulation stubs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.schemas import SimulationRequest, SimulationResponse

router = APIRouter()


@router.post("", response_model=SimulationResponse)
async def create_simulation(request: SimulationRequest) -> SimulationResponse:
    """Return a stubbed ghost timeline identifier with placeholder deltas."""

    timeline_id = f"sim_{uuid.uuid4().hex[:8]}"
    return SimulationResponse(timeline_id=timeline_id, diff_vs_base={"pnl_delta": 0.0, "max_dd_delta": 0.0})


__all__ = ["create_simulation"]
