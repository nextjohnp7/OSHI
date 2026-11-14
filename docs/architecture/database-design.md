# Database Design

Desain skema basis data OSHI (Part 7). Semua entitas menggunakan UUID sebagai primary key, memiliki `created_at` dan `updated_at`, dan mengikuti model provenansi (Part 6.4).

Database pengembangan default: SQLite. Produksi: PostgreSQL dengan ekstensi `pgvector` untuk pencarian vektor.

## 1. Entitas dan Relasi

```text
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   users     │      │ organizations    │      │   api_keys      │
├─────────────┤      ├──────────────────┤      ├─────────────────┤
│ id (UUID)   │────┤│ id (UUID)        │      │ id (UUID)       │
│ email       │      │ name             │      │ name            │
│ name        │      │ slug             │      │ key_hash        │
│ is_active   │      │ created_at       │      │ key_prefix      │
│ is_superuser│      │ updated_at       │      │ user_id ────────┼── users.id
│ created_at  │      │                  │      │ organization_id ┼─ organizations.id
│ updated_at  │      │                  │      │ is_active       │
└─────────────┘      │                  │      │ expires_at      │
                     └──────────────────┘      │ created_at      │
                                                └─────────────────┘
                                                        │
                                                        │
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│ publications│      │ organization_members│   │ documents       │
├─────────────┤      ├──────────────────┤      ├─────────────────┤
│ id (UUID)   │────┤│ id (UUID)        │      │ id (UUID)       │
│ source_name │      │ organization_id  ┼┬─── organizations.id │
│ source_id   │      │ user_id        ┼┼── users.id          │
│ title       │      │ role           │      │ source_name     │
│ abstract    │      │ created_at     │      │ source_id       │
│ authors (JSON)│   │                  │      │ title           │
│ publication_date│ │                  │      │ content_hash    │
│ source_url    │      │                  │      │ created_at    │
│ content_hash  │      │                  │      │ updated_at    │
│ license       │      │                  │└───────────────────┘
│ created_at    │      │                  │         │
│ updated_at    │      │                  │         ▼
└─────────────┘      │                  │ ┌─────────────────┐
                     │                  │ │ document_chunks │
                     │                  │ ├─────────────────┤
                     │                  │ │ id (UUID)       │
                     │                  │ │ document_id ────┼── documents.id
                     │                  │ │ chunk_index     │
                     │                  │ │ text            │
                     │                  │ │ embedding (BLOB)│
                     │                  │ │ created_at      │
                     │                  │ └─────────────────┘
                     │                  │
                     │                  │ ┌─────────────────┐
                     └──────────────────┤ │ evidence_items  │
                                        │ ├─────────────────┤
                                        │ │ id (UUID)       │
                                        │ │ publication_id ┼─ publications.id
                                        │ │ quote           │
                                        │ │ relevance_score │
                                        │ │ created_at      │
                                        │ └─────────────────┘
```

## 2. Detail Setiap Entitas

### 2.1 `users`

Akun platform pengguna (Part 7.1, Part 8.5 privasi).

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| email | String(255) | No | Unik, diindex |
| name | String(255) | Yes | |
| is_active | Boolean | No | Default true |
| is_superuser | Boolean | No | Default false |
| created_at | DateTime | No | Server default |
| updated_at | DateTime | No | Server default + onupdate |

### 2.2 `organizations`

Batas multi-tenancy (Part 7.1). Organisasi dapat berbagi deployment tanpa bocor data lintas organisasi.

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| name | String(255) | No | Diindex |
| slug | String(100) | No | Unik, diindex |
| created_at | DateTime | No | Server default |
| updated_at | DateTime | No | Server default + onupdate |

### 2.3 `organization_members`

Hubungan pengguna-organisasi dengan peran.

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| organization_id | UUID | No | FK → organizations.id |
| user_id | UUID | No | FK → users.id |
| role | String(50) | No | Default "member" |
| created_at | DateTime | No | Server default |

Index unik: `(organization_id, user_id)`.

### 2.4 `api_keys`

API key untuk akses terprogram (Part 7.1, Part 10 autentikasi). Plaintext key tidak tersimpan; hanya hash SHA-256 dan prefix.

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| name | String(255) | No | |
| key_hash | String(255) | No | Diindex |
| key_prefix | String(12) | No | Diindex |
| user_id | UUID | No | FK → users.id |
| organization_id | UUID | Yes | FK → organizations.id (SET NULL) |
| is_active | Boolean | No | Default true |
| last_used_at | DateTime | Yes | Diupdate saat digunakan |
| expires_at | DateTime | Yes | |
| created_at | DateTime | No | Server default |

### 2.5 `publications`

Metadata publikasi ilmiah dari sumber eksternal (OpenAlex, Crossref, arXiv, PubMed) dengan provenansi (Part 6.4).

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| source_name | String(100) | No | Diindex |
| source_id | String(255) | No | Diindex |
| title | Text | No | |
| abstract | Text | Yes | |
| authors | JSON | Yes | |
| publication_date | DateTime | Yes | Diindex |
| source_url | String(2048) | Yes | |
| content_hash | String(64) | Yes | Diindex |
| license | String(100) | Yes | |
| created_at | DateTime | No | Server default |
| updated_at | DateTime | No | Server default + onupdate |

Index unik: `(source_name, source_id)`.

### 2.6 `documents`

Dokumen yang diimpor pengguna (Sprint 3 Document Intelligence).

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| source_name | String(100) | No | |
| source_id | String(255) | No | |
| title | String(255) | No | |
| source_url | String(2048) | Yes | |
| content_hash | String(64) | Yes | |
| created_at | DateTime | No | Server default |
| updated_at | DateTime | No | Server default + onupdate |

Index unik: `(source_name, source_id)`.

### 2.7 `document_chunks`

Potongan teks dokumen dengan embedding (Sprint 3).

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| document_id | UUID | No | FK → documents.id (CASCADE) |
| chunk_index | Integer | No | Urutan potongan |
| text | Text | No | Isi potongan |
| embedding | BLOB | Yes | Vektor embedding (128 atau 384 dimensi) |
| created_at | DateTime | No | Server default |

Index unik: `(document_id, chunk_index)`.

### 2.8 `evidence_items`

Potongan bukti yang diekstrak dari publikasi (Sprint 4 Research Agent).

| Kolom | Tipe | Nullable | Keterangan |
|-------|------|----------|------------|
| id | UUID | No | Primary key |
| publication_id | UUID | No | FK → publications.id |
| quote | Text | No | Potongan teks bukti |
| relevance_score | Float | No | Skor relevansi ke kueri |
| created_at | DateTime | No | Server default |

## 3. Model Provenansi (Part 6.4)

Setiap catatan bukti material harus melacak:
- `source_id`, `source_name`, `source_url`, `source_type`
- `original_published_at` — saat peristiwa terjadi
- `observed_at` — saat observasi dibuat
- `retrieved_at` — saat OSHI mengambil laporan
- `content_hash` — hash konten asli
- `license`, `attribution`
- `verification_status` — UNVERIFIED, SOURCE_IDENTIFIED, CORROBORATED, OFFICIALLY_CONFIRMED, CONTRADICTED, OUTDATED
- `geographic_scope` — cakupan geografis
- `document_version` — versi dokumen

Stempel waktu ini tidak dapat ditukarkan satu sama lain.

## 4. Persyaratan Umum (Part 7.7)

- UUID di semua primary key
- `created_at` dan `updated_at` pada setiap tabel
- Constraints dan foreign key pada database
- Index yang sesuai pada kolom yang sering di-query
- Batasan organisasi dan tenant (multi-tenancy)
- Migrasi melalui Alembic
- Audit log (dapat ditambahkan di tabel terpisah di fase mendatang)
- Hindari PII yang tidak perlu

## 5. Migrasi Alembic

| Revisi | Deskripsi |
|--------|-----------|
| `8054612ce976` | Create `publications` table |
| `e065afc05779` | Create `documents` dan `document_chunks` tables |
| `9d3c5ad41c6f` | Auth tables: `organizations`, `users`, `organization_members`, `api_keys` |

Migrasi dapat diterapkan dengan:
```bash
uv run alembic upgrade head
```

## 6. Vector Search (Produksi)

Untuk produksi PostgreSQL, aktifkan ekstensi `pgvector` dan gunakan `PgVectorRetriever` (`packages/document_processing/retrieval.py`) dengan operator cosine distance `<=>`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE document_chunks ADD COLUMN embedding vector(384);
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

Pengembangan menggunakan pencarian cosine di memori (`rank_chunks_by_similarity` dalam retrieval.py) sebagai fallback.

## 7. Keamanan Basis Data

- Tidak menyimpan plaintext API key (hanya hash)
- Multi-tenancy melalui `organization_id` pada setiap entitas sensitif
- Foreign key dengan `ON DELETE CASCADE` / `SET NULL` sesuai kebutuhan
- Tidak menyimpan PII yang tidak perlu (Part 8.5 privasi)
