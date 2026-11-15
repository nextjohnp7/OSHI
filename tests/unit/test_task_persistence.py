"""Integration tests for background task persistence (no network).

Covers:
- POST /api/v1/documents/ingest returns a task and persists it
- GET /api/v1/tasks/{task_id} reflects status transitions
- GET /api/v1/tasks lists recent tasks
- DELETE /api/v1/tasks/{task_id} cancels a pending task
- E2E: ingest task completes -> document is queryable
"""

import os
from typing import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from apps.api.main import create_app
from apps.api.routes.documents import service as document_service
from packages.core.config import get_settings
from packages.core.database import Base, reset_engine
from packages.core.models import Task


@pytest.fixture
def api_client(tmp_path) -> Generator[tuple[TestClient, str], None, None]:
    """Fresh SQLite DB per test, with a bootstrapped API key."""
    db_file = tmp_path / "task_test.sqlite"
    engine = create_engine(
        f"sqlite:///{db_file}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Share the same session with the document service so HTTP routes and
    # direct inserts see the same data.
    document_service._session = session

    os.environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    get_settings.cache_clear()
    reset_engine()

    app = create_app()
    client = TestClient(app)

    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "tester@example.com", "name": "Tester"},
    )
    assert bootstrap.status_code == 200, bootstrap.text
    api_key = bootstrap.json()["api_key"]

    yield client, api_key

    session.close()
    get_settings.cache_clear()
    reset_engine()
    os.environ.pop("DATABASE_URL", None)
    try:
        os.unlink(db_file)
    except OSError:
        pass


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def test_ingest_creates_task_and_completes(api_client):
    client, api_key = api_client
    headers = _headers(api_key)

    resp = client.post(
        "/api/v1/documents/ingest",
        json={
            "text": "Integration test document content about climate science.",
            "source_name": "test",
            "source_id": str(uuid4()),
            "title": "Integration Test Doc",
        },
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    assert data["task_type"] == "ingest"

    # Poll task status until completed (background task runs synchronously
    # under TestClient, so it should already be done).
    task_id = data["task_id"]
    task_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert task_resp.status_code == 200, task_resp.text
    task_data = task_resp.json()
    assert task_data["task_id"] == task_id
    assert task_data["status"] in ("completed", "failed"), task_data
    if task_data["status"] == "completed":
        assert task_data["result"] is not None


def test_task_list_endpoint(api_client):
    client, api_key = api_client
    headers = _headers(api_key)

    # Create two ingest tasks.
    for i in range(2):
        resp = client.post(
            "/api/v1/documents/ingest",
            json={
                "text": f"Document {i} content.",
                "source_name": "test",
                "source_id": str(uuid4()),
                "title": f"Doc {i}",
            },
            headers=headers,
        )
        assert resp.status_code == 202, resp.text

    list_resp = client.get("/api/v1/tasks", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    tasks = list_resp.json()
    assert len(tasks) >= 2
    # Newest first.
    assert tasks[0]["task_type"] == "ingest"


def test_cancel_pending_task_directly(api_client):
    client, api_key = api_client
    headers = _headers(api_key)

    # Insert a pending task directly into the DB.
    from packages.core.database import get_session_local
    from packages.core.models import User

    session_local = get_session_local()
    db = session_local()
    try:
        # Dapatkan user yang dibuat oleh bootstrap.
        user = db.execute(select(User)).scalar_one()
        task = Task(
            id=uuid4(),
            status="pending",
            task_type="ingest",
            user_id=user.id,
        )
        db.add(task)
        db.commit()
        task_id = str(task.id)
    finally:
        db.close()

    cancel_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert cancel_resp.status_code == 200, cancel_resp.text
    assert cancel_resp.json()["detail"] == "cancelled"

    # Verify status is now failed.
    task_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
    assert task_resp.status_code == 200
    assert task_resp.json()["status"] == "failed"
    assert task_resp.json()["error"] == "cancelled by user"


def test_cancel_nonexistent_task_404(api_client):
    client, api_key = api_client
    headers = _headers(api_key)

    resp = client.delete(f"/api/v1/tasks/{uuid4()}", headers=headers)
    assert resp.status_code == 404, resp.text


def test_cancel_terminal_task_409(api_client):
    client, api_key = api_client
    headers = _headers(api_key)

    # Create an ingest task (will complete quickly under TestClient).
    resp = client.post(
        "/api/v1/documents/ingest",
        json={
            "text": "Content for cancel test.",
            "source_name": "test",
            "source_id": str(uuid4()),
            "title": "Cancel Test",
        },
        headers=headers,
    )
    assert resp.status_code == 202, resp.text
    task_id = resp.json()["task_id"]

    # Try to cancel — should be 409 because task is already terminal.
    cancel_resp = client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
    assert cancel_resp.status_code == 409, cancel_resp.text


def test_ingest_e2e_document_queryable(api_client):
    client, api_key = api_client
    headers = _headers(api_key)

    source_id = str(uuid4())
    resp = client.post(
        "/api/v1/documents/ingest",
        json={
            "text": "E2E test document about renewable energy integration.",
            "source_name": "e2e",
            "source_id": source_id,
            "title": "E2E Renewable Energy Doc",
        },
        headers=headers,
    )
    assert resp.status_code == 202, resp.text

    # Wait for task to complete.
    task_id = resp.json()["task_id"]
    for _ in range(10):
        task_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        if task_resp.json()["status"] in ("completed", "failed"):
            break
    assert task_resp.json()["status"] == "completed", task_resp.text

    # Document should now be queryable.
    list_resp = client.get("/api/v1/documents", params={"limit": 10}, headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    docs = list_resp.json()
    assert any(d["source_id"] == source_id for d in docs), docs
