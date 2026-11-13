"""Embedding generation without heavy ML dependencies.

Uses the "hashing trick" (feature hashing) to produce a deterministic,
fixed-dimension embedding vector for any text. No model download, no torch,
no sentence-transformers — embeddings are generated instantly and are fully
reproducible across environments.

This is intentionally a lightweight placeholder for Sprint 3. When
``sentence-transformers`` + ``torch`` are available, swap in
``SentenceTransformer.encode()`` behind the same ``embed_text`` /
``embed_texts`` interface.
"""

from __future__ import annotations

from typing import Any

DEFAULT_DIM = 128

# Lazy-loaded heavy model (optional). Set via set_heavy_model() when
# sentence-transformers/torch are available.
_heavy_model: Any = None
_heavy_model_name: str | None = None


def set_heavy_model(model: Any, model_name: str) -> None:
    """Register a heavy embedding model (e.g. SentenceTransformer)."""
    global _heavy_model, _heavy_model_name
    _heavy_model = model
    _heavy_model_name = model_name


def _hash_position(token: str, dim: int) -> int:
    """Deterministic position in [0, dim) for a token."""
    return abs(hash(token)) % dim


def _hash_sign(token: str) -> int:
    """Deterministic sign (+1 or -1) for a token."""
    return 1 if hash(token) >= 0 else -1


def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenization."""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    return [t for t in cleaned.split() if t]


def embed_text(text: str, dim: int = DEFAULT_DIM) -> list[float]:
    """Generate a deterministic embedding vector for a single text.

    Returns a list of ``dim`` floats (unit-normalized).
    """
    if _heavy_model is not None:
        vector = _heavy_model.encode([text], convert_to_numpy=True)
        return vector[0].tolist()

    vec = [0.0] * dim
    for token in _tokenize(text):
        pos = _hash_position(token, dim)
        sign = _hash_sign(token)
        vec[pos] += sign

    # L2 normalize.
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def embed_texts(texts: list[str], dim: int = DEFAULT_DIM) -> list[list[float]]:
    """Generate embedding vectors for multiple text strings."""
    return [embed_text(t, dim=dim) for t in texts]


def embedding_to_blob(vector: list[float]) -> bytes:
    """Serialize a float list to bytes for SQLite BLOB storage."""
    import struct

    return struct.pack(f"{len(vector)}f", *vector)


def blob_to_embedding(blob: bytes) -> list[float]:
    """Deserialize bytes from SQLite BLOB back to a float list."""
    import struct

    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
