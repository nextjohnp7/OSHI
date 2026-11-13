"""Shared schemas for scientific publication connectors."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, HttpUrl


class NormalizedPublication(BaseModel):
    source_name: str
    source_id: str
    title: str
    abstract: str | None = None
    authors: list[dict[str, Any]] | None = None
    publication_date: datetime | None = None
    source_url: str | None = None
    license: str | None = None
    content_hash: str | None = None
