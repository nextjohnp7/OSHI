"""Celery tasks for document ingest (runs in worker, durable across restarts).

In eager mode (``CELERY_EAGER=true`` / tests without Redis), the plain
``ingest_document_sync`` function can be called directly instead of going
through the broker.
"""

from __future__ import annotations

import uuid
from typing import Any

from redis.exceptions import RedisError
from sqlalchemy.exc import DatabaseError, OperationalError

from packages.core.celery_app import celery_app
from packages.core.tasks import TransientError, task_store
from packages.document_processing.service import DocumentService


def ingest_document_sync(
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
    """Run ingest synchronously (no broker needed). Used by eager mode."""
    from packages.core.database import get_session_local

    user_uuid = uuid.UUID(user_id) if user_id else None
    org_uuid = uuid.UUID(organization_id) if organization_id else None

    session_local = get_session_local()
    db = session_local()
    try:
        service = DocumentService(session=db)
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
        # Baca chunks sambil session masih terbuka (hindari lazy-load pada
        # instance yang sudah detached setelah session ditutup).
        chunk_count = len(document.chunks) if document.chunks else 0

        task_store.complete(
            task_id,
            {
                "document_id": str(document.id),
                "source_name": document.source_name,
                "source_id": document.source_id,
                "title": document.title,
                "chunk_count": chunk_count,
            },
        )
        return {"status": "completed", "document_id": str(document.id)}
    except TransientError:
        # Sudah wrapped oleh caller, re-raise agar Celery retry.
        raise
    except (
        OperationalError,
        DatabaseError,
        RedisError,
        ConnectionError,
        TimeoutError,
        OSError,
    ) as exc:
        # Kesalahan sementara (DB timeout, Redis gangguan, konektor timeout)
        # dibungkus sebagai TransientError agar Celery melakukan retry.
        raise TransientError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — record failure in task store
        # Kesalahan permanen (validasi, config, bug) — tidak diretry, gagal
        # cepat dan catat ke task store.
        task_store.fail(task_id, str(exc))
        raise
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="oshi.worker.ingest_document",
    # Idempotensi: task_id dikontrol oleh caller (API route membuat task_store
    # entry sebelum mengirim ke Celery). Jika task dicoba ulang, task_store
    # sudah memiliki entri dengan task_id yang sama dan worker hanya
    # memperbarui statusnya via task_store.complete() / task_store.fail().
    # Retry hanya untuk kesalahan sementara (DB timeout, Redis gangguan,
    # connector timeout). Kesalahan permanen (validasi, config, bug) tidak
    # diretry -- gagal cepat.
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
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
    """Ingest a document in a Celery worker (survives API restart).

    Idempotent: same (source_name, source_id, organization_id) re-ingest
    updates the existing document instead of creating a duplicate, thanks to
    the unique index on documents(source_name, source_id, organization_id).
    """
    try:
        return ingest_document_sync(
            task_id=task_id,
            text=text,
            source_name=source_name,
            source_id=source_id,
            title=title,
            source_url=source_url,
            chunk_size=chunk_size,
            overlap=overlap,
            user_id=user_id,
            organization_id=organization_id,
        )
    except TransientError:
        # Celery retry untuk kesalahan sementara; jangan tandai FAILED di
        # task store sebelum retry habis.
        raise
    except Exception:  # noqa: BLE001 — non-transient, sudah ditangani task_store.fail() di sync
        raise
