# OSHI — Open Science & Humanitarian Intelligence Infrastructure

Platform open source berbasis AI untuk membuat pengetahuan ilmiah lebih mudah diakses, diverifikasi, dan diaplikasikan dalam penyelesaian masalah kemanusiaan terpenting.

Dibangun dengan **FastAPI**, **SQLAlchemy**, **Alembic**, **LangChain**, dan **LangGraph**.

## Fitur Utama

- **Publikasi Ilmiah:** Cari dan simpan publikasi dari OpenAlex dan Crossref (dedupe lintas sumber).
- **Document Intelligence:** Impor dokumen, potong teks (chunking), buat embedding, dan cari vektor (semantic search).
- **REST API:** Endpoint lengkap untuk publikasi dan dokumen (ingest, list, detail, search).
- **Database:** SQLite untuk development, PostgreSQL untuk production (via `DATABASE_URL`).
- **Migrasi:** Alembic untuk schema versioning.

## Quick Start

```bash
# Clone repo
git clone https://github.com/nextjohnp7/OSHI.git
cd OSHI

# Buat dan aktifkan venv
uv sync

# Jalankan server
uv run uvicorn apps.api.main:app --reload

# Buka dokumentasi API
# http://localhost:8000/docs
```

## Endpoint Ringkasan

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/health` | Health check |
| POST | `/api/v1/publications/search` | Cari publikasi (parameter: `q`, `source`) |
| GET | `/api/v1/publications/` | Daftar publikasi |
| GET | `/api/v1/publications/{id}` | Detail publikasi |
| POST | `/api/v1/documents/ingest` | Impor dokumen baru |
| GET | `/api/v1/documents/` | Daftar dokumen |
| GET | `/api/v1/documents/{id}` | Detail dokumen |
| GET | `/api/v1/documents/{id}/chunks` | Daftar chunk dokumen |
| POST | `/api/v1/documents/search` | Pencarian vektor (semantic search) |

## Tes

```bash
uv run pytest tests/
```

Hasil terbaru: **46 passed, 0 failed**.

## Struktur Direktori

```
OSHI/
├── apps/api/           # FastAPI aplikasi (routes, schemas, service, errors)
├── packages/core/      # Config, database, models, logging
├── packages/connectors/scientific/  # OpenAlex, Crossref connectors
├── packages/document_processing/    # Models, chunking, embeddings, retrieval, service
├── tests/unit/         # Unit tests (semua tanpa jaringan)
├── alembic/            # Database migration
├── docs/               # Dokumentasi arsitektur dan research
│   ├── adr/            # Architecture Decision Records
│   ├── architecture/   # System architecture
│   └── research/       # Data source research & technology evaluation
├── pyproject.toml      # Dependensi & konfigurasi proyek
├── alembic.ini         # Konfigurasi Alembic
└── .env.example        # Contoh variabel lingkungan
```

## Dokumentasi

- [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) — Status proyek dan roadmap
- [`docs/architecture/system-architecture.md`](docs/architecture/system-architecture.md) — Arsitektur sistem
- [`docs/adr/`](docs/adr/) — Architecture Decision Records
- [`docs/research/data-source-research.md`](docs/research/data-source-research.md) — Penelitian sumber data
- [`docs/research/technology-evaluation.md`](docs/research/technology-evaluation.md) — Evaluasi teknologi

## Lisensi

Apache-2.0 untuk perangkat lunak asli. Seluruh lisensi pihak ketiga, hak data, dan persyaratan atribusi tetap dilestarikan.
