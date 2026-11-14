# Security Review

Tinjauan keamanan OSHI (Part 8, Rule E, Part 10). Dokumen ini mencatat model ancaman, kontrol keamanan yang diimplementasi, dan risiko yang diketahui.

## 1. Model Ancaman (Part 8.1)

| Ancaman | Deskripsi | Mitigasi yang Diimplementasi | Status |
|---------|-----------|------------------------------|--------|
| Prompt injection | Instruksi tersembunyi dalam dokumen yang diambil diinterpretasikan sebagai perintah sistem | Konten yang diambil dianggap sebagai data, tidak sebagai instruksi (Part 8.2). Tidak ada eksekusi instruksi dari konten eksternal. | Diimplementasi |
| Malicious documents | Dokumen berisi konten berbahaya | Konten ditangani sebagai teks mentah. Tidak ada eksekusi kode arbitrer dari dokumen yang diambil (Rule E). | Diimplementasi |
| Malicious tool outputs | Hasil tool yang berisi instruksi berbahaya | Output tool divisandikan sebelum ditampilkan ke pengguna. | Diimplementasi |
| SSRF (Server-Side Request Forgery) | Penyerang memaksa server membuat request ke jaringan internal | Konektor hanya memanggil endpoint publik yang ditentukan (OpenAlex, Crossref, arXiv, PubMed). Tidak ada input URL arbitrer dari pengguna. | Diimplementasi |
| SQL injection | Penyerang menyuntikkan query SQL berbahaya | Semua query menggunakan parameter binding (SQLAlchemy ORM + Alembic). Tidak ada string interpolation dalam query. | Diimplementasi |
| Unauthorized access | Pengguna tidak berhak mengakses data | API key authentication middleware (`require_api_key`) pada semua route terlindungi. Multi-tenancy melalui `organization_id`. | Diimplementasi |
| Cross-tenant data leakage | Data bocor antar organisasi | Query API key selalu difilter oleh `user_id` dan `organization_id`. Multi-tenancy di level model. | Diimplementasi |
| API key exposure | API key bocor melalui log atau response | Plaintext key hanya dikembalikan sekali pada pembuatan. Tersimpan sebagai hash SHA-256. Prefix hanya 12 karakter. | Diimplementasi |
| Sensitive information leakage | PII bocor dalam laporan | Tidak ada PII yang dikumpulkan secara default. Model `users` hanya menyimpan email dan nama. | Diimplementasi |
| Unsafe code execution | Eksekusi kode berbahaya dari dokumen eksternal | Tidak ada eksekusi kode arbitrer dari dokumen yang diambil (Rule E). | Diimplementasi |
| Denial of service | Serangan ke layanan | Rate limit pada konektor eksternal. Tidak ada rate limit middleware pada API sendiri (perlu ditambahkan). | Parsial |
| Supply-chain attacks | Dependensi yang dikompromikan | Dependensi dipin dan diperbarui melalui `uv.lock`. Audit keamanan dependensi perlu ditambahkan. | Parsial |
| Compromised data sources | Sumber data yang memberikan informasi palsu | Semua konten eksternal dianggap tidak terpercaya (Part 8.2). Verifikasi sumber diperlukan. | Diimplementasi |
| False disaster reports | Laporan bencana palsu yang menyebar | Laporan bencana ditandai sebagai preliminary. Verifikasi terhadap sumber resmi diperlukan (Part 8.4). | Diimplementasi |

## 2. Kontrol Keamanan yang Diimplementasi

### 2.1 Autentikasi dan Otorisasi
- API key authentication melalui header `Authorization: Bearer <key>` atau `X-API-Key`
- Keys disimpan sebagai hash SHA-256, plaintext tidak tersimpan
- Constant-time comparison (`secrets.compare_digest`) mencegah timing attack
- Key expiry dan nonaktifan (`is_active`, `expires_at`)
- `last_used_at` untuk audit penggunaan
- Multi-tenancy: setiap API key terikat pada `user_id` dan opsional `organization_id`
- Semua route non-`/health` dilindungi oleh `require_api_key`

### 2.2 Validasi Input
- Pydantic schemas untuk semua request/response
- Validasi tipe data dan batasan (mis. `limit` antara 1-100)
- Tidak ada string interpolation dalam query SQL

### 2.3 Error Handling
- Handler konsisten dengan request ID (tidak ada stack trace yang bocor ke klien)
- Kode error generik untuk exception yang tidak tertangani

### 2.4 Provenansi dan Audit
- Setiap publikasi memiliki `source_name`, `source_id`, `source_url`, `content_hash`
- `created_at` dan `updated_at` pada setiap entitas
- `last_used_at` pada API key untuk audit penggunaan

## 3. Risiko yang Diketahui

| Risiko | Dampak | Mitigasi yang Perlu Ditambahkan |
|--------|--------|---------------------------------|
| Tidak ada rate limiting pada API | Serangan DoS pada endpoint API | Tambahkan middleware rate limiting (mis. `slowapi` atau Redis-based) |
| Tidak ada JWT/session | API key adalah satu-satunya autentikasi | Pertimbangkan JWT untuk sesi pengguna web |
| Tidak ada audit log lengkap | Tidak dapat melacak siapa mengakses apa | Tambahkan tabel `audit_logs` untuk mencatat akses dan modifikasi |
| Dependensi tidak dipindai untuk vulnerabilitas | Dependensi yang dikompromikan tidak terdeteksi | Tambahkan dependency scanning (CI) |
| Tidak ada encryption at rest | Data pada disk tidak terenkripsi | Aktifkan enkripsi disk pada level infrastruktur |
| Tidak ada HTTPS enforcement | Komunikasi dapat diintersep | Paksa HTTPS pada load balancer / reverse proxy produksi |

## 4. Prinsip Keamanan (Part 8, Rule E)

- **Tidak ada peringatan bencana otomatis.** Keputusan evakuasi hanya dapat dibuat oleh otoritas resmi.
- **Tidak ada LLM yang secara otonom mengeluarkan peringatan resmi.** LLM hanya membantu analisis, tidak mengambil keputusan darurat.
- **Konten yang diambil tidak diperlakukan sebagai bukti ilmiah.** Setiap klaim harus diverifikasi terhadap sumber asli.
- **PII tidak diekspose.** Model data dirancang untuk mengumpulkan hanya data yang diperlukan.
- **Kode arbitrer tidak dieksekusi.** Tidak ada eksekusi kode dari dokumen atau sumber eksternal.

## 5. Rekomendasi Produksi

1. Aktifkan HTTPS pada semua endpoint produksi.
2. Tambahkan rate limiting middleware pada API.
3. Tambahkan audit log untuk akses dan modifikasi data sensitif.
4. Tambahkan dependency scanning dalam CI pipeline.
5. Lakukan security review eksternal sebelum meluncur ke publik (Part 15.4).
6. Enkripsi at-rest pada database produksi.
