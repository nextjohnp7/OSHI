# OSHI — Open Science & Humanitarian Intelligence Infrastructure

An open-source AI platform designed to make scientific knowledge more accessible, verifiable, and actionable for solving humanity's most important problems.

Built with **FastAPI**, **SQLAlchemy**, **Alembic**, **LangChain**, and **LangGraph**.

## Key Features

- **Scientific Publications:** Search and store publications from OpenAlex and Crossref with cross-source deduplication.
- **Document Intelligence:** Ingest documents, perform text chunking, generate embeddings, and execute vector-based semantic search.
- **REST API:** Complete endpoints for publications and documents (ingest, list, detail, search).
- **Database:** SQLite for development, PostgreSQL for production (via `DATABASE_URL`).
- **Migrations:** Alembic for schema versioning.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/nextjohnp7/OSHI.git
cd OSHI

# Create and activate the virtual environment
uv sync

# Run the server
uv run uvicorn apps.api.main:app --reload

# Open the API documentation
# http://localhost:8000/docs
```

## API Endpoints Summary

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/publications/search` | Search publications (parameters: `q`, `source`) |
| GET | `/api/v1/publications/` | List publications |
| GET | `/api/v1/publications/{id}` | Get publication details |
| POST | `/api/v1/documents/ingest` | Ingest a new document |
| GET | `/api/v1/documents/` | List documents |
| GET | `/api/v1/documents/{id}` | Get document details |
| GET | `/api/v1/documents/{id}/chunks` | List document chunks |
| POST | `/api/v1/documents/search` | Vector search (semantic search) |

## Running Tests

```bash
uv run pytest tests/
```

Latest result: **46 passed, 0 failed**.

## Project Structure

```
OSHI/
├── apps/api/               # FastAPI application (routes, schemas, service, errors)
├── packages/core/          # Configuration, database, models, logging
├── packages/connectors/scientific/  # OpenAlex and Crossref connectors
├── packages/document_processing/    # Models, chunking, embeddings, retrieval, service
├── tests/unit/             # Unit tests (no network required)
├── alembic/                # Database migrations
├── docs/                   # Documentation (architecture and research)
│   ├── adr/                # Architecture Decision Records
│   ├── architecture/       # System architecture
│   └── research/           # Data source research and technology evaluation
├── pyproject.toml          # Project dependencies and configuration
├── alembic.ini             # Alembic configuration
└── .env.example            # Example environment variables
```

## Documentation

- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — Project status and roadmap
- [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md) — System architecture
- [`docs/adr/`](docs/adr/) — Architecture Decision Records
- [`docs/research/data-source-research.md`](docs/research/data-source-research.md) — Data source research
- [`docs/research/technology-evaluation.md`](docs/research/technology-evaluation.md) — Technology evaluation

## License

Apache-2.0 for original software. All third-party licenses, data rights, and attribution requirements are preserved.
