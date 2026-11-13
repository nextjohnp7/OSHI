"""Unit tests for DocumentService using in-memory SQLite (no network)."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from packages.document_processing.models import Base, Document, DocumentChunk
from packages.document_processing.service import DocumentService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    yield db
    db.close()


@pytest.fixture
def svc(session):
    return DocumentService(session=session)


SAMPLE_TEXT = (
    "The quick brown fox jumps over the lazy dog. " * 20
    + "Climate change is a pressing global issue. " * 20
    + "Quantum computing represents a paradigm shift in computation. " * 20
)


def test_ingest_creates_document_and_chunks(svc, session):
    document = svc.ingest(
        text=SAMPLE_TEXT,
        source_name="test",
        source_id="doc-001",
        title="Test Document",
    )

    assert document.id is not None
    assert document.source_name == "test"
    assert document.source_id == "doc-001"
    assert document.title == "Test Document"
    assert document.content_hash is not None

    # Verify chunks were created
    rows = session.execute(select(DocumentChunk)).scalars().all()
    assert len(rows) > 0
    assert all(r.document_id == document.id for r in rows)
    assert all(r.embedding is not None for r in rows)


def test_ingest_dedupes_by_source(svc, session):
    svc.ingest(
        text="First version of the document.",
        source_name="test",
        source_id="doc-002",
        title="First Title",
    )
    svc.ingest(
        text="Second version of the document with more content here.",
        source_name="test",
        source_id="doc-002",
        title="Second Title",
    )

    rows = session.execute(select(Document)).scalars().all()
    assert len(rows) == 1  # no duplicate document
    assert rows[0].title == "Second Title"  # updated

    chunk_rows = session.execute(select(DocumentChunk)).scalars().all()
    # All chunks should belong to the single document
    assert all(r.document_id == rows[0].id for r in chunk_rows)


def test_semantic_search_returns_chunks(svc, session):
    svc.ingest(
        text="Climate change affects agriculture and food security worldwide.",
        source_name="test",
        source_id="doc-climate",
        title="Climate Report",
    )
    svc.ingest(
        text="Quantum computing uses qubits for computation.",
        source_name="test",
        source_id="doc-quantum",
        title="Quantum Report",
    )

    results = svc.semantic_search(query="climate change agriculture", top_k=5)
    assert len(results) >= 1
    # The climate document should rank higher than quantum
    assert any("climate" in r["text"].lower() for r in results)
    assert all("similarity" in r for r in results)
    assert all(r["document_title"] for r in results)


def test_semantic_search_empty(svc, session):
    results = svc.semantic_search(query="anything", top_k=5)
    assert results == []


def test_list_documents(svc, session):
    svc.ingest(
        text="Document one content.",
        source_name="test",
        source_id="doc-001",
        title="First Doc",
    )
    svc.ingest(
        text="Document two content.",
        source_name="test",
        source_id="doc-002",
        title="Second Doc",
    )

    docs = svc.list_documents(limit=10)
    assert len(docs) == 2
    titles = {d.title for d in docs}
    assert titles == {"First Doc", "Second Doc"}


def test_get_document(svc, session):
    document = svc.ingest(
        text="Content for retrieval test.",
        source_name="test",
        source_id="doc-get",
        title="Get Me",
    )

    found = svc.get_document(str(document.id))
    assert found is not None
    assert found.title == "Get Me"
    assert found.source_id == "doc-get"

    not_found = svc.get_document("00000000-0000-0000-0000-000000000000")
    assert not_found is None


def test_get_document_chunks(svc, session):
    document = svc.ingest(
        text="Chunk one. " * 200 + "Chunk two. " * 200 + "Chunk three. " * 200,
        source_name="test",
        source_id="doc-chunks",
        title="Chunked Doc",
    )

    chunks = svc.get_document_chunks(str(document.id))
    assert len(chunks) >= 3
    assert chunks[0].chunk_index == 0
    assert chunks[0].document_id == document.id
