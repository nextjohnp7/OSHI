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
    """Optional pgvector-backed retriever for PostgreSQL production deployments.

    Requires the ``pgvector`` Python package and a PostgreSQL database with the
    ``pgvector`` extension enabled. Falls back gracefully if unavailable.
    """

    def __init__(self, session: Any, table: str = "document_chunks") -> None:
        self.session = session
        self.table = table

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
        try:
            from pgvector.sqlalchemy import Vector  # type: ignore
        except ImportError:  # pragma: no cover - pgvector not installed
            return []

        from sqlalchemy import text

        # pgvector stores embeddings as Vector type; cosine distance <=> returns
        # smaller values for more similar vectors. Similarity = 1 - distance.
        sql = f"""
            SELECT id, document_id, chunk_index, text, embedding,
                   1 - (embedding <=> :query) AS similarity
            FROM {self.table}
            WHERE embedding IS NOT NULL
            {"AND document_id = :document_id" if document_id else ""}
            ORDER BY embedding <=> :query
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

