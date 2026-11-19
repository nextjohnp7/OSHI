"""Celery tasks for document ingest (runs in worker, durable across restarts)."""

from __future__ import annotations

import uuid
from typing import Any

from packages.core.celery_app import celery_app
from packages.core.tasks import task_store
from packages.document_processing.service import DocumentService


@celery_app.task(bind=True, name="oshi.worker.ingest_document")
def ingest_document(
    self,
    task_id: str,
    text: str,
    source_name: str,
    source_id: str,
    title: str,
    source_url: str | None = None,
    chunk_size: int = 500,
    overlap: int = 50,
    user_id: str | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    """Ingest a document in a Celery worker (survives API restart)."""
    try:
        user_uuid = uuid.UUID(user_id) if user_id else None
        org_uuid = uuid.UUID(organization_id) if organization_id else None

        service = DocumentService()
        document = service.ingest(
            text=text,
            source_name=source_name,
            source_id=source_id,
            title=title,
            source_url=source_url,
            chunk_size=chunk_size,
            overlap=overlap,
            user_id=user_uuid,
            organization_id=org_uuid,
        )

        task_store.complete(
            task_id,
            {
                "document_id": str(document.id),
                "source_name": document.source_name,
                "source_id": document.source_id,
                "title": document.title,
                "chunk_count": len(document.chunks) if document.chunks else 0,
            },
        )
        return {"status": "completed", "document_id": str(document.id)}
    except Exception as exc:  # noqa: BLE001 — record failure in task store
        task_store.fail(task_id, str(exc))
        raise
