# Testing Strategy

Strategi pengujian OSHI (Part 13). Dokumen ini mencakup filosofi pengujian, jenis tes, cakupan, dan definisi selesai.

## 1. Filosofi Pengujian (Part 13.1)

Setiap fitur harus memiliki tes yang sesuai dengan risikonya. Sebuah unit test yang lolos tidak menentukan kesiapan produksi. Pengujian harus mencakup kasus kegagalan, input tidak valid, dan kondisi batas.

## 2. Jenis Tes

### 2.1 Unit Tests (Part 13.2)

Menguji unit terisolasi tanpa jaringan. Lokasi: `tests/unit/`.

**Menguji:**
- Validasi skema (Pydantic models)
- Normalisasi data (connector normalize)
- Ekstraksi kutipan
- Identifikasi sumber
- Parsing geografis
- Deduplikasi peristiwa
- Penegakan izin
- Penanganan stempel waktu

**Contoh tes yang ada:**
- `test_auth_models.py` — organisasi, pengguna, anggota organisasi, API key
- `test_auth.py` — bootstrap, pembuatan key, daftar key, pencabutan, verifikasi, route terlindungi
- `test_chunking.py` — pemotongan teks dengan overlap
- `test_embeddings.py` — embedding deterministik, blob roundtrip, cosine similarity
- `test_retrieval.py` — ranking vektor, top_k, tanpa embedding
- `test_document_service.py` — ingest, dedup, pencarian semantik, daftar, dapatkan, potongan
- `test_research_agent.py` — pembangunan graph, pembuatan laporan, kasus kosong
- `test_arxiv_connector.py` — normalisasi, stripping versi ID, hash
- `test_pubmed_connector.py` — normalisasi, fallback URL, parsing tanggal
- `test_openalex_connector.py` — normalisasi (tanpa jaringan)
- `test_crossref_connector.py` — normalisasi (tanpa jaringan)
- `test_service.py` — insert, upsert/dedup, filter, in-memory SQLite
- `test_foundation.py` — endpoint health

### 2.2 Integration Tests (Part 13.3)

Menguji operasi basis data, konektor sumber ilmiah, impor dokumen, embedding dan pengambilan, eksekusi agen, pemanggilan tool, persetujuan manusia, pembuatan laporan. Menggunakan fixture deterministik dan layanan eksternal yang di-mock.

Lokasi: `tests/unit/` (dengan `tmp_path` untuk basis data SQLite temp).

### 2.3 AI Evaluation (Part 13.4)

Membuat dataset evaluasi yang berisi:
- Pertanyaan dengan cukup bukti
- Pertanyaan dengan bukti yang tidak cukup
- Publikasi yang saling bertentangan
- Kutipan yang salah
- Sumber yang ketinggalan zaman
- Lokasi peristiwa yang ambigu
- Laporan bencana yang duplikat
- Konten yang diambil yang berbahaya
- Kasus tepi terjemahan

**Mengevaluasi:**
- Keberangkatan kutipan (citation correctness)
- Relevansi sumber
- Dukungan faktual
- Tingkat klaim yang tidak didukung
- Penanganan kontradiksi
- Kualitas pengambilan (retrieval quality)
- Validitas skema output
- Latensi
- Biaya

**Peringatan:** Jangan menggunakan kepercayaan model sebagai ukuran keakuratan faktual.

### 2.4 Security Testing (Part 13.5)

Mencakup:
- Tes autentikasi
- Tes otorisasi
- Tes akses lintas organisasi
- Tes prompt injection
- Tes SSRF
- Tes upload file
- Tes SQL injection
- Pemindaian rahasia (secrets scanning)
- Pemindaian kerentanan dependensi

## 3. Cakupan Tes Saat Ini

| File Tes | Jumlah Tes | Fokus |
|----------|------------|-------|
| test_foundation.py | 2 | Endpoint health |
| test_openalex_connector.py | 5 | Normalisasi (tanpa jaringan) |
| test_crossref_connector.py | 5 | Normalisasi (tanpa jaringan) |
| test_service.py | 3 | Insert, upsert/dedup, filter |
| test_api_publications.py | 3 | Endpoint publikasi (dengan auth) |
| test_chunking.py | 5 | Logika pemotongan |
| test_embeddings.py | 12 | Embedding, blob roundtrip, cosine similarity |
| test_retrieval.py | 3 | Ranking vektor |
| test_document_service.py | 7 | Ingest, dedup, pencarian semantik |
| test_research_agent.py | 4 | Graph, pembuatan laporan |
| test_arxiv_connector.py | 5 | Normalisasi arXiv |
| test_pubmed_connector.py | 5 | Normalisasi PubMed |
| test_auth_models.py | 4 | Model autentikasi |
| test_auth.py | 7 | Bootstrap, key management, verifikasi, route terlindungi |
| **Total** | **73** | |

**Hasil terbaru:** 73 lolos, 0 gagal (`uv run pytest tests/`).

## 4. Basis Data untuk Tes

Semua tes menggunakan basis data SQLite file temporer (salah satu file per fungsi tes) melalui fixture `client` di `tests/unit/conftest.py`. Ini mencegah state bocor antar tes. Basis data `oshi_dev.db` (pengembangan) tidak digunakan untuk tes.

## 5. Definition of Done (Part 13.6)

Sebuah tugas dianggap selesai hanya jika:
1. Implementasi ada
2. Tes yang relevan lolos
3. Kasus kegagalan ditangani
4. Implikasi keamanan ditinjau
5. Dokumentasi diperbarui
6. Tidak ada perubahan yang tidak terkait diperkenalkan
7. Hasil dapat direproduksi
8. Status selesai dilaporkan dengan akurat

## 6. Jalankan Tes

```bash
# Semua tes
uv run pytest tests/

# Tes dengan detail
uv run pytest tests/ -v --tb=short

# Tes tertentu
uv run pytest tests/unit/test_auth.py -v

# Tes tanpa jaringan (semua unit test)
uv run pytest tests/ -m unit
```

## 7. Tes yang Perlu Ditambahkan (Roadmap)

- Tes integrasi basis data PostgreSQL + pgvector
- Tes endpoint krisis (`/crisis/*`)
- Tes endpoint peringatan dini (`/warnings/*`)
- Tes endpoint koordinasi kemanusiaan (`/humanitarian/*`)
- Tes integrasi agen LangGraph dengan basis data
- Tes prompt injection pada endpoint riset
- Tes SSRF pada konektor sumber
- Tes keamanan dependensi (CI)
