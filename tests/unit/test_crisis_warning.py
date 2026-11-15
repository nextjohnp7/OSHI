"""Unit tests for Crisis Intelligence and Early Warning API routes (no network)."""

from uuid import uuid4

from fastapi.testclient import TestClient


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
    # Warning baru dibuat dengan status UNVERIFIED; belum divalidasi oleh
    # otoritas resmi, jadi tidak langsung muncul dalam daftar verified.
    assert data["verification_status"] == "UNVERIFIED"

    # Hanya warning VERIFIED yang tampil dalam daftar publik.
    resp = client.get("/api/v1/warnings/official", headers=headers)
    assert resp.status_code == 200, resp.text
    warnings = resp.json()
    assert all(w["verification_status"] == "VERIFIED" for w in warnings)


def test_translate_warning(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    # Buat warning UNVERIFIED melalui API — translasi harus ditolak (404).
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
    unverified_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/warnings/translations",
        json={"warning_id": str(unverified_id), "target_language": "en"},
        headers=headers,
    )
    assert resp.status_code == 404, resp.text

    # Warning VERIFIED dapat diterjemahkan — insert langsung ke DB.
    from packages.core.database import get_session_local
    from packages.core.models import OfficialWarning

    session_local = get_session_local()
    db = session_local()
    try:
        verified = OfficialWarning(
            id=uuid4(),
            issuer="BMKG",
            warning_level="Awas",
            severity="severe",
            effective_time=None,
            expiry_time=None,
            affected_locations=None,
            preparedness_guidance="Evakuasi ke tempat tinggi",
            source_bulletin_url=None,
            is_active=True,
            verification_status="VERIFIED",
        )
        db.add(verified)
        db.commit()
        verified_id = str(verified.id)
    finally:
        db.close()

    resp = client.post(
        "/api/v1/warnings/translations",
        json={"warning_id": verified_id, "target_language": "en"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["target_language"] == "en"
    assert data["translated_text"] == "Evakuasi ke tempat tinggi"


def test_preparedness_guidance(client: TestClient):
    api_key = _bootstrap(client)
    headers = _auth_headers(api_key)

    # Buat warning UNVERIFIED melalui API — tidak boleh muncul di preparedness.
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
    assert all(g["guidance"] != "Evakuasi ke tempat tinggi" for g in guidance)

    # Warning VERIFIED muncul di preparedness — insert langsung ke DB.
    from packages.core.database import get_session_local
    from packages.core.models import OfficialWarning

    session_local = get_session_local()
    db = session_local()
    try:
        verified = OfficialWarning(
            id=uuid4(),
            issuer="BMKG",
            warning_level="Awas",
            severity="severe",
            effective_time=None,
            expiry_time=None,
            affected_locations=None,
            preparedness_guidance="Siapkan tas darurat dan dokumen penting",
            source_bulletin_url=None,
            is_active=True,
            verification_status="VERIFIED",
        )
        db.add(verified)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/warnings/preparedness", headers=headers)
    assert resp.status_code == 200, resp.text
    guidance = resp.json()
    assert any(
        g["guidance"] == "Siapkan tas darurat dan dokumen penting" for g in guidance
    )


def test_protected_without_key(client: TestClient):
    resp = client.get("/api/v1/crisis/events")
    assert resp.status_code == 401, resp.text

    resp = client.get("/api/v1/warnings/official")
    assert resp.status_code == 401, resp.text
