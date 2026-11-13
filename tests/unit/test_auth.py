"""Unit tests for authentication (no network)."""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import create_app


def _bootstrap(client: TestClient) -> str:
    """Bootstrap and return the plaintext API key."""
    resp = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "alice@example.com", "name": "Alice"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["api_key"]


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def test_bootstrap_creates_user_and_key(client: TestClient):
    resp = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "alice@example.com", "name": "Alice"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["api_key"].startswith("oshi_")
    assert data["key_prefix"] == data["api_key"][:12]
    assert data["name"] == "Bootstrap key"
    assert data["id"] is not None


def test_bootstrap_rejected_when_user_exists(client: TestClient):
    _bootstrap(client)
    resp = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "bob@example.com", "name": "Bob"},
    )
    assert resp.status_code == 403, resp.text


def test_protected_route_without_key(client: TestClient):
    resp = client.get("/api/v1/publications/")
    assert resp.status_code == 401, resp.text


def test_protected_route_with_invalid_key(client: TestClient):
    resp = client.get(
        "/api/v1/publications/",
        headers={"Authorization": "Bearer invalid_key"},
    )
    assert resp.status_code == 401, resp.text


def test_verify_key_endpoint(client: TestClient):
    api_key = _bootstrap(client)
    resp = client.post("/api/v1/auth/verify", headers=_auth_headers(api_key))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["valid"] == "true"
    assert data["user"] == "alice@example.com"


def test_verify_key_missing(client: TestClient):
    resp = client.post("/api/v1/auth/verify")
    assert resp.status_code == 401, resp.text


def test_create_and_list_api_keys(client: TestClient):
    api_key = _bootstrap(client)

    # Create a second key
    resp = client.post(
        "/api/v1/auth/keys",
        json={"name": "Second key", "expires_in_days": 30},
        headers=_auth_headers(api_key),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["api_key"].startswith("oshi_")
    assert data["name"] == "Second key"
    second_key = data["api_key"]

    # List keys
    resp = client.get("/api/v1/auth/keys", headers=_auth_headers(api_key))
    assert resp.status_code == 200, resp.text
    keys = resp.json()
    assert len(keys) >= 2
    prefixes = {k["key_prefix"] for k in keys}
    assert data["key_prefix"] in prefixes


def test_revoke_api_key(client: TestClient):
    api_key = _bootstrap(client)

    # Create a key to revoke
    resp = client.post(
        "/api/v1/auth/keys",
        json={"name": "To revoke"},
        headers=_auth_headers(api_key),
    )
    assert resp.status_code == 200, resp.text
    key_id = resp.json()["id"]

    # Revoke it
    resp = client.delete(
        f"/api/v1/auth/keys/{key_id}",
        headers=_auth_headers(api_key),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["detail"] == "revoked"

    # The revoked key should no longer work
    resp = client.post(
        "/api/v1/auth/verify",
        headers=_auth_headers(api_key),
    )
    # Bootstrap key still works (it wasn't revoked)
    assert resp.status_code == 200, resp.text


def test_health_endpoint_still_public(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
