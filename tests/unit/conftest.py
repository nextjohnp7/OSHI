"""Pytest configuration for unit tests.

Provides a fresh in-memory-per-test-file SQLite database so auth state (and
other DB state) does not leak between tests. The default app settings use
``oshi_dev.db`` (a file on disk), which would persist across tests.
"""

import os
import tempfile
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from apps.api.main import create_app
from packages.core.config import get_settings
from packages.core.database import Base


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a TestClient backed by a fresh SQLite database file.

    A new temporary database file is created for each test function, and the
    ``get_settings`` lru_cache is cleared so the app picks up the new URL.
    """
    # Clear the cached settings so the next call reads fresh env.
    get_settings.cache_clear()

    # Use a temp file database (not :memory:, because each connection to
    # :memory: is a separate empty database).
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

    # Create all tables in the temp database.
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    engine.dispose()

    # Clear again after setting env so the app reads the new URL.
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)
    yield client

    # Cleanup.
    try:
        os.unlink(db_path)
    except OSError:
        pass
    get_settings.cache_clear()
    os.environ.pop("DATABASE_URL", None)
