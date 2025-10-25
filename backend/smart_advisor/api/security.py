"""Security helpers for hashing passwords and issuing tokens."""

from __future__ import annotations

from datetime import timedelta

from passlib.context import CryptContext


_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_TOKEN_LIFETIME = timedelta(days=7)


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return _pwd_context.verify(plain_password, password_hash)


def token_lifetime() -> timedelta:
    return _TOKEN_LIFETIME

