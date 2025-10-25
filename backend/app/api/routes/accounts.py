"""Portfolio account management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import PortfolioAccount
from app.schemas.portfolio import PortfolioAccountCreateRequest, PortfolioAccountSchema
from app.services.portfolio import create_account, list_accounts

router = APIRouter()


def _serialize_account(record: PortfolioAccount) -> PortfolioAccountSchema:
    return PortfolioAccountSchema(
        id=record.id,
        name=record.name,
        type=record.type,
        currency=record.currency,
        notes=record.notes,
        is_default=record.is_default,
        created_at=record.created_at,
    )


@router.get("", response_model=list[PortfolioAccountSchema])
async def get_accounts(session: AsyncSession = Depends(get_db)) -> list[PortfolioAccountSchema]:
    records = await list_accounts(session)
    return [_serialize_account(record) for record in records]


@router.post("", response_model=PortfolioAccountSchema, status_code=status.HTTP_201_CREATED)
async def post_account(
    payload: PortfolioAccountCreateRequest,
    session: AsyncSession = Depends(get_db),
) -> PortfolioAccountSchema:
    try:
        record = await create_account(payload, session)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_account(record)


__all__ = ["router"]
