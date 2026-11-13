"""Business logic for scientific publications.

Responsibilities:
- fetch + normalize publications from an external source (OpenAlex),
- upsert records into the database keyed by (source_name, source_id),
- search stored publications by title/abstract.

Keeping persistence separate from the connector makes it possible to swap the
source or add a repository layer without changing the API routes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, select

from packages.connectors.scientific.openalex import OpenAlexConnector
from packages.connectors.scientific.schemas import NormalizedPublication
from packages.core.database import Base, get_session_local
from packages.core.models import Publication


class PublicationService:
    def __init__(
        self,
        connector: OpenAlexConnector | None = None,
        session: Any = None,
    ) -> None:
        self.connector = connector or OpenAlexConnector()
        self._session = session

    def _get_db(self):
        if self._session is not None:
            return self._session
        session_local = get_session_local()
        return session_local()

    def _to_model(self, normalized: NormalizedPublication) -> dict[str, Any]:
        return {
            "source_name": normalized.source_name,
            "source_id": normalized.source_id,
            "title": normalized.title,
            "abstract": normalized.abstract,
            "authors": normalized.authors,
            "publication_date": normalized.publication_date,
            "source_url": normalized.source_url,
            "content_hash": normalized.content_hash,
            "license": normalized.license,
        }

    def _upsert(self, db, normalized: NormalizedPublication) -> Publication:
        existing = db.execute(
            select(Publication).where(
                Publication.source_name == normalized.source_name,
                Publication.source_id == normalized.source_id,
            )
        ).scalar_one_or_none()

        fields = self._to_model(normalized)
        if existing is None:
            record = Publication(**fields)
            db.add(record)
            db.flush()
            return record

        for key, value in fields.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        db.add(existing)
        return existing

    async def search_and_store(self, query: str, limit: int = 10) -> list[Publication]:
        works = await self.connector.search(query, limit=limit)
        db = self._get_db()
        own_session = self._session is None
        try:
            stored: list[Publication] = []
            for work in works:
                normalized = self.connector.normalize(work)
                record = self._upsert(db, normalized)
                stored.append(record)
            db.commit()
            for record in stored:
                db.refresh(record)
            return stored
        except Exception:
            db.rollback()
            raise
        finally:
            if own_session:
                db.close()

    def search_stored(
        self, q: str | None, limit: int = 10
    ) -> list[Publication]:
        db = self._get_db()
        own_session = self._session is None
        try:
            stmt = select(Publication).limit(limit)
            if q:
                like = f"%{q}%"
                stmt = stmt.where(
                    or_(
                        Publication.title.ilike(like),
                        Publication.abstract.ilike(like),
                    )
                )
            return list(db.execute(stmt).scalars())
        finally:
            if own_session:
                db.close()

