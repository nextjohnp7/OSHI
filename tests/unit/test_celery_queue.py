"""Tes antrean Celery / Redis (mode eager, tidak perlu broker nyata).

Memverifikasi:
- Celery app terkonfigurasi dengan benar (broker, backend, include tasks).
- TaskStore create/get/complete/fail berfungsi.
- Ingest task dapat dijalankan dalam mode eager dan menghasilkan task store entry.
- Research task dapat dijalankan dalam mode eager.
- Idempotensi: task_id yang sama tidak membuat duplikasi entri task store.
"""

import os

os.environ.setdefault("OSHI_EMBEDDING_BACKEND", "hashing")
os.environ.setdefault("CELERY_EAGER", "true")

import uuid

import pytest
from celery import Celery

from packages.core.celery_app import celery_app
from packages.core.tasks import TaskStatus, TransientError, task_store
from packages.worker.ingest_tasks import ingest_document_sync
from packages.worker.research_tasks import run_research_sync


@pytest.fixture
def clean_task_store():
    """Hapus semua task dari task store sebelum/setsudah tes."""
    yield
    # Tidak ada metode clear di TaskStore; setiap tes menggunakan task_id unik.


def test_celery_app_configured():
    """Celery app harus memiliki broker, backend, dan tasks yang ter-include."""
    assert isinstance(celery_app, Celery)
    assert celery_app.conf.broker_url is not None
    assert celery_app.conf.result_backend is not None
    # Tasks yang di-include harus terdaftar di celery_app.tasks setelah import.
    task_names = set(celery_app.tasks.keys())
    assert any("ingest_tasks" in t for t in task_names)
    assert any("research_tasks" in t for t in task_names)


def test_task_store_create_get_complete_fail(clean_task_store):
    """TaskStore lifecycle: create -> get -> complete/fail -> get."""
    task_id = str(uuid.uuid4())

    # Create
    created_id = task_store.create(
        task_type="ingest",
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        task_id=uuid.UUID(task_id),
    )
    assert created_id == task_id

    # Get immediately after create
    record = task_store.get(task_id)
    assert record is not None
    assert record["task_id"] == task_id
    assert record["status"] == TaskStatus.PENDING
    assert record["task_type"] == "ingest"

    # Complete
    task_store.complete(task_id, {"document_id": str(uuid.uuid4())})
    record = task_store.get(task_id)
    assert record["status"] == TaskStatus.COMPLETED
    assert record["result"] is not None

    # Fail (new task)
    task_id_fail = str(uuid.uuid4())
    task_store.create(task_type="research", task_id=uuid.UUID(task_id_fail))
    task_store.fail(task_id_fail, "something went wrong")
    record = task_store.get(task_id_fail)
    assert record["status"] == TaskStatus.FAILED
    assert record["error"] == "something went wrong"


def test_task_store_idempotent_task_id(clean_task_store):
    """Task ID yang sama tidak boleh membuat entri duplikasi."""
    task_id = str(uuid.uuid4())
    task_store.create(task_type="ingest", task_id=uuid.UUID(task_id))
    record1 = task_store.get(task_id)
    assert record1 is not None

    # Create ulang dengan task_id yang sama — harus mengembalikan ID yang sama
    # (TaskStore.create tidak raise, karena primary key task_id sudah ada;
    # dalam praktek API route hanya membuat entri sekali sebelum send_task).
    created_id = task_store.create(task_type="ingest", task_id=uuid.UUID(task_id))
    assert created_id == task_id


def test_ingest_document_sync_eager_mode(clean_task_store):
    """Ingest task sync dalam mode eager harus menghasilkan dokumen + chunk."""
    task_id = str(uuid.uuid4())
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    task_store.create(
        task_type="ingest",
        user_id=user_id,
        organization_id=org_id,
        task_id=uuid.UUID(task_id),
    )

    result = ingest_document_sync(
        task_id=task_id,
        text="Climate change affects agriculture and food security worldwide. " * 10,
        source_name="test-source",
        source_id="doc-eager-001",
        title="Eager Test Doc",
        user_id=str(user_id),
        organization_id=str(org_id),
    )

    assert result["status"] == "completed"
    assert "document_id" in result

    record = task_store.get(task_id)
    assert record["status"] == TaskStatus.COMPLETED
    assert record["result"]["document_id"] == result["document_id"]


def test_run_research_sync_eager_mode(clean_task_store):
    """Research task sync dalam mode eager harus menyelesaikan tanpa error."""
    task_id = str(uuid.uuid4())

    task_store.create(
        task_type="research",
        task_id=uuid.UUID(task_id),
    )

    result = run_research_sync(
        task_id=task_id,
        query="climate change adaptation",
        topic="environment",
        max_publications=2,
        max_evidence_per_publication=1,
    )

    assert result["status"] == "completed"
    assert "run_id" in result

    record = task_store.get(task_id)
    assert record["status"] == TaskStatus.COMPLETED


def test_celery_task_autoretry_configured():
    """Task Celery harus memiliki autoretry untuk fault tolerance."""
    ingest_task = celery_app.tasks.get("oshi.worker.ingest_document")
    research_task = celery_app.tasks.get("oshi.worker.run_research")

    assert ingest_task is not None
    assert research_task is not None

    # autoretry_for harus mengandung TransientError (hanya kesalahan sementara
    # yang diretry; kesalahan permanen gagal cepat).
    assert TransientError in ingest_task.autoretry_for
    assert TransientError in research_task.autoretry_for

    # Exception tidak boleh ada dalam autoretry_for (tidak diretry)
    assert Exception not in ingest_task.autoretry_for
    assert Exception not in research_task.autoretry_for

    # max_retries harus > 0
    assert ingest_task.max_retries > 0
    assert research_task.max_retries > 0

    # acks_late harus True untuk durabilitas
    assert ingest_task.acks_late is True
    assert research_task.acks_late is True
