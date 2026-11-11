# 🏛️ NALAR - GovTech AI: Portal Analitik Penetapan Bantuan Sosial

Aplikasi web modern berbasis **Flask** dan **Framework CSS (Tailwind CSS)** dengan desain UI/UX bereputasi editorial tinggi yang diadaptasi dari referensi desain amal/bantuan sosial (*"Justice begins where inequality ends"*).

Sistem ini mentransformasikan proses penetapan bantuan sosial (bansos) nasional menjadi transparan, objektif, dan dapat dipertanggungjawabkan melalui integrasi **Ensemble Random Forest**, **Explainable AI (LIME)**, dan **Natural Language Processing (NLP)**.

---

## 🎨 Desain UI/UX: Minimalis, Bersih & Langsung Dipahami ("Sekali Pegang Langsung Paham")

Antarmuka dirancang dengan pendekatan minimalis fungsional, menghilangkan ornamen dekoratif yang tidak perlu, dan menonjolkan kejelasan fungsi bagi setiap pengguna:
1. **Tipografi & Hirarki Visual**:
   - Judul utama menggunakan font serif editorial **Fraunces** yang berwibawa dan mudah dibaca.
   - Teks badan dan kontrol antarmuka menggunakan **Plus Jakarta Sans** yang bersih, ringkas, dan modern.
2. **Pusat Kendali 4 Fitur Utama (Action Matrix)**:
   - Terpampang langsung di beranda dengan kartu aksi berpenjelasan lengkap: fungsi fitur, hasil yang didapat, dan tombol aksi yang jelas.
3. **Alur Kerja 3 Langkah Terstruktur**:
   - Menjelaskan alur kerja dari input data, evaluasi AI, hingga bukti keputusan sah secara visual.
4. **Keterangan Tombol yang Eksplisit (Self-Explanatory Controls)**:
   - Setiap tombol dilengkapi subtext atau indikator yang memberitahu pengguna apa yang akan terjadi saat tombol tersebut diklik.
5. **Indikator Status & Transparansi LIME**:
   - Visualisasi LIME dilengkapi panduan legenda warna (Hijau = Mendukung Layak, Merah = Mendorong Tolak) agar dapat dipahami masyarakat awam tanpa keraguan.

---

## ⚙️ Fitur Utama Aplikasi

### 1. 🧑‍🤝‍🧑 Verifikasi Kelayakan Individu & Explainable AI (LIME)
- **Formulir Interaktif**: Menginput 16-digit NIK, nama kepala keluarga, pekerjaan, penghasilan bulanan, tanggungan, kondisi rumah, daya listrik, dan narasi sanggahan/keluhan warga.
- **Pengecekan Kebijakan Otomatis (*Hard Rules*)**:
  - Peringatan instan blokir regulasi jika pekerjaan pemohon adalah ASN/TNI/POLRI.
  - Peringatan daya listrik tinggi (&ge; 1.300 VA) yang mengindikasikan keluarga mampu.
- **Prediksi Kecerdasan Buatan**: Mengkalkulasi status `LAYAK (Approve)` vs `TIDAK LAYAK (Reject)` beserta persentase probabilitas keyakinan.
- **Dekonstruksi Algoritma (LIME)**: Visualisasi grafik batang horizontal interaktif (*Chart.js*) yang membongkar faktor mana yang mendukung kelayakan (hijau) atau menolaknya (merah).
- **Analisis Sentimen NLP**: Mengklasifikasi aduan warga ke dalam kategori: *Kritis (Risiko Konflik)*, *Koperatif*, atau *Standar/Netral*.
- **Penerbitan Surat Keputusan Resmi (PDF)**: Cetak otomatis dokumen SK resmi ber-kop Kemensos RI dengan nomor registrasi unik, cap verifikasi algoritmik, dan ringkasan hukum.

### 2. 📂 Pemrosesan Massal (Batch CSV Processing)
- **Drag & Drop CSV**: Unggah berkas data ribuan warga tingkat desa atau kecamatan.
- **Unduh Template CSV**: Format template standar yang langsung kompatibel.
- **Evaluasi Serempak AI**: Menghitung status dan skor kemiskinan ribuan rekor dalam sekejap.
- **Dasbor Rekapitulasi**: Metrik total data, jumlah layak, jumlah tidak layak, dan rasio persentase.
- **Ekspor CSV Lengkap**: Unduh kembali data yang sudah diperkaya dengan kolom rekomendasi dan skor kemiskinan.

### 3. 📈 Simulasi Kuota & Pagu Anggaran APBN
- **Slider Kuota Interaktif**: Atur jumlah kuota keluarga penerima bantuan (dari 20 hingga seluruh populasi terdaftar).
- **Kalkulasi Ambang Batas (*Cutoff Score*) Real-time**: Menentukan skor kemiskinan minimum yang berhak lolos.
- **Proyeksi Finansial APBN**: Menghitung otomatis estimasi pagu anggaran bulanan dan tahunan (asumsi Rp 600.000/keluarga/bulan).
- **Tabel Urutan Prioritas**: Menampilkan warga paling rentan yang diprioritaskan mendapat bantuan.

### 4. 🛡️ Audit Bias Algoritma (XAI Hub)
- **Peta Dominasi Variabel Global**: Diagram bobot kepentingan fitur (*Feature Importance*) dari model Random Forest.
- **Checklist Keadilan Algoritmik**: Bukti tidak adanya diskriminasi suku, agama, ras, maupun relasi politis.
- **Rujukan Regulasi**: Mematuhi UU No. 13 Tahun 2011 dan Kepmensos No. 262/HUK/2022.

### 5. 🔐 Portal Operator Terverifikasi
- Login operator dengan autentikasi sesi (`Username: admin` | `Password: admin123`).
- Akses cepat untuk aparatur dinas sosial dan verifikator lapangan.

---

## 🚀 Cara Menjalankan Aplikasi

### Opsi 1: Menjalankan Langsung via Terminal
```powershell
# Masuk ke direktori proyek
cd c:\Users\Hi\proyek_nalar

# Jalankan server Flask menggunakan environment yang sudah terpasang
.\env\Scripts\python.exe app.py
```
Aplikasi akan aktif di: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

### Opsi 2: Double-Click File Batch
Cukup klik dua kali pada file `run_app.bat` di folder proyek.

### Menjalankan Unit Test Otomatis
```powershell
.\env\Scripts\python.exe test_app.py
```
*(Seluruh 9 pengujian otomatis terkonfirmasi lolos 100%)*

---

## 📂 Struktur Berkas Proyek

```
proyek_nalar/
├── app.py                      # Server Flask utama & routing REST API
├── model_service.py            # Mesin AI (Random Forest, LIME Explainer, Sentimen, FPDF)
├── dataset_sintetik_bansos.csv # Basis data sosio-ekonomi (1.500 sampel warga)
├── test_app.py                 # Automated test suite (9 unit test lengkap)
├── run_app.bat                 # Script peluncur satu klik
├── static/
│   ├── css/
│   │   └── custom.css          # Desain kapsul miring, tipografi editorial, aksen dots, tema
│   └── js/
│       └── app.js              # Interaktivitas AJAX, preset demo, Chart.js LIME, slider APBN
└── templates/
    ├── base.html               # Layout dasar, navbar GovTech, hotline, footer
    ├── index.html              # Landing page (adaptasi visual referensi desain)
    ├── verifikasi.html         # Form verifikasi individu & visualisasi XAI LIME
    ├── massal.html             # Batch CSV uploader & tabel rekapitulasi
    ├── simulasi.html           # Simulator interaktif pagu kuota APBN
    ├── audit.html              # Audit dominasi fitur & etika model
    └── login.html              # Portal masuk operator & admin
```
