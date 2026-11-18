"""Organization-level tenancy tests (Part 7.1 / review item 4).

Covers:
- Two users in the same organization sharing a source_id dedupe to one document.
- A user with multiple organizations selects tenant via X-Organization-ID header.
- X-Organization-ID for an organization the user is not a member of returns 403.
"""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from packages.core.database import get_session_local
from packages.core.models import APIKey, Organization, OrganizationMember, User


def _bootstrap(client: TestClient) -> str:
    """Bootstrap first superuser; return api_key."""
    resp = client.post(
        "/api/v1/auth/bootstrap",
        params={"email": "org-admin@example.com", "name": "Org Admin"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["api_key"]


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


def _insert_user_and_key(
    client: TestClient,
    email: str,
    name: str,
    org_id: UUID,
    is_superuser: bool = False,
) -> tuple[str, UUID]:
    """Insert a user + API key directly into the test DB; return (api_key, user_id)."""
    import hashlib

    session_local = get_session_local()
    db = session_local()
    try:
        user = User(
            id=uuid4(),
            email=email,
            name=name,
            is_active=True,
            is_superuser=is_superuser,
        )
        db.add(user)
        db.flush()

        membership = OrganizationMember(
            id=uuid4(),
            organization_id=org_id,
            user_id=user.id,
            role="member",
        )
        db.add(membership)
        db.flush()

        key_hash = hashlib.sha256(f"{email}-secret".encode()).hexdigest()
        db.add(
            APIKey(
                id=uuid4(),
                name=f"{email}-key",
                key_hash=key_hash,
                key_prefix=f"{email[:12]}",
                user_id=user.id,
                organization_id=org_id,
                is_active=True,
            )
        )
        db.commit()
        return f"{email}-secret", user.id
    finally:
        db.close()


def _ingest(
    client: TestClient,
    headers: dict[str, str],
    source_id: str,
    org_id: UUID | None = None,
    title: str = "Doc",
):
    extra_headers = dict(headers)
    if org_id is not None:
        extra_headers["X-Organization-ID"] = str(org_id)
    resp = client.post(
        "/api/v1/documents/ingest",
        json={
            "text": "Some content for the document.",
            "source_name": "test",
            "source_id": source_id,
            "title": title,
            "chunk_size": 500,
            "overlap": 50,
        },
        headers=extra_headers,
    )
    return resp


def test_same_org_dedupe_shared_source_id(client: TestClient):
    """Two users in the same org ingesting same source_id -> one document."""
    api_key_a = _bootstrap(client)
    headers_a = _auth_headers(api_key_a)

    # Get org A from bootstrap (first membership of superuser).
    session_local = get_session_local()
    db = session_local()
    try:
        org_a = db.execute(select(Organization).limit(1)).scalar_one()
    finally:
        db.close()

    # User B in same org A.
    api_key_b, _ = _insert_user_and_key(
        client, "org-user@example.com", "Org User", org_a.id
    )
    headers_b = _auth_headers(api_key_b)

    # User A ingests shared source.
    resp = _ingest(client, headers_a, "shared-source-1", org_id=org_a.id)
    assert resp.status_code == 202, resp.text

    # User B ingests same source in same org -> dedupe (one document).
    resp = _ingest(client, headers_b, "shared-source-1", org_id=org_a.id)
    assert resp.status_code == 202, resp.text

    # List documents as user A in org A -> should see exactly one.
    resp = client.get(
        "/api/v1/documents",
        headers={**headers_a, "X-Organization-ID": str(org_a.id)},
    )
    assert resp.status_code == 200, resp.text
    docs = resp.json()
    shared = [d for d in docs if d["source_id"] == "shared-source-1"]
    assert len(shared) == 1, f"Expected 1 shared doc, got {len(shared)}"


def test_x_organization_id_header_selects_tenant(client: TestClient):
    """User with X-Organization-ID header gets that org's scope."""
    _ = _bootstrap(client)

    session_local = get_session_local()
    db = session_local()
    try:
        org_a = db.execute(select(Organization).limit(1)).scalar_one()
    finally:
        db.close()

    # Create org B.
    session_local = get_session_local()
    db = session_local()
    try:
        org_b = Organization(id=uuid4(), name="Org B", slug="org-b")
        db.add(org_b)
        db.commit()
        org_b_id = org_b.id
    finally:
        db.close()

    # Insert user C as member of org B only.
    api_key_c, _ = _insert_user_and_key(
        client, "orgb-user@example.com", "Org B User", org_b_id
    )
    headers_c = _auth_headers(api_key_c)

    # User C ingests in org B.
    resp = _ingest(client, headers_c, "orgb-source-1", org_id=org_b.id)
    assert resp.status_code == 202, resp.text

    # User C with X-Organization-ID = org A (not a member) -> 403.
    resp = _ingest(client, headers_c, "orgb-source-1", org_id=org_a.id)
    assert resp.status_code == 403, resp.text


def test_organization_id_from_api_key(client: TestClient):
    """API key's organization_id is used when no X-Organization-ID header."""
    api_key_a = _bootstrap(client)
    headers_a = _auth_headers(api_key_a)

    session_local = get_session_local()
    db = session_local()
    try:
        org_a = db.execute(select(Organization).limit(1)).scalar_one()
        # The bootstrapped API key should have organization_id = org_a.
        key_row = db.execute(select(APIKey).limit(1)).scalars().first()
    finally:
        db.close()

    assert key_row is not None
    assert key_row.organization_id == org_a.id

    # Ingest without X-Organization-ID -> uses key's org.
    resp = _ingest(client, headers_a, "key-org-source-1", org_id=None)
    assert resp.status_code == 202, resp.text
