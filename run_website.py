"""
Script Eksekusi Langsung: Web Dashboard Skripsi Partisipasi Pemilih Kab. Kampar
Jalankan:
    python run_website.py
Akan otomatis membuka browser ke http://localhost:5000
"""

import os
import sys

if __name__ == "__main__":
    from app import run_server
    run_server(port=5000, open_browser=True)
