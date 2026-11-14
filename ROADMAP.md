# OSHI Roadmap

## Vision

Build an open intelligence infrastructure that makes scientific knowledge more
usable and humanitarian information more actionable (blueprint Part 2).

## Completed

- Foundation API (FastAPI, SQLAlchemy, Alembic) — Sprint 1
- Scientific source connectors (OpenAlex, Crossref, arXiv, PubMed) — Sprint 2, 5
- Document intelligence (chunking, embedding, vector search) — Sprint 3
- LangGraph research agent — Sprint 4, 6
- Docker containerization with PostgreSQL + pgvector — Docker task
- API key authentication for all connectors — Auth task
- Auth foundation + protected routes — Sprint 7a
- Frontend MVP (dashboard, research search, crisis timeline, warnings) — Sprint 7b
- Open source governance files — Sprint 8a

## In Progress / Next

| Milestone | Description | Priority |
|-----------|-------------|----------|
| Additional API endpoints | `/api/v1/agents/`, `/api/v1/admin/`, `/api/v1/reproducibility/` | High |
| CI/CD pipeline | GitHub Actions workflow for tests | High |
| Evidence engine | Claim extraction, claim-evidence linking, contradiction detection | Medium |
| Frontend enhancements | Document reader, evidence explorer, admin UI | Medium |
| Reproducibility engine | Experiment environment, reproduction plans | Medium |
| Crisis source connectors | GDACS, ReliefWeb, BMKG, BNPB integration | Medium |
| Early warning feeds | Official warning ingestion from BMKG, NOAA | Medium |

## Long-Term (Post-MVP)

- Scientific Reproducibility Engine (SRE)
- Global Scientific Collaboration Network (GSCN) knowledge graph
- Global Crisis Intelligence Network (GCIN) with PostGIS
- Universal Early Warning Intelligence (UEWI) notification simulation
- Humanitarian Resource Intelligence (HRI)
- Disaster Knowledge Memory (DKM)
- External security review and institutional pilot testing

See blueprint Part 11 (Development Roadmap) for full phase details.

## License

OSHI is licensed under Apache-2.0. See [LICENSE](LICENSE).
