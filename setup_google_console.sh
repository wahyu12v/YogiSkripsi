#!/bin/bash
# ==============================================================================
# Script Otomatisasi untuk Menjalankan di Google Cloud Console (Cloud Shell / VM)
# Proyek Skripsi: Prediksi Tingkat Partisipasi Pemilih Kab. Kampar (GRU + Adam)
# ==============================================================================

set -e

echo "================================================================="
echo " Menyiapkan Lingkungan di Google Cloud Console (Cloud Shell)..."
echo "================================================================="

# 1. Pastikan Python 3 tersedia
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 tidak ditemukan. Silakan install Python 3 terlebih dahulu."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Deteksi Python versi: $PYTHON_VERSION"

# 2. Buat virtual environment jika belum ada
if [ ! -d ".venv" ]; then
    echo "Membuat virtual environment (.venv)..."
    python3 -m venv .venv
fi

# 3. Aktifkan virtual environment
echo "Mengaktifkan .venv..."
source .venv/bin/activate

# 4. Install / Upgrade dependensi
echo "Menginstall dependensi dari requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 5. Jalankan verifikasi prep data
echo "================================================================="
echo " Menjalankan verifikasi prep data..."
echo "================================================================="
python main.py --prep-only

echo "================================================================="
echo " SIAP! Menjalankan main.py dan Web Dashboard..."
echo " PETUNJUK GOOGLE CLOUD SHELL:"
echo " 1. Klik ikon 'Web Preview' (Pratinjau Web) di kanan atas Cloud Shell"
echo " 2. Pilih 'Preview on port 5000' (atau 'Change port' -> 5000)"
echo " 3. Website dashboard akan langsung terbuka di browser Anda!"
echo "================================================================="

python main.py
