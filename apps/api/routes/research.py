"""Research agent API routes (Sprint 4).

Endpoints:
- POST /api/v1/research/run — run the LangGraph research agent
- GET /api/v1/research/{run_id} — get research run status/result
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException

from apps.api.schemas import (
    ResearchEvidenceOut,
    ResearchPublicationOut,
    ResearchRunRequest,
    ResearchRunResponse,
    TaskResponse,
)
from packages.core.celery_app import celery_app
from packages.core.tasks import task_store
from packages.core.auth import (
    require_api_key,
    get_organization_context,
)

router = APIRouter(prefix="/api/v1/research", tags=["research"])


@router.post("/run", response_model=TaskResponse, status_code=202)
async def run_research(
    request: ResearchRunRequest,
    current_user=Depends(require_api_key),
    org_id=Depends(get_organization_context),
) -> TaskResponse:
    """Run the research agent workflow (Celery background task).

    Discovers publications from OpenAlex and Crossref, extracts evidence
    snippets, and generates a markdown research report. Returns a task ID
    immediately; poll ``GET /api/v1/tasks/{task_id}`` for the result.

    The actual research runs in a Celery worker backed by Redis, so the job
    survives API restarts and can be retried across workers.
    """
    run_id = str(uuid.uuid4())
    task_store.create(
        task_type="research",
        user_id=current_user.id,
        organization_id=org_id,
        task_id=uuid.UUID(run_id),
    )

    celery_app.send_task(
        "oshi.worker.run_research",
        args=[run_id, request.query],
        kwargs={
            "topic": request.topic,
            "crisis_context": request.crisis_context,
            "max_publications": request.max_publications,
            "max_evidence_per_publication": request.max_evidence_per_publication,
        },
    )
    task_record = task_store.get(run_id, user_id=current_user.id)
    if task_record is None:
        raise HTTPException(status_code=500, detail="Task record not found")
    return TaskResponse(
        task_id=run_id,
        status=task_record["status"],
        task_type=task_record["task_type"],
        created_at=task_record["created_at"],
    )


@router.get(
    "/{run_id}",
    response_model=ResearchRunResponse,
    summary="Get a research run",
    description="Get the result of a previously run research job by run ID. "
    "Only the user who started the research can view its result.",
)
async def get_research_run(
    run_id: str,
    current_user=Depends(require_api_key),
) -> ResearchRunResponse:
    """Get the result of a previously run research job."""
    run = task_store.get(run_id, user_id=current_user.id)
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
