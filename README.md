# Skripsi: Prediksi Tingkat Partisipasi Pemilih Kabupaten Kampar

Penelitian komparasi arsitektur **Gated Recurrent Unit (GRU) + Optimizer Adam** terhadap **LSTM-Adam** (metode jurnal acuan), **BiLSTM-Adam**, **GRU-SGD**, **LSTM-SGD**, dan **Baseline Naif (Lag-1)** pada 24 kecamatan di Kabupaten Kampar.

## 🚀 Panduan Eksekusi

### 1. Menjalankan di Komputer Lokal (Windows)
```powershell
# Jalankan pipeline pemodelan & evaluasi
.\.venv\Scripts\python.exe main.py

# Membuka Web Dashboard (http://localhost:5000)
.\.venv\Scripts\python.exe run_website.py
```

### 2. Menjalankan di Google Cloud Console (Cloud Shell)
Lihat panduan lengkap di [PANDUAN_GOOGLE_CONSOLE.md](file:///c:/Users/Ardian%20Wahyu%20Saputra/Desktop/Code/YogiSkripsi/PANDUAN_GOOGLE_CONSOLE.md)
```bash
chmod +x setup_google_console.sh
./setup_google_console.sh
```
Lalu buka menu **Web Preview** di Cloud Shell pada port `5000`.

### 3. Menjalankan di Google Colab
Buka **[Google Colaboratory](https://colab.research.google.com/)**, upload file `notebook_skripsi_yogi.ipynb`, dan jalankan setiap selnya.

## 📁 Struktur Berkas Utama
- `main.py` : Pipeline pemodelan, training 5 seed, evaluasi metrik, uji Wilcoxon, dan export grafik/excel.
- `app.py` : Server Web Dashboard interaktif (Flask + Tailwind CSS + Chart.js).
- `run_website.py` : Skrip peluncur cepat untuk membuka website dashboard.
- `requirements.txt` : Daftar pustaka Python yang dibutuhkan.
- `setup_google_console.sh` : Skrip otomasi untuk Google Cloud Console / Linux.
- `notebook_skripsi_yogi.ipynb` : Notebook interaktif untuk Google Colab.
- `hasil/` : Direktori output berisi file Excel (`laporan_hasil.xlsx`), grafik 300 DPI (`.png`), dan ringkasan riset (`RINGKASAN.md`).
