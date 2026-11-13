"""Research agent API routes (Sprint 4).

Endpoints:
- POST /api/v1/research/run — run the LangGraph research agent
- GET /api/v1/research/{run_id} — get research run status/result
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas import (
    ResearchEvidenceOut,
    ResearchPublicationOut,
    ResearchRunRequest,
    ResearchRunResponse,
)
from packages.agents.research.graph import run_research_agent

router = APIRouter(prefix="/api/v1/research", tags=["research"])

# In-memory store for research run results (dev only; replace with DB in prod)
_research_runs: dict[str, dict] = {}


@router.post("/run", response_model=ResearchRunResponse)
async def run_research(request: ResearchRunRequest) -> ResearchRunResponse:
    """Run the research agent workflow.

    Discovers publications from OpenAlex and Crossref, extracts evidence
    snippets, and generates a markdown research report.
    """
    try:
        final_state = await run_research_agent(
            query=request.query,
            topic=request.topic,
            crisis_context=request.crisis_context,
            max_publications=request.max_publications,
            max_evidence_per_publication=request.max_evidence_per_publication,
        )

        run_id = final_state.get("run_id", "")
        _research_runs[run_id] = final_state

        return ResearchRunResponse(
            run_id=run_id,
            status=final_state.get("status", "failed"),
            query=final_state.get("query", ""),
            topic=final_state.get("topic", ""),
            crisis_context=final_state.get("crisis_context"),
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
                for p in final_state.get("publications", [])
            ],
            evidence=[
                ResearchEvidenceOut(
                    publication_id=e.get("publication_id", ""),
                    publication_title=e.get("publication_title", ""),
                    quote=e.get("quote", ""),
                    relevance_to_query=e.get("relevance_to_query", 0.0),
                )
                for e in final_state.get("evidence", [])
            ],
            report=final_state.get("report"),
            error=final_state.get("error"),
        )
    except Exception as exc:  # pragma: no cover - network/LLM failure
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{run_id}", response_model=ResearchRunResponse)
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
