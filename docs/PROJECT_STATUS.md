# Project Status

## Current Phase

PHASE 0 — Foundation and Reconnaissance (Sprint 0 in progress)

## Completed

- Project directory structure created at `D:\Project OSHI_MASTER_BLUEPRINT`
- Python virtual environment configured via `uv` (35 packages: FastAPI, SQLAlchemy, Alembic, Pydantic, pytest, httpx, uvicorn)
- `pyproject.toml` with build config (setuptools), dependencies, and pytest settings
- `.env.example` and `.gitignore`
- `packages/core/config.py` — Pydantic Settings (DATABASE_URL, LLM provider, etc.)
- `packages/core/database.py` — SQLAlchemy engine + session factory + `get_db()`
- `packages/core/models.py` — `Publication` model with provenance fields (source_name, source_id, content_hash, etc.)
- `alembic.ini` + `alembic/env.py` — configured to read DATABASE_URL from OSHI settings
- Migration `8054612ce976` — create `publications` table (applied to SQLite dev DB)
- `packages/connectors/scientific/openalex.py` — OpenAlex connector (search + normalize)
- `packages/connectors/scientific/schemas.py` — `NormalizedPublication` schema
- `apps/api/main.py` — FastAPI app with `/health` endpoint + publications router
- `apps/api/routes/publications.py` — `POST /search`, `GET /`, `GET /{id}`
- `apps/api/schemas.py` — `PublicationOut`, `SearchRequest`, `SearchResponse`, `HealthOut`
- `apps/api/service.py` — `PublicationService` (search_and_store upsert/dedup, search_stored)
- `tests/unit/test_foundation.py` — 2 tests (health endpoint)
- `tests/unit/test_openalex_connector.py` — 5 tests (normalization, no network)
- `tests/unit/test_service.py` — 3 tests (insert, upsert/dedup, filters, in-memory SQLite)
- `tests/unit/test_api_publications.py` — 2 tests (API routes, connector tiruan) — **2 FAILING** (see Known Issues)
- Repository pushed to GitHub: `https://github.com/nextjohnp7/OSHI` (commit `6c4a1ae`, branch `main`)

## In Progress

- Fix 2 failing API integration tests (`id: UUID` pydantic validation in `PublicationOut`)

## Tests Executed

- `uv run pytest tests/ -v` — 10 passed, 2 failed (before UUID fix)
- After UUID fix in `apps/api/schemas.py` (`id: UUID`), tests **not yet re-run**

## Test Results

- `test_foundation.py::test_health_endpoint_returns_ok` — PASSED
- `test_foundation.py::test_health_endpoint_shape` — PASSED
- `test_openalex_connector.py::test_reconstruct_abstract` — PASSED
- `test_openalex_connector.py::test_extract_authors` — PASSED
- `test_openalex_connector.py::test_work_id` — PASSED
- `test_openalex_connector.py::test_normalize_roundtrip` — PASSED
- `test_openalex_connector.py::test_normalize_missing_fields` — PASSED
- `test_service.py::test_search_and_store_inserts` — PASSED
- `test_service.py::test_search_and_store_upsert_dedupes` — PASSED
- `test_service.py::test_search_stored_filters` — PASSED
- `test_api_publications.py::test_search_endpoint_returns_stored_records` — FAILED (UUID validation)
- `test_api_publications.py::test_list_endpoint_returns_stored` — FAILED (UUID validation)

## Known Issues

1. `PublicationOut.id` was `str` but SQLAlchemy returns `UUID` object — Pydantic `from_attributes` validation failed. Fixed in `apps/api/schemas.py` (changed to `UUID`), tests not yet re-run.
2. `oshi.egg-info/` accidentally committed to Git — should be removed from tracking and added to `.gitignore`.
3. OpenAlex real-endpoint test (end-to-end with live API) verified manually but not committed as an automated test (network-dependent).

## Technical Decisions

- SQLite for local development; PostgreSQL for production via `DATABASE_URL` env variable (no code change)
- FastAPI + Pydantic v2 for backend API
- SQLAlchemy 2.0 + Alembic for ORM and migrations
- OpenAlex as first scientific publication connector (no API key required for basic usage)
- `uv` for Python package management

## Blockers

None.

## Next Tasks

1. Re-run all tests after UUID fix (verify 12/12 pass)
2. Remove `oshi.egg-info` from Git tracking + add to `.gitignore`
3. Create architecture documentation (`docs/architecture/system-architecture.md`)
4. Create ADRs (ADR-0001 to ADR-0004)
5. Implement Sprint 1 backend foundation (logging, error handling, config validation)
6. Implement Sprint 2: Crossref connector

## Files Changed (this session)

- `docs/PROJECT_STATUS.md` (new)
- `docs/architecture/system-architecture.md` (new)
- `docs/adr/ADR-0001.md` through `ADR-0004.md` (new)

## Commit References

- `6c4a1ae` — pushed to `https://github.com/nextjohnp7/OSHI` (main)

## Risks

- None currently.
