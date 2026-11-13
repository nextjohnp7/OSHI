"""Unit tests for PubMed / Europe PMC connector (no network, normalizes mock results)."""

import pytest

from packages.connectors.scientific.pubmed import PubMedConnector


MOCK_RESULT = {
    "id": "37000001",
    "pmid": "37000001",
    "title": "Climate Change Impacts on Global Health",
    "authorString": "Smith, Alice; Jones, Bob; Lee, Carol",
    "abstractText": "This study examines the health impacts of climate change in vulnerable populations.",
    "pubDate": "2023 Mar 15",
    "doi": "10.1234/example.2023.001",
    "pmcid": "PMC1000001",
    "isOpenAccess": "Y",
    "inEPMC": "Y",
    "hasPDF": "Y",
    "citedByCount": 5,
}


def test_pubmed_normalize_basic():
    connector = PubMedConnector()
    normalized = connector.normalize(MOCK_RESULT)

    assert normalized.source_name == "pubmed"
    assert normalized.source_id == "37000001"
    assert normalized.title == "Climate Change Impacts on Global Health"
    assert normalized.abstract == "This study examines the health impacts of climate change in vulnerable populations."
    assert len(normalized.authors) == 3
    assert normalized.authors[0]["name"] == "Smith, Alice"
    assert normalized.publication_date is not None
    assert normalized.source_url == "10.1234/example.2023.001"
    assert normalized.license is None
    assert normalized.content_hash is not None


def test_pubmed_no_doi_falls_back_to_article_url():
    result = dict(MOCK_RESULT)
    result.pop("doi")
    connector = PubMedConnector()
    normalized = connector.normalize(result)
    assert normalized.source_url == "https://europepmc.org/article/37000001"


def test_pubmed_empty_authors():
    result = dict(MOCK_RESULT)
    result["authorString"] = ""
    connector = PubMedConnector()
    normalized = connector.normalize(result)
    assert normalized.authors == []


def test_pubmed_content_hash_deterministic():
    connector = PubMedConnector()
    n1 = connector.normalize(MOCK_RESULT)
    n2 = connector.normalize(MOCK_RESULT)
    assert n1.content_hash == n2.content_hash


def test_pubmed_date_parsing():
    connector = PubMedConnector()
    result = dict(MOCK_RESULT)
    result["pubDate"] = "2023-03-15"
    normalized = connector.normalize(result)
    assert normalized.publication_date is not None
    assert normalized.publication_date.year == 2023
    assert normalized.publication_date.month == 3
    assert normalized.publication_date.day == 15
