"""Document API routes (Sprint 3)."""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Query

from apps.api.schemas import (
    DocumentChunkOut,
    DocumentIngestRequest,
    DocumentOut,
    DocumentSearchRequest,
    DocumentSearchResponse,
    TaskResponse,
)
from packages.core.tasks import task_store
from packages.document_processing.service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

service = DocumentService()


@router.post("/ingest", response_model=TaskResponse, status_code=202)
async def ingest_document(
    request: DocumentIngestRequest,
    background_tasks: BackgroundTasks,
):
    """Import a document: chunk, embed, and store (background task).

    Deduplicates by (source_name, source_id): re-ingesting the same source
    replaces its chunks. Returns a task ID immediately; poll
    ``GET /api/v1/tasks/{task_id}`` for the result.
    """
    task_id = task_store.create()

    async def _ingest() -> None:
        try:
            document = service.ingest(
                text=request.text,
                source_name=request.source_name,
                source_id=request.source_id,
                title=request.title,
                source_url=request.source_url,
                chunk_size=request.chunk_size,
                overlap=request.overlap,
            )
            task_store.complete(
                task_id, DocumentOut.model_validate(document).model_dump()
            )
        except Exception as exc:  # noqa: BLE001 — record failure in task store
            task_store.fail(task_id, str(exc))

    background_tasks.add_task(_ingest)
    task_record = task_store.get(task_id)
    return TaskResponse(
        task_id=task_id,
        status=task_record.status,
        created_at=task_record.created_at,
    )


@router.get(
    "",
    response_model=list[DocumentOut],
    summary="List imported documents",
    description="List imported documents. ``limit`` controls page size (1-100).",
)
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
):
    """List imported documents."""
    return service.list_documents(limit=limit)


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Get a document by ID",
    description="Get a single imported document by its internal UUID.",
)
def get_document(document_id: str):
    """Get a single document by its internal UUID."""
    document = service.get_document(document_id)
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
def get_document_chunks(document_id: str):
    """Get all chunks of a document, ordered by chunk_index."""
    chunks = service.get_document_chunks(document_id)
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
def semantic_search(request: DocumentSearchRequest):
    """Semantic (vector) search across stored document chunks.

    Returns chunks ranked by cosine similarity to the query.
    """
    ranked = service.semantic_search(
        query=request.q,
        top_k=request.top_k,
        source_name=request.source_name,
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
