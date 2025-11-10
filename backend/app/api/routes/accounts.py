"""Proxy portfolio account endpoints to the portfolio service."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas import PortfolioAccountCreateRequest, PortfolioAccountSchema
from app.services import portfolio as portfolio_client

router = APIRouter()


@router.get("", response_model=list[PortfolioAccountSchema])
async def get_accounts() -> list[PortfolioAccountSchema]:
    data = await portfolio_client.list_accounts()
    return [PortfolioAccountSchema(**item) for item in data]


@router.post("", response_model=PortfolioAccountSchema, status_code=201)
async def post_account(payload: PortfolioAccountCreateRequest) -> PortfolioAccountSchema:
    data = await portfolio_client.create_account(payload.dict())
    return PortfolioAccountSchema(**data)


__all__ = ["router"]
