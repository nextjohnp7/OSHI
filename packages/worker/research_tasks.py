"""Celery tasks for research agent execution (runs in worker, durable across restarts).

In eager mode (``CELERY_EAGER=true`` / tests without Redis), the plain
``run_research_sync`` function can be called directly instead of going
through the broker.
"""

from __future__ import annotations

from typing import Any

from packages.core.celery_app import celery_app
from packages.core.tasks import task_store
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

    final_state = asyncio.run(
        run_research_agent(
            query=query,
            topic=topic,
            crisis_context=crisis_context,
            max_publications=max_publications,
            max_evidence_per_publication=max_evidence_per_publication,
        )
    )

    run_id = final_state.get("run_id", task_id)
    task_store.complete(task_id, final_state)
    return {"status": "completed", "run_id": run_id}


@celery_app.task(bind=True, name="oshi.worker.run_research")
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
    except Exception as exc:  # noqa: BLE001 — record failure in task store
        task_store.fail(task_id, str(exc))
        raise
