"""Unit tests for Crossref connector normalization (no network)."""

from datetime import datetime, timezone

from packages.connectors.scientific.crossref import (
    CrossrefConnector,
    _extract_authors,
    _parse_date,
    _strip_html,
)


FIXTURE_ITEM = {
    "DOI": "10.1000/example.2024.001",
    "title": ["Climate Change and Agriculture"],
    "author": [
        {"given": "Andrew", "family": "Sturman", "sequence": "first"},
        {"given": "Hervé", "family": "Quénol", "sequence": "additional"},
        {"family": "NoGivenName"},
    ],
    "published": {"date-parts": [[2023, 11, 21]]},
    "abstract": "<p>This chapter discusses how climate change affects agriculture.</p>",
    "URL": "https://doi.org/10.1000/example.2024.001",
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


def test_strip_html():
    assert _strip_html("<p>hello world</p>") == "hello world"
    assert _strip_html("<p>a</p> <p>b</p>") == "a b"
    assert _strip_html(None) is None
    assert _strip_html("") is None
    assert _strip_html("plain text") == "plain text"


def test_extract_authors():
    authors = _extract_authors(FIXTURE_ITEM["author"])
    assert authors == [
        {"name": "Andrew Sturman"},
        {"name": "Hervé Quénol"},
        {"name": "NoGivenName"},
    ]
    assert _extract_authors(None) == []


def test_parse_date():
    assert _parse_date([[2023, 11, 21]]) == datetime(
        2023, 11, 21, tzinfo=timezone.utc
    )
    assert _parse_date([[2023]]) == datetime(2023, 1, 1, tzinfo=timezone.utc)
    assert _parse_date(None) is None
    assert _parse_date([[]]) is None


def test_normalize_roundtrip():
    connector = CrossrefConnector()
    normalized = connector.normalize(FIXTURE_ITEM)
    assert normalized.source_name == "crossref"
    assert normalized.source_id == "10.1000/example.2024.001"
    assert normalized.title == "Climate Change and Agriculture"
    assert normalized.abstract == "This chapter discusses how climate change affects agriculture."
    assert normalized.authors == [
        {"name": "Andrew Sturman"},
        {"name": "Hervé Quénol"},
        {"name": "NoGivenName"},
    ]
    assert normalized.publication_date == datetime(2023, 11, 21, tzinfo=timezone.utc)
    assert normalized.source_url == "https://doi.org/10.1000/example.2024.001"
    assert normalized.license == "https://creativecommons.org/licenses/by/4.0/"
    assert normalized.content_hash is not None
    assert len(normalized.content_hash) == 64


def test_normalize_missing_fields():
    connector = CrossrefConnector()
    normalized = connector.normalize({"DOI": "10.1000/minimal"})
    assert normalized.source_id == "10.1000/minimal"
    assert normalized.title == ""
    assert normalized.abstract is None
    assert normalized.authors == []
    assert normalized.publication_date is None
    assert normalized.source_url is None
    assert normalized.license is None
