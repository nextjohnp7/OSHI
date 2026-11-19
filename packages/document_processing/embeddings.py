"""Embedding generation with a required sentence-transformers backend.

Loads ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim, ~80 MB) lazily on
first use. Unlike the previous implementation, there is no silent fallback to
the hashing trick: if the model cannot be loaded (missing dependency, no
network at build time, etc.) ``embed_text`` / ``embed_texts`` raise
``EmbeddingBackendUnavailable`` with a clear message. This guarantees the
production backend is explicit and consistent between ingest and query.

A deterministic hashing-trick backend remains available *only* when
``OSHI_EMBEDDING_BACKEND=hashing`` is set explicitly (dev/offline smoke tests
only). It is never the default.

The public interface (``embed_text`` / ``embed_texts`` /
``embedding_to_blob`` / ``blob_to_embedding`` / ``cosine_similarity`` /
``get_embedding_backend_info``) is stable regardless of backend.
"""

from __future__ import annotations

import os
from typing import Any

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIM = 384

# Lazy-loaded heavy model.
_heavy_model: Any = None
_heavy_model_name: str | None = None
_heavy_model_dim: int | None = None


class EmbeddingBackendUnavailable(RuntimeError):
    """Raised when the embedding backend cannot be used."""


def set_heavy_model(model: Any, model_name: str, dim: int | None = None) -> None:
    """Register a heavy embedding model (e.g. SentenceTransformer)."""
    global _heavy_model, _heavy_model_name, _heavy_model_dim
    _heavy_model = model
    _heavy_model_name = model_name
    _heavy_model_dim = dim


def get_embedding_backend_info() -> dict[str, Any]:
    """Return the active embedding backend identity (model name + dimension).

    Callers can compare this between ingest and query to guarantee the same
    model is used on both sides.
    """
    return {
        "backend": "sentence-transformers"
        if _heavy_model is not None
        else (
            "hashing"
            if os.environ.get("OSHI_EMBEDDING_BACKEND") == "hashing"
            else "unavailable"
        ),
        "model_name": _heavy_model_name or DEFAULT_MODEL,
        "dimension": _heavy_model_dim or DEFAULT_DIM,
    }


def _require_backend() -> None:
    """Ensure an embedding backend is available; raise otherwise."""
    if _heavy_model is not None:
        return
    if os.environ.get("OSHI_EMBEDDING_BACKEND") == "hashing":
        return
    raise EmbeddingBackendUnavailable(
        "sentence-transformers model is not available and no explicit "
        "backend was selected. Install sentence-transformers (it is in the "
        "'prod' dependency group) or set OSHI_EMBEDDING_BACKEND=hashing for "
        "dev/offline smoke tests only."
    )


def _load_sentence_transformers(model_name: str = DEFAULT_MODEL) -> Any:
    """Load sentence-transformers model, returning None if unavailable."""
    global _heavy_model, _heavy_model_name, _heavy_model_dim
    if _heavy_model is not None and _heavy_model_name == model_name:
        return _heavy_model
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model = SentenceTransformer(model_name)
        _heavy_model = model
        _heavy_model_name = model_name
        # SentenceTransformer embeddings are normalized when
        # normalize_embeddings=True; get dim from the model.
        try:
            _heavy_model_dim = model.get_sentence_embedding_dimension()
        except Exception:  # pragma: no cover - defensive
            _heavy_model_dim = None
        return model
    except Exception:  # pragma: no cover - fallback path
        _heavy_model = None
        _heavy_model_name = None
        _heavy_model_dim = None
        return None


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


def _hash_embed(text: str, dim: int) -> list[float]:
    """Deterministic hashing-trick embedding (fallback backend)."""
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


def embed_text(
    text: str, dim: int = DEFAULT_DIM, model_name: str = DEFAULT_MODEL
) -> list[float]:
    """Generate an embedding vector for a single text.

    Uses sentence-transformers when available; raises
    ``EmbeddingBackendUnavailable`` otherwise (no silent hashing fallback).
    Returns a list of floats (unit-normalized).
    """
    _require_backend()
    model = _load_sentence_transformers(model_name)
    if model is not None:
        vector = model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vector[0].tolist()

    # Explicit hashing backend (dev only).
    return _hash_embed(text, dim=dim)


def embed_texts(
    texts: list[str],
    dim: int = DEFAULT_DIM,
    model_name: str = DEFAULT_MODEL,
) -> list[list[float]]:
    """Generate embedding vectors for multiple text strings.

    Uses batched encoding when sentence-transformers is active.
    """
    if not texts:
        return []

    _require_backend()
    model = _load_sentence_transformers(model_name)
    if model is not None:
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [v.tolist() for v in vectors]

    # Explicit hashing backend (dev only).
    return [_hash_embed(t, dim=dim) for t in texts]


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
