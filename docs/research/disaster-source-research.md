# Disaster Source Research

Penelitian sumber data bencana dan kemanusiaan untuk platform OSHI (Global Crisis Intelligence Network / GCIN). Dokumen ini mencatat sumber informasi bencana publik yang dapat diintegrasikan, metode akses, rate limit, lisensi, dan keterbatasan.

Status: Initial research. Semua sumber adalah kandidat integrasi, bukan jaminan ketersediaan API tanpa pembatasan.

## Sumber Data Utama (Kandidat Integrasi)

### 1. GDACS (Global Disaster Alert and Coordination System)

- **URL:** https://www.gdacs.org/
- **Tipe:** Informasi bencana global (pencarian, peringatan, dampak)
- **Akses:** RSS feeds, API (terbatas), data terbuka
- **Autentikasi:** Tidak diperlukan untuk data publik
- **Rate limit:** Tidak terpecat secara publik untuk feed RSS
- **Format data:** XML (RSS/GeoRSS), JSON (beberapa endpoint)
- **Frekuensi update:** Near real-time (menit ke jam)
- **Cakupan geografis:** Global
- **Lisensi:** Data dapat digunakan dengan atribusi ke GDACS/JRC
- **Keterbatasan:** Data bersifat preliminary, memerlukan verifikasi terhadap sumber resmi

### 2. ReliefWeb

- **URL:** https://reliefweb.int/
- **Tipe:** Laporan kemanusiaan, update bencana, situasi report
- **Akses:** API REST (https://api.reliefweb.int/)
- **Autentikasi:** API key (opsional, untuk rate limit lebih tinggi)
- **Rate limit:** Terbatas tanpa API key
- **Format data:** JSON
- **Frekuensi update:** Real-time (organisasi kemanusiaan memposting)
- **Cakupan geografis:** Global, fokus krisis kemanusiaan
- **Lisensi:** Data dapat digunakan dengan atribusi
- **Keterbatasan:** Fokus pada response kemanusiaan, bukan data meteorologi mentah

### 3. NASA FIRMS (Fire Information for Resource Management System)

- **URL:** https://firms.modaps.eosdis.nasa.gov/
- **Tipe:** Data pantauan kebakaran hutan dari satelit
- **Akses:** API, data download (CSV/Shapefile), email alerts
- **Autentikasi:** Earthdata Login (untuk beberapa data)
- **Rate limit:** Terbatas
- **Format data:** CSV, Shapefile, KML, WMS
- **Frekuensi update:** Harian (satelit MODIS/VIIRS)
- **Cakupan geografis:** Global
- **Lisensi:** NASA data terbuka (data policy NASA)
- **Keterbatasan:** Deteksi kebakaran hanya, tidak mencakup semua jenis bencana

### 4. USGS (United States Geological Survey)

- **URL:** https://earthquake.usgs.gov/
- **Tipe:** Informasi gempa bumi, data geologi
- **Akses:** API (https://earthquake.usgs.gov/fdsnws/event/1/)
- **Autentikasi:** Tidak diperlukan
- **Rate limit:** Terbatas (polite pool dengan email)
- **Format data:** GeoJSON, CSV, XML, QuakeML
- **Frekuensi update:** Near real-time (menit)
- **Cakupan geografis:** Global (fokus AS dan wilayah sekitar)
- **Lisensi:** Data USGS terdepublikkkan (public domain untuk sebagian besar)
- **Keterbatasan:** Fokus gempa, tidak semua jenis bencana

### 5. NOAA (National Oceanic and Atmospheric Administration)

- **URL:** https://www.noaa.gov/
- **Tipe:** Cuaca, iklim, samudera, peringatan cuaca ekstrem
- **Akses:** API (https://www.weather.gov/documentation/services-web-api)
- **Autentikasi:** Tidak diperlukan untuk data publik
- **Rate limit:** Terbatas
- **Format data:** JSON, XML, GRIB2, NetCDF
- **Frekuensi update:** Real-time (cuaca), harian (iklim)
- **Cakupan geografis:** Global (fokus AS dan wilayah sekitar)
- **Lisensi:** Data NOAA terdepublikkkan (public domain)
- **Keterbatasan:** Data cuaca AS lebih lengkap dari internasional

### 6. WMO (World Meteorological Organization)

- **URL:** https://wmo.int/
- **Tipe:** Informasi meteorologi internasional, peringatan cuaca
- **Akses:** GDPFS (Global Data-processing and Forecasting System)
- **Autentikasi:** Terbatas (untuk anggota negara)
- **Rate limit:** Tidak terpecat publik
- **Format data:** BUFR, GRIB, XML (CAP - Common Alerting Protocol)
- **Frekuensi update:** Real-time
- **Cakupan geografis:** Global (melayani negara anggota)
- **Lisensi:** Terbentuk oleh perjanjian internasional
- **Keterbatasan:** Akses terbatas bagi non-anggota untuk beberapa data

### 7. Copernicus (Earth Observation, EU)

- **URL:** https://www.copernicus.eu/
- **Tipe:** Observasi bumi dari satelit Sentinel, data bencana
- **Akses:** API (Copernicus Open Access Hub), data download
- **Autentikasi:** Copernicus account (gratis)
- **Rate limit:** Terbatas
- **Format data:** GeoTIFF, NetCDF, Shapefile, SAFE format
- **Frekuensi update:** Harian ke mingguan (tergantung satelit)
- **Cakupan geografis:** Global (fokus Eropa dan sekelilingnya)
- **Lisensi:** Copernicus data policy (gratis dan terbuka)
- **Keterbatasan:** Data satelit memerlukan pemrosesan, tidak langsung siap pakai

### 8. OpenStreetMap (OSM)

- **URL:** https://www.openstreetmap.org/
- **Tipe:** Data geospasial, peta, koordinat, batas administrasi
- **Akses:** API (Overpass API, Nominatim), data download (OSM XML/PBF)
- **Autentikasi:** Tidak diperlukan untuk data publik
- **Rate limit:** Terbatas (Overpass API)
- **Format data:** OSM XML, PBF, GeoJSON, Shapefile
- **Frekuensi update:** Kontinyu (komunitas memetakan)
- **Cakupan geografis:** Global
- **Lisensi:** ODbL (Open Data Commons Open Database License)
- **Keterbatasan:** Kualitas data bervariasi per wilayah

### 9. BNPB (Badan Nasional Penanggulangan Bencana — Indonesia)

- **URL:** https://bnpb.go.id/
- **Tipe:** Informasi bencana Indonesia, peringatan, dampak
- **Akses:** Website, data terbuka (terbatas), media sosial
- **Autentikasi:** Tidak diperlukan untuk data publik
- **Rate limit:** Tidak terpecat publik
- **Format data:** HTML, PDF, beberapa API internal
- **Frekuensi update:** Saat terjadi bencana
- **Cakupan geografis:** Indonesia
- **Lisensi:** Data pemerintah Indonesia (terbuka dengan atribusi)
- **Keterbatasan:** API terbatas, sebagian besar data dalam format HTML/PDF

### 10. BMKG (Badan Meteorologi, Klimatologi, dan Geofisika — Indonesia)

- **URL:** https://www.bmkg.go.id/
- **Tipe:** Cuaca, gempa, cuaca ekstrem, peringatan dini Indonesia
- **Akses:** Website, API (terbatas), data terbuka
- **Autentikasi:** Tidak diperlukan untuk data publik
- **Rate limit:** Tidak terpecat publik
- **Format data:** HTML, JSON (beberapa endpoint), XML
- **Frekuensi update:** Real-time (cuaca, gempa)
- **Cakupan geografis:** Indonesia
- **Lisensi:** Data pemerintah Indonesia
- **Keterbatasan:** Fokus Indonesia, API terbatas

### 11. InaRISK (Indonesian Disaster Risk Information)

- **URL:** https://inarisk.bnpb.go.id/
- **Tipe:** Data risiko bencana Indonesia, peta risiko
- **Akses:** Website, peta interaktif, data download
- **Autentikasi:** Tidak diperlukan
- **Rate limit:** Tidak terpecat publik
- **Format data:** Shapefile, GeoJSON, PDF, peta web
- **Frekuensi update:** Periodik (update risiko)
- **Cakupan geografis:** Indonesia
- **Lisensi:** Data pemerintah Indonesia
- **Keterbatasan:** Fokus risiko, tidak data bencana real-time

## Tabel Perbandingan Sumber Data Bencana

| Sumber | Jenis Bencana | Cakupan | Real-time | Auth | Format | Status |
|--------|--------------|---------|-----------|------|--------|--------|
| GDACS | Multipurpose | Global | Ya | Tidak | RSS/XML | Kandidat |
| ReliefWeb | Kemanusiaan | Global | Ya | Opsional | JSON | Kandidat |
| NASA FIRMS | Kebakaran | Global | Harian | Opsional | CSV/SHP | Kandidat |
| USGS | Gempa | Global | Menit | Tidak | GeoJSON | Kandidat |
| NOAA | Cuaca/iklim | Global | Real-time | Tidak | JSON/XML | Kandidat |
| WMO | Cuaca | Global | Real-time | Terbatas | BUFR/GRIB | Kandidat |
| Copernicus | Observasi bumi | Global | Harian | Diperlukan | GeoTIFF | Kandidat |
| OpenStreetMap | Geospasial | Global | Kontinyu | Tidak | OSM/GeoJSON | Kandidat |
| BNPB | Semua (ID) | Indonesia | Saat bencana | Tidak | HTML/PDF | Kandidat |
| BMKG | Cuaca/gempa (ID) | Indonesia | Real-time | Tidak | HTML/JSON | Kandidat |
| InaRISK | Risiko (ID) | Indonesia | Periodik | Tidak | SHP/PDF | Kandidat |

## Rekomendasi Integrasi (Menurut Roadmap OSHI)

1. **Fase 4 — Crisis Intelligence MVP:** USGS (gempa), BMKG (cuaca/gempa Indonesia), BNPB (bencana Indonesia) — pilot historis banjir di Indonesia.
2. **Fase 5 — Early Warning Intelligence:** BMKG, NOAA, WMO — peringatan cuaca ekstrem resmi.
3. **Fase 6+ — Humanitarian Coordination:** ReliefWeb, GDACS — laporan dan koordinasi kemanusiaan.

## Peringatan Keamanan dan Etika (Part 8)

- **Jangan meng-presentasikan data bencana sebagai peringatan resmi.** Semua data harus difilter dan diverifikasi.
- **Tidak ada peringatan evakuasi otomatis.** Keputusan evakuasi hanya dapat dibuat oleh otoritas resmi.
- **Tampilkan stempel waktu sumber** dan identifikasi pemberi peringatan.
- **Tandai laporan tidak terverifikasi** secara jelas.
- **Jangan menciptakan koordinat presisi** dari deskripsi lokasi yang samar.
- **Hormati lisensi data** setiap sumber (terutama ODbL untuk OSM, data policy NASA/NOAA).

## Referensi

- GDACS: https://www.gdacs.org/
- ReliefWeb API: https://api.reliefweb.int/
- NASA FIRMS: https://firms.modaps.eosdis.nasa.gov/
- USGS Earthquake API: https://earthquake.usgs.gov/fdsnws/event/1/
- NOAA Weather API: https://www.weather.gov/documentation/services-web-api
- WMO: https://wmo.int/
- Copernicus: https://www.copernicus.eu/
- OpenStreetMap: https://www.openstreetmap.org/
- ODbL License: https://opendatacommons.org/licenses/odbl/
- BNPB: https://bnpb.go.id/
- BMKG: https://www.bmkg.go.id/
- InaRISK: https://inarisk.bnpb.go.id/
