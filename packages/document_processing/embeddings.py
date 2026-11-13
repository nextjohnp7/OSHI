"""Embedding generation with optional sentence-transformers backend.

Tries to load ``sentence-transformers/all-MiniLM-L6-v2`` lazily on first use
(384-dim, ~80 MB download). Falls back to the deterministic hashing trick if
the model is not installed or cannot be loaded — no network, no torch required.

The public interface (``embed_text`` / ``embed_texts`` / ``embedding_to_blob`` /
``blob_to_embedding`` / ``cosine_similarity``) is identical regardless of which
backend is active, so the rest of the codebase does not need to change.
"""

from __future__ import annotations

from typing import Any

DEFAULT_DIM = 128
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Lazy-loaded heavy model.
_heavy_model: Any = None
_heavy_model_name: str | None = None
_heavy_model_dim: int | None = None


def set_heavy_model(model: Any, model_name: str, dim: int | None = None) -> None:
    """Register a heavy embedding model (e.g. SentenceTransformer)."""
    global _heavy_model, _heavy_model_name, _heavy_model_dim
    _heavy_model = model
    _heavy_model_name = model_name
    _heavy_model_dim = dim


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


def embed_text(text: str, dim: int = DEFAULT_DIM, model_name: str = DEFAULT_MODEL) -> list[float]:
    """Generate an embedding vector for a single text.

    Uses sentence-transformers when available; falls back to the hashing trick.
    Returns a list of floats (unit-normalized).
    """
    model = _load_sentence_transformers(model_name)
    if model is not None:
        vector = model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vector[0].tolist()

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

    model = _load_sentence_transformers(model_name)
    if model is not None:
        vectors = model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return [v.tolist() for v in vectors]

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
