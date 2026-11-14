"""Research agent API routes (Sprint 4).

Endpoints:
- POST /api/v1/research/run — run the LangGraph research agent
- GET /api/v1/research/{run_id} — get research run status/result
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from apps.api.schemas import (
    ResearchEvidenceOut,
    ResearchPublicationOut,
    ResearchRunRequest,
    ResearchRunResponse,
    TaskResponse,
)
from packages.core.tasks import task_store
from packages.agents.research.graph import run_research_agent

router = APIRouter(prefix="/api/v1/research", tags=["research"])

# In-memory store for research run results (dev only; replace with DB in prod)
_research_runs: dict[str, dict] = {}


@router.post("/run", response_model=TaskResponse, status_code=202)
async def run_research(
    request: ResearchRunRequest,
    background_tasks: BackgroundTasks,
) -> TaskResponse:
    """Run the research agent workflow (background task).

    Discovers publications from OpenAlex and Crossref, extracts evidence
    snippets, and generates a markdown research report. Returns a task ID
    immediately; poll ``GET /api/v1/tasks/{task_id}`` for the result.
    """
    task_id = task_store.create()

    async def _run() -> None:
        try:
            final_state = await run_research_agent(
                query=request.query,
                topic=request.topic,
                crisis_context=request.crisis_context,
                max_publications=request.max_publications,
                max_evidence_per_publication=request.max_evidence_per_publication,
            )
            run_id = final_state.get("run_id", task_id)
            _research_runs[run_id] = final_state
            task_store.complete(task_id, final_state)
        except Exception as exc:  # noqa: BLE001 — record failure in task store
            task_store.fail(task_id, str(exc))

    background_tasks.add_task(_run)
    task_record = task_store.get(task_id)
    return TaskResponse(
        task_id=task_id,
        status=task_record.status,
        created_at=task_record.created_at,
    )


@router.get(
    "/{run_id}",
    response_model=ResearchRunResponse,
    summary="Get a research run",
    description="Get the result of a previously run research job by run ID.",
)
async def get_research_run(run_id: str) -> ResearchRunResponse:
    """Get the result of a previously run research job."""
    run = _research_runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Research run not found")

    return ResearchRunResponse(
        run_id=run.get("run_id", run_id),
        status=run.get("status", "failed"),
        query=run.get("query", ""),
        topic=run.get("topic", ""),
        crisis_context=run.get("crisis_context"),
        publications=[
            ResearchPublicationOut(
                id=p.get("id", ""),
                title=p.get("title", ""),
                authors=p.get("authors", []),
                abstract=p.get("abstract", ""),
                source=p.get("source", ""),
                url=p.get("url", ""),
                published_date=p.get("published_date"),
                relevance_score=p.get("relevance_score", 0.0),
            )
            for p in run.get("publications", [])
        ],
        evidence=[
            ResearchEvidenceOut(
                publication_id=e.get("publication_id", ""),
                publication_title=e.get("publication_title", ""),
                quote=e.get("quote", ""),
                relevance_to_query=e.get("relevance_to_query", 0.0),
            )
            for e in run.get("evidence", [])
        ],
        report=run.get("report"),
        error=run.get("error"),
    )
