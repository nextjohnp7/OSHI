"""Document processing service.

Responsibilities:
- import + store a document,
- chunk its text,
- generate embeddings for chunks,
- persist chunks to the database,
- semantic (vector) search across stored chunks.

Persistence is separated from the embedding/retrieval logic so the vector
search strategy can be swapped (in-memory cosine now, pgvector later) without
changing the API routes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from packages.document_processing.chunking import chunk_text
from packages.document_processing.embeddings import (
    embed_text,
    embed_texts,
    embedding_to_blob,
)
from packages.document_processing.models import Document, DocumentChunk
from packages.document_processing.retrieval import (
    PgVectorRetriever,
    rank_chunks_by_similarity,
)
from packages.core.database import get_session_local


class DocumentService:
    def __init__(self, session: Any = None) -> None:
        self._session = session

    def _get_db(self):
        if self._session is not None:
            return self._session
        session_local = get_session_local()
        return session_local()

    def _content_hash(self, text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()

    def ingest(
        self,
        text: str,
        source_name: str,
        source_id: str,
        title: str,
        source_url: str | None = None,
        chunk_size: int = 500,
        overlap: int = 50,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> Document:
        """Import a document: hash, deduplicate, chunk, embed, store.

        If a document with the same (source_name, source_id, organization_id)
        already exists, its chunks are replaced (delete + re-insert).

        Documents are scoped to a user/organization for multi-tenant isolation.
        ``organization_id`` is the tenant boundary; ``user_id`` is the actor.
        """
        content_hash = self._content_hash(text)
        db = self._get_db()
        own_session = self._session is None
        try:
            # Row lock on existing document prevents two concurrent ingest
            # tasks for the same source from overwriting each other. nowait
            # fails fast instead of blocking; the IntegrityError path below
            # handles the concurrent-insert case.
            existing = db.execute(
                select(Document).where(
                    Document.source_name == source_name,
                    Document.source_id == source_id,
                    Document.organization_id == organization_id,
                ).with_for_update(nowait=True)
            ).scalar_one_or_none()

            if existing is not None:
                document = existing
                document.title = title
                document.source_url = source_url
                document.content_hash = content_hash
                document.updated_at = datetime.now(timezone.utc)
                # Jangan overwrite user_id / organization_id pada dokumen yang
                # sudah ada — provenance pembuat asli harus tetap tercatat.
                # organization_id sudah sama karena dedup mencakupnya.
                # Remove old chunks.
                db.execute(
                    __import__("sqlalchemy")
                    .delete(DocumentChunk)
                    .where(DocumentChunk.document_id == document.id)
                )
                db.flush()
            else:
                document = Document(
                    source_name=source_name,
                    source_id=source_id,
                    title=title,
                    source_url=source_url,
                    content_hash=content_hash,
                    user_id=user_id,
                    organization_id=organization_id,
                )
                db.add(document)
                try:
                    db.flush()
                except IntegrityError:
                    # Concurrent transaction inserted the same source first.
                    # Roll back and fall through to the update path using the
                    # document created by the other transaction.
                    db.rollback()
                    existing = db.execute(
                        select(Document).where(
                            Document.source_name == source_name,
                            Document.source_id == source_id,
                            Document.organization_id == organization_id,
                        )
                    ).scalar_one_or_none()
                    if existing is None:
                        raise
                    document = existing
                    document.title = title
                    document.source_url = source_url
                    document.content_hash = content_hash
                    document.updated_at = datetime.now(timezone.utc)
                    db.execute(
                        __import__("sqlalchemy")
                        .delete(DocumentChunk)
                        .where(DocumentChunk.document_id == document.id)
                    )
                    db.flush()

            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
            if chunks:
                chunk_texts = [c["text"] for c in chunks]
                vectors = embed_texts(chunk_texts)
                for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
                    blob = embedding_to_blob(vector)
                    # pgvector column expects text input format '{v1,v2,...}';
                    # LargeBinary `embedding` keeps raw bytes for dev/SQLite.
                    embedding_vector_str = (
                        "{" + ",".join(f"{v:.8f}" for v in vector) + "}"
                    )
                    db_chunk = DocumentChunk(
                        document_id=document.id,
                        chunk_index=i,
                        text=chunk["text"],
                        embedding=blob,
                        embedding_vector=embedding_vector_str,
                    )
                    db.add(db_chunk)

            db.commit()
            db.refresh(document)
            return document
        except Exception:
            db.rollback()
            raise
        finally:
            if own_session:
                db.close()

    def semantic_search(
        self,
        query: str,
        top_k: int = 5,
        source_name: str | None = None,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search across stored document chunks.

        Returns chunks ranked by cosine similarity to the query, augmented with
        document metadata (title, source_name, source_id, source_url).

        Optionally scoped to a specific user/organization for multi-tenant
        isolation. ``organization_id`` is the tenant boundary.
        """
        db = self._get_db()
        own_session = self._session is None
        try:
            stmt = select(DocumentChunk).join(Document)
            if source_name is not None:
                stmt = stmt.where(Document.source_name == source_name)
            if organization_id is not None:
                stmt = stmt.where(Document.organization_id == organization_id)
            elif user_id is not None:
                stmt = stmt.where(Document.user_id == user_id)
            rows = list(db.execute(stmt).scalars())

            if not rows:
                return []

            query_vector = embed_text(query)

            # pgvector path: PostgreSQL-side cosine distance when the extension
            # + embedding_vector column are available (production).
            if PgVectorRetriever.is_available(db):
                retriever = PgVectorRetriever(db)
                ranked = retriever.search_sync(query_vector, top_k=top_k)
                # Augment with document metadata from the ORM rows.
                doc_by_id = {str(r.id): r for r in rows}
                for r in ranked:
                    doc = doc_by_id.get(r["document_id"])
                    if doc is not None:
                        r["document_title"] = doc.title
                        r["document_source_name"] = doc.source_name
                        r["document_source_id"] = doc.source_id
                        r["document_source_url"] = doc.source_url
                return ranked

            # In-memory cosine path (dev / SQLite).
            chunks: list[dict[str, Any]] = []
            for row in rows:
                document = row.document  # type: ignore[attr-defined]
                chunks.append(
                    {
                        "id": str(row.id),
                        "document_id": str(row.document_id),
                        "chunk_index": row.chunk_index,
                        "text": row.text,
                        "embedding": row.embedding,
                        "document_title": document.title,
                        "document_source_name": document.source_name,
                        "document_source_id": document.source_id,
                        "document_source_url": document.source_url,
                    }
                )

            ranked = rank_chunks_by_similarity(query_vector, chunks, top_k=top_k)
            return ranked
        finally:
            if own_session:
                db.close()

    def list_documents(
        self,
        limit: int = 20,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> list[Document]:
        """List imported documents.

        Optionally scoped to a specific user/organization for multi-tenant
        isolation. ``organization_id`` is the tenant boundary.
        """
        db = self._get_db()
        own_session = self._session is None
        try:
            stmt = select(Document).order_by(Document.created_at.desc()).limit(limit)
            if organization_id is not None:
                stmt = stmt.where(Document.organization_id == organization_id)
            elif user_id is not None:
                stmt = stmt.where(Document.user_id == user_id)
            return list(db.execute(stmt).scalars())
        finally:
            if own_session:
                db.close()

    def get_document(
        self,
        document_id: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> Document | None:
        """Get a single document by its internal UUID.

        Optionally scoped to a specific user/organization for multi-tenant
        isolation. ``organization_id`` is the tenant boundary.
        """
        db = self._get_db()
        own_session = self._session is None
        try:
            stmt = select(Document).where(Document.id == uuid.UUID(document_id))
            if organization_id is not None:
                stmt = stmt.where(Document.organization_id == organization_id)
            elif user_id is not None:
                stmt = stmt.where(Document.user_id == user_id)
            return db.execute(stmt).scalar_one_or_none()
        finally:
            if own_session:
                db.close()

    def get_document_chunks(
        self,
        document_id: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> list[DocumentChunk]:
        """Get all chunks of a document, ordered by chunk_index.

        Optionally scoped to a specific user/organization for multi-tenant
        isolation. ``organization_id`` is the tenant boundary.
        """
        from uuid import UUID

        from sqlalchemy import select

        db = self._get_db()
        own_session = self._session is None
        try:
            stmt = (
                select(DocumentChunk)
                .join(Document)
                .where(DocumentChunk.document_id == UUID(document_id))
                .order_by(DocumentChunk.chunk_index)
            )
            if organization_id is not None:
                stmt = stmt.where(Document.organization_id == organization_id)
            elif user_id is not None:
                stmt = stmt.where(Document.user_id == user_id)
            return list(db.execute(stmt).scalars())
        finally:
            if own_session:
                db.close()
