# Project Status

## Current Phase

PHASE 0 — Foundation and Reconnaissance (Auth middleware + protected routes, DONE)

## Completed

- Project directory structure created at `D:\Project OSHI_MASTER_BLUEPRINT`
- Python virtual environment via `uv` (35 packages: FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, httpx, uvicorn)
- `pyproject.toml`, `.env.example`, `.gitignore`
- `packages/core/config.py` — Pydantic Settings (DATABASE_URL, LLM provider, etc.)
- `packages/core/database.py` — SQLAlchemy engine + session factory + `get_db()`
- `packages/core/models.py` — `Publication`, `Organization`, `User`, `OrganizationMember`, `APIKey` models (provenance + multi-tenant auth)
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

- `uv run pytest tests/ -v` — **73 passed, 0 failed**

## Test Results

All 64 tests pass:
- test_foundation.py: 2 passed
- test_openalex_connector.py: 5 passed
- test_crossref_connector.py: 5 passed
- test_service.py: 3 passed
- test_api_publications.py: 3 passed
- test_chunking.py: 5 passed
- test_embeddings.py: 12 passed
- test_retrieval.py: 3 passed
- test_document_service.py: 7 passed
- test_research_agent.py: 4 passed
- test_arxiv_connector.py: 5 passed
- test_pubmed_connector.py: 5 passed
- test_auth_models.py: 4 passed
- test_auth.py: 7 passed

Live API verification:
- OpenAlex: search + normalize + store + list (verified earlier)
- Crossref: search + normalize + store (verified live, 2 publications about "climate change")

## Known Issues

1. `oshi.egg-info/` was previously committed, then removed from tracking + added to `.gitignore` (commit `22bbf8b`). Verified clean.
2. Crossref `license` field often `None` in live API — handled gracefully (normalized to `None`).
3. Embedding defaults to deterministic hashing-trick (128-dim) when sentence-transformers model cannot be downloaded (no network). Set `OPENAI_API_KEY` or install model for semantic embeddings.
4. Frontend MVP not yet built (Sprint 7 optional).

## Technical Decisions (ADRs)

- ADR-0001: SQLite dev / PostgreSQL prod via `DATABASE_URL`
- ADR-0002: FastAPI as backend framework
- ADR-0003: OpenAlex as first scientific publication connector
- ADR-0004: Crossref as second scientific publication connector

## Blockers

None.

## Next Tasks

- Sprint 7: Frontend MVP (dashboard, publication search, document reader) — optional
- Keep `docs/PROJECT_STATUS.md` updated each session

## Files Changed (Sprint 3 + Research + Auth + Docker)

- `packages/document_processing/__init__.py` (new)
- `packages/document_processing/models.py` (new)
- `packages/document_processing/chunking.py` (new)
- `packages/document_processing/embeddings.py` (upgraded: sentence-transformers + hashing fallback)
- `packages/document_processing/retrieval.py` (new)
- `packages/document_processing/service.py` (new)
- `apps/api/routes/documents.py` (new)
- `apps/api/main.py` (documents router wired)
- `apps/api/schemas.py` (document schemas added)
- `alembic/env.py` (document models registered)
- `alembic/versions/e065afc05779_create_documents_and_document_chunks_.py` (new migration)
- `tests/unit/test_chunking.py` (new)
- `tests/unit/test_embeddings.py` (new, upgraded)
- `tests/unit/test_retrieval.py` (new)
- `tests/unit/test_document_service.py` (new)
- `packages/core/models.py` (auth models added)
- `packages/core/config.py` (connector credential settings added)
- `packages/connectors/scientific/arxiv.py` (new)
- `packages/connectors/scientific/pubmed.py` (new)
- `packages/agents/research/__init__.py` (new)
- `packages/agents/research/graph.py` (new)
- `packages/agents/research/nodes.py` (new)
- `packages/agents/research/state.py` (new)
- `apps/api/routes/research.py` (new)
- `tests/unit/test_arxiv_connector.py` (new)
- `tests/unit/test_pubmed_connector.py` (new)
- `tests/unit/test_research_agent.py` (new)
- `tests/unit/test_auth_models.py` (new)
- `Dockerfile` (new)
- `docker-compose.yml` (new)
- `.env.example` (connector credential variables added)
- `docs/PROJECT_STATUS.md` (updated)
- `docs/research/data-source-research.md` (new)
- `docs/research/disaster-source-research.md` (new)
- `docs/research/technology-evaluation.md` (new)
- `docs/research/repository-reconnaissance.md` (new)
- `docs/architecture/database-design.md` (new)
- `docs/SECURITY_REVIEW.md` (new)
- `docs/TESTING_STRATEGY.md` (new)

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

## Risks

None currently.
