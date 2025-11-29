"""Proxy portfolio endpoints that delegate to the portfolio service."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.schemas import (
    PortfolioAccountCreateRequest,
    PortfolioAccountSchema,
    TransactionCreateRequest,
    TransactionSchema,
    TransactionUpdateRequest,
    WatchlistCreateRequest,
    WatchlistSymbolSchema,
)
from app.services import portfolio as portfolio_client
from app.api.dependencies.auth import get_current_user
from smart_advisor.api.models import User

router = APIRouter()


@router.get("/watchlist", response_model=list[WatchlistSymbolSchema])
async def get_watchlist(current_user: User = Depends(get_current_user)) -> list[WatchlistSymbolSchema]:
    data = await portfolio_client.fetch_watchlist(str(current_user.id))
    return [WatchlistSymbolSchema(**item) for item in data]


@router.post("/watchlist", response_model=WatchlistSymbolSchema, status_code=status.HTTP_201_CREATED)
async def post_watchlist(
    payload: WatchlistCreateRequest,
    current_user: User = Depends(get_current_user),
) -> WatchlistSymbolSchema:
    try:
        data = await portfolio_client.add_watchlist(payload.model_dump(mode="json"), str(current_user.id))
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return WatchlistSymbolSchema(**data)


@router.get("/transactions", response_model=list[TransactionSchema])
async def get_transactions(current_user: User = Depends(get_current_user)) -> list[TransactionSchema]:
    data = await portfolio_client.list_transactions(str(current_user.id))
    return [TransactionSchema(**item) for item in data]


@router.post("/transactions", response_model=TransactionSchema, status_code=201)
async def post_transaction(
    payload: TransactionCreateRequest,
    current_user: User = Depends(get_current_user),
) -> TransactionSchema:
    data = await portfolio_client.create_transaction(payload.model_dump(mode="json"), str(current_user.id))
    return TransactionSchema(**data)


@router.put("/transactions/{transaction_id}", response_model=TransactionSchema)
async def put_transaction(
    transaction_id: int,
    payload: TransactionUpdateRequest,
    current_user: User = Depends(get_current_user),
) -> TransactionSchema:
    data = await portfolio_client.update_transaction(
        transaction_id,
        payload.model_dump(mode="json"),
        str(current_user.id),
    )
    return TransactionSchema(**data)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
) -> Response:
    await portfolio_client.delete_transaction(transaction_id, str(current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/accounts", response_model=list[PortfolioAccountSchema])
async def get_accounts(current_user: User = Depends(get_current_user)) -> list[PortfolioAccountSchema]:
    data = await portfolio_client.list_accounts(str(current_user.id))
    return [PortfolioAccountSchema(**item) for item in data]


@router.post("/accounts", response_model=PortfolioAccountSchema, status_code=201)
async def post_account(
    payload: PortfolioAccountCreateRequest,
    current_user: User = Depends(get_current_user),
) -> PortfolioAccountSchema:
    data = await portfolio_client.create_account(payload.model_dump(mode="json"), str(current_user.id))
    return PortfolioAccountSchema(**data)


__all__ = ["router"]
