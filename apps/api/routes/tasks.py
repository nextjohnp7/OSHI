"""Background task status API routes.

Endpoints:
- GET /api/v1/tasks/{task_id} — get task status and result

Used for document ingest and research agent execution that run in the
background via FastAPI ``BackgroundTasks``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from apps.api.schemas import TaskStatusOut
from packages.core.auth import require_api_key
from packages.core.tasks import task_store

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get(
    "/{task_id}",
    response_model=TaskStatusOut,
    summary="Get task status",
    description="Get the status and result of a background task.",
)
def get_task_status(
    task_id: str,
    current_user=Depends(require_api_key),
) -> TaskStatusOut:
    """Get the status and result of a background task."""
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusOut.model_validate(task)
