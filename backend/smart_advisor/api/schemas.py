"""Pydantic schemas for API payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    created_at: datetime
    role: str


class AuthResponse(BaseModel):
    access_token: str = Field(..., description="Opaque token for session management")
    token_type: str = Field(default="bearer")
    user: UserOut


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user", min_length=4, max_length=32)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class AdminCreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="user", min_length=4, max_length=32)


class AdminUpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    role: str | None = Field(default=None, min_length=4, max_length=32)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class StockListProviderUpsert(BaseModel):
    provider: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=2, max_length=255)
    api_key: str | None = Field(default=None, max_length=255)
    base_url: str | None = Field(default=None, max_length=255)
    is_active: bool = True
    is_default: bool = False


class StockListProviderOut(BaseModel):
    id: UUID
    provider: str
    display_name: str
    api_key: str | None
    base_url: str | None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class LlmProviderUpsert(BaseModel):
    provider: str = Field(..., min_length=2, max_length=64)
    display_name: str = Field(..., min_length=2, max_length=255)
    api_key: str | None = Field(default=None, max_length=255)
    base_url: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=128)
    is_active: bool = True
    is_default: bool = False


class LlmProviderOut(BaseModel):
    id: UUID
    provider: str
    display_name: str
    api_key: str | None
    base_url: str | None
    model: str | None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    status: str
    service: str
    database_url: Optional[str]

