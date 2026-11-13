"""Document API routes (Sprint 3)."""

from fastapi import APIRouter, Query

from apps.api.schemas import (
    DocumentChunkOut,
    DocumentIngestRequest,
    DocumentOut,
    DocumentSearchRequest,
    DocumentSearchResponse,
)
from packages.document_processing.service import DocumentService

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

service = DocumentService()


@router.post("/ingest", response_model=DocumentOut)
def ingest_document(request: DocumentIngestRequest):
    """Import a document: chunk, embed, and store.

    Deduplicates by (source_name, source_id): re-ingesting the same source
    replaces its chunks.
    """
    document = service.ingest(
        text=request.text,
        source_name=request.source_name,
        source_id=request.source_id,
        title=request.title,
        source_url=request.source_url,
        chunk_size=request.chunk_size,
        overlap=request.overlap,
    )
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    limit: int = Query(default=20, ge=1, le=100),
):
    """List imported documents."""
    return service.list_documents(limit=limit)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str):
    """Get a single document by its internal UUID."""
    document = service.get_document(document_id)
    if document is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/chunks", response_model=list[DocumentChunkOut])
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


@router.post("/search", response_model=DocumentSearchResponse)
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
