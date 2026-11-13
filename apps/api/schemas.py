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



