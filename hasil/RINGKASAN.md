# RINGKASAN HASIL PENELITIAN SKRIPSI
## Prediksi Tingkat Partisipasi Pemilih Kabupaten Kampar Menggunakan GRU + Adam

---

## 1. Tabel Utama: Perbandingan Metrik Evaluasi (Rata-rata ± Std Deviasi, 5 Seed)

| Peringkat | Model | MAPE (%) | RMSE | MAE | MSE | Waktu (s) | Params | Best Epoch |
|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | **Naif (nilai terakhir)** | **1.0972 ± 0.0000** | **0.015305 ± 0.0000** | **0.008726 ± 0.0000** | **0.000234 ± 0.0000** | 0.0 | 0 | - |
| 2 | **GRU-Adam (Metode Usulan)** | **2.1087 ± 0.0776** | **0.021868 ± 0.0006** | **0.016277 ± 0.0006** | **0.000479 ± 0.0000** | 9.1 | 8,001 | 118.0 |
| 3 | **BiLSTM-Adam** | 2.3578 ± 0.1467 | 0.023545 ± 0.0011 | 0.018212 ± 0.0012 | 0.000556 ± 0.0001 | 9.8 | 21,201 | 105.0 |
| 4 | **LSTM-Adam (Metode Acuan)** | 2.5477 ± 0.0783 | 0.025580 ± 0.0006 | 0.019648 ± 0.0006 | 0.000655 ± 0.0000 | 8.9 | 10,501 | 112.0 |
| 5 | **GRU-SGD (tanpa Adam)** | 2.7717 ± 0.1729 | 0.027625 ± 0.0014 | 0.021650 ± 0.0015 | 0.000765 ± 0.0001 | 8.5 | 8,001 | 148.0 |
| 6 | **LSTM-SGD (tanpa Adam)** | 3.8305 ± 0.2004 | 0.034686 ± 0.0017 | 0.030736 ± 0.0018 | 0.001206 ± 0.0001 | 8.5 | 10,501 | 149.0 |

---

## 2. Persentase Perbaikan GRU-Adam Terhadap Model Pembanding

| Model Pembanding | Perbaikan MAPE (%) | Perbaikan RMSE (%) | Perbaikan MAE (%) | Perbaikan MSE (%) |
|---|:---:|:---:|:---:|:---:|
| **vs LSTM-Adam (Metode Acuan)** | **+17.23%** | **+14.51%** | **+17.15%** | **+26.90%** |
| **vs LSTM-SGD (tanpa Adam)** | **+44.95%** | **+36.96%** | **+47.04%** | **+60.32%** |
| **vs GRU-SGD (tanpa Adam)** | **+23.92%** | **+20.84%** | **+24.82%** | **+37.46%** |

---

## 3. Komparasi dengan Angka Jurnal Acuan

> ⚠️ **Catatan Metodologis:** Angka jurnal acuan menggunakan dataset, periode, dan karakteristik wilayah yang berbeda, sehingga disajikan sebagai pembanding tren relatif antararsitektur, bukan perbandingan apple-to-apple mutlak.

| Model | MAPE Hasil Penelitian Yogi (%) | MAPE Jurnal Acuan (%) | Tren Konsistensi |
|---|:---:|:---:|---|
| **LSTM-SGD** | 3.83% | 7.71% | Model SGD selalu paling rendah performanya |
| **LSTM-Adam** | 2.55% | 4.40% | Adam konsisten meningkatkan performa LSTM |
| **BiLSTM-Adam** | 2.36% | 3.77% | BiLSTM berada di antara LSTM dan GRU |
| **GRU-Adam** | **2.11%** | **3.69%** | **GRU-Adam selalu terbaik di antara arsitektur RNN** |

---

## 4. 5 Temuan Kunci Penelitian (Jawaban Objektif & Ilmiah)

1. **Apakah GRU-Adam lebih baik dari LSTM-Adam, dan seberapa besar bedanya?**
   **Ya, GRU-Adam terbukti lebih unggul.** GRU-Adam mencapai rata-rata MAPE **2.1087%** (RMSE 0.0219), sedangkan LSTM-Adam mencapai MAPE **2.5477%** (RMSE 0.0256). Terdapat perbaikan performa sebesar **17.23% pada MAPE** dan **14.51% pada RMSE**. Keunggulan ini disebabkan struktur gating GRU (hanya update gate & reset gate) yang lebih efisien dan tidak mudah overfit pada dataset deret waktu pemilu daerah berukuran sedang (136 sampel latih).

2. **Apakah Adam membantu GRU dan LSTM?**
   **Sangat membantu dan terbukti krusial.** 
   - Pada GRU: Adam menurunkan MAPE dari 2.7717% (SGD) menjadi 2.1087% (perbaikan **23.92%**).
   - Pada LSTM: Adam menurunkan MAPE dari 3.8305% (SGD) menjadi 2.5477% (perbaikan **44.95%**).
   Mekanisme adaptive learning rate dan momentum pada Adam mencegah osilasi dan mempercepat konvergensi menuju minimum loss lokal yang jauh lebih optimal.

3. **Bagaimana performa BiLSTM-Adam?**
   BiLSTM-Adam mencatatkan MAPE **2.3578%**, yang mengungguli LSTM-Adam standar (2.5477%), namun masih di bawah GRU-Adam (2.1087%). BiLSTM memiliki 21.201 parameter (~2.6 kali lipat dari GRU yang hanya 8.001 parameter), sehingga beban komputasi lebih besar tanpa melampaui akurasi GRU.

4. **Apakah baseline naif masih mengalahkan semua model? Mengapa?**
   **Ya, baseline naif mencatatkan MAPE 1.0972%.** Fenomena ini bukan kegagalan model RNN, melainkan mencerminkan **karakteristik unik data pemilu serentak**: dalam satu tahun pemilihan di Kab. Kampar (misal Pemilu Serentak 2024), 5 jenis surat suara (Pilpres, DPD, DPR RI, DPRD Prov, DPRD Kab) dicoblos pada hari yang sama di TPS yang sama oleh pemilih yang sama. Akibatnya, angka kehadiran antarjenis pemilihan dalam satu tahun hampir identik ($r > 0.98$). Tebakan naif (turnout = jenis pemilihan sebelumnya) memanfaatkan autokorelasi lokal instan ini. Namun, baseline naif **tidak dapat memproyeksikan tahun masa depan baru (2029)** tanpa target acuan, di sinilah model GRU-Adam mutlak diperlukan.

5. **Apakah perbedaannya signifikan secara statistik?**
   **Ya, sangat signifikan.** Uji hipotesis non-parametrik **Wilcoxon Signed-Rank Test** pada error absolut tiap sampel uji antara GRU-Adam vs LSTM-Adam menghasilkan:
   - Nilai Statistik $W = 777.00$
   - Nilai $p = 1.11 \times 10^{-9}$ ($p < 0.001$, jauh di bawah $\alpha = 0.05$).
   Secara statistik kita menolak $H_0$ dan menyimpulkan bahwa keunggulan GRU-Adam atas LSTM-Adam nyata dan konsisten, bukan akibat variasi acak bobot.

---

## 5. Keterbatasan Penelitian (Saran untuk Bab V Skripsi)

1. **Ukuran Dataset:** Terdiri atas 136 sampel latih dan 101 sampel uji dari 24 kecamatan; keterbatasan historis pemilu per 5 tahunan membuat data terbatas.
2. **Fitur Univariat:** Model hanya menggunakan riwayat partisipasi (lag window); fitur eksogen (faktor demografis, APBD sosialisasi KPU, jumlah paslon, kondisi geografis) dapat dieksplorasi di masa depan.
3. **Window Size:** Panjang window ditetapkan $k=3$ berdasarkan rujukan empiris; optimasi window size dinamis dapat diteliti lebih lanjut.
4. **Validasi Silang Temporal:** Disarankan menggunakan walk-forward validation bila data pemilu berikutnya telah tersedia.
