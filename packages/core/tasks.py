"""Database-backed background task store.

Tracks asynchronous tasks (document ingest, research agent execution) so the
API can return immediately with a task ID while the actual work continues in
the background. Tasks are persisted in the ``tasks`` table so they survive
server restarts and can be queried across workers in production.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from packages.core.database import get_session_local
from packages.core.models import Task


class TaskStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStore:
    """Database-backed task store (survives server restarts)."""

    def create(
        self,
        task_type: str = "ingest",
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> str:
        """Create a new pending task and return its ID."""
        task_id = uuid.uuid4()
        session_local = get_session_local()
        db = session_local()
        try:
            task = Task(
                id=task_id,
                status=TaskStatus.PENDING,
                task_type=task_type,
                user_id=user_id,
                organization_id=organization_id,
            )
            db.add(task)
            db.commit()
        finally:
            db.close()
        return str(task_id)

    def get(
        self, task_id: str, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Return a task record as a dict, or None if not found.

        If ``user_id`` is given, only tasks owned by that user are returned.
        """
        session_local = get_session_local()
        db = session_local()
        try:
            stmt = select(Task).where(Task.id == uuid.UUID(task_id))
            if user_id is not None:
                stmt = stmt.where(Task.user_id == user_id)
            task = db.execute(stmt).scalar_one_or_none()
            if task is None:
                return None
            result = _json_safe(task.result)
            return {
                "task_id": str(task.id),
                "status": task.status,
                "task_type": task.task_type,
                "result": result,
                "error": task.error,
                "user_id": str(task.user_id),
                "organization_id": (
                    str(task.organization_id) if task.organization_id else None
                ),
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "completed_at": (
                    task.completed_at.isoformat() if task.completed_at else None
                ),
            }
        finally:
            db.close()

    def complete(self, task_id: str, result: Any) -> None:
        """Mark a task as completed with its result."""
        session_local = get_session_local()
        db = session_local()
        try:
            stmt = select(Task).where(Task.id == uuid.UUID(task_id))
            task = db.execute(stmt).scalar_one_or_none()
            if task is None:
                return
            task.status = TaskStatus.COMPLETED
            safe_result = _json_safe(result)
            task.result = (
                safe_result
                if isinstance(safe_result, dict)
                else {"result": safe_result}
            )
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

    def fail(self, task_id: str, error: str) -> None:
        """Mark a task as failed with an error message."""
        session_local = get_session_local()
        db = session_local()
        try:
            stmt = select(Task).where(Task.id == uuid.UUID(task_id))
            task = db.execute(stmt).scalar_one_or_none()
            if task is None:
                return
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

    def list_tasks(
        self, limit: int = 50, user_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """List the most recent tasks (newest first).

        If ``user_id`` is given, only tasks owned by that user are returned.
        """
        session_local = get_session_local()
        db = session_local()
        try:
            stmt = select(Task)
            if user_id is not None:
                stmt = stmt.where(Task.user_id == user_id)
            stmt = stmt.order_by(Task.created_at.desc()).limit(limit)
            tasks = db.execute(stmt).scalars().all()
            return [
                {
                    "task_id": str(t.id),
                    "status": t.status,
                    "task_type": t.task_type,
                    "result": _json_safe(t.result),
                    "error": t.error,
                    "user_id": str(t.user_id),
                    "organization_id": (
                        str(t.organization_id) if t.organization_id else None
                    ),
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": (
                        t.completed_at.isoformat() if t.completed_at else None
                    ),
                }
                for t in tasks
            ]
        finally:
            db.close()

    def cancel(self, task_id: str, user_id: uuid.UUID | None = None) -> bool:
        """Mark a pending task as cancelled (failed with user-cancelled error).

        Returns True if a task was cancelled, False if not found or already
        terminal. If ``user_id`` is given, only tasks owned by that user can
        be cancelled.
        """
        session_local = get_session_local()
        db = session_local()
        try:
            stmt = select(Task).where(Task.id == uuid.UUID(task_id))
            if user_id is not None:
                stmt = stmt.where(Task.user_id == user_id)
            task = db.execute(stmt).scalar_one_or_none()
            if task is None:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                return False
            task.status = TaskStatus.FAILED
            task.error = "cancelled by user"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return True
        finally:
            db.close()


task_store = TaskStore()


def _json_safe(value: Any) -> Any:
    """Recursively convert uuid.UUID and datetime objects to str so the result is JSON-safe."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    return value
