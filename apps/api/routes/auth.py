"""Authentication API routes.

Endpoints:
- POST /api/v1/auth/bootstrap — create first superuser + API key (no auth required; bootstrap only)
- POST /api/v1/auth/keys — create a new API key for the authenticated user
- GET /api/v1/auth/keys — list the authenticated user's API keys
- DELETE /api/v1/auth/keys/{key_id} — revoke an API key

Security (Part 8, Part 10):
- The plaintext API key is returned only once, at creation time.
- Keys are stored as salted hashes; only the prefix is stored in plaintext.
- Bootstrap is disabled once any user exists.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from apps.api.schemas import (
    APIKeyCreatedResponse,
    APIKeyCreateRequest,
    APIKeyOut,
    APIKeyRevokeRequest,
)
from packages.core.auth import (
    get_api_key,
    hash_api_key,
    key_prefix,
    require_api_key,
    verify_api_key,
)
from packages.core.database import get_db
from packages.core.models import APIKey as APIKeyModel
from packages.core.models import Organization
from packages.core.models import User
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _generate_api_key() -> str:
    """Generate a new API key with the ``oshi_`` prefix."""
    return f"oshi_{secrets.token_urlsafe(32)}"


@router.post("/bootstrap", response_model=APIKeyCreatedResponse)
def bootstrap(
    email: str,
    name: str | None = None,
    db: Session = Depends(get_db),
) -> APIKeyCreatedResponse:
    """Create the first superuser and an API key.

    Only works when no users exist yet. After bootstrap, all protected routes
    require a valid API key.
    """
    existing = db.execute(select(User).limit(1)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap already performed. Use /api/v1/auth/keys to manage keys.",
        )

    user = User(email=email, name=name, is_superuser=True, is_active=True)
    db.add(user)
    db.flush()

    org = Organization(name=f"{user.name or user.email}'s Organization", slug=f"org-{user.id}")
    db.add(org)
    db.flush()

    membership = None
    # Create membership linking user to org
    from packages.core.models import OrganizationMember

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
    )
    db.add(membership)
    db.flush()

    plain_key = _generate_api_key()
    key_hash = hash_api_key(plain_key)
    prefix = key_prefix(plain_key)

    api_key = APIKeyModel(
        name="Bootstrap key",
        key_hash=key_hash,
        key_prefix=prefix,
        user_id=user.id,
        organization_id=org.id,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreatedResponse(
        api_key=plain_key,
        key_prefix=prefix,
        id=api_key.id,
        name=api_key.name,
        created_at=api_key.created_at,
    )


@router.post("/keys", response_model=APIKeyCreatedResponse)
def create_api_key(
    request: APIKeyCreateRequest,
    current_user: User = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> APIKeyCreatedResponse:
    """Create a new API key for the authenticated user."""
    organization_id = None
    if request.organization_id:
        # Verify the user is a member of the organization.
        from packages.core.models import OrganizationMember

        membership = db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == UUID(request.organization_id),
                OrganizationMember.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of the specified organization.",
            )
        organization_id = UUID(request.organization_id)

    expires_at = None
    if request.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    plain_key = _generate_api_key()
    key_hash = hash_api_key(plain_key)
    prefix = key_prefix(plain_key)

    api_key = APIKeyModel(
        name=request.name,
        key_hash=key_hash,
        key_prefix=prefix,
        user_id=current_user.id,
        organization_id=organization_id,
        is_active=True,
        expires_at=expires_at,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return APIKeyCreatedResponse(
        api_key=plain_key,
        key_prefix=prefix,
        id=api_key.id,
        name=api_key.name,
        created_at=api_key.created_at,
    )


@router.get("/keys", response_model=list[APIKeyOut])
def list_api_keys(
    current_user: User = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> list[APIKeyOut]:
    """List the authenticated user's API keys (prefix only; plaintext never returned)."""
    keys = db.execute(
        select(APIKeyModel).where(APIKeyModel.user_id == current_user.id)
    ).scalars().all()
    return [APIKeyOut.model_validate(k) for k in keys]


@router.delete("/keys/{key_id}")
def revoke_api_key(
    key_id: UUID,
    current_user: User = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Revoke (deactivate) an API key owned by the authenticated user."""
    key = db.execute(
        select(APIKeyModel).where(
            APIKeyModel.id == key_id,
            APIKeyModel.user_id == current_user.id,
        )
    ).scalar_one_or_none()
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )
    key.is_active = False
    db.add(key)
    db.commit()
    return {"detail": "revoked"}


@router.post("/verify")
def verify_key(
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Verify that an API key is valid. Returns the user email on success."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key.",
        )
    user = verify_api_key(api_key, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return {"valid": "true", "user": user.email, "is_superuser": str(user.is_superuser)}
