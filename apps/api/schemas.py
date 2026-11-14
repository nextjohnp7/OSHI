"""API request/response schemas for OSHI foundation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class PublicationOut(BaseModel):
    id: UUID
    source_name: str
    source_id: str
    title: str
    abstract: str | None = None
    authors: list[dict[str, Any]] | None = None
    publication_date: datetime | None = None
    source_url: str | None = None
    license: str | None = None
    content_hash: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    q: str
    limit: int = 10
    source: str | None = None


class SearchResponse(BaseModel):
    query: str
    source: str
    count: int
    results: list[PublicationOut]


class HealthOut(BaseModel):
    status: str
    service: str
    env: str
    database: str
    database_error: str | None = None


# --- Document schemas (Sprint 3) ---


class DocumentOut(BaseModel):
    id: UUID
    source_name: str
    source_id: str
    title: str
    source_url: str | None = None
    content_hash: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentChunkOut(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    text: str
    similarity: float | None = None
    document_title: str | None = None
    document_source_name: str | None = None
    document_source_id: str | None = None
    document_source_url: str | None = None

    model_config = {"from_attributes": True}


class DocumentIngestRequest(BaseModel):
    text: str
    source_name: str
    source_id: str
    title: str
    source_url: str | None = None
    chunk_size: int = 500
    overlap: int = 50


class DocumentSearchRequest(BaseModel):
    q: str
    top_k: int = 5
    source_name: str | None = None


class DocumentSearchResponse(BaseModel):
    query: str
    count: int
    results: list[DocumentChunkOut]


# --- Research Agent schemas (Sprint 4) ---


class ResearchRunRequest(BaseModel):
    query: str
    topic: str | None = None
    crisis_context: str | None = None
    max_publications: int = 10
    max_evidence_per_publication: int = 3


class ResearchPublicationOut(BaseModel):
    id: str
    title: str
    authors: list[str]
    abstract: str
    source: str
    url: str
    published_date: str | None = None
    relevance_score: float


class ResearchEvidenceOut(BaseModel):
    publication_id: str
    publication_title: str
    quote: str
    relevance_to_query: float


class ResearchRunResponse(BaseModel):
    run_id: str
    status: str
    query: str
    topic: str
    crisis_context: str | None = None
    publications: list[ResearchPublicationOut]
    evidence: list[ResearchEvidenceOut]
    report: str | None = None
    error: str | None = None


# --- Auth schemas ---


class APIKeyCreateRequest(BaseModel):
    name: str
    organization_id: str | None = None
    expires_in_days: int | None = None


class APIKeyOut(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    user_id: UUID
    organization_id: UUID | None = None
    is_active: bool
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(BaseModel):
    api_key: str  # plaintext shown only once
    key_prefix: str
    id: UUID
    name: str
    created_at: datetime


class APIKeyRevokeRequest(BaseModel):
    key_id: UUID


# --- Crisis Intelligence schemas (Part 3.4 GCIN, Part 10 API) ---


class EventReportOut(BaseModel):
    id: UUID
    event_id: UUID
    source_name: str
    source_url: str | None = None
    publication_time: datetime | None = None
    observation_time: datetime | None = None
    event_type: str | None = None
    reported_impact: str | None = None
    geographic_scope: str | None = None
    verification_status: str
    retrieved_at: datetime

    model_config = {"from_attributes": True}


class EventLocationOut(BaseModel):
    id: UUID
    event_id: UUID
    region_id: UUID | None = None
    latitude: float | None = None
    longitude: float | None = None
    description: str | None = None

    model_config = {"from_attributes": True}


class DisasterEventOut(BaseModel):
    id: UUID
    event_type: str
    title: str
    description: str | None = None
    status: str
    verification_status: str
    reported_impact: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    reports: list[EventReportOut] = []
    locations: list[EventLocationOut] = []

    model_config = {"from_attributes": True}


class CrisisEventCreateRequest(BaseModel):
    event_type: str
    title: str
    description: str | None = None
    status: str = "preliminary"
    verification_status: str = "UNVERIFIED"
    reported_impact: str | None = None


class OfficialWarningOut(BaseModel):
    id: UUID
    event_id: UUID | None = None
    issuer: str
    warning_level: str
    severity: str
    effective_time: datetime | None = None
    expiry_time: datetime | None = None
    affected_locations: str | None = None
    preparedness_guidance: str | None = None
    source_bulletin_url: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class SituationReportOut(BaseModel):
    id: UUID
    event_id: UUID
    title: str
    summary: str
    geographic_scope: str | None = None
    confirmed_information: str | None = None
    unverified_reports: str | None = None
    conflicting_information: str | None = None
    known_impact: str | None = None
    information_gaps: str | None = None
    last_update_time: datetime

    model_config = {"from_attributes": True}


# --- Early Warning schemas (Part 3.5 UEWI) ---


class WarningTranslationRequest(BaseModel):
    warning_id: UUID
    target_language: str


class WarningTranslationOut(BaseModel):
    warning_id: UUID
    target_language: str
    translated_text: str
    original_text: str
    translation_timestamp: datetime

    model_config = {"from_attributes": True}


# --- Background task schemas ---


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime


class TaskStatusOut(BaseModel):
    task_id: str
    status: str
    result: Any = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}




