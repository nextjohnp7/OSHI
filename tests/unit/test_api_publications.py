"""Integration tests for publication API routes (no network; connector tiruan)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.api.main import create_app
from apps.api.routes.publications import service
from packages.connectors.scientific.schemas import NormalizedPublication
from packages.core.database import Base
from packages.core.models import Publication


class FakeConnector:
    async def search(self, query, limit=10):
        return [
            {
                "id": "https://openalex.org/W1",
                "display_name": "Test Paper",
                "publication_date": "2024-01-01",
                "authorships": [{"author": {"display_name": "A Researcher"}}],
                "primary_location": {"landing_page_url": "https://example.org/W1"},
                "license": None,
                "abstract_inverted_index": {"test": [0]},
            }
        ][:limit]

    def normalize(self, work):
        return NormalizedPublication(
            source_name="openalex",
            source_id=work["id"].rsplit("/", 1)[-1],
            title=work["display_name"],
            abstract="test abstract",
            authors=[{"name": "A Researcher"}],
            publication_date=None,
            source_url=work["primary_location"]["landing_page_url"],
            license=work.get("license"),
        )


@pytest.fixture
def api_client(tmp_path):
    db_file = tmp_path / "test_api.sqlite"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = Session(engine)
    service._session = session
    service.connectors["openalex"] = FakeConnector()

    # Point the app at the same temp database so HTTP routes share state.
    import os
    from packages.core.config import get_settings

    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    get_settings.cache_clear()

    client = TestClient(create_app())

    # Bootstrap a user + API key so protected routes can be called.
    bootstrap_resp = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "tester@example.com", "name": "Tester"},
    )
    assert bootstrap_resp.status_code == 200, bootstrap_resp.text
    api_key = bootstrap_resp.json()["api_key"]

    yield client, api_key

    session.close()
    get_settings.cache_clear()
    os.environ.pop("DATABASE_URL", None)
    try:
        os.unlink(db_file)
    except OSError:
        pass


def test_search_endpoint_returns_stored_records(api_client):
    client, api_key = api_client
    headers = {"Authorization": f"Bearer {api_key}"}
    response = client.post(
        "/api/v1/publications/search",
        json={"q": "climate", "limit": 5},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["query"] == "climate"
    assert data["source"] == "openalex"
    assert data["count"] == 1
    record = data["results"][0]
    assert record["title"] == "Test Paper"
    assert record["source_name"] == "openalex"
    assert record["source_id"] == "W1"
    assert record["source_url"] == "https://example.org/W1"
    assert record["abstract"] == "test abstract"


def test_list_endpoint_returns_stored(api_client):
    client, api_key = api_client
    headers = {"Authorization": f"Bearer {api_key}"}
    # Insert directly into the injected session
    session = service._session
    session.add(
        Publication(
            source_name="openalex",
            source_id="W999",
            title="Already Stored Paper",
            abstract="stored abstract",
            authors=[{"name": "Stored Author"}],
            content_hash="hash-stored",
        )
    )
    session.commit()

    response = client.get(
        "/api/v1/publications?q=stored",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source"] == "local"
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Already Stored Paper"


class FakeCrossrefConnector:
    async def search(self, query, limit=10):
        return [
            {
                "DOI": "10.1000/crossref.2024.002",
                "title": ["Crossref Test Paper"],
                "author": [{"given": "C", "family": "Researcher"}],
                "published": {"date-parts": [[2024, 2, 1]]},
                "abstract": "<p>Crossref abstract here.</p>",
                "URL": "https://doi.org/10.1000/crossref.2024.002",
                "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
            }
        ][:limit]

    def normalize(self, item):
        return NormalizedPublication(
            source_name="crossref",
            source_id=item["DOI"],
            title=item["title"][0],
            abstract="Crossref abstract here.",
            authors=[{"name": "C Researcher"}],
            publication_date=None,
            source_url=item["URL"],
            license="https://creativecommons.org/licenses/by/4.0/",
        )


def test_search_endpoint_crossref_source(api_client):
    client, api_key = api_client
    headers = {"Authorization": f"Bearer {api_key}"}
    service.connectors["crossref"] = FakeCrossrefConnector()
    response = client.post(
        "/api/v1/publications/search",
        json={"q": "climate", "limit": 5, "source": "crossref"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["query"] == "climate"
    assert data["source"] == "crossref"
    assert data["count"] == 1
    record = data["results"][0]
    assert record["title"] == "Crossref Test Paper"
    assert record["source_name"] == "crossref"
    assert record["source_id"] == "10.1000/crossref.2024.002"
    assert record["source_url"] == "https://doi.org/10.1000/crossref.2024.002"
    assert record["abstract"] == "Crossref abstract here."
    assert record["license"] == "https://creativecommons.org/licenses/by/4.0/"

