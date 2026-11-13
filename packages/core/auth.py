"""Authentication utilities for OSHI.

Provides API key verification and FastAPI dependencies for protecting routes.

API keys are sent via the ``Authorization: Bearer <key>`` header or the
``X-API-Key`` header. The plaintext key is never stored; only a SHA-256 hash
is kept in the database. The key prefix (first 12 characters) is stored
separately for fast lookup.

Security notes (Part 8):
- Keys are hashed before storage; the plaintext value is shown only once at
  creation time.
- Constant-time comparison (``secrets.compare_digest``) prevents timing
  attacks.
- Inactive or expired keys are rejected.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.database import get_db
from packages.core.models import APIKey, User


def hash_api_key(key: str) -> str:
    """Return the SHA-256 hex digest of an API key."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def key_prefix(key: str) -> str:
    """Return the first 12 characters of a key as a lookup prefix."""
    return key[:12]


def verify_api_key(key: str, db: Session) -> User | None:
    """Verify an API key and return the associated user, or ``None``.

    Performs constant-time comparison of the hashed key against stored hashes
    for the matching key prefix. Updates ``last_used_at`` on success.
    """
    if not key:
        return None

    prefix = key_prefix(key)
    key_hash = hash_api_key(key)

    # Look up candidate keys by prefix first (fast index lookup), then
    # compare full hashes in constant time.
    candidates = db.execute(
        select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True)  # noqa: E712
    ).scalars().all()

    for candidate in candidates:
        if candidate.expires_at is not None and candidate.expires_at < datetime.now(timezone.utc):
            continue
        if secrets.compare_digest(candidate.key_hash, key_hash):
            # Record usage.
            candidate.last_used_at = datetime.now(timezone.utc)
            db.add(candidate)
            db.commit()
            return candidate.user

    return None


def get_api_key(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    """Extract the API key from the ``Authorization: Bearer`` or ``X-API-Key`` header."""
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return x_api_key


def require_api_key(
    api_key: str | None = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency that requires a valid API key.

    Returns the authenticated ``User`` on success, raises 401 otherwise.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide Authorization: Bearer <key> or X-API-Key header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = verify_api_key(api_key, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled.",
        )

    return user


def get_current_user(
    api_key: str | None = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> User | None:
    """Optional authentication dependency.

    Returns the authenticated ``User`` if a valid API key is provided,
    otherwise ``None``. Useful for endpoints that work both with and without
    auth (e.g. read-only discovery).
    """
    if api_key is None:
        return None
    user = verify_api_key(api_key, db)
    if user is None or not user.is_active:
        return None
    return user


__all__ = [
    "hash_api_key",
    "key_prefix",
    "verify_api_key",
    "get_api_key",
    "require_api_key",
    "get_current_user",
]
