"""Unit tests for Crisis Intelligence and Early Warning API routes (no network)."""

from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import create_app


def _bootstrap(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "crisis@example.com", "name": "Crisis Tester"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["api_key"]


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def test_create_and_list_event(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    resp = client.post(
        "/api/v1/crisis/events",
        json={
            "event_type": "flood",
            "title": "Banji Jakarta",
            "description": "Banjir di beberapa wilayah",
            "verification_status": "UNVERIFIED",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["event_type"] == "flood"
    assert data["title"] == "Banji Jakarta"
    assert data["verification_status"] == "UNVERIFIED"
    event_id = data["id"]

    resp = client.get("/api/v1/crisis/events", headers=headers)
    assert resp.status_code == 200, resp.text
    events = resp.json()
    assert len(events) >= 1
    assert any(e["id"] == event_id for e in events)


def test_get_event_not_found(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    resp = client.get(f"/api/v1/crisis/events/{uuid4()}", headers=headers)
    assert resp.status_code == 404, resp.text


def test_timeline_endpoint(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    resp = client.get("/api/v1/crisis/timeline", headers=headers)
    assert resp.status_code == 200, resp.text
    timeline = resp.json()
    assert isinstance(timeline, list)


def test_verification_summary(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    resp = client.get("/api/v1/crisis/verification", headers=headers)
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert isinstance(summary, dict)


def test_create_and_list_warning(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    resp = client.post(
        "/api/v1/warnings/official",
        params={
            "issuer": "BMKG",
            "warning_level": "Waspada",
            "severity": "moderate",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["issuer"] == "BMKG"
    assert data["warning_level"] == "Waspada"
    assert data["severity"] == "moderate"
    assert data["is_active"] is True

    resp = client.get("/api/v1/warnings/official", headers=headers)
    assert resp.status_code == 200, resp.text
    warnings = resp.json()
    assert len(warnings) >= 1


def test_translate_warning(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    # Create a warning first
    resp = client.post(
        "/api/v1/warnings/official",
        params={
            "issuer": "BMKG",
            "warning_level": "Waspada",
            "severity": "moderate",
            "preparedness_guidance": "Siapkan tas darurat",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    warning_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/warnings/translations",
        json={"warning_id": str(warning_id), "target_language": "en"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["target_language"] == "en"
    assert data["translated_text"] == "Siapkan tas darurat"


def test_preparedness_guidance(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    # Create warning with preparedness guidance
    client.post(
        "/api/v1/warnings/official",
        params={
            "issuer": "BMKG",
            "warning_level": "Awas",
            "severity": "severe",
            "preparedness_guidance": "Evakuasi ke tempat tinggi",
        },
        headers=headers,
    )

    resp = client.get("/api/v1/warnings/preparedness", headers=headers)
    assert resp.status_code == 200, resp.text
    guidance = resp.json()
    assert len(guidance) >= 1
    assert guidance[0]["guidance"] == "Evakuasi ke tempat tinggi"


def test_protected_without_key(client: TestClient):
    resp = client.get("/api/v1/crisis/events")
    assert resp.status_code == 401, resp.text

    resp = client.get("/api/v1/warnings/official")
    assert resp.status_code == 401, resp.text
