"""SQLAlchemy models for document processing.

Stores imported documents and their text chunks with embeddings for
semantic (vector) retrieval.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import BYTEA as PGBytea, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.database import Base


class Document(Base):
    """Imported document record.

    Keeps metadata and provenance so every document remains traceable to its
    source (see Blueprint Part 6.4 provenance model).
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    source_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_documents_source",
            "source_name",
            "source_id",
            "user_id",
            unique=True,
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Document(id={self.id}, source={self.source_name}:{self.source_id}, title={self.title!r})>"


class DocumentChunk(Base):
    """Text chunk of a document with its embedding vector.

    Embedding is stored as LargeBinary (numpy float32 bytes) for portability
    across SQLite and PostgreSQL. On PostgreSQL production deployments, an
    additional ``embedding_vector vector(384)`` column (added via migration)
    enables pgvector-powered retrieval; ``embedding`` remains for dev/SQLite
    compatibility.
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document: Mapped["Document"] = relationship(back_populates="chunks")

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(
        LargeBinary().with_variant(PGBytea, "postgresql"),
        nullable=True,
    )
    embedding_vector: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_document_chunks_document", "document_id"),
        Index(
            "ix_document_chunks_document_index",
            "document_id",
            "chunk_index",
            unique=True,
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DocumentChunk(id={self.id}, doc={self.document_id}, idx={self.chunk_index})>"
