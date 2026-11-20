# 🌐 Panduan Menjalankan Program di Google Cloud Console & Google Colab

Program skripsi **Prediksi Partisipasi Pemilih Kab. Kampar (GRU + Adam)** telah disiapkan secara lengkap dan fleksibel agar dapat dijalankan di:
1. **Google Cloud Console (Cloud Shell / VM)**
2. **Google Colab (Google Colaboratory)** *(Bila yang Anda maksud adalah Google Colab)*

---

## 🚀 OPSI 1: Menjalankan di Google Cloud Console (Cloud Shell)

Google Cloud Console menyediakan terminal Linux cloud gratis (**Cloud Shell**) lengkap dengan fitur **Web Preview**.

### Langkah-langkah:
1. Buka browser dan login ke **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Klik ikon **Activate Cloud Shell** (ikon terminal `>_` di bilah menu kanan atas).
3. Upload folder proyek ini ke Cloud Shell:
   - Klik ikon titik tiga `...` di bilah menu Cloud Shell -> pilih **Upload** -> unggah file/zip proyek, **atau**
   - Jika proyek disimpan di GitHub/Git, cukup jalankan:
     ```bash
     git clone <URL_REPOSITORY_ANDA>
     cd YogiSkripsi
     ```
4. Jalankan script otomatisasi yang sudah kami sediakan:
   ```bash
   chmod +x setup_google_console.sh
   ./setup_google_console.sh
   ```
   *(Atau secara manual):*
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python main.py
   ```
5. **Membuka Tampilan Website Dashboard di Cloud Console:**
   - Setelah server aktif, klik tombol **Web Preview** (ikon Pratinjau Web di pojok kanan atas jendela Cloud Shell).
   - Pilih **Change port** -> masukkan `5000` -> klik **Change and Preview**.
   - Website dashboard skripsi Anda akan langsung terbuka di tab browser baru!

---

## 📓 OPSI 2: Menjalankan di Google Colab (Google Colaboratory)

Banyak mahasiswa menyebut Google Colab sebagai "Google Console" karena sama-sama lingkungan cloud Google untuk deep learning (GPU gratis). Kami sudah membuatkan notebook khusus: **`notebook_skripsi_yogi.ipynb`**.

### Langkah-langkah:
1. Buka **[Google Colaboratory](https://colab.research.google.com/)**.
2. Klik tab **Upload** -> pilih file **`notebook_skripsi_yogi.ipynb`** dari folder ini.
3. Hubungkan runtime (Bisa pilih **Runtime** -> **Change runtime type** -> pilih **T4 GPU** atau **CPU**).
4. Jalankan sel (Cell) dari atas ke bawah (tekan **Shift + Enter** atau tombol Play):
   - **Sel 1:** Menginstall library pendukung (`openpyxl`, `tensorflow`, `matplotlib`, dll).
   - **Sel 2:** Upload file `Dataset_Yogi.xlsx`, `main.py`, dan `app.py`.
   - **Sel 3:** Menjalankan pipeline training 5 seed secara otomatis.
   - **Sel 4:** Menampilkan tabel metrik evaluasi lengkap.
   - **Sel 5:** Menampilkan 6 grafik riset 300 DPI langsung di dalam notebook.
   - **Sel 6:** Otomatis mengunduh file `laporan_hasil.xlsx` (9 sheet) ke laptop Anda.
   - **Sel 7:** Membuka Web Dashboard interaktif langsung dari dalam Google Colab menggunakan fitur `output.serve_kernel_port_as_window(5000)`.

---

## 📂 File-File Baru yang Disediakan

| File | Fungsi |
| :--- | :--- |
| **`setup_google_console.sh`** | Script shell otomatis untuk setup venv, pip install, dan running di Google Cloud Console / Linux. |
| **`requirements.txt`** | Daftar dependensi resmi lintas platform (Windows, Linux Cloud, Colab). |
| **`notebook_skripsi_yogi.ipynb`** | File Jupyter Notebook interaktif siap pakai untuk Google Colab. |
| **`PANDUAN_GOOGLE_CONSOLE.md`** | Dokumen panduan langkah demi langkah ini. |
| **`app.py`** | Telah disesuaikan agar otomatis mengenali `PORT` cloud (8080/5000) dan aman berjalan di lingkungan headless. |
