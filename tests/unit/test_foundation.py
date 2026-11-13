"""Unit tests for OSHI foundation."""

from fastapi.testclient import TestClient

from apps.api.main import create_app


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "oshi"
    assert data["database"] == "connected"


def test_health_endpoint_shape():
    client = TestClient(create_app())
    response = client.get("/health")
    data = response.json()
    for key in ("status", "service", "env", "database", "database_error"):
        assert key in data
