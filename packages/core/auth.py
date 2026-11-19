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
import uuid
from datetime import datetime, timezone

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
    candidates = (
        db.execute(
            select(APIKey).where(APIKey.key_prefix == prefix, APIKey.is_active == True)  # noqa: E712
        )
        .scalars()
        .all()
    )

    for candidate in candidates:
        if candidate.expires_at is not None and candidate.expires_at < datetime.now(
            timezone.utc
        ):
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


def require_admin(
    current_user=Depends(require_api_key),
) -> User:
    """FastAPI dependency that requires an admin (superuser) account.

    Returns the authenticated ``User`` if they are a superuser, raises 403
    otherwise. Use this for administrative actions such as warning
    verification, user management, and system configuration.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user


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


def resolve_primary_organization(user: User) -> uuid.UUID | None:
    """Resolve the organization for a user.

    Prefer a non-member role (admin/owner) when multiple memberships exist,
    otherwise fall back to the first membership. Returns ``None`` if the user
    has no memberships. This avoids silently picking an arbitrary organization
    via ``memberships[0]`` when a user belongs to several.
    """
    if not user.memberships:
        return None
    for m in user.memberships:
        if m.role not in ("member", "viewer"):
            return m.organization_id
    return user.memberships[0].organization_id


def get_organization_context(
    x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
    current_user=Depends(require_api_key),
    api_key: str | None = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> uuid.UUID | None:
    """Resolve the organization (tenant) for the current request.

    Resolution order:
    1. If the API key is bound to an organization (APIKey.organization_id),
       the key may only act on that organization. ``X-Organization-ID`` must
       either match it or be absent (then the key's org is used).
    2. ``X-Organization-ID`` request header, validated against the user's
       memberships (explicit tenant context from the caller).
    3. ``resolve_primary_organization(current_user)`` as fallback.

    Returns ``None`` when the user has no organization context. This makes
    tenant scoping explicit instead of heuristically picking ``memberships[0]``.
    """
    # 1. API key organization binding (strongest signal).
    if api_key is not None:
        prefix = key_prefix(api_key)
        key_hash = hash_api_key(api_key)
        candidates = (
            db.execute(
                select(APIKey).where(
                    APIKey.key_prefix == prefix,
                    APIKey.is_active == True,  # noqa: E712
                )
            )
            .scalars()
            .all()
        )
        for candidate in candidates:
            if secrets.compare_digest(candidate.key_hash, key_hash):
                if candidate.organization_id is not None:
                    if x_organization_id is not None:
                        try:
                            req_org = uuid.UUID(x_organization_id)
                        except (ValueError, AttributeError):
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid X-Organization-ID format.",
                            )
                        if req_org != candidate.organization_id:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail=(
                                    "API key is bound to a different organization "
                                    "than the requested X-Organization-ID."
                                ),
                            )
                    return candidate.organization_id
                break

    # 2. X-Organization-ID request header, validated against memberships.
    if x_organization_id is not None:
        try:
            org_id = uuid.UUID(x_organization_id)
        except (ValueError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Organization-ID format.",
            )
        for m in current_user.memberships:
            if m.organization_id == org_id:
                return org_id
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of the specified organization.",
        )
    # 3. Fallback to primary organization resolution.
    return resolve_primary_organization(current_user)


__all__ = [
    "hash_api_key",
    "key_prefix",
    "verify_api_key",
    "get_api_key",
    "require_api_key",
    "require_admin",
    "resolve_primary_organization",
    "get_organization_context",
    "get_current_user",
]
