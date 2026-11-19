"""Vector retrieval using cosine similarity.

Embeddings are stored as BLOBs in SQLite. Retrieval fetches all chunks with
embeddings and computes cosine similarity in Python. This is portable across
SQLite (development) and PostgreSQL (production, where pgvector can replace
this in-memory computation later).
"""

from __future__ import annotations

from typing import Any, Optional

from packages.document_processing.embeddings import (
    blob_to_embedding,
    cosine_similarity,
)


def rank_chunks_by_similarity(
    query_vector: list[float],
    chunks: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rank document chunks by cosine similarity to a query vector.

    Each chunk dict must contain an ``embedding`` key holding either a list of
    floats or bytes (BLOB) that can be deserialized via ``blob_to_embedding``.

    Returns the top_k chunks sorted by similarity (descending), each augmented
    with a ``similarity`` key.
    """
    scored: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        embedding_raw = chunk.get("embedding")
        if embedding_raw is None:
            continue
        if isinstance(embedding_raw, (bytes, bytearray)):
            vector = blob_to_embedding(embedding_raw)
        else:
            vector = list(embedding_raw)
        similarity = cosine_similarity(query_vector, vector)
        scored.append((similarity, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for similarity, chunk in scored[:top_k]:
        result = dict(chunk)
        result["similarity"] = float(similarity)
        results.append(result)
    return results


class PgVectorRetriever:
    """pgvector-backed retriever for PostgreSQL production deployments.

    Requires the ``pgvector`` Python package and a PostgreSQL database with the
    ``pgvector`` extension enabled and an ``embedding_vector vector(384)``
    column on ``document_chunks``. Falls back gracefully if unavailable.
    """

    def __init__(self, session: Any, table: str = "document_chunks") -> None:
        self.session = session
        self.table = table

    @classmethod
    def is_available(cls, session: Any) -> bool:
        """Return True if pgvector extension + embedding_vector column exist."""
        from sqlalchemy import text

        try:
            result = session.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector' LIMIT 1")
            ).scalar_one_or_none()
            if not result:
                return False
            result = session.execute(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :table AND column_name = 'embedding_vector' "
                    "LIMIT 1"
                ),
                {"table": cls._table_name(session)},
            ).scalar_one_or_none()
            return bool(result)
        except Exception:  # pragma: no cover - pgvector not available
            return False

    @staticmethod
    def _table_name(session: Any) -> str:
        """Best-effort table name from the session bind."""
        try:
            bind = session.get_bind()
            if bind is not None:
                return str(bind.dialect.name)
        except Exception:
            pass
        return "document_chunks"

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Search chunks using pgvector cosine distance (<=> operator).

        Returns results sorted by similarity (descending), each augmented with
        a ``similarity`` key (1 - cosine distance).
        """
        from sqlalchemy import text

        # pgvector stores embeddings as Vector type; cosine distance <=> returns
        # smaller values for more similar vectors. Similarity = 1 - distance.
        sql = f"""
            SELECT id, document_id, chunk_index, text, embedding_vector,
                   1 - (embedding_vector <=> :query) AS similarity
            FROM {self.table}
            WHERE embedding_vector IS NOT NULL
            {"AND document_id = :document_id" if document_id else ""}
            ORDER BY embedding_vector <=> :query
            LIMIT :top_k
        """
        params: dict[str, Any] = {
            "query": str(query_vector),
            "top_k": top_k,
        }
        if document_id:
            params["document_id"] = document_id

        result = self.session.execute(text(sql), params)
        rows = []
        for row in result:
            rows.append(
                {
                    "id": str(row.id),
                    "document_id": str(row.document_id),
                    "chunk_index": row.chunk_index,
                    "text": row.text,
                    "similarity": float(row.similarity),
                }
            )
        return rows

    def search_sync(
        self,
        query_vector: list[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Synchronous wrapper around :meth:`search`."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Already inside an event loop (e.g. FastAPI async endpoint).
                return asyncio.run_coroutine_threadsafe(
                    self.search(query_vector, top_k=top_k, document_id=document_id),
                    loop,
                ).result()
        except RuntimeError:
            pass
        return asyncio.run(
            self.search(query_vector, top_k=top_k, document_id=document_id)
        )
