"""Unit tests for auth models (organizations, users, api_keys) — no network."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from packages.core.models import (
    APIKey,
    Organization,
    OrganizationMember,
    User,
    Base,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = Session(engine)
    yield db
    db.close()


def test_create_organization(session):
    org = Organization(name="Acme Humanitarian", slug="acme")
    session.add(org)
    session.commit()
    session.refresh(org)

    assert org.id is not None
    assert org.name == "Acme Humanitarian"
    assert org.slug == "acme"
    assert org.created_at is not None


def test_create_user_and_membership(session):
    org = Organization(name="Org", slug="org")
    session.add(org)
    session.flush()

    user = User(email="alice@example.com", name="Alice", is_superuser=True)
    session.add(user)
    session.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="admin",
    )
    session.add(membership)
    session.commit()

    # Verify relationship loading
    stored_org = session.execute(select(Organization)).scalar_one()
    assert len(stored_org.members) == 1
    assert stored_org.members[0].user.email == "alice@example.com"
    assert stored_org.members[0].role == "admin"

    stored_user = session.execute(select(User)).scalar_one()
    assert len(stored_user.memberships) == 1
    assert stored_user.memberships[0].organization.slug == "org"


def test_create_api_key(session):
    org = Organization(name="Org", slug="org")
    user = User(email="bob@example.com", name="Bob")
    session.add_all([org, user])
    session.flush()

    key = APIKey(
        name="Test Key",
        key_hash="hashed_value_123",
        key_prefix="oshi_abc",
        user_id=user.id,
        organization_id=org.id,
    )
    session.add(key)
    session.commit()

    assert key.id is not None
    assert key.key_prefix == "oshi_abc"
    assert key.is_active is True
    assert key.organization_id == org.id
    assert key.user_id == user.id

    # Verify API key belongs to organization via relationship
    stored_org = session.execute(select(Organization)).scalar_one()
    assert len(stored_org.api_keys) == 1
    assert stored_org.api_keys[0].name == "Test Key"


def test_unique_email_and_slug(session):
    session.add(Organization(name="Org", slug="org"))
    session.add(User(email="dup@example.com", name="Dup"))
    session.commit()

    with pytest.raises(Exception):
        session.add(Organization(name="Org2", slug="org"))
        session.commit()
    session.rollback()

    with pytest.raises(Exception):
        session.add(User(email="dup@example.com", name="Dup2"))
        session.commit()