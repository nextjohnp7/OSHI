# Data Source Research

## Overview

Documentasi penelitian sumber data untuk platform OSHI (Open Science & Humanitarian Intelligence Infrastructure). Tujuannya adalah mengidentifikasi, mengevaluasi, dan mendokumentasikan sumber data ilmiah dan kemanusiaan yang akan diintegrasikan ke dalam sistem.

## Sumber Data Utama (Terintegrasi)

### 1. OpenAlex

- **URL:** https://api.openalex.org
- **Tipe:** Open index of scholarly works
- **Lisensi:** OpenAlex data is available under CC0 / ODC-BY (tergantung sumber asli)
- **Rate limit:** Tidak ada rate limit publik yang ketat untuk request dengan email (mailto parameter)
- **Keunggulan:**
  - Cakupan luas (250+ juta karya ilmiah)
  - API REST yang terstruktur dengan filtering yang kaya
  - Open access location data tersedia
  - Konsep dan topik hierarkis
- **Keterbatasan:**
  - Metadata terkadang tidak lengkap untuk karya lama
  - Abstrak tersedia dalam bentuk inverted index (perlu rekonstruksi)

**Status:** Sudah terintegrasi (`packages/connectors/scientific/openalex.py`), live API verified.

### 2. Crossref

- **URL:** https://api.crossref.org
- **Tipe:** Metadata publishers (DOI registration agency)
- **Lisensi:** Crossref API terms of service
- **Rate limit:** 50 request/second untuk mailto terdaftar, lebih rendah tanpa
- **Keunggulan:**
  - DOI resolusi yang andal
  - Metadata referensi dan sitasi
  - Cakupan publisher komersial dan akademis
- **Keterbatasan:**
  - Full text jarang tersedia langsung (hanya metadata)
  - Beberapa field (license, abstract) sering null

**Status:** Sudah terintegrasi (`packages/connectors/scientific/crossref.py`), live API verified.

## Sumber Data Kandidat (Sprint 4+)

### 3. Semantic Scholar

- **URL:** https://api.semanticscholar.org
- **Tipe:** AI-powered research paper discovery
- **Rate limit:** 100 request/5 menit (tanpa API key), lebih tinggi dengan API key
- **Keunggulan:**
  - Abstrak dan full text tersedia untuk banyak paper
  - Citation context dan influence metrics
  - Field of study klasifikasi
- **Keterbatasan:**
  - Rate limit ketat tanpa API key
  - Cakupan lebih kecil dari OpenAlex

### 4. arXiv

- **URL:** https://export.arxiv.org/api/query
- **Tipe:** Preprint repository (fisika, matematika, komputer science, dll.)
- **Rate limit:** 1 request/3 detik (berasakan beban server)
- **Keunggulan:**
  - Full text PDF tersedia gratis
  - Fokus pada STEM
  - Open access secara default
- **Keterbatasan:**
  - Hanya preprint (belum peer review)
  - Cakupan terbatas pada STEM

### 5. PubMed / Europe PMC

- **URL:** https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ (PubMed), https://www.ebi.ac.uk/europepmc/webservices/rest (Europe PMC)
- **Tipe:** Biomedical dan life sciences literature
- **Rate limit:** 3 request/detik (PubMed), lebih tinggi dengan API key
- **Keunggulan:**
  - Fokus pada kesehatan dan kedokteran (relevan untuk humanitarian crisis)
  - MeSH terms untuk pencarian yang presisi
  - Full text tersedia untuk open access article
- **Keterbatasan:**
  - Terfokus pada biomedical, kurang relevan untuk topik non-medis

### 6. ReliefWeb (Humanitarian)

- **URL:** https://api.reliefweb.int
- **Tipe:** Humanitarian disaster and crisis information
- **Lisensi:** Data dapat digunakan dengan atribusi
- **Keunggulan:**
  - Report, update, dan informasi bencana real-time
  - Relevan untuk komponen humanitarian intelligence OSHI
  - Geotagging untuk lokasi bencana
- **Keterbatasan:**
  - Fokus pada humanitarian, bukan publikasi ilmiah akademis

## Tabel Perbandingan Sumber Data

| Sumber | Domain | Full Text | Rate Limit | Auth | Status |
|--------|--------|-----------|------------|------|--------|
| OpenAlex | Multidisipliner | Tidak (metadata) | Lebih tinggi dengan email | Opsional | Terintegrasi |
| Crossref | Multidisipliner | Tidak (metadata DOI) | 50 detik | Opsional | Terintegrasi |
| Semantic Scholar | Multidisipliner | Ya (beberapa) | 100/5 menit | Opsional | Kandidat |
| arXiv | STEM | Ya (PDF) | 1/3 detik | Tidak | Kandidat |
| PubMed/Europe PMC | Biomedical | Ya (beberapa) | 3/detik | Opsional | Kandidat |
| ReliefWeb | Humanitarian | Ya (report) | Tidak publik | Tidak | Kandidat |

## Rekomendasi Integrasi

1. **Sprint 4:** Semantic Scholar (untuk paper discovery yang lebih cerdas dengan citation context)
2. **Sprint 5:** arXiv (untuk preprint STEM, relevan untuk humanitarian tech)
3. **Sprint 6:** PubMed/Europe PMC (untuk informasi kesehatan dalam konteks humaniter)
4. **Sprint 7:** ReliefWeb (untuk data bencana dan krisis real-time)

## Referensi

- OpenAlex API Docs: https://docs.openalex.org
- Crossref API Docs: https://github.com/CrossRef/rest-api-doc
- Semantic Scholar API: https://api.semanticscholar.org/api-docs/
- arXiv API: https://info.arxiv.org/help/api/index.html
- Europe PMC API: https://europepmc.org/docs/Web_Services_Guide
- ReliefWeb API: https://api.rwlabs.org
