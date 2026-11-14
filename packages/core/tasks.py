"""In-memory background task store.

Tracks asynchronous tasks (document ingest, research agent execution) so the
API can return immediately with a task ID while the actual work continues in
the background.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class TaskStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskRecord:
    id: str
    status: str = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class TaskStore:
    """Thread-unsafe in-memory store (sufficient for single-worker dev)."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}

    def create(self) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = TaskRecord(id=task_id)
        return task_id

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def complete(self, task_id: str, result: Any) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            return
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = datetime.now(timezone.utc)

    def fail(self, task_id: str, error: str) -> None:
        task = self._tasks.get(task_id)
        if task is None:
            return
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = datetime.now(timezone.utc)


task_store = TaskStore()
