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
