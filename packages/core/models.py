"""SQLAlchemy model definitions for OSHI foundation."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from packages.core.database import Base


class Publication(Base):
    """Scientific publication record from an external source.

    Keeps raw metadata plus provenance so every record remains traceable to its
    original source (see Part 6.4 provenance model).
    """

    __tablename__ = "publications"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    publication_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    license: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_publications_source", "source_name", "source_id", unique=True),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Publication(id={self.id}, source={self.source_name}:{self.source_id}, title={self.title!r})>"


class Organization(Base):
    """Organization / tenant boundary (Part 7.1).

    Provides multi-tenant isolation so different organizations can share
    the same deployment without leaking data across boundaries.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )


class OrganizationMember(Base):
    """Link between a user and an organization with a role."""

    __tablename__ = "organization_members"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")

    __table_args__ = (
        Index("ix_org_members_org_user", "organization_id", "user_id", unique=True),
    )


class User(Base):
    """Platform user account (Part 7.1, Part 8.5 privacy)."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    memberships: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class APIKey(Base):
    """API key for programmatic access (Part 7.1, Part 10 authentication).

    Keys are stored as salted hashes; the plaintext value is shown only once
    at creation time.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="api_keys")
    organization: Mapped["Organization | None"] = relationship(
        back_populates="api_keys"
    )


# --- Disaster Intelligence models (Part 7.4, Part 3.4 GCIN, Part 3.5 UEWI) ---


class DisasterEvent(Base):
    """A detected disaster event (Part 7.4, Part 3.4.B).

    An event detection result is labeled as preliminary until verified
    against appropriate sources (Part 3.4.B).
    """

    __tablename__ = "disaster_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="preliminary", index=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED", index=True
    )
    reported_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    reports: Mapped[list["EventReport"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    locations: Mapped[list["EventLocation"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    warnings: Mapped[list["OfficialWarning"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    situation_reports: Mapped[list["SituationReport"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class GeographicRegion(Base):
    """Administrative region / geographic boundary (Part 7.4, Part 3.4.E)."""

    __tablename__ = "geographic_regions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    region_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country_code: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    boundary_geojson: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class EventLocation(Base):
    """Geographic location of a disaster event (Part 3.4.E)."""

    __tablename__ = "event_locations"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("disaster_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    region_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("geographic_regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    event: Mapped["DisasterEvent"] = relationship(back_populates="locations")
    region: Mapped["GeographicRegion | None"] = relationship()


class EventReport(Base):
    """An incoming disaster report (Part 3.4.C)."""

    __tablename__ = "event_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("disaster_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    publication_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    observation_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reported_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_scope: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED", index=True
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event: Mapped["DisasterEvent"] = relationship(back_populates="reports")

    __table_args__ = (
        Index("ix_event_reports_source", "source_name", "content_hash", unique=True),
    )


class OfficialWarning(Base):
    """An official hazard warning (Part 3.5 UEWI).

    Never independently invented; always retrieved from an official issuer.
    Severity is preserved exactly as issued (Part 3.5 mandatory restrictions).
    """

    __tablename__ = "official_warnings"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("disaster_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    issuer: Mapped[str] = mapped_column(String(255), nullable=False)
    warning_level: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    expiry_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    affected_locations: Mapped[str | None] = mapped_column(Text, nullable=True)
    preparedness_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_bulletin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event: Mapped["DisasterEvent | None"] = relationship(back_populates="warnings")


class SituationReport(Base):
    """A generated situation report (Part 3.4.F)."""

    __tablename__ = "situation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("disaster_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    geographic_scope: Mapped[str | None] = mapped_column(String(500), nullable=True)
    confirmed_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    unverified_reports: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflicting_information: Mapped[str | None] = mapped_column(Text, nullable=True)
    known_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    information_gaps: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    event: Mapped["DisasterEvent"] = relationship(back_populates="situation_reports")
