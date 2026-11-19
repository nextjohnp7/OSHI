# PR_DETAILS.md

## Title
feat: P1 production readiness — persistent queue (Celery + Redis), explicit embedding backend, pgvector active retrieval

## Description
Implement the P1 priorities from the latest review (commit cbb7429 / CI run 44473815729):

1. **Persistent task queue (Celery + Redis)** — ingest and research jobs now run in Celery workers backed by Redis instead of FastAPI BackgroundTasks, so jobs survive API restart and can be retried across workers. New `packages/core/celery_app.py`, `packages/worker/ingest_tasks.py`, `packages/worker/research_tasks.py`. `task_store.create()` accepts an explicit `task_id` so research `run_id == task_id`. `routes/documents.py` and `routes/research.py` use `celery_app.send_task`; `routes/agents.py` reads from `task_store`. `docker-compose.yml` adds a Redis service and `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` env on the API.

2. **Explicit embedding backend (no silent hashing fallback)** — `packages/document_processing/embeddings.py` now raises `EmbeddingBackendUnavailable` when sentence-transformers is unavailable; `OSHI_EMBEDDING_BACKEND=hashing` opts into the dev-only hashing backend explicitly. Added `get_embedding_backend_info()` (model name + dimension) for ingest/query consistency. `DEFAULT_DIM=384`, `DEFAULT_MODEL="sentence-transformers/all-MiniLM-L6-v2"`. Unit tests set `OSHI_EMBEDDING_BACKEND=hashing` so they run offline.

3. **pgvector as active retrieval path** — `DocumentChunk.embedding_vector` column (LargeBinary in ORM; `vector(384)` via migration `n7o8p9q0r1s2`), `PgVectorRetriever` uses `embedding_vector` with pgvector cosine distance, `is_available()` detects extension + column, `semantic_search` routes to pgvector in production and falls back to in-memory cosine for SQLite dev.

## Verification
- `uv run ruff check` — all checks passed
- `uv run ruff format` — clean
- Offline unit tests passing: `test_embeddings.py`, `test_auth.py`, `test_document_service.py`, `test_retrieval.py` (22 + 8 + 3 = 33 tests)
- Tests requiring `sentence-transformers` model download cannot run offline locally; they run in CI/Docker where the model/image is available.

## Files changed
- `packages/document_processing/embeddings.py`
- `packages/document_processing/models.py`
- `packages/document_processing/retrieval.py`
- `packages/document_processing/service.py`
- `packages/core/celery_app.py` (new)
- `packages/core/config.py`
- `packages/core/tasks.py`
- `packages/worker/__init__.py` (new)
- `packages/worker/ingest_tasks.py` (new)
- `packages/worker/research_tasks.py` (new)
- `apps/api/routes/documents.py`
- `apps/api/routes/research.py`
- `apps/api/routes/agents.py`
- `docker-compose.yml`
- `pyproject.toml`
- `tests/unit/conftest.py`
- `tests/unit/test_embeddings.py`
- `alembic/versions/n7o8p9q0r1s2_add_embedding_vector_column.py` (new)

## Linked issues
P1 review items: durable queue, embedding production consistency, pgvector active retrieval.
