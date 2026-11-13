# System Architecture

## Overview

OSHI (Open Science & Humanitarian Intelligence Infrastructure) is a modular monolith backend platform that makes scientific knowledge more accessible, verifiable, and actionable. The initial implementation focuses on the **Open Research Intelligence (ORI)** product — scientific publication discovery, document understanding, and evidence-linked research reports.

## High-Level Data Flow

```text
External Source (OpenAlex, Crossref, ...)
        |
        v
Connector (fetch + normalize)
        |
        v
Publication Service (upsert/dedup, store)
        |
        v
PostgreSQL / SQLite (publications table)
        |
        v
FastAPI API (REST endpoints)
        |
        v
Client (web, CLI, other consumers)
```

## Layered Architecture

| Layer | Responsibility | Key Files |
|-------|---------------|-----------|
| **API** | HTTP routes, request/response validation, error handling | `apps/api/main.py`, `apps/api/routes/`, `apps/api/schemas.py` |
| **Service** | Business logic, source orchestration, database transactions | `apps/api/service.py` |
| **Connectors** | External source clients (OpenAlex, Crossref, ...), normalization | `packages/connectors/scientific/` |
| **Core** | Configuration, database engine, base models | `packages/core/config.py`, `packages/core/database.py`, `packages/core/models.py` |
| **Tests** | Unit and integration tests | `tests/unit/`, `tests/integration/` |

## Technology Stack (Foundation)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.11+ | Blueprint requirement, rich AI/ML ecosystem |
| Web Framework | FastAPI | Async support, automatic OpenAPI docs, Pydantic integration |
| ORM | SQLAlchemy 2.0 | Mature, async-ready, strong typing |
| Migrations | Alembic | Standard for SQLAlchemy, autogenerate support |
| Settings | Pydantic Settings | Type-safe env var parsing, `.env` support |
| Database (dev) | SQLite | Zero-config local development |
| Database (prod) | PostgreSQL + pgvector | Blueprint requirement, vector search for embeddings |
| Package Manager | uv | Fast, reliable, locks dependencies |
| Testing | pytest + pytest-asyncio | Standard Python testing |
| HTTP Client | httpx | Async HTTP for external API calls |

## Directory Structure

```text
oshi/
├── apps/
│   └── api/
│       ├── __init__.py
│       ├── main.py          # FastAPI app factory
│       ├── schemas.py       # Pydantic request/response models
│       ├── service.py       # Business logic
│       └── routes/
│           └── publications.py
├── packages/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic Settings
│   │   ├── database.py      # SQLAlchemy engine/session
│   │   └── models.py        # SQLAlchemy models
│   └── connectors/
│       └── scientific/
│           ├── __init__.py
│           ├── schemas.py   # NormalizedPublication
│           └── openalex.py  # OpenAlex connector
├── tests/
│   └── unit/
│       ├── test_foundation.py
│       ├── test_openalex_connector.py
│       ├── test_service.py
│       └── test_api_publications.py
├── docs/
│   ├── PROJECT_STATUS.md
│   ├── architecture/
│   │   └── system-architecture.md
│   └── adr/
│       ├── ADR-0001.md
│       ├── ADR-0002.md
│       ├── ADR-0003.md
│       └── ADR-0004.md
├── alembic/
│   ├── env.py
│   ├── versions/
│   └── ...
├── alembic.ini
├── pyproject.toml
├── .env.example
└── .gitignore
```

## Provenance Model (per Blueprint Part 6.4)

Every `Publication` record stores:
- `source_name` — e.g. "openalex"
- `source_id` — e.g. "W1587057093"
- `source_url` — original source URL
- `content_hash` — SHA-256 of source identity + title
- `license` — source license when available
- `created_at` / `updated_at` — record timestamps

Unique constraint on `(source_name, source_id)` prevents duplicates.

## Future Layers (Planned, Not Yet Implemented)

- **AI/Agent Layer** — LangChain + LangGraph for research agents (Sprint 4+)
- **Vector Search** — pgvector for semantic search (Sprint 3+)
- **Document Processing** — PDF ingestion, text chunking, embeddings (Sprint 3)
- **Frontend** — React/Next.js dashboard (Sprint 5)
- **Crisis Intelligence** — GCIN product (Phase 4)
