"""Unit tests for PublicationService using an in-memory SQLite database (no network)."""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from packages.connectors.scientific.schemas import NormalizedPublication
from packages.core.database import Base
from packages.core.models import Publication


class FakeConnector:
    """Connector tiruan yang mengembalikan data fixture tanpa jaringan."""

    def __init__(self, works):
        self.works = works

    async def search(self, query, limit=10):
        return self.works[:limit]

    def normalize(self, work):
        return NormalizedPublication(
            source_name="openalex",
            source_id=work["source_id"],
            title=work["title"],
            abstract=work.get("abstract"),
            authors=work.get("authors"),
            publication_date=work.get("publication_date"),
            source_url=work.get("source_url"),
            license=work.get("license"),
        )


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    yield db
    db.close()


@pytest.fixture
def svc(session):
    from apps.api.service import PublicationService

    return PublicationService(session=session)


FIXTURE_WORKS = [
    {
        "source_name": "openalex",
        "source_id": "W111",
        "title": "Climate Change Study One",
        "abstract": "A study about climate change.",
        "authors": [{"name": "Alice"}],
        "publication_date": datetime(2024, 1, 15, tzinfo=timezone.utc),
        "source_url": "https://example.org/W111",
        "license": "cc-by",
    },
    {
        "source_name": "openalex",
        "source_id": "W222",
        "title": "Quantum Computing Basics",
        "abstract": "Introduction to quantum computing.",
        "authors": [{"name": "Bob"}],
        "publication_date": datetime(2023, 6, 1, tzinfo=timezone.utc),
        "source_url": "https://example.org/W222",
        "license": None,
    },
]


@pytest.mark.asyncio
async def test_search_and_store_inserts(svc, session):
    connector = FakeConnector(FIXTURE_WORKS)
    svc.connector = connector
    stored = await svc.search_and_store("climate", limit=2)

    assert len(stored) == 2
    ids = {r.source_id for r in stored}
    assert ids == {"W111", "W222"}

    rows = session.execute(select(Publication)).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_search_and_store_upsert_dedupes(svc, session):
    connector = FakeConnector(FIXTURE_WORKS)
    svc.connector = connector
    await svc.search_and_store("climate", limit=2)
    # Run again with updated title for W111
    updated = [
        {**FIXTURE_WORKS[0], "title": "Climate Change Study One (Revised)"},
        FIXTURE_WORKS[1],
    ]
    connector2 = FakeConnector(updated)
    svc.connector = connector2
    stored = await svc.search_and_store("climate", limit=2)

    assert len(stored) == 2
    rows = session.execute(select(Publication)).scalars().all()
    assert len(rows) == 2
    w111 = [r for r in rows if r.source_id == "W111"][0]
    assert w111.title == "Climate Change Study One (Revised)"


def test_search_stored_filters(svc, session):
    # Insert directly
    session.add_all(
        [
            Publication(**{**w, "content_hash": f"hash-{w['source_id']}"})
            for w in FIXTURE_WORKS
        ]
    )
    session.commit()

    results = svc.search_stored("climate", limit=10)
    assert len(results) == 1
    assert results[0].title == "Climate Change Study One"

    results = svc.search_stored(None, limit=10)
    assert len(results) == 2
