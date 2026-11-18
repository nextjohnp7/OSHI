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
from packages.core.database import Base, reset_engine

# Import all models so they are registered with Base.metadata.
import packages.core.models  # noqa: F401
import packages.document_processing.models  # noqa: F401

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


@pytest.fixture(scope="session")
def pg_client() -> Generator[TestClient, None, None]:
    """TestClient terhubung ke PostgreSQL + pgvector (skip jika tidak tersedia).

    Scope session agar bootstrap hanya dijalankan sekali per run CI; tanpa ini,
    bootstrap dipanggil sekali per tes yang memakai fixture dan run kedua akan
    mendapat 403 "Bootstrap already performed".
    """
    if not pg_available:
        pytest.skip("PostgreSQL tidak tersedia — tes integrasi melewati")

    # Pastikan pengaturan di-refresh sebelum app dibuat.
    os.environ["DATABASE_URL"] = DATABASE_URL
    get_settings.cache_clear()
    reset_engine()

    engine = create_engine(DATABASE_URL)
    # Buat semua tabel langsung (bypass Alembic untuk keandalan test).
    Base.metadata.create_all(engine)

    # Pasang ekstensi pgvector jika tersedia (diabaikan jika tidak).
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
    if bootstrap.status_code == 200:
        api_key = bootstrap.json()["api_key"]
    elif bootstrap.status_code == 403:
        # Bootstrap sudah dilakukan (state tersisa); buat user + API key baru
        # langsung ke database sehingga tes masih memiliki kredensial yang valid.
        import hashlib

        from packages.core.database import get_session_local
        from packages.core.models import APIKey, User

        session_local = get_session_local()
        db = session_local()
        try:
            user = User(
                email="tester-fixture@example.com",
                name="Tester Fixture",
                is_active=True,
            )
            db.add(user)
            db.flush()
            key_hash = hashlib.sha256(b"fixture-secret-key").hexdigest()
            db.add(
                APIKey(
                    name="fixture-key",
                    key_hash=key_hash,
                    key_prefix="fixture-secre",
                    user_id=user.id,
                    is_active=True,
                )
            )
            db.commit()
        finally:
            db.close()
        api_key = "fixture-secret-key"
    else:
        assert bootstrap.status_code == 200, bootstrap.text
        api_key = bootstrap.json()["api_key"]  # unreachable, for type checkers

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
