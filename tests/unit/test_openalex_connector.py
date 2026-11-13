"""Unit tests for OpenAlex connector normalization (no network)."""

import pytest

from packages.connectors.scientific.openalex import (
    OpenAlexConnector,
    _reconstruct_abstract,
    _extract_authors,
    _work_id,
)


FIXTURE_WORK = {
    "id": "https://openalex.org/W2741809807",
    "display_name": "Climate Change: A Test Study",
    "publication_date": "2024-03-10",
    "authorships": [
        {"author": {"display_name": "Alice Researcher"}},
        {"author": {"display_name": "Bob Scientist"}},
        {"author": {}},
    ],
    "primary_location": {"landing_page_url": "https://example.org/paper"},
    "license": "cc-by",
    "abstract_inverted_index": {"climate": [0], "change": [1], "study": [2]},
}


def test_reconstruct_abstract():
    assert _reconstruct_abstract(FIXTURE_WORK["abstract_inverted_index"]) == (
        "climate change study"
    )
    assert _reconstruct_abstract(None) is None
    assert _reconstruct_abstract({}) == ""


def test_extract_authors():
    authors = _extract_authors(FIXTURE_WORK["authorships"])
    assert authors == [{"name": "Alice Researcher"}, {"name": "Bob Scientist"}]
    assert _extract_authors(None) == []


def test_work_id():
    assert _work_id(FIXTURE_WORK) == "W2741809807"
    assert _work_id({"id": "https://openalex.org/W999/"}) == "W999"


def test_normalize_roundtrip():
    connector = OpenAlexConnector()
    normalized = connector.normalize(FIXTURE_WORK)
    assert normalized.source_name == "openalex"
    assert normalized.source_id == "W2741809807"
    assert normalized.title == "Climate Change: A Test Study"
    assert normalized.abstract == "climate change study"
    assert normalized.authors == [{"name": "Alice Researcher"}, {"name": "Bob Scientist"}]
    assert normalized.publication_date is not None
    assert normalized.publication_date.year == 2024
    assert normalized.source_url == "https://example.org/paper"
    assert normalized.license == "cc-by"
    assert normalized.content_hash is not None
    assert len(normalized.content_hash) == 64


def test_normalize_missing_fields():
    connector = OpenAlexConnector()
    normalized = connector.normalize({"id": "https://openalex.org/W000000001"})
    assert normalized.source_id == "W000000001"
    assert normalized.title == ""
    assert normalized.abstract is None
    assert normalized.authors == []
