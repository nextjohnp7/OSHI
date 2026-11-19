"""Document API routes (Sprint 3)."""

from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.schemas import (
    DocumentChunkOut,
    DocumentIngestRequest,
    DocumentOut,
    DocumentSearchRequest,
    DocumentSearchResponse,
    TaskResponse,
)
from packages.core.auth import (
    require_api_key,
    get_organization_context,
)
from packages.core.celery_app import celery_app
from packages.core.config import get_settings
from packages.core.tasks import task_store
from packages.document_processing.service import DocumentService
from packages.worker.ingest_tasks import ingest_document_sync

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

service = DocumentService()


@router.post("/ingest", response_model=TaskResponse, status_code=202)
async def ingest_document(
    request: DocumentIngestRequest,
    current_user=Depends(require_api_key),
    org_id=Depends(get_organization_context),
):
    """Import a document: chunk, embed, and store (Celery background task).

    Deduplicates by (source_name, source_id, organization_id): re-ingesting
    the same source replaces its chunks. Returns a task ID immediately; poll
    ``GET /api/v1/tasks/{task_id}`` for the result.

    The actual ingest runs in a Celery worker backed by Redis, so the job
    survives API restarts and can be retried across workers. When
    ``CELERY_EAGER=true`` (tests/dev without Redis), the task runs inline.
    """
    task_id = task_store.create(
        task_type="ingest",
        user_id=current_user.id,
        organization_id=org_id,
    )

    settings = get_settings()
    if settings.celery_eager:
        ingest_document_sync(
            task_id=task_id,
            text=request.text,
            source_name=request.source_name,
            source_id=request.source_id,
            title=request.title,
            source_url=request.source_url,
            chunk_size=request.chunk_size,
            overlap=request.overlap,
            user_id=str(current_user.id),
            organization_id=str(org_id) if org_id else None,
        )
    else:
        celery_app.send_task(
            "oshi.worker.ingest_document",
            args=[
                task_id,
                request.text,
                request.source_name,
                request.source_id,
                request.title,
            ],
            kwargs={
                "source_url": request.source_url,
                "chunk_size": request.chunk_size,
                "overlap": request.overlap,
                "user_id": str(current_user.id),
                "organization_id": str(org_id) if org_id else None,
            },
        )
    task_record = task_store.get(task_id, user_id=current_user.id)
    if task_record is None:
        raise HTTPException(status_code=500, detail="Task record not found")
    return TaskResponse(
        task_id=task_id,
        status=task_record["status"],
        task_type=task_record["task_type"],
        created_at=task_record["created_at"],
    )


@router.get(
    "",
    response_model=list[DocumentOut],
    summary="List imported documents",
    description="List imported documents. ``limit`` controls page size (1-100).",
)
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_api_key),
    org_id=Depends(get_organization_context),
):
    """List imported documents."""
    return service.list_documents(limit=limit, organization_id=org_id)


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Get a document by ID",
    description="Get a single imported document by its internal UUID.",
)
def get_document(
    document_id: str,
    current_user=Depends(require_api_key),
    org_id=Depends(get_organization_context),
):
    """Get a single document by its internal UUID."""
    document = service.get_document(document_id, organization_id=org_id)
    if document is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get(
    "/{document_id}/chunks",
    response_model=list[DocumentChunkOut],
    summary="Get document chunks",
    description="Get all chunks of a document, ordered by chunk_index.",
)
def get_document_chunks(
    document_id: str,
    current_user=Depends(require_api_key),
    org_id=Depends(get_organization_context),
):
    """Get all chunks of a document, ordered by chunk_index."""
    chunks = service.get_document_chunks(document_id, organization_id=org_id)
    return [
        DocumentChunkOut(
            id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            text=c.text,
        )
        for c in chunks
    ]


@router.post(
    "/search",
    response_model=DocumentSearchResponse,
    summary="Semantic search document chunks",
    description="Semantic (vector) search across stored document chunks. "
    "Returns chunks ranked by cosine similarity to the query.",
)
def semantic_search(
    request: DocumentSearchRequest,
    current_user=Depends(require_api_key),
    org_id=Depends(get_organization_context),
):
    """Semantic (vector) search across stored document chunks.

    Returns chunks ranked by cosine similarity to the query.
    """
    ranked = service.semantic_search(
        query=request.q,
        top_k=request.top_k,
        source_name=request.source_name,
        organization_id=org_id,
    )
    return DocumentSearchResponse(
        query=request.q,
        count=len(ranked),
        results=[
            DocumentChunkOut(
                id=r["id"],
                document_id=r["document_id"],
                chunk_index=r["chunk_index"],
                text=r["text"],
                similarity=r.get("similarity"),
                document_title=r.get("document_title"),
                document_source_name=r.get("document_source_name"),
                document_source_id=r.get("document_source_id"),
                document_source_url=r.get("document_source_url"),
            )
            for r in ranked
        ],
    )
