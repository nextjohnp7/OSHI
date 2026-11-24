"""Celery tasks for research agent execution (runs in worker, durable across restarts).

In eager mode (``CELERY_EAGER=true`` / tests without Redis), the plain
``run_research_sync`` function can be called directly instead of going
through the broker.
"""

from __future__ import annotations

from typing import Any

import httpx
from redis.exceptions import RedisError
from sqlalchemy.exc import DatabaseError, OperationalError

from packages.core.celery_app import celery_app
from packages.core.tasks import TransientError, task_store
from packages.agents.research.graph import run_research_agent


def run_research_sync(
    task_id: str,
    query: str,
    topic: str | None = None,
    crisis_context: str | None = None,
    max_publications: int = 5,
    max_evidence_per_publication: int = 3,
) -> dict[str, Any]:
    """Run research synchronously (no broker needed). Used by eager mode."""
    import asyncio

    try:
        final_state = asyncio.run(
            run_research_agent(
                query=query,
                topic=topic,
                crisis_context=crisis_context,
                max_publications=max_publications,
                max_evidence_per_publication=max_evidence_per_publication,
            )
        )
    except TransientError:
        raise
    except (
        httpx.ConnectTimeout,
        httpx.ReadTimeout,
        OperationalError,
        DatabaseError,
        RedisError,
        ConnectionError,
        TimeoutError,
        OSError,
    ) as exc:
        raise TransientError(str(exc)) from exc
    except Exception:  # noqa: BLE001 — non-transient, gagal cepat
        raise

    run_id = final_state.get("run_id", task_id)
    task_store.complete(task_id, final_state)
    return {"status": "completed", "run_id": run_id}


@celery_app.task(
    bind=True,
    name="oshi.worker.run_research",
    # Idempotensi: task_id (== run_id) dikontrol oleh caller. Jika task
    # dicoba ulang, task_store sudah memiliki entri dengan task_id yang sama.
    # Retry untuk kesalahan sementara (external API timeout, DB gangguan,
    # connector gangguan). Kesalahan permanen tidak diretry.
    autoretry_for=(TransientError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
def run_research(
    self,
    task_id: str,
    query: str,
    topic: str | None = None,
    crisis_context: str | None = None,
    max_publications: int = 5,
    max_evidence_per_publication: int = 3,
) -> dict[str, Any]:
    """Run the research agent in a Celery worker (survives API restart)."""
    try:
        return run_research_sync(
            task_id=task_id,
            query=query,
            topic=topic,
            crisis_context=crisis_context,
            max_publications=max_publications,
            max_evidence_per_publication=max_evidence_per_publication,
        )
    except TransientError:
        # Celery retry untuk kesalahan sementara; jangan tandai FAILED di
        # task store sebelum retry habis.
        raise
    except Exception:  # noqa: BLE001 — non-transient, sudah gagal cepat di sync
        raise
