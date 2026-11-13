# Repository Reconnaissance

Technical reconnaissance of upstream open-source repositories referenced in the OSHI blueprint (Part 13). This document records each repository's purpose, architecture, licensing, and integration relevance so OSHI can adopt documented interfaces without copying large portions of upstream code.

Status: Initial reconnaissance. Version numbers and license terms should be re-verified before production adoption.

## 1. langchain-ai/langchain

| Field | Value |
|-------|-------|
| URL | https://github.com/langchain-ai/langchain |
| License | MIT |
| Default branch | master |
| Latest release (observed) | langchain==1.5.0 (2026-11-11) |
| Stars / Forks | ~149k / ~25k |
| Open issues | ~742 |
| Minimum Python | 3.11 (as of 1.5.0) |

### Main purpose
Agent engineering platform providing model abstraction, document loading, text processing, embedding integrations, retrieval interfaces, tool definitions, structured output, and model integration.

### Relevant architecture
- `langchain-core`: base abstractions (LLM, chat model, embeddings, vector stores, retrievers, tools, callbacks).
- `langchain`: higher-level chains, agents, and toolkits built on langchain-core.
- Provider packages (e.g. langchain-openai, langchain-anthropic) for model integrations.
- Community integrations maintained in separate packages.

### Reusable concepts for OSHI
- Model provider abstraction (OSHI should not bind to one AI provider — Part 14.1).
- Document loading and text splitting pipeline.
- Retriever interface for vector search (compatible with pgvector / in-memory fallback).
- Tool calling and structured output (Pydantic-based).

### Integration opportunities
- LangChain document loaders for permitted document import (Sprint 3).
- Embedding integrations via `langchain-community` or `langchain-huggingface`.
- Retriever interface wrapping OSHI's pgvector or in-memory cosine search.

### Technical limitations
- Large surface area; OSHI should adopt only the abstractions it needs.
- Rapid release cadence; pin versions to avoid breaking changes.

### License considerations
- MIT license: permissive, compatible with OSHI's Apache-2.0 strategy. Attribution required.

### Recommended learning path
- https://docs.langchain.com/langchain/ — official docs.
- Review `langchain-core` abstractions before adopting higher-level `langchain` packages.

---

## 2. langchain-ai/langgraph

| Field | Value |
|-------|-------|
| URL | https://github.com/langchain-ai/langgraph |
| License | MIT |
| Default branch | master |
| Latest release (observed) | langgraph==1.2.21 (2026-11-12) |
| Stars / Forks | Not observed in search |
| Open issues | Not observed in search |

### Main purpose
Stateful, multi-step agent orchestration library. Enables graph-based workflows with cycles, persistence (checkpointing), human-in-the-loop interrupts, and multi-agent supervision.

### Relevant architecture
- `StateGraph`: nodes + edges defining a state machine over a typed state dict.
- `checkpoint`: persistence for resuming long-running graph executions.
- `interrupt` / `Command`: human-in-the-loop approval gates.
- `send`: multi-agent fan-out / dynamic routing.

### Reusable concepts for OSHI
- Research agent workflow: `discover → retrieve → generate` (implemented in Sprint 4/6).
- Crisis report generation with human approval gates (Part 5.5).
- Long-running data processing with resumable checkpoints.

### Integration opportunities
- `packages/agents/research/graph.py` already uses LangGraph `StateGraph`.
- Future: `langgraph-supervisor` for multi-agent coordination patterns.

### Technical limitations
- Graph state must be serializable for checkpointing.
- Human-in-the-loop requires an approval UI or API endpoint (not yet implemented in OSHI).

### License considerations
- MIT license: permissive, compatible with Apache-2.0. Attribution required.

### Recommended learning path
- https://langchain-ai.github.io/langgraph/ — official docs.
- Study `StateGraph` and `checkpoint` before adding more agent graphs.

---

## 3. langchain-ai/langgraph-supervisor

| Field | Value |
|-------|-------|
| URL | https://github.com/langchain-ai/langgraph-supervisor |
| License | MIT (expected, same org) |
| Default branch | master |
| Status | Referenced in blueprint Part 13; not yet inspected in detail |

### Main purpose
Multi-agent supervision patterns built on LangGraph. Enables coordinator-worker agent topologies.

### Relevant architecture
- Supervisor node that routes tasks to specialized worker agents.
- Handoff mechanisms between agents.

### Reusable concepts for OSHI
- `ResearchCoordinator` → `PublicationDiscoveryAgent`, `DocumentExtractionAgent`, etc. (Part 5.3).
- `CrisisCoordinator` → `SourceMonitoringAgent`, `EventExtractionAgent`, etc. (Part 5.3).

### Integration opportunities
- Future sprints: replace the single research graph with a supervisor-topology graph when multi-agent coordination is needed.

### Technical limitations
- Not yet adopted in OSHI; add only when a single graph is insufficient.

### License considerations
- Expected MIT; verify before adoption.

### Recommended learning path
- https://github.com/langchain-ai/langgraph-supervisor — README and examples.

---

## 4. pgvector/pgvector

| Field | Value |
|-------|-------|
| URL | https://github.com/pgvector/pgvector |
| License | MIT (PostgreSQL extension) |
| Default branch | master |
| Latest release (observed) | Active; Docker image `ankane/pgvector` used in OSHI docker-compose |
| Stars / Forks | Not observed in search |
| Open issues | Not observed in search |

### Main purpose
Open-source vector similarity search extension for PostgreSQL. Supports exact and approximate nearest neighbor search with multiple distance functions (cosine, L2, inner product) and vector types (float, half, binary, sparse).

### Relevant architecture
- SQL extension: `vector` type, `<=>` (cosine distance), `<->` (L2 distance), `<#>` (negative inner product).
- Index types: HNSW (approximate), IVFFlat (approximate), exact (no index).
- Operators integrated into PostgreSQL query planner.

### Reusable concepts for OSHI
- `packages/document_processing/retrieval.py` already includes `PgVectorRetriever` using `1 - (embedding <=> :query)` for cosine similarity.
- Production vector search alongside relational data (Part 4.3).

### Integration opportunities
- `docker-compose.yml` uses `ankane/pgvector` image.
- Future: migrate from in-memory cosine search to pgvector for production-scale document search.

### Technical limitations
- Requires PostgreSQL with pgvector extension installed.
- Approximate indexes trade recall for speed; exact search is slower on large datasets.

### License considerations
- MIT license; PostgreSQL extension distributed as source/SQL. Attribution required.

### Recommended learning path
- https://github.com/pgvector/pgvector — README and SQL examples.
- Test HNSW vs exact recall/performance with OSHI embedding dimensions.

---

## 5. postgis/postgis

| Field | Value |
|-------|-------|
| URL | https://github.com/postgis/postgis |
| License | GPL-2.0 (PostGIS extension) |
| Default branch | master |
| Status | Referenced in blueprint Part 4.2 (GEO[(PostGIS)]); not yet adopted in OSHI |

### Main purpose
Spatial and geographic object extension for PostgreSQL. Enables storage and querying of geometry/geography types, coordinates, and spatial relationships.

### Relevant architecture
- `geometry` / `geography` column types.
- Spatial indexes (GiST, SP-GiST).
- Spatial functions (distance, intersection, within, etc.).

### Reusable concepts for OSHI
- Part 3.4 (GCIN) geographic intelligence: administrative regions, coordinates, event locations, impact areas.
- Part 4.2 architecture diagram includes GEO[(PostGIS)].

### Integration opportunities
- Future: disaster event geolocation, impact area mapping, geographic similarity retrieval (Part 7.7, Part 3.4.E).
- Future: `docker-compose` could add a PostGIS container alongside pgvector.

### Technical limitations
- GPL-2.0 license: stronger copyleft than MIT/Apache-2.0. Verify compatibility with OSHI's license strategy.
- Additional operational complexity (PostGIS installation, spatial index tuning).

### License considerations
- GPL-2.0 may impose obligations on derivative works. OSHI evaluates Apache-2.0 for original software; confirm PostGIS inclusion does not conflict.

### Recommended learning path
- https://postgis.net/ — official docs and tutorials.

---

## 6. fastapi/fastapi

| Field | Value |
|-------|-------|
| URL | https://github.com/fastapi/fastapi |
| License | MIT |
| Default branch | master |
| Latest release (observed) | 0.162.5 (recent), 0.158.x (Oct 2026 tags) |
| Stars / Forks | Not observed in search |
| Open issues | Not observed in search |

### Main purpose
High-performance Python web API framework built on Starlette and Pydantic. Automatic OpenAPI/Swagger documentation, async/await support, dependency injection, and data validation.

### Relevant architecture
- `FastAPI` app with route decorators (`@app.get`, `@app.post`).
- Pydantic `BaseModel` for request/response schemas.
- Dependency injection (`Depends`).
- Middleware support (CORS, authentication, logging).
- Starlette-based routing and ASGI server compatibility.

### Reusable concepts for OSHI
- `apps/api/main.py` — FastAPI app factory with `/health`, error handlers, and routers.
- `apps/api/schemas.py` — Pydantic models for all API contracts.
- `apps/api/routes/*` — versioned REST endpoints (`/api/v1/publications`, `/api/v1/documents`, `/api/v1/research`).

### Integration opportunities
- Future: add authentication middleware, rate limiting, and OpenAPI customization per Part 10.

### Technical limitations
- Async endpoints require async-compatible database drivers (psycopg2 is sync; consider asyncpg for high-concurrency production).
- Pydantic v2 migration considerations.

### License considerations
- MIT license: permissive, compatible with Apache-2.0. Attribution required.

### Recommended learning path
- https://fastapi.tiangolo.com/ — official docs and tutorial.

---

## 7. open-webui/open-webui

| Field | Value |
|-------|-------|
| URL | https://github.com/open-webui/open-webui |
| License | Not observed in search (verify) |
| Default branch | Not observed (verify) |
| Status | Referenced in blueprint Part 13 as AI interface design reference; not yet inspected in detail |

### Main purpose
Self-hosted AI interface (web UI) for interacting with LLMs. Provides chat interface, document upload, model management, and user access control.

### Relevant architecture
- Frontend web application communicating with LLM backends via API.
- User management, workspaces, document collections.
- Extensible through functions/tools and pipelines.

### Reusable concepts for OSHI
- Part 9.1 main application structure: dashboard, research intelligence, crisis intelligence, early warning, humanitarian coordination, knowledge memory.
- Chat-style research conversation interface (Sprint 5 frontend).
- Document upload and citation display.

### Integration opportunities
- Future: OSHI frontend could draw UI patterns from Open WebUI (chat, citations, document viewer).
- Not a mandatory dependency; OSHI backend is API-first.

### Technical limitations
- Not yet adopted; verify license compatibility before any code reuse.

### License considerations
- Verify license before adoption; blueprint requires license compatibility check (Rule A).

### Recommended learning path
- https://github.com/open-webui/open-webui — README and documentation.

---

## Summary Table

| Repository | License | Adopted in OSHI | Purpose in OSHI |
|------------|---------|-----------------|-----------------|
| langchain-ai/langchain | MIT | Partial (via langchain-core abstractions) | Model abstraction, document processing, retrieval |
| langchain-ai/langgraph | MIT | Yes | Research agent state machine (Sprint 4/6) |
| langchain-ai/langgraph-supervisor | MIT (expected) | No | Future multi-agent coordination |
| pgvector/pgvector | MIT | Partial (PgVectorRetriever class) | Production vector search (PostgreSQL) |
| postgis/postgis | GPL-2.0 | No | Future geographic intelligence (GCIN) |
| fastapi/fastapi | MIT | Yes | Backend API framework |
| open-webui/open-webui | Verify | No | Frontend UI design reference |

## Next Actions

1. Verify licenses of all adopted repositories before production release (Part 15.4).
2. Pin LangChain/LangGraph versions in `pyproject.toml` to avoid breaking changes.
3. Evaluate `langgraph-supervisor` when multi-agent coordination is required (future sprint).
4. Re-evaluate PostGIS adoption given GPL-2.0 copyleft implications.
