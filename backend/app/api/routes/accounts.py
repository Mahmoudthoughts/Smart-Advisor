"""Proxy portfolio account endpoints to the portfolio service."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas import PortfolioAccountCreateRequest, PortfolioAccountSchema
from app.services import portfolio as portfolio_client
from app.api.dependencies.auth import get_current_user
from smart_advisor.api.models import User

router = APIRouter()


@router.get("", response_model=list[PortfolioAccountSchema])
async def get_accounts(current_user: User = Depends(get_current_user)) -> list[PortfolioAccountSchema]:
    data = await portfolio_client.list_accounts(str(current_user.id))
    return [PortfolioAccountSchema(**item) for item in data]


@router.post("", response_model=PortfolioAccountSchema, status_code=201)
async def post_account(
    payload: PortfolioAccountCreateRequest,
    current_user: User = Depends(get_current_user),
) -> PortfolioAccountSchema:
    data = await portfolio_client.create_account(payload.dict(), str(current_user.id))
    return PortfolioAccountSchema(**data)


__all__ = ["router"]
