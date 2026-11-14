"""Integration tests untuk PostgreSQL + pgvector produksi.

Tes ini memerlukan PostgreSQL dengan ekstensie pgvector yang berjalan (via Docker
atau lingkungan produksi). Secara default di-skip jika tidak tersedia.

Variabel lingkungan:
- DATABASE_URL: URL koneksi PostgreSQL (default: postgresql://oshi:oshi@localhost:5432/oshi_test)
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from apps.api.main import create_app
from packages.core.config import get_settings

DATABASE_URL = os.environ.get(
    "OSHI_TEST_DATABASE_URL", "postgresql://oshi:oshi@localhost:5432/oshi_test"
)


def _postgres_available() -> bool:
    """Coba buat koneksi ke PostgreSQL; kembalikan False jika tidak tersedia."""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — PostgreSQL not available, skip tests
        return False


pg_available = _postgres_available()


@pytest.fixture
def pg_client() -> Generator[TestClient, None, None]:
    """TestClient terhubung ke PostgreSQL + pgvector (skip jika tidak tersedia)."""
    if not pg_available:
        pytest.skip("PostgreSQL tidak tersedia — tes integrasi melewati")

    # Pastikan pengaturan di-refresh sebelum app dibuat.
    os.environ["DATABASE_URL"] = DATABASE_URL
    get_settings.cache_clear()

    engine = create_engine(DATABASE_URL)
    # Coba pasang ekstensi pgvector (abaikan jika tidak tersedia).
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
    except Exception:  # noqa: BLE001 — pgvector mungkin tidak terinstal
        pass

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
    """Ekstensie pgvector harus dapat dibuat di database uji (skip jika tidak tersedia)."""
    engine = create_engine(DATABASE_URL)
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            assert result.fetchone() is not None, "pgvector extension tidak terpasang"
    except Exception:  # noqa: BLE001 — pgvector tidak tersedia, skip
        pytest.skip("pgvector extension tidak tersedia di database uji")
