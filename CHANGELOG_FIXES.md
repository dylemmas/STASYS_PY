# CHANGELOG_FIXES.md

Entri baru di **paling ATAS** (terbaru → terlama). Hanya tulis setelah fix terverifikasi;
masih dugaan? tandai `PENDING verifikasi`. Baca entri relevan dengan grep sebelum memperbaiki bug.

### Fix #1 — PENDING: Receiver auth gagal total vs firmware v2 (gejala) — aplikasi menulis protokol auth v1, firmware sudah v2 (akar)

| Kolom | Isi |
| --- | --- |
| Tanggal | 2026-10-06 |
| File | `python_app/stasys_app/core.py` (`perform_auth`, `discover_stasys_devices`, `parse_binary_packet`); vendor baru: `tools/stasys_packet.py`, `tools/README.md`, `tools/__init__.py`; tes: `python_app/test/test_parser_drift.py`, `python_app/test/test_v2_parsing.py` |
| Masalah | Receiver PyQt tidak pernah bisa autentikasi ke firmware saat ini. `perform_auth`/`discover_stasys_devices` bicara challenge-response legacy v1 (`sha256(challenge+SECRET_KEY)`), sedangkan firmware bicara v2 (`READY v=2` → `AUTH <64-hex nonce>` → `PROOF 70-char` → `OK`). `parse_binary_packet` memindai byte-by-byte `AA BB` alih-alih accumulating-buffer resync ber-batas (cap 144 B, advance-1-on-failure). Lebih buruk: discovery lama melihat kata `READY` di banner v2 lalu menulis baris challenge sampah ke handshake perangkat — membakar satu percobaan auth dalam koneksi itu, lalu menutupnya. |
| Akar | Kecocokan generasi protokol: aplikasi ditulis untuk auth v1 sedangkan firmware pindah ke auth v2 HMAC-SHA256 atas transcript (`spp-parsing-guide.md`). Parser referensi hanya ada di repo saudara `STASYS_FW` dan tidak pernah di-vendor, sehingga tidak ada kontrak yang bisa mendeteksi pergeseran ini. |
| Fix | Vendor byte-identical `STASYS_FW/tools/{stasys_packet.py,README.md,__init__.py}` ke `STASYS_PY/tools/` (tes drift mengunci kesamaan byte + panjang `AUTH_DOMAIN` 15 + konstanta + re-derivation HMAC dari prinsip pertama); tulis ulang `parse_binary_packet` sebagai wrapper `feed()` dari `PacketParser`; ganti auth dengan handshake berbasis `SppReceiver` v2 (Task 4); discovery berbasis banner-only tanpa mengirim apa pun (Task 6). |
| Verifikasi | **PENDING verifikasi** — perbaikan penuh mendarat di Tasks 3–7 plan `read-spp-parsing-guide-md-and-test-parsi-hashed-candy.md` dan difinalisasi di Task 10. Nomor interim yang sudah dijalankan 2026-10-06: `python -m pytest python_app/test/test_parser_drift.py -q` → **5 passed**; `python -m pytest test/test_v2_parsing.py -q` (cwd `python_app`) → **7 passed, 2 failed** — 2 gagal tersebut adalah baseline RED Task 3 (`TypeError: parse_binary_packet() takes 1 positional argument but 2 were given`), memang merah pada titik ini. |
| Pelajaran | Kunci klaim protokol dengan tes kontrak terhadap sumber firmware; jangan pernah mengimplementasi ulang handshake yang sudah tersedia pada implementasi referensi; discovery banner harus **tidak mengirim apa pun** (invarian write-zero-probe). |
| Log Keyword | auth, PROOF, FAIL, generation, AA BB, checksum, PacketParser, drift |
| Deploy | Lokal saja, branch `spp-v2-upgrade`; tanpa deployment. |
