"""
Web Dashboard Skripsi: Prediksi Tingkat Partisipasi Pemilih Kab. Kampar
Arsitektur: GRU + Adam (Pembanding: LSTM-Adam, BiLSTM-Adam, GRU-SGD, LSTM-SGD, Naif)
Tema: Terang (Clean Light Theme) dengan Pemisahan Warna Data yang Jelas & Rapi
"""

import os
import sys
import json
import socket
import webbrowser
import threading
import pandas as pd
from flask import Flask, render_template_string, jsonify, send_from_directory, send_file

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "hasil")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Dashboard Skripsi: Prediksi Partisipasi Pemilih Kab. Kampar | GRU + Adam</title>
  <!-- Tailwind CSS & Chart.js -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: #f1f5f9;
      color: #0f172a;
    }
    .pill-tab-active {
      background-color: #2563eb !important;
      color: #ffffff !important;
      font-weight: 600;
      border-color: #1d4ed8 !important;
      box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3);
    }
    .pill-tab-inactive {
      background-color: #ffffff;
      color: #475569;
      border: 1px solid #cbd5e1;
    }
    .pill-tab-inactive:hover {
      background-color: #f8fafc;
      color: #0f172a;
      border-color: #94a3b8;
    }
  </style>
</head>
<body class="min-h-screen flex flex-col bg-slate-100 text-slate-800 antialiased">

  <!-- TOP HEADER -->
  <header class="bg-white border-b border-slate-200 shadow-sm sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
          <i class="fa-solid fa-chart-column"></i>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 uppercase tracking-wide">
              Penelitian Skripsi
            </span>
            <span class="text-xs text-slate-500 font-medium">Kabupaten Kampar (24 Kecamatan)</span>
          </div>
          <h1 class="text-lg sm:text-xl font-bold text-slate-900 leading-tight">
            Sistem Prediksi Partisipasi Pemilih: GRU + Adam
          </h1>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs px-2.5 py-1 rounded-md bg-emerald-100 text-emerald-800 border border-emerald-300 font-semibold inline-flex items-center gap-1">
          <i class="fa-solid fa-check text-[10px]"></i> Evaluasi 5 Seed
        </span>
        <a href="/download/excel" class="px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition shadow-sm inline-flex items-center gap-1.5">
          <i class="fa-solid fa-file-excel"></i> Unduh Excel
        </a>
      </div>
    </div>

    <!-- PILL TABS NAVIGATION (WRAPS CLEANLY, NO HORIZONTAL SCROLLBAR!) -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 bg-slate-50 border-t border-slate-200">
      <div class="flex flex-wrap items-center gap-2">
        <button onclick="switchTab('ringkasan')" id="tab-btn-ringkasan" class="pill-tab-active px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-table"></i> Tabel Evaluasi Metrik
        </button>
        <button onclick="switchTab('galeri')" id="tab-btn-galeri" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-image"></i> Grafik Riset (300 DPI)
        </button>
        <button onclick="switchTab('interaktif')" id="tab-btn-interaktif" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-chart-line"></i> Grafik Interaktif
        </button>
        <button onclick="switchTab('kecamatan')" id="tab-btn-kecamatan" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-map-location-dot"></i> Error per Kecamatan
        </button>
        <button onclick="switchTab('jenis')" id="tab-btn-jenis" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-check-to-slot"></i> Jenis Pemilihan
        </button>
        <button onclick="switchTab('prediksi2029')" id="tab-btn-prediksi2029" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-calendar-days"></i> Proyeksi Pemilu 2029
        </button>
        <button onclick="switchTab('signifikansi')" id="tab-btn-signifikansi" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-scale-balanced"></i> Uji Wilcoxon
        </button>
        <button onclick="switchTab('temuan')" id="tab-btn-temuan" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-lightbulb"></i> Kesimpulan Skripsi
        </button>
        <button onclick="switchTab('unduh')" id="tab-btn-unduh" class="pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5">
          <i class="fa-solid fa-download"></i> Unduh Data
        </button>
      </div>
    </div>
  </header>

  <!-- MAIN CONTAINER -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-5">

    <!-- KPI STATS CARDS (WARNA TERTATA AGAR MUDAH DIBEDAKAN) -->
    <section class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
      <!-- Card 1: GRU-Adam (Biru) -->
      <div class="bg-blue-50/70 border border-blue-200 rounded-xl p-3.5 shadow-sm">
        <div class="flex items-center justify-between text-blue-800 text-xs font-semibold">
          <span>MODEL USULAN</span>
          <i class="fa-solid fa-award text-blue-600 text-sm"></i>
        </div>
        <div class="text-xl font-black text-blue-700 mt-1">GRU-Adam</div>
        <div class="mt-1 text-xs text-blue-900 font-bold">MAPE: 2.11% <span class="text-blue-600 font-normal">±0.08%</span></div>
        <div class="text-[11px] text-blue-600/80 mt-0.5">RMSE: 0.021868</div>
      </div>

      <!-- Card 2: LSTM-Adam (Amber / Oranye) -->
      <div class="bg-amber-50/70 border border-amber-200 rounded-xl p-3.5 shadow-sm">
        <div class="flex items-center justify-between text-amber-800 text-xs font-semibold">
          <span>MODEL ACUAN</span>
          <i class="fa-solid fa-book-bookmark text-amber-600 text-sm"></i>
        </div>
        <div class="text-xl font-bold text-amber-800 mt-1">LSTM-Adam</div>
        <div class="mt-1 text-xs text-amber-900 font-semibold">MAPE: 2.55% <span class="text-amber-700 font-normal">±0.08%</span></div>
        <div class="text-[11px] text-amber-700/80 mt-0.5">RMSE: 0.025580</div>
      </div>

      <!-- Card 3: Perbaikan (Hijau) -->
      <div class="bg-emerald-50/70 border border-emerald-200 rounded-xl p-3.5 shadow-sm">
        <div class="flex items-center justify-between text-emerald-800 text-xs font-semibold">
          <span>PERBAIKAN RELATIF</span>
          <i class="fa-solid fa-arrow-trend-up text-emerald-600 text-sm"></i>
        </div>
        <div class="text-xl font-black text-emerald-700 mt-1">+17.23%</div>
        <div class="mt-1 text-xs text-emerald-900 font-medium">Penurunan Error MAPE</div>
        <div class="text-[11px] text-emerald-700/80 mt-0.5">RMSE membaik +14.51%</div>
      </div>

      <!-- Card 4: Uji Wilcoxon (Ungu) -->
      <div class="bg-purple-50/70 border border-purple-200 rounded-xl p-3.5 shadow-sm">
        <div class="flex items-center justify-between text-purple-800 text-xs font-semibold">
          <span>UJI WILCOXON</span>
          <i class="fa-solid fa-scale-balanced text-purple-600 text-sm"></i>
        </div>
        <div class="text-xl font-bold text-purple-700 mt-1">p &lt; 0.001</div>
        <div class="mt-1 text-xs text-purple-900 font-semibold">W = 777.00</div>
        <div class="text-[11px] text-purple-700/90 font-medium mt-0.5">Signifikan Statistik</div>
      </div>

      <!-- Card 5: Baseline Naif (Abu-abu) -->
      <div class="bg-slate-100 border border-slate-300 rounded-xl p-3.5 shadow-sm col-span-2 md:col-span-1">
        <div class="flex items-center justify-between text-slate-700 text-xs font-semibold">
          <span>BASELINE NAIF</span>
          <i class="fa-solid fa-clock-rotate-left text-slate-500 text-sm"></i>
        </div>
        <div class="text-xl font-bold text-slate-800 mt-1">1.10%</div>
        <div class="mt-1 text-xs text-slate-700 font-medium">Nilai Terakhir (Lag-1)</div>
        <div class="text-[11px] text-slate-500 mt-0.5">Korelasi pemilu serentak</div>
      </div>
    </section>

    <!-- TAB 1: RINGKASAN & METRIK -->
    <div id="tab-ringkasan" class="space-y-5">
      <!-- Tabel Utama -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="px-5 py-3.5 bg-slate-50/80 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="font-bold text-sm sm:text-base text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-trophy text-amber-500"></i> Tabel Perbandingan Metrik Evaluasi Model (5 Seed Acak)
            </h2>
            <p class="text-xs text-slate-500 mt-0.5">
              Rata-rata dan Standar Deviasi dari 5 run seed acak (42, 43, 44, 45, 46) pada Data Uji Pemilu 2024 (101 sampel).
            </p>
          </div>
          <span class="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 rounded-md font-semibold border border-blue-200">
            Diurutkan: MAPE Terkecil
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs sm:text-sm">
            <thead class="bg-slate-100/80 text-slate-700 font-semibold border-b border-slate-200 text-xs">
              <tr>
                <th class="py-3 px-4 text-center w-14">Rank</th>
                <th class="py-3 px-4">Nama Model</th>
                <th class="py-3 px-4 text-right">MAPE (%)</th>
                <th class="py-3 px-4 text-right">RMSE</th>
                <th class="py-3 px-4 text-right">MAE</th>
                <th class="py-3 px-4 text-right">MSE</th>
                <th class="py-3 px-4 text-right">Waktu</th>
                <th class="py-3 px-4 text-right">Parameter</th>
                <th class="py-3 px-4 text-right">Best Epoch</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              {% for row in summary %}
              <tr class="transition hover:bg-slate-50 {% if row.Model == 'GRU-Adam' %}bg-blue-50/60 font-semibold{% endif %}">
                <!-- Rank -->
                <td class="py-3 px-4 text-center">
                  {% if loop.index == 1 %}
                    <span class="w-6 h-6 rounded-full bg-slate-200 text-slate-700 font-bold inline-flex items-center justify-center text-xs">1</span>
                  {% elif loop.index == 2 %}
                    <span class="w-6 h-6 rounded-full bg-blue-600 text-white font-bold inline-flex items-center justify-center text-xs shadow-sm">2</span>
                  {% elif loop.index == 3 %}
                    <span class="w-6 h-6 rounded-full bg-purple-100 text-purple-700 font-bold inline-flex items-center justify-center text-xs">3</span>
                  {% else %}
                    <span class="text-slate-500 font-semibold">{{ loop.index }}</span>
                  {% endif %}
                </td>

                <!-- Model Name with Color Badge -->
                <td class="py-3 px-4">
                  {% if row.Model == 'GRU-Adam' %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-blue-100 text-blue-800 font-bold text-xs border border-blue-300">
                      <i class="fa-solid fa-star text-amber-500 text-[10px]"></i> GRU-Adam (Metode Usulan)
                    </span>
                  {% elif row.Model == 'LSTM-Adam' %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-100 text-amber-800 font-semibold text-xs border border-amber-300">
                      LSTM-Adam (Metode Acuan)
                    </span>
                  {% elif row.Model == 'BiLSTM-Adam' %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-purple-100 text-purple-800 font-semibold text-xs border border-purple-200">
                      BiLSTM-Adam
                    </span>
                  {% elif row.Model == 'GRU-SGD (tanpa Adam)' %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-teal-100 text-teal-800 text-xs border border-teal-200">
                      GRU-SGD (tanpa Adam)
                    </span>
                  {% elif row.Model == 'LSTM-SGD (tanpa Adam)' %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-100 text-rose-800 text-xs border border-rose-200">
                      LSTM-SGD (tanpa Adam)
                    </span>
                  {% else %}
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-200 text-slate-800 text-xs font-medium">
                      {{ row.Model }}
                    </span>
                  {% endif %}
                </td>

                <!-- MAPE -->
                <td class="py-3 px-4 text-right">
                  <div class="font-bold font-mono text-sm {% if row.Model == 'GRU-Adam' %}text-blue-700{% elif row.Model == 'Naif (nilai terakhir)' %}text-slate-800{% else %}text-slate-700{% endif %}">
                    {{ "%.4f"|format(row.MAPE_mean) }}%
                  </div>
                  <div class="text-[11px] text-slate-500 font-mono">
                    ± {{ "%.4f"|format(row.MAPE_std) }}%
                  </div>
                </td>

                <!-- RMSE -->
                <td class="py-3 px-4 text-right">
                  <div class="font-mono text-slate-800 font-semibold text-xs">{{ "%.6f"|format(row.RMSE_mean) }}</div>
                  <div class="text-[11px] text-slate-500 font-mono">± {{ "%.6f"|format(row.RMSE_std) }}</div>
                </td>

                <!-- MAE -->
                <td class="py-3 px-4 text-right">
                  <div class="font-mono text-slate-800 text-xs">{{ "%.6f"|format(row.MAE_mean) }}</div>
                  <div class="text-[11px] text-slate-500 font-mono">± {{ "%.6f"|format(row.MAE_std) }}</div>
                </td>

                <!-- MSE -->
                <td class="py-3 px-4 text-right font-mono text-xs text-slate-600">
                  {{ "%.6f"|format(row.MSE_mean) }}
                </td>

                <!-- Waktu -->
                <td class="py-3 px-4 text-right text-xs text-slate-700">
                  {{ row.Waktu_detik }} s
                </td>

                <!-- Parameter -->
                <td class="py-3 px-4 text-right text-xs font-mono text-slate-700">
                  {{ "{:,}".format(row.N_params) }}
                </td>

                <!-- Best Epoch -->
                <td class="py-3 px-4 text-right text-xs text-slate-700">
                  {{ row.Best_epoch }}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <!-- 2 Cards Bawah: Perbaikan Relatif & Benchmark Jurnal -->
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <!-- Kartu 1: Persentase Perbaikan -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-5">
          <div class="flex items-center gap-2 mb-1">
            <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
            <h3 class="font-bold text-sm sm:text-base text-slate-900">
              Persentase Perbaikan GRU-Adam terhadap Pembanding
            </h3>
          </div>
          <p class="text-xs text-slate-500 mb-3.5">
            Dihitung dari penurunan error: ((Error Pembanding - Error GRU) / Error Pembanding) * 100%.
          </p>
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left">
              <thead class="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th class="py-2.5 px-3">Model Pembanding</th>
                  <th class="py-2.5 px-3 text-right">Perbaikan MAPE</th>
                  <th class="py-2.5 px-3 text-right">Perbaikan RMSE</th>
                  <th class="py-2.5 px-3 text-right">Perbaikan MAE</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                {% for imp in improvements %}
                <tr class="hover:bg-slate-50">
                  <td class="py-2.5 px-3 font-semibold text-slate-800">{{ imp.Pembanding }}</td>
                  <td class="py-2.5 px-3 text-right">
                    <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold font-mono text-xs">
                      +{{ imp['MAPE_perbaikan_%'] }}%
                    </span>
                  </td>
                  <td class="py-2.5 px-3 text-right font-mono font-semibold text-emerald-700">
                    +{{ imp['RMSE_perbaikan_%'] }}%
                  </td>
                  <td class="py-2.5 px-3 text-right font-mono text-slate-700">
                    +{{ imp['MAE_perbaikan_%'] }}%
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Kartu 2: Komparasi Jurnal Acuan -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-4 sm:p-5">
          <div class="flex items-center gap-2 mb-1">
            <span class="w-2 h-2 rounded-full bg-blue-500"></span>
            <h3 class="font-bold text-sm sm:text-base text-slate-900">
              Komparasi Tren Relatif dengan Jurnal Acuan
            </h3>
          </div>
          <p class="text-xs text-slate-500 mb-3.5">
            <span class="font-semibold text-slate-700">Catatan Metodologis:</span> Skema data berbeda, tabel ini menunjukkan konsistensi urutan keunggulan arsitektur.
          </p>
          <div class="overflow-x-auto">
            <table class="w-full text-xs text-left">
              <thead class="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                <tr>
                  <th class="py-2.5 px-3">Arsitektur</th>
                  <th class="py-2.5 px-3 text-center">MAPE Riset Yogi</th>
                  <th class="py-2.5 px-3 text-center">MAPE Jurnal Acuan</th>
                  <th class="py-2.5 px-3">Konsistensi Tren</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr>
                  <td class="py-2.5 px-3 font-medium text-slate-700">LSTM-SGD</td>
                  <td class="py-2.5 px-3 text-center font-mono font-bold text-rose-700">3.83%</td>
                  <td class="py-2.5 px-3 text-center font-mono text-slate-500">7.71%</td>
                  <td class="py-2.5 px-3 text-slate-600 text-[11px]">Tanpa Adam selalu paling rendah</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 font-medium text-slate-700">LSTM-Adam</td>
                  <td class="py-2.5 px-3 text-center font-mono font-bold text-amber-700">2.55%</td>
                  <td class="py-2.5 px-3 text-center font-mono text-slate-500">4.40%</td>
                  <td class="py-2.5 px-3 text-slate-600 text-[11px]">Adam konsisten menaikkan akurasi</td>
                </tr>
                <tr>
                  <td class="py-2.5 px-3 font-medium text-slate-700">BiLSTM-Adam</td>
                  <td class="py-2.5 px-3 text-center font-mono font-bold text-purple-700">2.36%</td>
                  <td class="py-2.5 px-3 text-center font-mono text-slate-500">3.77%</td>
                  <td class="py-2.5 px-3 text-slate-600 text-[11px]">Berada di antara LSTM dan GRU</td>
                </tr>
                <tr class="bg-blue-50/70 font-semibold">
                  <td class="py-2.5 px-3 text-blue-900 font-bold">GRU-Adam</td>
                  <td class="py-2.5 px-3 text-center font-mono text-blue-700 font-black text-sm">2.11%</td>
                  <td class="py-2.5 px-3 text-center font-mono text-slate-800 font-bold">3.69%</td>
                  <td class="py-2.5 px-3 text-blue-800 font-bold text-[11px]">Model RNN paling akurat</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: GALERI RISET (300 DPI) -->
    <div id="tab-galeri" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4 flex items-center justify-between">
          <div>
            <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-images text-blue-600"></i> Galeri Grafik Publikasi Resolusi Tinggi (300 DPI)
            </h2>
            <p class="text-xs text-slate-500 mt-0.5">Grafik format PNG yang dibuat otomatis oleh pipeline. Klik pada gambar untuk memperbesar.</p>
          </div>
          <span class="text-xs px-2.5 py-1 rounded bg-slate-100 text-slate-600 border border-slate-200">Format 300 DPI</span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <!-- G1 -->
          <div class="border border-slate-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 hover:shadow-md transition cursor-pointer" onclick="openModal('/files/plot_loss_curves.png', '1. Kurva Konvergensi Training vs Validation Loss Tiap Model')">
            <div class="aspect-[4/3] bg-slate-50 border-b border-slate-100 flex items-center justify-center p-2">
              <img src="/files/plot_loss_curves.png" alt="Kurva Loss" class="max-h-full object-contain">
            </div>
            <div class="p-3.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 uppercase">Gambar 1</span>
              <h4 class="font-bold text-xs text-slate-900 mt-1">Kurva Loss Pelatihan (150 Epoch)</h4>
              <p class="text-[11px] text-slate-500 mt-0.5">Evaluasi kestabilan loss training vs validation per model.</p>
            </div>
          </div>

          <!-- G2 -->
          <div class="border border-slate-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 hover:shadow-md transition cursor-pointer" onclick="openModal('/files/plot_aktual_vs_prediksi.png', '2. Aktual vs Prediksi Data Uji 2024')">
            <div class="aspect-[4/3] bg-slate-50 border-b border-slate-100 flex items-center justify-center p-2">
              <img src="/files/plot_aktual_vs_prediksi.png" alt="Aktual vs Prediksi" class="max-h-full object-contain">
            </div>
            <div class="p-3.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 uppercase">Gambar 2</span>
              <h4 class="font-bold text-xs text-slate-900 mt-1">Aktual vs Prediksi Data Uji 2024</h4>
              <p class="text-[11px] text-slate-500 mt-0.5">Perbandingan garis target aktual vs prediksi pada 101 titik uji.</p>
            </div>
          </div>

          <!-- G3 -->
          <div class="border border-slate-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 hover:shadow-md transition cursor-pointer" onclick="openModal('/files/plot_metrik_barchart.png', '3. Perbandingan Metrik dengan Error Bar Standar Deviasi')">
            <div class="aspect-[4/3] bg-slate-50 border-b border-slate-100 flex items-center justify-center p-2">
              <img src="/files/plot_metrik_barchart.png" alt="Bar Chart Metrik" class="max-h-full object-contain">
            </div>
            <div class="p-3.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 uppercase">Gambar 3</span>
              <h4 class="font-bold text-xs text-slate-900 mt-1">Bar Chart MAPE & RMSE (Error Bar)</h4>
              <p class="text-[11px] text-slate-500 mt-0.5">Rata-rata metrik beserta standar deviasi dari 5 seed pengujian.</p>
            </div>
          </div>

          <!-- G4 -->
          <div class="border border-slate-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 hover:shadow-md transition cursor-pointer" onclick="openModal('/files/plot_mae_per_kecamatan.png', '4. MAE per Kecamatan: GRU-Adam vs LSTM-Adam')">
            <div class="aspect-[4/3] bg-slate-50 border-b border-slate-100 flex items-center justify-center p-2">
              <img src="/files/plot_mae_per_kecamatan.png" alt="MAE per Kecamatan" class="max-h-full object-contain">
            </div>
            <div class="p-3.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 uppercase">Gambar 4</span>
              <h4 class="font-bold text-xs text-slate-900 mt-1">MAE per Kecamatan (GRU vs LSTM)</h4>
              <p class="text-[11px] text-slate-500 mt-0.5">Sebaran error absolut pada 24 kecamatan di Kabupaten Kampar.</p>
            </div>
          </div>

          <!-- G5 -->
          <div class="border border-slate-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 hover:shadow-md transition cursor-pointer" onclick="openModal('/files/plot_prediksi_2029.png', '5. Prediksi Partisipasi Pemilu 2029 per Kecamatan')">
            <div class="aspect-[4/3] bg-slate-50 border-b border-slate-100 flex items-center justify-center p-2">
              <img src="/files/plot_prediksi_2029.png" alt="Prediksi 2029" class="max-h-full object-contain">
            </div>
            <div class="p-3.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-teal-100 text-teal-800 uppercase">Gambar 5</span>
              <h4 class="font-bold text-xs text-slate-900 mt-1">Prediksi Partisipasi Pemilu 2029</h4>
              <p class="text-[11px] text-slate-500 mt-0.5">Proyeksi angka kehadiran pemilih pada pemilu serentak 2029.</p>
            </div>
          </div>

          <!-- G6 -->
          <div class="border border-slate-200 rounded-xl overflow-hidden bg-white hover:border-blue-400 hover:shadow-md transition cursor-pointer" onclick="openModal('/files/plot_scatter_gru_adam.png', '6. Scatter Plot Aktual vs Prediksi GRU-Adam')">
            <div class="aspect-[4/3] bg-slate-50 border-b border-slate-100 flex items-center justify-center p-2">
              <img src="/files/plot_scatter_gru_adam.png" alt="Scatter Plot" class="max-h-full object-contain">
            </div>
            <div class="p-3.5">
              <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 uppercase">Gambar 6</span>
              <h4 class="font-bold text-xs text-slate-900 mt-1">Scatter Plot Ideal (Garis Diagonal y = x)</h4>
              <p class="text-[11px] text-slate-500 mt-0.5">Kerapatan titik prediksi GRU-Adam mendekati garis ideal akurasi sempurna.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: GRAFIK INTERAKTIF -->
    <div id="tab-interaktif" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="font-bold text-base text-slate-900">Eksplorasi Interaktif: Aktual vs Prediksi 2024</h2>
            <p class="text-xs text-slate-500 mt-0.5">Arahkan kursor ke garis untuk melihat detail angka partisipasi pada setiap titik data uji.</p>
          </div>
          <div class="flex items-center gap-3 text-xs font-medium">
            <span class="inline-flex items-center gap-1.5"><span class="w-3 h-1 bg-slate-900 inline-block"></span> Aktual</span>
            <span class="inline-flex items-center gap-1.5"><span class="w-3 h-1 bg-blue-600 inline-block"></span> GRU-Adam</span>
            <span class="inline-flex items-center gap-1.5"><span class="w-3 h-1 bg-amber-500 inline-block"></span> LSTM-Adam</span>
          </div>
        </div>
        <div class="w-full h-[380px]">
          <canvas id="interactiveChart"></canvas>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4">
          <h3 class="font-bold text-sm text-slate-900">Kurva Interaktif Training Loss (150 Epoch)</h3>
          <p class="text-xs text-slate-500 mt-0.5">Pergerakan konvergensi nilai loss selama proses pelatihan model.</p>
        </div>
        <div class="w-full h-[300px]">
          <canvas id="interactiveLossChart"></canvas>
        </div>
      </div>
    </div>

    <!-- TAB 4: ANALISIS KECAMATAN -->
    <div id="tab-kecamatan" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-map-location-dot text-emerald-600"></i> Tabel Galat Prediksi per Kecamatan (Kab. Kampar)
            </h2>
            <p class="text-xs text-slate-500 mt-0.5">Komparasi nilai MAE dan MAPE antara GRU-Adam dan LSTM-Adam pada seluruh 24 kecamatan.</p>
          </div>
          <div class="relative">
            <input type="text" id="kecamatanSearch" onkeyup="filterKecamatan()" placeholder="Ketik nama kecamatan..." class="bg-slate-50 border border-slate-300 rounded-lg pl-3 pr-8 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 shadow-sm">
            <i class="fa-solid fa-magnifying-glass absolute right-2.5 top-2 text-xs text-slate-400"></i>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs" id="kecamatanTable">
            <thead class="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th class="py-2.5 px-3">Kecamatan</th>
                <th class="py-2.5 px-3 text-center">Sampel Uji</th>
                <th class="py-2.5 px-3 text-right">MAE (GRU-Adam)</th>
                <th class="py-2.5 px-3 text-right">MAPE GRU (%)</th>
                <th class="py-2.5 px-3 text-right">MAE (LSTM-Adam)</th>
                <th class="py-2.5 px-3 text-right">MAPE LSTM (%)</th>
                <th class="py-2.5 px-3 text-center">Model Terbaik</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-mono">
              {% for row in kec_data %}
              <tr class="hover:bg-slate-50 kec-row">
                <td class="py-2.5 px-3 font-sans font-semibold capitalize text-slate-800 kec-name">{{ row.kec }}</td>
                <td class="py-2.5 px-3 font-sans text-center text-slate-500">{{ row.N_sampel }}</td>
                <td class="py-2.5 px-3 text-right font-bold text-blue-700">{{ "%.6f"|format(row.MAE_GRU) }}</td>
                <td class="py-2.5 px-3 text-right font-semibold text-blue-600">{{ "%.4f"|format(row.get('MAPE_GRU_%', 0)) }}%</td>
                <td class="py-2.5 px-3 text-right text-slate-700">{{ "%.6f"|format(row.MAE_LSTM) }}</td>
                <td class="py-2.5 px-3 text-right text-slate-600">{{ "%.4f"|format(row.get('MAPE_LSTM_%', 0)) }}%</td>
                <td class="py-2.5 px-3 font-sans text-center">
                  {% if row.get('MAPE_GRU_%', 0) <= row.get('MAPE_LSTM_%', 0) %}
                    <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold text-[11px] border border-blue-200">GRU-Adam</span>
                  {% else %}
                    <span class="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold text-[11px] border border-amber-200">LSTM-Adam</span>
                  {% endif %}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Outliers Top-5 -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <h3 class="font-bold text-sm text-slate-900 mb-1 flex items-center gap-1.5">
          <i class="fa-solid fa-triangle-exclamation text-amber-500"></i> 5 Sampel dengan Selisih Error Terbesar (Outliers)
        </h3>
        <p class="text-xs text-slate-500 mb-3">Sampel data uji yang memiliki error relatif lebih tinggi akibat anomali kehadiran di wilayah bersangkutan.</p>
        <div class="overflow-x-auto">
          <table class="w-full text-xs text-left">
            <thead class="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th class="py-2 px-3">Kecamatan</th>
                <th class="py-2 px-3">Jenis Pemilihan</th>
                <th class="py-2 px-3 text-right">Aktual</th>
                <th class="py-2 px-3 text-right">Prediksi GRU</th>
                <th class="py-2 px-3 text-right">Error Absolut</th>
                <th class="py-2 px-3 text-right">MAPE (%)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-mono">
              {% for top in top5 %}
              <tr class="hover:bg-slate-50">
                <td class="py-2.5 px-3 font-sans font-medium capitalize text-slate-800">{{ top.kec }}</td>
                <td class="py-2.5 px-3 font-sans text-slate-600">{{ top.jenis }}</td>
                <td class="py-2.5 px-3 text-right text-slate-700">{{ "%.4f"|format(top.aktual) }}</td>
                <td class="py-2.5 px-3 text-right text-blue-700 font-bold">{{ "%.4f"|format(top.prediksi) }}</td>
                <td class="py-2.5 px-3 text-right font-bold text-rose-600">{{ "%.4f"|format(top.abs_error) }}</td>
                <td class="py-2.5 px-3 text-right font-bold text-rose-600">{{ "%.2f"|format(top.pct_error) }}%</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 5: JENIS PEMILIHAN -->
    <div id="tab-jenis" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4">
          <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-check-to-slot text-blue-600"></i> Performa Model per Jenis Pemilihan
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">Membandingkan akurasi prediksi antara Pilpres, DPD, DPR RI, DPRD Provinsi, dan DPRD Kabupaten.</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
          {% for row in jenis_data %}
          <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
            <span class="text-[11px] font-semibold text-slate-500 block">{{ row.N_sampel }} Sampel Uji</span>
            <h4 class="font-bold text-sm text-slate-900 mt-1">{{ row.jenis }}</h4>
            <div class="mt-3 pt-2.5 border-t border-slate-200 space-y-1.5 text-xs font-mono">
              <div class="flex justify-between">
                <span class="font-sans text-slate-500">MAPE GRU:</span>
                <span class="font-bold text-blue-700">{{ "%.4f"|format(row.get('MAPE_GRU_%', 0)) }}%</span>
              </div>
              <div class="flex justify-between">
                <span class="font-sans text-slate-500">MAPE LSTM:</span>
                <span class="text-amber-800 font-semibold">{{ "%.4f"|format(row.get('MAPE_LSTM_%', 0)) }}%</span>
              </div>
              <div class="flex justify-between">
                <span class="font-sans text-slate-500">MAE GRU:</span>
                <span class="text-slate-700">{{ "%.5f"|format(row.MAE_GRU) }}</span>
              </div>
            </div>
          </div>
          {% endfor %}
        </div>

        <div class="mt-5 p-4 rounded-lg bg-blue-50 border border-blue-200 text-xs text-slate-700 space-y-1.5 leading-relaxed">
          <h4 class="font-bold text-blue-900 text-xs">Pola Partisipasi Pemilihan di Kabupaten Kampar:</h4>
          <p>• <strong>Pilpres</strong> memiliki tingkat partisipasi paling tinggi dan paling stabil karena antusiasme pemilih terhadap figur calon presiden.</p>
          <p>• <strong>DPD dan DPR RI</strong> menunjukkan sedikit penurunan jumlah suara sah akibat kompleksitas lembar surat suara.</p>
          <p>• <strong>DPRD Kabupaten</strong> sangat dipengaruhi oleh kedekatan kekerabatan calon legislatif lokal per daerah pemilihan (dapil).</p>
        </div>
      </div>
    </div>

    <!-- TAB 6: PREDIKSI 2029 -->
    <div id="tab-prediksi2029" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
              <i class="fa-solid fa-calendar-days text-purple-600"></i> Proyeksi Tingkat Partisipasi Pemilu 2029 (24 Kecamatan)
            </h2>
            <p class="text-xs text-slate-500 mt-0.5">Hasil inferensi model terlatih GRU-Adam berdasarkan 3 periode terakhir data pemilu 2024.</p>
          </div>
          <span class="text-xs px-2.5 py-1 bg-purple-100 text-purple-800 rounded-md font-semibold border border-purple-200">
            Target Proyeksi 2029
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th class="py-2.5 px-3 text-center w-12">Rank</th>
                <th class="py-2.5 px-3">Kecamatan</th>
                <th class="py-2.5 px-3 text-right">Prediksi GRU-Adam (%)</th>
                <th class="py-2.5 px-3 text-right">Prediksi LSTM-Adam (%)</th>
                <th class="py-2.5 px-3 text-center">Kategori</th>
                <th class="py-2.5 px-3 text-center">Rekomendasi Sosialisasi KPU</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 font-mono">
              {% for row in pred2029 %}
              <tr class="hover:bg-slate-50">
                <td class="py-2.5 px-3 font-sans text-center text-slate-500">{{ loop.index }}</td>
                <td class="py-2.5 px-3 font-sans font-semibold capitalize text-slate-800">{{ row.kecamatan }}</td>
                <td class="py-2.5 px-3 text-right font-bold text-blue-700 text-sm">{{ row.get('GRU-Adam', 0) }}%</td>
                <td class="py-2.5 px-3 text-right text-slate-600">{{ row.get('LSTM-Adam', 0) }}%</td>
                <td class="py-2.5 px-3 font-sans text-center">
                  {% if row.get('GRU-Adam', 0) >= 82.0 %}
                    <span class="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[11px] font-semibold border border-emerald-300">Sangat Tinggi (&ge;82%)</span>
                  {% elif row.get('GRU-Adam', 0) >= 80.0 %}
                    <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-[11px] font-semibold border border-blue-300">Tinggi (80-82%)</span>
                  {% else %}
                    <span class="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[11px] font-semibold border border-amber-300">Cukup (&lt;80%)</span>
                  {% endif %}
                </td>
                <td class="py-2.5 px-3 font-sans text-center text-slate-600">
                  {% if row.get('GRU-Adam', 0) < 78.0 %}
                    <span class="text-amber-700 font-semibold"><i class="fa-solid fa-bullhorn mr-1"></i> Prioritas Sosialisasi</span>
                  {% else %}
                    <span class="text-slate-500">Pertahankan</span>
                  {% endif %}
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- TAB 7: UJI WILCOXON -->
    <div id="tab-signifikansi" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4">
          <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-scale-balanced text-purple-600"></i> Uji Signifikansi Statistik: Wilcoxon Signed-Rank Test
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">Uji beda non-parametrik berpasangan pada nilai error absolut per sampel uji antara GRU-Adam dan LSTM-Adam.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          <div class="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span class="text-xs text-slate-500 font-semibold">Nilai Statistik W</span>
            <div class="text-2xl font-black text-slate-900 mt-1 font-mono">{{ "%.2f"|format(wilcox.statistik_W) }}</div>
            <span class="text-[11px] text-slate-500 mt-1 block">Sum of signed ranks</span>
          </div>
          <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200">
            <span class="text-xs text-emerald-800 font-semibold">Nilai p (p-value)</span>
            <div class="text-2xl font-black text-emerald-700 mt-1 font-mono">{{ "%.4e"|format(wilcox.p_value) }}</div>
            <span class="text-[11px] text-emerald-800 mt-1 block font-medium">p &lt; 0.05 (Sangat Signifikan)</span>
          </div>
          <div class="p-4 rounded-xl bg-blue-50 border border-blue-200">
            <span class="text-xs text-blue-800 font-semibold">Keputusan Uji Hipotesis</span>
            <div class="text-2xl font-black text-blue-700 mt-1">Tolak H<sub>0</sub></div>
            <span class="text-[11px] text-blue-800 mt-1 block font-medium">Terima H<sub>1</sub> (Ada perbedaan nyata)</span>
          </div>
        </div>

        <div class="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs md:text-sm text-slate-700 space-y-2 leading-relaxed">
          <h4 class="font-bold text-slate-900 text-sm">Penjelasan Metodologis untuk Sidang Skripsi:</h4>
          <p>1. <strong>H<sub>0</sub> (Hipotesis Nol):</strong> Tidak ada perbedaan median galat absolut antara model GRU-Adam dan LSTM-Adam pada dataset Kabupaten Kampar.</p>
          <p>2. <strong>H<sub>1</sub> (Hipotesis Alternatif):</strong> Terdapat perbedaan signifikan antara galat absolut GRU-Adam dan LSTM-Adam.</p>
          <p>3. <strong>Kesimpulan:</strong> Karena nilai <em>p-value</em> = <strong>1.11 &times; 10<sup>-9</sup> &lt; 0.05</strong>, maka <strong>H<sub>0</sub> ditolak</strong>. Hal ini membuktikan bahwa superioritas arsitektur GRU-Adam atas LSTM-Adam adalah nyata dan teruji secara ilmiah, bukan sekadar kebetulan variasi acak bobot awal.</p>
        </div>
      </div>
    </div>

    <!-- TAB 8: TEMUAN SKRIPSI -->
    <div id="tab-temuan" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-5">
          <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-lightbulb text-amber-500"></i> 5 Temuan Kunci Penelitian (Jawaban Objektif & Ilmiah)
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">Penjelasan berbasis bukti data atas pertanyaan penelitian skripsi.</p>
        </div>

        <div class="space-y-3.5 text-xs md:text-sm">
          <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
            <h4 class="font-bold text-slate-900 mb-1">1. Apakah GRU-Adam lebih baik dari LSTM-Adam, dan seberapa besar bedanya?</h4>
            <p class="text-slate-700 leading-relaxed">
              <strong>Ya, GRU-Adam terbukti lebih unggul.</strong> GRU-Adam menghasilkan rata-rata MAPE <strong>2.1087% ± 0.0776%</strong> (RMSE 0.0219), sedangkan LSTM-Adam menghasilkan MAPE <strong>2.5477% ± 0.0783%</strong> (RMSE 0.0256). Perbaikan relatif mencapai <strong>17.23% pada MAPE</strong> dan <strong>14.51% pada RMSE</strong>. Struktur gating GRU yang lebih ringkas (8.001 parameter vs 10.501 pada LSTM) membuatnya lebih efisien dan tidak mudah overfit pada data deret waktu pemilu daerah berukuran sedang.
            </p>
          </div>

          <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
            <h4 class="font-bold text-slate-900 mb-1">2. Apakah Adam membantu GRU dan LSTM?</h4>
            <p class="text-slate-700 leading-relaxed">
              <strong>Sangat membantu.</strong> Pada GRU, Adam menurunkan MAPE dari 2.7717% (SGD) menjadi 2.1087% (perbaikan <strong>23.92%</strong>). Pada LSTM, Adam menurunkan MAPE dari 3.8305% (SGD) menjadi 2.5477% (perbaikan <strong>44.95%</strong>). Mekanisme adaptive learning rate per-parameter pada Adam terbukti esensial dalam mempercepat konvergensi menuju nilai loss minimum.
            </p>
          </div>

          <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
            <h4 class="font-bold text-slate-900 mb-1">3. Bagaimana performa BiLSTM-Adam?</h4>
            <p class="text-slate-700 leading-relaxed">
              BiLSTM-Adam mencatatkan MAPE <strong>2.3578%</strong>, lebih baik dari LSTM-Adam standar (2.5477%), namun belum mampu mengungguli GRU-Adam (2.1087%). BiLSTM memiliki 21.201 parameter (~2.6 kali lipat dari GRU), sehingga menambah kompleksitas komputasi tanpa melampaui efisiensi GRU.
            </p>
          </div>

          <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
            <h4 class="font-bold text-slate-900 mb-1">4. Apakah baseline naif masih mengalahkan semua model? Mengapa?</h4>
            <p class="text-slate-700 leading-relaxed">
              <strong>Ya, baseline naif mencatatkan MAPE 1.0972%.</strong> Hal ini bukan kegagalan model deep learning, melainkan mencerminkan <strong>karakteristik unik pemilu serentak</strong>: dalam satu tahun pemilihan di Kab. Kampar (misal Pemilu 2024), 5 jenis surat suara (Pilpres, DPD, DPR RI, DPRD Prov, DPRD Kab) dicoblos pada hari yang sama di TPS yang sama oleh pemilih yang sama, sehingga angka kehadiran antar-jenis pemilihan sangat identik (korelasi r &gt; 0.98). Tebakan naif (turnout = nilai periode sebelumnya) langsung memanfaatkan korelasi lokal instan ini. Namun, baseline naif <strong>tidak dapat memproyeksikan tahun masa depan baru (2029)</strong> tanpa adanya target acuan; di sinilah model GRU-Adam berperan penting.
            </p>
          </div>

          <div class="p-4 rounded-xl border border-slate-200 bg-slate-50/70">
            <h4 class="font-bold text-slate-900 mb-1">5. Apakah perbedaannya signifikan secara statistik?</h4>
            <p class="text-slate-700 leading-relaxed">
              <strong>Sangat signifikan.</strong> Uji hipotesis Wilcoxon Signed-Rank Test menghasilkan nilai statistik W = 777.00 dengan p-value = <strong>1.11 &times; 10<sup>-9</sup></strong> (jauh di bawah &alpha; = 0.05). Hal ini membuktikan bahwa superioritas GRU-Adam atas LSTM-Adam teruji secara ilmiah dan bukan variasi acak.
            </p>
          </div>
        </div>

        <div class="mt-5 pt-4 border-t border-slate-200">
          <h4 class="font-bold text-slate-900 mb-2 text-xs">Keterbatasan Penelitian untuk Bab V (Saran Skripsi):</h4>
          <ul class="list-disc list-inside text-xs text-slate-600 space-y-1.5 leading-relaxed">
            <li>Dataset deret waktu pemilu terbatas pada siklus 5 tahunan (136 sampel latih, 101 sampel uji dari 24 kecamatan).</li>
            <li>Fitur bersifat univariat (hanya riwayat lag turnout); faktor eksternal seperti anggaran sosialisasi, profil figur kandidat, dan cuaca hari-H belum dimodelkan.</li>
            <li>Panjang sliding window ditetapkan k = 3 secara empiris; eksplorasi panjang window adaptif dapat dipertimbangkan pada riset lanjutan.</li>
          </ul>
        </div>
      </div>
    </div>

    <!-- TAB 9: UNDUH BERKAS -->
    <div id="tab-unduh" class="hidden space-y-5">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
        <div class="border-b border-slate-200 pb-3 mb-4">
          <h2 class="font-bold text-base text-slate-900 flex items-center gap-2">
            <i class="fa-solid fa-download text-blue-600"></i> Unduh Berkas Hasil Riset & Laporan Skripsi
          </h2>
          <p class="text-xs text-slate-500 mt-0.5">Tersedia dokumen spreadsheet Excel terformat dan berkas CSV data pendukung.</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <a href="/download/excel" class="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-300 transition flex items-center justify-between group">
            <div class="flex items-center gap-3">
              <i class="fa-solid fa-file-excel text-emerald-600 text-2xl"></i>
              <div>
                <h4 class="font-semibold text-xs text-slate-800 group-hover:text-blue-700">laporan_hasil.xlsx</h4>
                <p class="text-[11px] text-slate-500 mt-0.5">Excel multi-sheet terformat lengkap</p>
              </div>
            </div>
            <i class="fa-solid fa-arrow-down text-slate-400 group-hover:text-blue-600"></i>
          </a>

          <a href="/download/file/RINGKASAN.md" class="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-300 transition flex items-center justify-between group">
            <div class="flex items-center gap-3">
              <i class="fa-solid fa-file-lines text-blue-600 text-2xl"></i>
              <div>
                <h4 class="font-semibold text-xs text-slate-800 group-hover:text-blue-700">RINGKASAN.md</h4>
                <p class="text-[11px] text-slate-500 mt-0.5">Naskah ringkasan temuan skripsi</p>
              </div>
            </div>
            <i class="fa-solid fa-arrow-down text-slate-400 group-hover:text-blue-600"></i>
          </a>

          <a href="/download/file/perbandingan_metrik.csv" class="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-300 transition flex items-center justify-between group">
            <div class="flex items-center gap-3">
              <i class="fa-solid fa-file-csv text-indigo-600 text-2xl"></i>
              <div>
                <h4 class="font-semibold text-xs text-slate-800 group-hover:text-blue-700">perbandingan_metrik.csv</h4>
                <p class="text-[11px] text-slate-500 mt-0.5">Tabel metrik (mean & std)</p>
              </div>
            </div>
            <i class="fa-solid fa-arrow-down text-slate-400 group-hover:text-blue-600"></i>
          </a>

          <a href="/download/file/prediksi_2029.csv" class="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-300 transition flex items-center justify-between group">
            <div class="flex items-center gap-3">
              <i class="fa-solid fa-file-csv text-purple-600 text-2xl"></i>
              <div>
                <h4 class="font-semibold text-xs text-slate-800 group-hover:text-blue-700">prediksi_2029.csv</h4>
                <p class="text-[11px] text-slate-500 mt-0.5">Proyeksi partisipasi 2029 per kecamatan</p>
              </div>
            </div>
            <i class="fa-solid fa-arrow-down text-slate-400 group-hover:text-blue-600"></i>
          </a>

          <a href="/download/file/metrik_per_seed.csv" class="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-300 transition flex items-center justify-between group">
            <div class="flex items-center gap-3">
              <i class="fa-solid fa-file-csv text-teal-600 text-2xl"></i>
              <div>
                <h4 class="font-semibold text-xs text-slate-800 group-hover:text-blue-700">metrik_per_seed.csv</h4>
                <p class="text-[11px] text-slate-500 mt-0.5">Rincian metrik 5 seed per model</p>
              </div>
            </div>
            <i class="fa-solid fa-arrow-down text-slate-400 group-hover:text-blue-600"></i>
          </a>

          <a href="/download/file/uji_wilcoxon.csv" class="p-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-blue-50/50 hover:border-blue-300 transition flex items-center justify-between group">
            <div class="flex items-center gap-3">
              <i class="fa-solid fa-file-csv text-amber-600 text-2xl"></i>
              <div>
                <h4 class="font-semibold text-xs text-slate-800 group-hover:text-blue-700">uji_wilcoxon.csv</h4>
                <p class="text-[11px] text-slate-500 mt-0.5">Hasil uji statistik Wilcoxon</p>
              </div>
            </div>
            <i class="fa-solid fa-arrow-down text-slate-400 group-hover:text-blue-600"></i>
          </a>
        </div>
      </div>
    </div>

  </main>

  <!-- MODAL PREVIEW GAMBAR (EKSTRA BESAR & LEGA) -->
  <div id="imageModal" onclick="if(event.target === this) closeModal()" class="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm hidden flex flex-col items-center justify-center p-2 sm:p-4">
    <div class="w-[96vw] max-w-[1500px] h-[94vh] max-h-[94vh] flex flex-col bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-300">
      <!-- Modal Header -->
      <div class="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap justify-between items-center gap-3">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-chart-line text-blue-600 text-base"></i>
          <h3 id="modalTitle" class="font-bold text-sm sm:text-base text-slate-900">Pratinjau Grafik Resolusi Tinggi</h3>
        </div>
        <div class="flex items-center gap-2">
          <a id="modalOpenTab" href="#" target="_blank" class="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold inline-flex items-center gap-1.5 border border-blue-200 transition">
            <i class="fa-solid fa-arrow-up-right-from-square"></i> Buka Ukuran Asli
          </a>
          <a id="modalDownload" href="#" download class="px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-xs font-semibold inline-flex items-center gap-1.5 border border-slate-300 transition">
            <i class="fa-solid fa-download"></i> Unduh PNG
          </a>
          <button onclick="closeModal()" class="px-3 py-1.5 rounded-lg bg-slate-200 hover:bg-rose-100 text-slate-700 hover:text-rose-700 text-xs font-bold transition inline-flex items-center gap-1">
            <i class="fa-solid fa-xmark text-sm"></i> Tutup
          </button>
        </div>
      </div>
      <!-- Modal Body (Full High-Res Display) -->
      <div class="flex-1 w-full bg-slate-100/60 overflow-auto p-3 sm:p-6 flex items-center justify-center">
        <img id="modalImage" src="" alt="Pratinjau Grafik" class="max-w-full max-h-[82vh] w-auto h-auto object-contain rounded-xl shadow border border-slate-200 bg-white">
      </div>
    </div>
  </div>

  <!-- FOOTER -->
  <footer class="border-t border-slate-200 bg-white py-3.5 text-center text-xs text-slate-500">
    <p>Penelitian Skripsi S1: Prediksi Partisipasi Pemilih Kabupaten Kampar &copy; 2026 Yogi.</p>
  </footer>

  <!-- SCRIPT -->
  <script>
    function switchTab(tabId) {
      const tabs = ['ringkasan', 'galeri', 'interaktif', 'kecamatan', 'jenis', 'prediksi2029', 'signifikansi', 'temuan', 'unduh'];
      tabs.forEach(t => {
        const el = document.getElementById('tab-' + t);
        const btn = document.getElementById('tab-btn-' + t);
        if (t === tabId) {
          el.classList.remove('hidden');
          btn.className = 'pill-tab-active px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5';
        } else {
          el.classList.add('hidden');
          btn.className = 'pill-tab-inactive px-3.5 py-1.5 rounded-full text-xs transition inline-flex items-center gap-1.5';
        }
      });
      if (tabId === 'interaktif') {
        renderInteractiveCharts();
      }
    }

    function openModal(imgSrc, title) {
      document.getElementById('modalImage').src = imgSrc;
      document.getElementById('modalTitle').innerText = title;
      document.getElementById('modalOpenTab').href = imgSrc;
      document.getElementById('modalDownload').href = imgSrc;
      document.getElementById('imageModal').classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('imageModal').classList.add('hidden');
    }

    // Tutup modal dengan tombol Escape
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') closeModal();
    });

    function filterKecamatan() {
      const input = document.getElementById('kecamatanSearch').value.toLowerCase();
      const rows = document.querySelectorAll('.kec-row');
      rows.forEach(r => {
        const name = r.querySelector('.kec-name').innerText.toLowerCase();
        r.style.display = name.includes(input) ? '' : 'none';
      });
    }

    let chart1 = null;
    let chart2 = null;

    function renderInteractiveCharts() {
      if (chart1 && chart2) return;

      fetch('/api/interactive-data')
        .then(res => res.json())
        .then(data => {
          const ctx1 = document.getElementById('interactiveChart').getContext('2d');
          chart1 = new Chart(ctx1, {
            type: 'line',
            data: {
              labels: data.labels,
              datasets: [
                {
                  label: 'Aktual',
                  data: data.actual,
                  borderColor: '#0f172a',
                  borderWidth: 2,
                  pointRadius: 1,
                  tension: 0.1
                },
                {
                  label: 'GRU-Adam',
                  data: data.gru_adam,
                  borderColor: '#2563eb',
                  borderWidth: 1.8,
                  pointRadius: 1,
                  borderDash: [3, 3],
                  tension: 0.1
                },
                {
                  label: 'LSTM-Adam',
                  data: data.lstm_adam,
                  borderColor: '#d97706',
                  borderWidth: 1.5,
                  pointRadius: 1,
                  borderDash: [5, 5],
                  tension: 0.1
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              interaction: { mode: 'index', intersect: false },
              plugins: {
                legend: { labels: { color: '#334155', font: { size: 11 } } },
                tooltip: { backgroundColor: '#1e293b', titleColor: '#ffffff', bodyColor: '#f1f5f9' }
              },
              scales: {
                x: { ticks: { color: '#64748b', maxTicksLimit: 20 }, grid: { color: '#f1f5f9' } },
                y: { ticks: { color: '#64748b' }, grid: { color: '#e2e8f0' } }
              }
            }
          });

          const ctx2 = document.getElementById('interactiveLossChart').getContext('2d');
          chart2 = new Chart(ctx2, {
            type: 'line',
            data: {
              labels: Array.from({length: data.loss_gru.length}, (_, i) => i + 1),
              datasets: [
                {
                  label: 'GRU-Adam Training Loss',
                  data: data.loss_gru,
                  borderColor: '#2563eb',
                  borderWidth: 1.8,
                  pointRadius: 0
                },
                {
                  label: 'LSTM-Adam Training Loss',
                  data: data.loss_lstm,
                  borderColor: '#d97706',
                  borderWidth: 1.8,
                  pointRadius: 0
                },
                {
                  label: 'GRU-SGD Loss',
                  data: data.loss_gru_sgd,
                  borderColor: '#7c3aed',
                  borderWidth: 1.5,
                  borderDash: [4, 4],
                  pointRadius: 0
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { labels: { color: '#334155', font: { size: 11 } } }
              },
              scales: {
                x: { title: { display: true, text: 'Epoch', color: '#64748b' }, ticks: { color: '#64748b' }, grid: { color: '#f1f5f9' } },
                y: { title: { display: true, text: 'MSE Loss', color: '#64748b' }, ticks: { color: '#64748b' }, grid: { color: '#e2e8f0' } }
              }
            }
          });
        });
    }
  </script>
</body>
</html>
"""

@app.route("/")
def index():
    summary_path = os.path.join(OUT_DIR, "perbandingan_metrik.csv")
    summary = pd.read_csv(summary_path).to_dict(orient="records") if os.path.exists(summary_path) else []

    imp_path = os.path.join(OUT_DIR, "perbaikan_vs_pembanding.csv")
    improvements = pd.read_csv(imp_path).to_dict(orient="records") if os.path.exists(imp_path) else []

    p29_path = os.path.join(OUT_DIR, "prediksi_2029.csv")
    pred2029 = pd.read_csv(p29_path).to_dict(orient="records") if os.path.exists(p29_path) else []

    pk_g_path = os.path.join(OUT_DIR, "error_per_kecamatan_gru_adam.csv")
    pk_l_path = os.path.join(OUT_DIR, "error_per_kecamatan_lstm_adam.csv")
    if os.path.exists(pk_g_path) and os.path.exists(pk_l_path):
        pkg = pd.read_csv(pk_g_path).rename(columns={"MAE": "MAE_GRU", "MAPE": "MAPE_GRU_%", "N": "N_sampel"})
        pkl = pd.read_csv(pk_l_path)[["kec", "MAE", "MAPE"]].rename(columns={"MAE": "MAE_LSTM", "MAPE": "MAPE_LSTM_%"})
        kec_data = pd.merge(pkg, pkl, on="kec", how="outer").to_dict(orient="records")
    else:
        kec_data = []

    pj_g_path = os.path.join(OUT_DIR, "error_per_jenis_gru_adam.csv")
    pj_l_path = os.path.join(OUT_DIR, "error_per_jenis_lstm_adam.csv")
    if os.path.exists(pj_g_path) and os.path.exists(pj_l_path):
        pjg = pd.read_csv(pj_g_path).rename(columns={"MAE": "MAE_GRU", "MAPE": "MAPE_GRU_%", "N": "N_sampel"})
        pjl = pd.read_csv(pj_l_path)[["jenis", "MAE", "MAPE"]].rename(columns={"MAE": "MAE_LSTM", "MAPE": "MAPE_LSTM_%"})
        jenis_data = pd.merge(pjg, pjl, on="jenis", how="outer").to_dict(orient="records")
    else:
        jenis_data = []

    t5_path = os.path.join(OUT_DIR, "top5_error_gru_adam.csv")
    top5 = pd.read_csv(t5_path).to_dict(orient="records") if os.path.exists(t5_path) else []

    w_path = os.path.join(OUT_DIR, "uji_wilcoxon.csv")
    wilcox = pd.read_csv(w_path).iloc[0].to_dict() if os.path.exists(w_path) else {"statistik_W": 0, "p_value": 1, "kesimpulan": ""}

    return render_template_string(
        HTML_TEMPLATE,
        summary=summary,
        improvements=improvements,
        pred2029=pred2029,
        kec_data=kec_data,
        jenis_data=jenis_data,
        top5=top5,
        wilcox=wilcox
    )

@app.route("/files/<path:filename>")
def serve_file(filename):
    return send_from_directory(OUT_DIR, filename)

@app.route("/download/excel")
def download_excel():
    excel_path = os.path.join(OUT_DIR, "laporan_hasil.xlsx")
    if os.path.exists(excel_path):
        return send_file(excel_path, as_attachment=True, download_name="Laporan_Skripsi_GRU_Kampar.xlsx")
    return "File belum tersedia", 404

@app.route("/download/file/<path:filename>")
def download_file(filename):
    return send_from_directory(OUT_DIR, filename, as_attachment=True)

@app.route("/api/interactive-data")
def interactive_data():
    gru_path = os.path.join(OUT_DIR, "aktual_vs_prediksi_2024_gru_adam.csv")
    lstm_path = os.path.join(OUT_DIR, "aktual_vs_prediksi_2024_lstm_adam.csv")
    loss_gru_path = os.path.join(OUT_DIR, "loss_GRU-Adam.csv")
    loss_lstm_path = os.path.join(OUT_DIR, "loss_LSTM-Adam.csv")
    loss_gsgd_path = os.path.join(OUT_DIR, "loss_GRU-SGD_tanpa_Adam.csv")

    actual, gru_pred, lstm_pred, labels = [], [], [], []
    if os.path.exists(gru_path):
        df_gru = pd.read_csv(gru_path)
        actual = (df_gru["aktual"] * 100).round(2).tolist()
        gru_pred = (df_gru["prediksi"] * 100).round(2).tolist()
        labels = [f"#{i+1} {r['kec'].title()} ({r['jenis']})" for i, r in df_gru.iterrows()]

    if os.path.exists(lstm_path):
        df_lstm = pd.read_csv(lstm_path)
        lstm_pred = (df_lstm["prediksi"] * 100).round(2).tolist()

    loss_gru = pd.read_csv(loss_gru_path)["loss"].round(5).tolist() if os.path.exists(loss_gru_path) else []
    loss_lstm = pd.read_csv(loss_lstm_path)["loss"].round(5).tolist() if os.path.exists(loss_lstm_path) else []
    loss_gsgd = pd.read_csv(loss_gsgd_path)["loss"].round(5).tolist() if os.path.exists(loss_gsgd_path) else []

    return jsonify({
        "labels": labels,
        "actual": actual,
        "gru_adam": gru_pred,
        "lstm_adam": lstm_pred,
        "loss_gru": loss_gru,
        "loss_lstm": loss_lstm,
        "loss_gru_sgd": loss_gsgd
    })

def find_free_port(start_port=5000):
    for port in range(start_port, start_port + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return start_port

def run_server(port=5000, open_browser=True):
    env_port = os.environ.get("PORT")
    if env_port:
        try:
            port = int(env_port)
        except ValueError:
            pass
    port = find_free_port(port)
    url = f"http://localhost:{port}"
    print("\n" + "=" * 65)
    print(f"DASHBOARD WEB AKTIF DI: {url}")
    print(f"Catatan Google Cloud Console / Cloud Shell:")
    print(f"  Gunakan tombol 'Web Preview' (Pratinjau Web) di kanan atas")
    print(f"  terminal Cloud Shell dan pilih 'Preview on port {port}'.")
    print("=" * 65 + "\n")
    if open_browser:
        def _safe_open():
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Timer(1.2, _safe_open).start()
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    run_server()
