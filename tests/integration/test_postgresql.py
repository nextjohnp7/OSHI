"""Integration tests untuk PostgreSQL + pgvector produksi.

Tes ini memerlukan PostgreSQL dengan ekstensie pgvector yang berjalan (via Docker
atau lingkungan produksi). Secara default di-skip jika tidak tersedia.

Variabel lingkungan:
- DATABASE_URL: URL koneksi PostgreSQL (default: postgresql://oshi:oshi@localhost:5432/oshi_test)
"""

import os
import shutil
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from apps.api.main import create_app
from packages.core.config import get_settings

DATABASE_URL = os.environ.get(
    "OSHI_TEST_DATABASE_URL", "postgresql://oshi:oshi@localhost:5432/oshi_test"
)

pgvector_available = shutil.which("psql") is not None


@pytest.fixture
def pg_client() -> Generator[TestClient, None, None]:
    """TestClient terhubung ke PostgreSQL + pgvector (skip jika tidak tersedia)."""
    if not pgvector_available:
        pytest.skip(
            "psql tidak ditemukan — PostgreSQL/pgvector tidak tersedia secara lokal"
        )

    engine = create_engine(DATABASE_URL)
    # Pastikan ekstensie pgvector tersedia.
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    os.environ["DATABASE_URL"] = DATABASE_URL
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    bootstrap = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "tester@example.com", "name": "Tester"},
    )
    assert bootstrap.status_code == 200, bootstrap.text
    api_key = bootstrap.json()["api_key"]

    yield client, api_key

    get_settings.cache_clear()
    os.environ.pop("DATABASE_URL", None)


@pytest.mark.integration
def test_health_postgres(pg_client):
    """Health check harus melaporkan database connected pada PostgreSQL."""
    client, api_key = pg_client
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = client.get("/health", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["database"] == "connected", data


@pytest.mark.integration
def test_pgvector_extension(pg_client):
    """Ekstensie pgvector harus dapat dibuat di database uji."""
    client, api_key = pg_client
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = client.get("/health", headers=headers)
    assert resp.status_code == 200, resp.text
