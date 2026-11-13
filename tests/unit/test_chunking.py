"""Unit tests for text chunking (no network, no ML)."""

import pytest

from packages.document_processing.chunking import chunk_text


def test_chunk_text_basic():
    text = "A" * 100 + " " + "B" * 100
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1
    assert chunks[0]["index"] == 0
    assert chunks[-1]["index"] == len(chunks) - 1


def test_chunk_text_overlap():
    text = "x" * 200
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    # Consecutive chunks should overlap by 10 chars
    for i in range(len(chunks) - 1):
        end = chunks[i]["text"][-10:]
        start = chunks[i + 1]["text"][:10]
        assert end == start


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_single_chunk():
    text = "short text"
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0]["text"] == text


def test_chunk_text_invalid():
    with pytest.raises(ValueError):
        chunk_text("text", chunk_size=0)
    with pytest.raises(ValueError):
        chunk_text("text", chunk_size=10, overlap=10)
    with pytest.raises(ValueError):
        chunk_text("text", chunk_size=10, overlap=11)
