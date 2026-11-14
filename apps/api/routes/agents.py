"""Agent execution API routes.

Endpoints:
- GET /api/v1/agents/runs — list agent runs
- GET /api/v1/agents/runs/{run_id} — get agent run status/result
- GET /api/v1/agents/approvals — list pending approvals

These expose the LangGraph research agent execution state for monitoring
and human-in-the-loop review (Part 5.5).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from apps.api.routes.research import _research_runs
from packages.core.auth import require_api_key

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("/runs", response_model=list[dict[str, Any]])
def list_agent_runs(
    current_user=Depends(require_api_key),
) -> list[dict[str, Any]]:
    """List research agent runs (in-memory store, dev only)."""
    runs = []
    for run_id, state in _research_runs.items():
        runs.append(
            {
                "run_id": run_id,
                "status": state.get("status", "unknown"),
                "query": state.get("query", ""),
                "topic": state.get("topic", ""),
                "created_at": state.get("created_at"),
            }
        )
    return runs


@router.get("/runs/{run_id}", response_model=dict[str, Any])
def get_agent_run(
    run_id: str,
    current_user=Depends(require_api_key),
) -> dict[str, Any]:
    """Get the status and result of a specific agent run."""
    run = _research_runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return {
        "run_id": run_id,
        "status": run.get("status", "unknown"),
        "query": run.get("query", ""),
        "topic": run.get("topic", ""),
        "crisis_context": run.get("crisis_context"),
        "report": run.get("report"),
        "error": run.get("error"),
        "publication_count": len(run.get("publications", [])),
        "evidence_count": len(run.get("evidence", [])),
    }


@router.get("/approvals", response_model=list[dict[str, Any]])
def list_approvals(
    current_user=Depends(require_api_key),
) -> list[dict[str, Any]]:
    """List pending human-in-the-loop approvals (placeholder).

    In production, this would query a persistence layer for pending
    approval gates (Part 5.5). Currently returns an empty list as
    the research agent runs synchronously without interruption points.
    """
    return []
