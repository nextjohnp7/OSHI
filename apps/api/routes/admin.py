"""Administration API routes.

Endpoints:
- GET /api/v1/admin/health — detailed system health
- GET /api/v1/admin/version — version and build information
- GET /api/v1/admin/routes — list registered API routes

These endpoints require API key authentication and are intended for
operational monitoring and debugging (Part 10 /api/v1/admin/).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.core.auth import require_admin, require_api_key
from packages.core.config import get_settings
from packages.core.database import get_db
from packages.core.models import OfficialWarning, WarningVerificationEvent

from apps.api.schemas import (
    WarningVerificationOut,
    WarningVerificationRequest,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

__version__ = "0.1.0"


@router.get(
    "/health",
    response_model=dict[str, Any],
    summary="Admin health check",
    description="Detailed system health for operators.",
)
def admin_health(
    request: Request,
    current_user=Depends(require_api_key),
) -> dict[str, Any]:
    """Detailed system health for operators."""
    routes = []
    for route in request.app.routes:
        if isinstance(route, APIRoute):
            routes.append(
                {
                    "path": route.path,
                    "methods": sorted(list(route.methods)) if route.methods else [],
                    "name": route.name,
                }
            )
    return {
        "status": "ok",
        "service": get_settings().app_name,
        "env": get_settings().app_env,
        "version": __version__,
        "route_count": len(routes),
        "routes": routes,
    }


@router.get(
    "/version",
    response_model=dict[str, str],
    summary="Version information",
    description="Return version and build information.",
)
def admin_version(
    current_user=Depends(require_api_key),
) -> dict[str, str]:
    """Return version and build information."""
    return {
        "version": __version__,
        "service": get_settings().app_name,
    }


@router.get(
    "/routes",
    response_model=list[dict[str, Any]],
    summary="List API routes",
    description="List all registered API routes.",
)
def admin_routes(
    request: Request,
    current_user=Depends(require_api_key),
) -> list[dict[str, Any]]:
    """List all registered API routes."""
    out = []
    for route in request.app.routes:
        if isinstance(route, APIRoute):
            out.append(
                {
                    "path": route.path,
                    "methods": sorted(list(route.methods)) if route.methods else [],
                    "name": route.name,
                }
            )
    return sorted(out, key=lambda r: r["path"])


@router.post(
    "/warnings/{warning_id}/verify",
    response_model=WarningVerificationOut,
    status_code=status.HTTP_200_OK,
    summary="Verify an official warning",
    description="Verify an official warning (transition UNVERIFIED -> VERIFIED). "
    "Requires admin privileges. Records who verified and when (audit trail).",
)
def verify_warning(
    warning_id: UUID = Path(..., description="ID of the warning to verify"),
    request: WarningVerificationRequest | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
) -> WarningVerificationOut:
    """Verify an official warning (Part 3.5 UEFI authorization).

    Only superusers can transition a warning from UNVERIFIED to VERIFIED.
    The verifying user and timestamp are recorded for audit purposes.
    """
    warning = db.execute(
        select(OfficialWarning).where(OfficialWarning.id == warning_id)
    ).scalar_one_or_none()
    if warning is None:
        raise HTTPException(status_code=404, detail="Warning not found")

    if warning.verification_status == "VERIFIED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warning is already verified.",
        )

    warning.verification_status = "VERIFIED"
    warning.verified_by = current_user.id
    warning.verified_at = datetime.now(timezone.utc)
    warning.verification_notes = request.notes if request else None
    db.add(warning)

    # Append-only audit event for the verification transition.
    audit_event = WarningVerificationEvent(
        warning_id=warning.id,
        from_status="UNVERIFIED",
        to_status="VERIFIED",
        verified_by=current_user.id,
        verified_at=warning.verified_at,
        notes=request.notes if request else None,
        source_bulletin_url=warning.source_bulletin_url,
    )
    db.add(audit_event)
    db.commit()
    db.refresh(warning)

    return WarningVerificationOut(
        warning_id=warning.id,
        verification_status=warning.verification_status,
        verified_by=warning.verified_by,
        verified_at=warning.verified_at,
        notes=warning.verification_notes,
    )
