"""Background task status API routes.

Endpoints:
- GET /api/v1/tasks/{task_id} — get task status and result

Used for document ingest and research agent execution that run in the
background via FastAPI ``BackgroundTasks``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from apps.api.schemas import TaskStatusOut
from packages.core.auth import require_api_key, resolve_primary_organization
from packages.core.tasks import task_store

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get(
    "",
    response_model=list[TaskStatusOut],
    summary="List background tasks",
    description="List the most recent background tasks (newest first) owned by the authenticated user.",
)
def list_tasks(
    current_user=Depends(require_api_key),
) -> list[TaskStatusOut]:
    """List background tasks (newest first) owned by the authenticated user."""
    user_id = current_user.id
    org_id = resolve_primary_organization(current_user)
    tasks = task_store.list_tasks(limit=1000, user_id=user_id)
    # Filter tambahan di level aplikasi untuk memastikan tenant isolation.
    tasks = [t for t in tasks if t["user_id"] == str(user_id)]
    if org_id is not None:
        tasks = [t for t in tasks if t.get("organization_id") == str(org_id)]
    return [TaskStatusOut.model_validate(t) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=TaskStatusOut,
    summary="Get task status",
    description="Get the status and result of a background task owned by the authenticated user.",
)
def get_task_status(
    task_id: str,
    current_user=Depends(require_api_key),
) -> TaskStatusOut:
    """Get the status and result of a background task owned by the authenticated user."""
    task = task_store.get(task_id, user_id=current_user.id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusOut.model_validate(task)


@router.delete(
    "/{task_id}",
    summary="Cancel a task",
    description="Cancel a pending background task owned by the authenticated user. Returns 404 if not found or 409 if already terminal.",
)
def cancel_task(
    task_id: str,
    current_user=Depends(require_api_key),
) -> dict[str, str]:
    """Cancel a pending background task owned by the authenticated user."""
    cancelled = task_store.cancel(task_id, user_id=current_user.id)
    if not cancelled:
        # Check if task exists
        task = task_store.get(task_id, user_id=current_user.id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task is already in a terminal state",
        )
    return {"detail": "cancelled"}
