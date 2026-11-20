# Project Status

## Current Phase

PHASE 0 — Foundation and Reconnaissance (Sprint 10 — Production hardening, observability, frontend enhancements, DONE)

## Completed

- Project directory structure created at `D:\Project OSHI_MASTER_BLUEPRINT`
- Python virtual environment via `uv` (35 packages: FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, httpx, uvicorn)
- `pyproject.toml`, `.env.example`, `.gitignore`
- `packages/core/config.py` — Pydantic Settings (DATABASE_URL, LLM provider, etc.)
- `packages/core/database.py` — SQLAlchemy engine + session factory + `get_db()`
- `packages/core/models.py` — `Publication`, `Organization`, `User`, `OrganizationMember`, `APIKey`, `DisasterEvent`, `GeographicRegion`, `EventLocation`, `EventReport`, `OfficialWarning`, `SituationReport` models (provenance + multi-tenant auth + crisis intelligence)
- `packages/core/auth.py` — API key hashing, verification, `require_api_key` / `get_current_user` dependencies
- `packages/core/logging.py` — structured logging (JSON/plain)
- `alembic.ini` + `alembic/env.py` — configured to read DATABASE_URL from OSHI settings
- Migration `8054612ce976` — create `publications` table (applied to SQLite dev DB)
- Migration `e065afc05779` — create `documents` and `document_chunks` tables
- Migration `9d3c5ad41c6f` — auth tables: `organizations`, `users`, `organization_members`, `api_keys`
- `packages/connectors/scientific/openalex.py` — OpenAlex connector (search + normalize) — **live API verified**
- `packages/connectors/scientific/crossref.py` — Crossref connector (search + normalize) — **live API verified**
- `packages/connectors/scientific/schemas.py` — `NormalizedPublication` schema
- `apps/api/main.py` — FastAPI app with `/health`, logging + error handlers wired
- `apps/api/routes/publications.py` — `POST /search` (with `source` param), `GET /`, `GET /{id}`
- `apps/api/routes/crisis.py` — `GET/POST /crisis/events`, `GET /crisis/timeline`, `GET /crisis/verification`, `GET/POST /warnings/official`, `POST /warnings/translations`, `GET /warnings/preparedness`
- `apps/api/schemas.py` — `PublicationOut`, `SearchRequest` (with `source`), `SearchResponse`, `HealthOut`
- `apps/api/service.py` — `PublicationService` multi-source (connectors dict, default_source, upsert/dedup)
- `apps/api/errors.py` — FastAPI exception handlers (SQLAlchemy, Pydantic, generic) with request ID
- `tests/unit/test_foundation.py` — 2 tests (health endpoint)
- `tests/unit/test_openalex_connector.py` — 5 tests (normalization, no network)
- `tests/unit/test_crossref_connector.py` — 5 tests (normalization, no network)
- `tests/unit/test_service.py` — 3 tests (insert, upsert/dedup, filters, in-memory SQLite)
- `tests/unit/test_api_publications.py` — 3 tests (OpenAlex API, list, Crossref API) — connector tiruan
- Repository pushed to GitHub: `https://github.com/nextjohnp7/OSHI`

## In Progress

None.

## Tests Executed

- `uv run pytest tests/ -v` — **92 passed, 0 failed, 0 skipped** (PostgreSQL integration tests skip when no Docker/psql locally)

## Test Results

- test_foundation.py: 2 passed
- test_openalex_connector.py: 5 passed
- test_crossref_connector.py: 5 passed
- test_service.py: 3 passed
- test_api_publications.py: 3 passed
- test_chunking.py: 5 passed
- test_embeddings.py: 12 passed
- test_retrieval.py: 3 passed
- test_document_service.py: 8 passed
- test_research_agent.py: 4 passed
- test_arxiv_connector.py: 5 passed
- test_pubmed_connector.py: 5 passed
- test_auth_models.py: 4 passed
- test_auth.py: 7 passed
- test_crisis_warning.py: 8 passed
- test_task_persistence.py: 6 passed (task persistence + e2e ingest flow)
- tests/integration/test_postgresql.py: 2 skipped (requires PostgreSQL + pgvector via Docker)

Live API verification:
- OpenAlex: search + normalize + store + list (verified earlier)
- Crossref: search + normalize + store (verified live, 2 publications about "climate change")

## Known Issues

1. `oshi.egg-info/` was previously committed, then removed from tracking + added to `.gitignore` (commit `22bbf8b`). Verified clean.
2. Crossref `license` field often `None` in live API — handled gracefully (normalized to `None`).
3. Embedding defaults to deterministic hashing-trick (128-dim) when sentence-transformers model cannot be downloaded (no network). Set `OPENAI_API_KEY` or install model for semantic embeddings.
4. PostgreSQL integration tests (`tests/integration/test_postgresql.py`) skip locally — no Docker/PostgreSQL available. Verify on CI with service container or Docker.
5. Crisis map markers are demonstrative (random coordinates around Indonesia). Replace with real `event_locations` data when PostGIS integration is complete.
6. Rate limiting is in-memory sliding window (single-worker). For multi-worker production, replace store with Redis.

## Technical Decisions (ADRs)

- ADR-0001: SQLite dev / PostgreSQL prod via `DATABASE_URL`
- ADR-0002: FastAPI as backend framework
- ADR-0003: OpenAlex as first scientific publication connector
- ADR-0004: Crossref as second scientific publication connector

## P1 Production Readiness (commit 8960890, 89115fa)

- **Durable queue**: Celery + Redis worker (`packages/core/celery_app.py`, `packages/worker/`), `routes/documents.py` & `routes/research.py` use `celery_app.send_task`; eager mode (`CELERY_EAGER=true`) for tests/dev without Redis.
- **Explicit embedding backend**: `embed_text`/`embed_texts` raise `EmbeddingBackendUnavailable` without silent hashing fallback; `OSHI_EMBEDDING_BACKEND=hashing` opts into dev-only hashing; `get_embedding_backend_info()` exposes model identity.
- **pgvector active retrieval**: `embedding_vector vector(384)` column via migration; `PgVectorRetriever` uses pgvector cosine distance; `is_available()` checks extension + column; `semantic_search` routes to pgvector in production, falls back to in-memory cosine for SQLite.
- **Docker/CI**: Dockerfile installs `--group prod` (Celery, Redis, pgvector, sentence-transformers); CI uses `uv sync --dev --group prod` + Redis service container; `docker-compose.yml` adds Celery worker service + Redis persistence.

## Blockers

None.

## Next Tasks

- Run PostgreSQL + pgvector integration tests on CI/GitHub Actions with service container
- PostGIS integration for crisis map (connect Leaflet markers to real `event_locations` data)
- Observability enhancements: distributed tracing, detailed metrics
- Production hardening: rate limiting via Redis, CORS origin restriction, input sanitization review

## Files Changed (Sprint 9 — Task Persistence + Integration Tests)

- `packages/core/models.py` — `Task` model added
- `packages/core/tasks.py` — rewritten DB-backed `TaskStore` + `_json_safe`
- `alembic/versions/7e90140cf32c_add_task_persistence_table.py` — new migration
- `apps/api/schemas.py` — `task_type` added to `TaskResponse`/`TaskStatusOut`; `id` → `task_id`
- `apps/api/routes/tasks.py` — `GET /api/v1/tasks` (list), `DELETE /api/v1/tasks/{task_id}` (cancel)
- `apps/api/routes/documents.py` — POST uses DB-backed `task_store` with `task_type`
- `apps/api/routes/research.py` — POST uses DB-backed `task_store` with `task_type`
- `tests/unit/test_task_persistence.py` — new (6 integration tests)

## Files Changed (Sprint 10 — Production Hardening, Observability, Frontend Enhancements)

- `packages/core/middleware.py` — new (`RateLimitMiddleware`, `add_cors_middleware`)
- `apps/api/main.py` — CORS + rate limiting middleware wired; `/health` enhanced with `pending_tasks`
- `apps/api/routes/metrics.py` — new (Prometheus `/api/v1/metrics`)
- `apps/api/routes/documents.py` — input sanitization (strip control chars)
- `apps/web/index.html` — document reader modal + Leaflet.js crisis map
- `tests/integration/test_postgresql.py` — new (skipif no Docker)

## Commit References

- `4368898` — feat(backend): add structured logging and API error handling
- `8558b34` — feat(sprint2): add Crossref connector and multi-source publication service
- `e10e050` — feat(sprint3): document intelligence - ingest, chunk, embed, semantic search
- `e6c2d5a` — chore(build): remove temp hermes file and ignore .hermes-tmp
- `cdb8e60` — feat(embedding): upgrade to sentence-transformers with hashing-trick fallback
- `5324c65` — docs(research): add data source research and technology evaluation
- `8546862` — docs: rewrite README.md in formal English
- `191ba52` — feat(sprint4): research agent workflow - LangGraph publication discovery, evidence retrieval, report generation
- `bd80dcb` — feat(sprint5): pgvector production vector search, arXiv and PubMed connectors
- `2e51ee3` — feat(sprint6): integrate arxiv and pubmed into research agent discovery
- `09ab1ff` — feat(docker): containerize for production with PostgreSQL + pgvector
- `7d4d0f5` — feat(auth): API key / mailto support for all scientific connectors
- `9a7ad4a` — feat(sprint7a): Crisis Intelligence and Early Warning API endpoints
- `af48871` — feat(sprint7b): Frontend MVP dashboard
- `6d8a0f9` — feat(sprint8): Open source governance, agents/admin API, CI/CD
- `5122ffc` — fix: resolve ruff CI failures
- `fa8fdfa` — feat(sprint8b): background tasks, retry mechanism, CI lint, API docs
- `e4a936d` — feat(sprint9): task persistence + integration tests
- `c8118db` — feat(sprint10): production hardening, observability, frontend enhancements

## Risks

None currently.
