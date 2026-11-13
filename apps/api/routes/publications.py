"""Publication API routes."""

from fastapi import APIRouter, Query

from apps.api.schemas import PublicationOut, SearchRequest, SearchResponse
from apps.api.service import PublicationService

router = APIRouter(prefix="/api/v1/publications", tags=["publications"])

service = PublicationService()


@router.post("/search", response_model=SearchResponse)
async def search_publications(request: SearchRequest):
    """Search publications from a scientific source, normalize them, and store locally.

    Default source is OpenAlex. Use ``source`` to select another connector
    (e.g. ``crossref``).

    Returns the stored records so callers can open original sources via
    ``source_url`` and inspect provenance (source_name / source_id).
    """
    stored = await service.search_and_store(
        request.q, limit=request.limit, source=request.source
    )
    return SearchResponse(
        query=request.q,
        source=request.source or service.default_source,
        count=len(stored),
        results=[PublicationOut.model_validate(record) for record in stored],
    )


@router.get("", response_model=SearchResponse)
def list_publications(
    q: str | None = Query(default=None, description="Search title/abstract"),
    limit: int = Query(default=10, ge=1, le=100),
):
    """Search publications already stored in the local database."""
    stored = service.search_stored(q, limit=limit)
    return SearchResponse(
        query=q or "",
        source="local",
        count=len(stored),
        results=[PublicationOut.model_validate(record) for record in stored],
    )


@router.get("/{publication_id}", response_model=PublicationOut)
def get_publication(publication_id: str):
    """Get a single stored publication by its internal UUID."""
    from uuid import UUID

    from sqlalchemy import select

    from packages.core.database import get_session_local
    from packages.core.models import Publication

    session_local = get_session_local()
    db = session_local()
    try:
        record = db.execute(
            select(Publication).where(Publication.id == UUID(publication_id))
        ).scalar_one_or_none()
    finally:
        db.close()
    if record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Publication not found")
    return record

