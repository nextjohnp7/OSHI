"""Crisis Intelligence and Early Warning API routes.

Endpoints (Part 10 API structure):

Crisis:
- GET /api/v1/crisis/events — list disaster events
- POST /api/v1/crisis/events — create a disaster event (preliminary)
- GET /api/v1/crisis/events/{id} — get a single event with reports/locations
- GET /api/v1/crisis/timeline — chronological event timeline
- GET /api/v1/crisis/verification — verification status summary

Early Warning:
- GET /api/v1/warnings/official — list active official warnings
- POST /api/v1/warnings/official — create an official warning
- POST /api/v1/warnings/translations — translate warning content
- GET /api/v1/warnings/preparedness — preparedness guidance

Safety (Part 8.4, Part 3.5 mandatory restrictions):
- Warnings are never independently invented; issuer and severity are
  preserved exactly as provided.
- Unverified reports are clearly labeled.
- No evacuation instructions are generated automatically.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.api.schemas import (
    CrisisEventCreateRequest,
    DisasterEventOut,
    EventLocationOut,
    EventReportOut,
    OfficialWarningOut,
    SituationReportOut,
    WarningTranslationOut,
    WarningTranslationRequest,
)
from packages.core.auth import require_api_key
from packages.core.database import get_db
from packages.core.models import (
    DisasterEvent,
    EventLocation,
    EventReport,
    GeographicRegion,
    OfficialWarning,
    SituationReport,
)

router = APIRouter(prefix="/api/v1/crisis", tags=["crisis"])
warnings_router = APIRouter(prefix="/api/v1/warnings", tags=["warnings"])


# ---------------------------------------------------------------------------
# Crisis endpoints
# ---------------------------------------------------------------------------


@router.get("/events", response_model=list[DisasterEventOut])
def list_events(
    event_type: str | None = Query(default=None),
    verification_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> list[DisasterEventOut]:
    """List disaster events, optionally filtered by type and verification status."""
    stmt = select(DisasterEvent)
    if event_type:
        stmt = stmt.where(DisasterEvent.event_type == event_type)
    if verification_status:
        stmt = stmt.where(DisasterEvent.verification_status == verification_status)
    stmt = stmt.order_by(DisasterEvent.created_at.desc()).limit(limit)
    events = db.execute(stmt).scalars().all()
    return [DisasterEventOut.model_validate(e) for e in events]


@router.post("/events", response_model=DisasterEventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    request: CrisisEventCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> DisasterEventOut:
    """Create a new disaster event (preliminary until verified)."""
    event = DisasterEvent(
        event_type=request.event_type,
        title=request.title,
        description=request.description,
        status=request.status,
        verification_status=request.verification_status,
        reported_impact=request.reported_impact,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return DisasterEventOut.model_validate(event)


@router.get("/events/{event_id}", response_model=DisasterEventOut)
def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> DisasterEventOut:
    """Get a single disaster event with its reports and locations."""
    event = db.execute(
        select(DisasterEvent).where(DisasterEvent.id == event_id)
    ).scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return DisasterEventOut.model_validate(event)


@router.get("/timeline", response_model=list[dict[str, Any]])
def get_timeline(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> list[dict[str, Any]]:
    """Chronological timeline of disaster events (Part 3.4.D)."""
    events = db.execute(
        select(DisasterEvent)
        .order_by(DisasterEvent.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "title": e.title,
            "status": e.status,
            "verification_status": e.verification_status,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.get("/verification", response_model=dict[str, int])
def verification_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> dict[str, int]:
    """Count of events grouped by verification status (Part 3.4.C)."""
    events = db.execute(select(DisasterEvent)).scalars().all()
    summary: dict[str, int] = {}
    for event in events:
        status = event.verification_status
        summary[status] = summary.get(status, 0) + 1
    return summary


# ---------------------------------------------------------------------------
# Early Warning endpoints
# ---------------------------------------------------------------------------


@warnings_router.get("/official", response_model=list[OfficialWarningOut])
def list_warnings(
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> list[OfficialWarningOut]:
    """List official hazard warnings (Part 3.5 UEWI).

    Warnings are never independently invented; issuer and severity are
    preserved exactly as issued.
    """
    stmt = select(OfficialWarning)
    if active_only:
        stmt = stmt.where(OfficialWarning.is_active == True)  # noqa: E712
    stmt = stmt.order_by(OfficialWarning.created_at.desc()).limit(limit)
    warnings = db.execute(stmt).scalars().all()
    return [OfficialWarningOut.model_validate(w) for w in warnings]


@warnings_router.post("/official", response_model=OfficialWarningOut, status_code=status.HTTP_201_CREATED)
def create_warning(
    issuer: str,
    warning_level: str,
    severity: str,
    event_id: str | None = Query(default=None),
    effective_time: str | None = Query(default=None),
    expiry_time: str | None = Query(default=None),
    affected_locations: str | None = Query(default=None),
    preparedness_guidance: str | None = Query(default=None),
    source_bulletin_url: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> OfficialWarningOut:
    """Create an official warning retrieved from an authorized source.

    Severity is preserved exactly as issued (Part 3.5). No evacuation
    instructions are generated.
    """
    parsed_event_id = None
    if event_id:
        try:
            parsed_event_id = UUID(event_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid event_id format")

    parsed_effective = None
    if effective_time:
        try:
            parsed_effective = datetime.fromisoformat(effective_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid effective_time format")

    parsed_expiry = None
    if expiry_time:
        try:
            parsed_expiry = datetime.fromisoformat(expiry_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiry_time format")

    warning = OfficialWarning(
        event_id=parsed_event_id,
        issuer=issuer,
        warning_level=warning_level,
        severity=severity,
        effective_time=parsed_effective,
        expiry_time=parsed_expiry,
        affected_locations=affected_locations,
        preparedness_guidance=preparedness_guidance,
        source_bulletin_url=source_bulletin_url,
        is_active=True,
    )
    db.add(warning)
    db.commit()
    db.refresh(warning)
    return OfficialWarningOut.model_validate(warning)


@warnings_router.post("/translations", response_model=WarningTranslationOut)
def translate_warning(
    translation_request: WarningTranslationRequest = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> WarningTranslationOut:
    """Translate warning content into accessible language (Part 3.5.G).

    Translation must never change the severity or meaning of an official
    warning. This is a placeholder that returns the original text with a
    timestamp; real machine translation should be wired behind this.
    """
    warning = db.execute(
        select(OfficialWarning).where(OfficialWarning.id == translation_request.warning_id)
    ).scalar_one_or_none()
    if warning is None:
        raise HTTPException(status_code=404, detail="Warning not found")

    original = warning.preparedness_guidance or warning.severity
    return WarningTranslationOut(
        warning_id=warning.id,
        target_language=translation_request.target_language,
        translated_text=original,
        original_text=original,
        translation_timestamp=datetime.now(timezone.utc),
    )


@warnings_router.get("/preparedness", response_model=list[dict[str, Any]])
def preparedness_guidance(
    db: Session = Depends(get_db),
    current_user=Depends(require_api_key),
) -> list[dict[str, Any]]:
    """Preparedness guidance from active official warnings (Part 3.5).

    Returns approved preparedness information only; no evacuation
    instructions are generated automatically.
    """
    warnings = db.execute(
        select(OfficialWarning).where(
            OfficialWarning.is_active == True,  # noqa: E712
            OfficialWarning.preparedness_guidance.isnot(None),
        )
    ).scalars().all()
    return [
        {
            "id": str(w.id),
            "issuer": w.issuer,
            "severity": w.severity,
            "guidance": w.preparedness_guidance,
            "source_bulletin_url": w.source_bulletin_url,
        }
        for w in warnings
    ]
