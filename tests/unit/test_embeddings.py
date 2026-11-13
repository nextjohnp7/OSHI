"""Unit tests for deterministic embeddings (no network, no ML)."""

from packages.document_processing.embeddings import (
    DEFAULT_DIM,
    blob_to_embedding,
    cosine_similarity,
    embed_text,
    embed_texts,
    embedding_to_blob,
)


def test_embed_text_dimension():
    vector = embed_text("hello world")
    assert len(vector) > 0
    # Same text should always produce the same dimension
    vector2 = embed_text("hello world")
    assert len(vector2) == len(vector)


def test_embed_text_dimension_consistent_across_calls():
    # Dimension must be stable regardless of backend
    v1 = embed_text("dimension check")
    v2 = embed_text("another dimension check")
    assert len(v1) == len(v2)


def test_embed_text_deterministic():
    v1 = embed_text("same text")
    v2 = embed_text("same text")
    assert v1 == v2


def test_embed_text_different_texts():
    v1 = embed_text("text one")
    v2 = embed_text("text two")
    assert v1 != v2


def test_embed_text_empty():
    vector = embed_text("")
    assert len(vector) == DEFAULT_DIM
    assert all(v == 0.0 for v in vector)


def test_embed_text_unit_normalized():
    vector = embed_text("some text for normalization check")
    norm = sum(v * v for v in vector) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_embed_texts_multiple():
    vectors = embed_texts(["one", "two", "three"])
    assert len(vectors) == 3
    assert all(len(v) == DEFAULT_DIM for v in vectors)


def test_embed_texts_empty():
    vectors = embed_texts([])
    assert vectors == []


def test_embedding_blob_roundtrip():
    vector = [0.1, -0.2, 0.3, 0.0, 0.5]
    blob = embedding_to_blob(vector)
    restored = blob_to_embedding(blob)
    assert len(restored) == len(vector)
    for a, b in zip(restored, vector):
        assert abs(a - b) < 1e-5


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - 0.0) < 1e-6


def test_cosine_similarity_opposite():
    v1 = [1.0, 0.0, 0.0]
    v2 = [-1.0, 0.0, 0.0]
    assert abs(cosine_similarity(v1, v2) - (-1.0)) < 1e-6


def test_cosine_similarity_zero_vector():
    v1 = [0.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 0.0
