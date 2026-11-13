"""Vector retrieval using cosine similarity.

Embeddings are stored as BLOBs in SQLite. Retrieval fetches all chunks with
embeddings and computes cosine similarity in Python. This is portable across
SQLite (development) and PostgreSQL (production, where pgvector can replace
this in-memory computation later).
"""

from __future__ import annotations

from typing import Any

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
