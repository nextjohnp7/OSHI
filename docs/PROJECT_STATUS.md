# Project Status

## Current Phase

PHASE 0 — Foundation and Reconnaissance (Sprint 2 — Scientific Source Integration, DONE)

## Completed

- Project directory structure created at `D:\Project OSHI_MASTER_BLUEPRINT`
- Python virtual environment via `uv` (35 packages: FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, httpx, uvicorn)
- `pyproject.toml`, `.env.example`, `.gitignore`
- `packages/core/config.py` — Pydantic Settings (DATABASE_URL, LLM provider, etc.)
- `packages/core/database.py` — SQLAlchemy engine + session factory + `get_db()`
- `packages/core/models.py` — `Publication` model with provenance fields
- `packages/core/logging.py` — structured logging (JSON/plain)
- `alembic.ini` + `alembic/env.py` — configured to read DATABASE_URL from OSHI settings
- Migration `8054612ce976` — create `publications` table (applied to SQLite dev DB)
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

- `uv run pytest tests/ -v` — **18 passed, 0 failed**

## Test Results

All 18 tests pass:
- test_foundation.py: 2 passed
- test_openalex_connector.py: 5 passed
- test_crossref_connector.py: 5 passed
- test_service.py: 3 passed
- test_api_publications.py: 3 passed

Live API verification:
- OpenAlex: search + normalize + store + list (verified earlier)
- Crossref: search + normalize + store (verified live, 2 publications about "climate change")

## Known Issues

1. `oshi.egg-info/` was previously committed, then removed from tracking + added to `.gitignore` (commit `22bbf8b`). Verified clean.
2. Crossref `license` field often `None` in live API — handled gracefully (normalized to `None`).

## Technical Decisions (ADRs)

- ADR-0001: SQLite dev / PostgreSQL prod via `DATABASE_URL`
- ADR-0002: FastAPI as backend framework
- ADR-0003: OpenAlex as first scientific publication connector
- ADR-0004: Crossref as second scientific publication connector

## Blockers

None.

## Next Tasks

- Sprint 3: Document intelligence (PDF import, text extraction, chunking, embeddings, vector retrieval)
- Create `docs/research/data-source-research.md` and `docs/research/technology-evaluation.md`
- Keep `docs/PROJECT_STATUS.md` updated each session

## Files Changed (Sprint 2)

- `packages/connectors/scientific/crossref.py` (new)
- `tests/unit/test_crossref_connector.py` (new)
- `tests/unit/test_api_publications.py` (added Crossref API test)
- `apps/api/service.py` (multi-source support)
- `apps/api/schemas.py` (SearchRequest.source field)
- `apps/api/routes/publications.py` (source param on /search)
- `docs/PROJECT_STATUS.md` (updated)

## Commit References

- `4368898` — feat(backend): add structured logging and API error handling
- New Sprint 2 commit pending push

## Risks

None currently.
