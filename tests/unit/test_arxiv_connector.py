"""Unit tests for arXiv connector (no network, normalizes mock Atom entries)."""

import pytest

from packages.connectors.scientific.arxiv import ArxivConnector


MOCK_ENTRY = {
    "id": "http://arxiv.org/abs/2301.00001v1",
    "title": "Climate Change and Crop Yields: A Meta-Analysis",
    "summary": "Rising temperatures reduce maize yields by 15% in tropical regions.",
    "published": "2023-01-15T00:00:00Z",
    "updated": "2023-02-01T00:00:00Z",
    "authors": [{"name": "Alice Smith"}, {"name": "Bob Jones"}],
    "links": [
        {"href": "http://arxiv.org/abs/2301.00001v1", "rel": "alternate", "type": "text/html"},
        {"href": "http://arxiv.org/pdf/2301.00001v1", "rel": "related", "type": "application/pdf"},
    ],
}


def test_arxiv_normalize_basic():
    connector = ArxivConnector()
    normalized = connector.normalize(MOCK_ENTRY)

    assert normalized.source_name == "arxiv"
    assert normalized.source_id == "2301.00001"
    assert normalized.title == "Climate Change and Crop Yields: A Meta-Analysis"
    assert normalized.abstract == "Rising temperatures reduce maize yields by 15% in tropical regions."
    assert len(normalized.authors) == 2
    assert normalized.authors[0]["name"] == "Alice Smith"
    assert normalized.authors[1]["name"] == "Bob Jones"
    assert normalized.publication_date is not None
    assert normalized.source_url == "http://arxiv.org/abs/2301.00001v1"
    assert normalized.content_hash is not None


def test_arxiv_source_id_strips_version():
    entry = dict(MOCK_ENTRY)
    entry["id"] = "http://arxiv.org/abs/2301.00001v3"
    connector = ArxivConnector()
    normalized = connector.normalize(entry)
    assert normalized.source_id == "2301.00001"


def test_arxiv_empty_authors():
    entry = dict(MOCK_ENTRY)
    entry["authors"] = []
    connector = ArxivConnector()
    normalized = connector.normalize(entry)
    assert normalized.authors == []


def test_arxiv_content_hash_deterministic():
    connector = ArxivConnector()
    n1 = connector.normalize(MOCK_ENTRY)
    n2 = connector.normalize(MOCK_ENTRY)
    assert n1.content_hash == n2.content_hash


def test_arxiv_content_hash_changes_with_title():
    connector = ArxivConnector()
    entry1 = dict(MOCK_ENTRY)
    entry2 = dict(MOCK_ENTRY)
    entry2["title"] = "Different Title"
    n1 = connector.normalize(entry1)
    n2 = connector.normalize(entry2)
    assert n1.content_hash != n2.content_hash
