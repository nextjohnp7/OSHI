"""Text chunking utilities.

Simple character-based chunking with overlap. Suitable for the Sprint 3
foundation; more sophisticated strategies (sentence-aware, semantic) can be
added later without changing the storage layer.
"""

from typing import Any


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[dict[str, Any]]:
    """Split text into overlapping chunks.

    Returns a list of dicts with ``index`` and ``text`` keys. ``index`` is the
    zero-based chunk position within the document.

    Args:
        text: The source text to chunk.
        chunk_size: Maximum characters per chunk.
        overlap: Number of characters to overlap between consecutive chunks.

    Raises:
        ValueError: If chunk_size <= 0 or overlap >= chunk_size.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    if not text or not text.strip():
        return []

    chunks: list[dict[str, Any]] = []
    start = 0
    index = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_text_value = text[start:end]
        chunks.append({"index": index, "text": chunk_text_value})
        index += 1

        if end >= text_len:
            break

        start = end - overlap

    return chunks
