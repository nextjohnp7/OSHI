"""Unit tests for vector retrieval (no network, no ML)."""

from packages.document_processing.embeddings import embedding_to_blob
from packages.document_processing.retrieval import rank_chunks_by_similarity


def test_rank_chunks_by_similarity():
    query = [1.0, 0.0, 0.0]
    chunks = [
        {
            "id": "c1",
            "text": "similar chunk",
            "embedding": embedding_to_blob([1.0, 0.0, 0.0]),
        },
        {
            "id": "c2",
            "text": "orthogonal chunk",
            "embedding": embedding_to_blob([0.0, 1.0, 0.0]),
        },
        {
            "id": "c3",
            "text": "opposite chunk",
            "embedding": embedding_to_blob([-1.0, 0.0, 0.0]),
        },
    ]
    results = rank_chunks_by_similarity(query, chunks, top_k=3)
    assert len(results) == 3
    assert results[0]["id"] == "c1"  # most similar
    assert results[0]["similarity"] == 1.0
    assert results[1]["id"] == "c2"  # similarity 0
    assert results[2]["id"] == "c3"  # similarity -1


def test_rank_chunks_top_k():
    query = [1.0, 0.0]
    chunks = [
        {
            "id": f"c{i}",
            "text": f"chunk {i}",
            "embedding": embedding_to_blob([1.0, 0.0]),
        }
        for i in range(10)
    ]
    results = rank_chunks_by_similarity(query, chunks, top_k=3)
    assert len(results) == 3


def test_rank_chunks_no_embedding():
    query = [1.0, 0.0]
    chunks = [
        {"id": "c1", "text": "no embedding", "embedding": None},
        {
            "id": "c2",
            "text": "has embedding",
            "embedding": embedding_to_blob([1.0, 0.0]),
        },
    ]
    results = rank_chunks_by_similarity(query, chunks, top_k=5)
    assert len(results) == 1
    assert results[0]["id"] == "c2"
