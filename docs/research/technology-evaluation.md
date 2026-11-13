# Technology Evaluation

## Overview

Documentasi evaluasi teknologi yang dipilih untuk arsitektur OSHI. Termasuk alasan seleksi, perbandingan dengan alternatif, dan pengambilan keputusan yang tercermin dalam ADR (Architecture Decision Records).

## Backend Framework

### FastAPI (Terpilih — ADR-0002)

- **URL:** https://fastapi.tiangolo.com
- **Versi:** 0.100+
- **Keunggulan:**
  - Async/await native support (Python 3.11+)
  - Otomatis OpenAPI/Swagger documentation
  - Pydantic-based data validation
  - Tinggi performa (dibawah Starlette + Pydantic)
  - Dependensi injection yang bersih
- **Alternatif yang dipertimbangkan:**
  - Flask: lebih sederhana tetapi async support terbatas
  - Django: terlalu berat untuk microservice API
  - Flask-RESTful: kurang modern dibanding FastAPI
- **Keputusan:** FastAPI dipilih karena performa tinggi, developer experience yang baik, dan dukungan async untuk integrasi AI/LLM.

## Database & ORM

### SQLAlchemy 2.0 + Alembic (Terpilih — ADR-0001)

- **URL:** https://www.sqlalchemy.org, https://alembic.sqlalchemy.org
- **Keunggulan:**
  - ORM yang matang dan fleksibel
  - Alembic untuk database migration
  - Dukungan SQLite (dev) dan PostgreSQL (prod) dengan DATABASE_URL
  - Type safety dengan Mapped[...] dan typed columns
- **Alternatif yang dipertimbangkan:**
  - Databases + SQLAlchemy Core: lebih rendah level, lebih banyak boilerplate
  - Tortoise ORM: lebih sederhana tetapi ekosistem lebih kecil
  - MongoDB: tidak cocok untuk data relasial publikasi
- **Keputusan:** SQLAlchemy 2.0 + Alembic dipilih karena fleksibilitas migrasi antar SQLite/PostgreSQL tanpa perubahan kode.

### Database Dev: SQLite

- **File:** `oshi_dev.db` (tidak di-track Git)
- **Tujuan:** Development dan testing lokal tanpa setup PostgreSQL

### Database Produksi: PostgreSQL

- **Konfigurasi:** Via `DATABASE_URL` environment variable
- **Ekstensi potensial:** pgvector untuk pencarian vektor (Sprint 5+)

## Embedding & Vector Search

### Sentence Transformers / all-MiniLM-L6-v2 (Terpilih)

- **URL:** https://www.sbert.net
- **Model:** sentence-transformers/all-MiniLM-L6-v2 (384-dim, ~80 MB)
- **Keunggulan:**
  - Embedding semantik berkualitas tinggi
  - Ringan (cocok untuk CPU inference)
  - Normalisasi cosine bawaan
  - Cocok untuk pencarian dokumen ilmiah
- **Keterbatasan:**
  - Memerlukan download model (~80 MB)
  - Inference lebih lambat dari hashing trick
- **Fallback:** Hashing trick (deterministik, 128-dim, tanpa dependensi ML)
- **Status:** Sudah diimplementasi di `packages/document_processing/embeddings.py` dengan switch otomatis

### Alternatif yang dipertimbangkan

- **OpenAI embeddings:** Biaya per token, dependensi jaringan, tidak cocok untuk deployment offline
- **HuggingFace transformers langsung:** Lebih banyak boilerplate, tidak ada pooling/normalisasi bawaan
- **pgvector (PostgreSQL):** Untuk production vector search (Sprint 5+), menggantikan in-memory cosine similarity

## AI Agent Framework

### LangChain + LangGraph (Direncanakan — Sprint 4+)

- **URL:** https://langchain.com, https://langchain-ai.github.io/langgraph
- **Keunggulan:**
  - Ekosistem komponen AI yang luas (LLM, vector store, tools, agents)
  - LangGraph untuk stateful agent workflow (dibutuhkan untuk research agent)
  - Integrasi dengan FastAPI melalui dependency injection
- **Alternatif yang dipertimbangkan:**
  - LlamaIndex: lebih fokus pada RAG, kurang fleksibel untuk multi-agent workflow
  - AutoGPT: terlalu spesifik, kurang dapat dikustomisasi
  - Custom agent loop: lebih banyak kode yang harus ditulis sendiri
- **Keputusan:** LangChain + LangGraph dipilih karena ekosistem matang dan dukungan workflow agen yang stateful.

## Testing

### pytest + httpx (Terpilih)

- **URL:** https://pytest.org, https://www.encode.io/httpx
- **Keunggulan:**
  - pytest: standar de facto untuk Python testing
  - httpx: async HTTP client untuk tes API (terbaik untuk FastAPI TestClient)
  - sqlite in-memory untuk tes database tanpa side effect
- **Cakupan:** 46 tes unit (semua lolos), tidak tergantung jaringan eksternal

## Tabel Ringkasan Teknologi

| Layer | Teknologi | Versi | Status |
|-------|-----------|-------|--------|
| Backend Framework | FastAPI | 0.100+ | Terpilih (ADR-0002) |
| ORM | SQLAlchemy 2.0 | 2.0+ | Terpilih |
| Migration | Alembic | 1.13+ | Terpilih |
| Database Dev | SQLite | - | Terpilih (ADR-0001) |
| Database Prod | PostgreSQL | 15+ | Terpilih (ADR-0001) |
| Embedding | sentence-transformers | 4.x | Terpilih (fallback: hashing) |
| Vector Search | In-memory cosine (dev), pgvector (prod) | - | Terpilih |
| Agent Framework | LangChain + LangGraph | 0.1+ | Direncanakan (Sprint 4) |
| Testing | pytest + httpx | 8.x + 0.27+ | Terpilih |
| Container | Docker (opsional) | - | Belum diputuskan |

## Risiko & Mitigasi

| Risiko | Dampak | Mitigasi |
|--------|--------|----------|
| Model download gagal (tidak ada jaringan) | Embedding fallback ke hashing trick (kualitas lebih rendah) | Fallback otomatis terimplementasi |
| PostgreSQL pgvector tidak tersedia | Vector search menggunakan in-memory cosine (terbatas pada dataset kecil) | Strategi pgvector dapat diimplementasikan nanti |
| LangChain/LangGraph breaking change | Agent workflow perlu diulis ulang | Pin versi, gunakan abstraction layer |
| Rate limit API eksternal | Pencarian publikasi terhambat | Implementasi retry dengan exponential backoff, cache hasil |

## Referensi ADR

- ADR-0001: SQLite dev / PostgreSQL prod via `DATABASE_URL`
- ADR-0002: FastAPI as backend framework
- ADR-0003: OpenAlex as first scientific publication connector
- ADR-0004: Crossref as second scientific publication connector
