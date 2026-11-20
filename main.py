"""
Prediksi Tingkat Partisipasi Pemilih Kab. Kampar dengan GRU + Adam
===================================================================
Pipeline:
  1. Bersihkan nama kecamatan (80 ejaan -> 24 nama baku)
  2. Buang kecamatan hasil pemekaran (data terlalu sedikit)
  3. Susun deret waktu per kecamatan (urut tahun, lalu jenis pemilihan)
  4. Sliding window (fitur = turnout periode sebelumnya, TANPA leakage)
  5. Split berdasarkan waktu: latih <= 2019, uji = 2024
  6. Normalisasi (MinMax, fit hanya pada data latih)
  7. Latih model (GRU-Adam, GRU-SGD, LSTM-Adam, LSTM-SGD, + opsional BiLSTM-Adam)
  8. Evaluasi MSE, MAE, RMSE, MAPE pada skala asli (rata-rata 5 seed)
  9. Prediksi pemilu berikutnya (2029) per kecamatan

Mode Penggunaan:
  # Mode lama (kompatibel penuh):
  python main.py --data Dataset_Yogi.xlsx --prep-only
  python main.py --data Dataset_Yogi.xlsx
  python main.py --data Dataset_Yogi.xlsx --grid
  python main.py --data Dataset_Yogi.xlsx --with-lstm

  # Mode baru (laporan lengkap multi-seed + grafik + Excel):
  python main.py --data Dataset_Yogi.xlsx --report
  python main.py --data Dataset_Yogi.xlsx --report --with-bilstm

Kebutuhan: pandas numpy scikit-learn openpyxl tensorflow matplotlib scipy tabulate
"""

import argparse
import itertools
import os
import random
import time
import warnings

warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# ================================================================ KONSTANTA
SEED = 42
SEEDS = [42, 43, 44, 45, 46]
WINDOW = 3                      # panjang sliding window (k) — JANGAN UBAH
TRAIN_LAST_YEAR = 2019          # <= 2019 -> latih, > 2019 -> uji — JANGAN UBAH
DROP_KEC = {"bangkinang barat", "bangkinang kota", "kampar timur"}
JENIS_ORDER = {"Pilpres": 0, "DPD": 1, "DPR RI": 2, "DPRD PROV": 3, "DPRD Kabupaten": 4}

TYPO_MAP = {
    "bangknang kota": "bangkinang kota",
    "bangkinnag seberang": "bangkinang seberang",
    "kamapr kiri hilir": "kampar kiri hilir",
    "xii koto kampar": "xiii koto kampar",
    "tampung hulu": "tapung hulu",
    "rumbio jaya dprd prov": "rumbio jaya",
}

# Angka dari jurnal acuan — skema data BERBEDA, tidak sebanding langsung
JURNAL_REF = [
    {"Model_Jurnal": "LSTM-SGD (Jurnal)",    "MAPE_Jurnal_%": 7.71},
    {"Model_Jurnal": "LSTM-Adam (Jurnal)",   "MAPE_Jurnal_%": 4.40},
    {"Model_Jurnal": "GRU-Adam (Jurnal)",    "MAPE_Jurnal_%": 3.69},
    {"Model_Jurnal": "BiLSTM-Adam (Jurnal)", "MAPE_Jurnal_%": 3.77},
]


# ================================================================ SEED
def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    try:
        import tensorflow as tf
        tf.random.set_seed(seed)
    except ImportError:
        pass


# ================================================================ DATA (tidak diubah)
def load_and_clean(path):
    df = pd.read_excel(path)
    df.columns = ["tahun", "jenis", "kec", "hadir", "tidak_hadir", "terdaftar", "turnout"]

    df["kec"] = df["kec"].astype(str).str.strip().str.lower().replace(TYPO_MAP)
    df["jenis"] = df["jenis"].astype(str).str.strip()

    print(f"Kecamatan setelah dibersihkan : {df['kec'].nunique()}")
    n0 = len(df)
    df = df[~df["kec"].isin(DROP_KEC)].copy()
    print(f"Baris dibuang (pemekaran)     : {n0 - len(df)}")

    recomputed = df["hadir"] / df["terdaftar"]
    df["turnout"] = recomputed
    n_bad = int((df["hadir"] + df["tidak_hadir"] != df["terdaftar"]).sum())
    print(f"Baris hadir+tidak_hadir != terdaftar (catat di skripsi): {n_bad}")

    df["jenis_ord"] = df["jenis"].map(JENIS_ORDER)
    if df["jenis_ord"].isna().any():
        raise ValueError("Ada jenis pemilihan tak dikenal: "
                         f"{df.loc[df['jenis_ord'].isna(), 'jenis'].unique()}")
    df = df.sort_values(["kec", "tahun", "jenis_ord"]).reset_index(drop=True)
    return df


def make_windows(df, window=WINDOW):
    """Satu sampel: X = turnout [t-k .. t-1] satu kecamatan, y = turnout t."""
    X, y, meta, last_windows = [], [], [], {}
    for kec, g in df.groupby("kec"):
        v = g["turnout"].to_numpy()
        if len(v) <= window:
            continue
        for i in range(window, len(v)):
            X.append(v[i - window:i])
            y.append(v[i])
            meta.append((kec, int(g["tahun"].iloc[i]), g["jenis"].iloc[i], i))
        last_windows[kec] = v[-window:]
    meta = pd.DataFrame(meta, columns=["kec", "tahun", "jenis", "pos"])
    return np.array(X), np.array(y), meta, last_windows


def split_by_time(X, y, meta):
    tr = (meta["tahun"] <= TRAIN_LAST_YEAR).to_numpy()
    te = ~tr
    tr_idx = np.where(tr)[0]
    order = np.lexsort((meta.loc[tr_idx, "pos"], meta.loc[tr_idx, "tahun"]))
    tr_idx = tr_idx[order]
    return (X[tr_idx], y[tr_idx], X[te], y[te], meta[te].reset_index(drop=True))


def scale(Xtr, ytr, Xte, yte, last_windows):
    """MinMax di-fit HANYA pada data latih (hindari kebocoran dari data uji)."""
    sc = MinMaxScaler()
    sc.fit(np.concatenate([Xtr.ravel(), ytr]).reshape(-1, 1))
    f = lambda a: sc.transform(a.reshape(-1, 1)).reshape(a.shape)
    last_s = {k: f(v) for k, v in last_windows.items()}
    return f(Xtr)[..., None], f(ytr), f(Xte)[..., None], f(yte), last_s, sc


# ================================================================ MODEL
def build_model(kind="gru", units=50, dropout=0.3, optimizer="adam", lr=0.001, window=WINDOW):
    """
    Bangun model RNN.
    kind: "gru" | "lstm" | "bilstm"
    Arsitektur identik untuk semua — hanya layer RNN yang berbeda.
    """
    import keras
    from keras import layers

    if kind == "bilstm":
        rnn_layer = layers.Bidirectional(layers.LSTM(units, activation="tanh"))
    else:
        rnn_cls = {"gru": layers.GRU, "lstm": layers.LSTM}[kind]
        rnn_layer = rnn_cls(units, activation="tanh")

    model = keras.Sequential([
        layers.Input(shape=(window, 1)),
        rnn_layer,
        layers.Dropout(dropout),
        layers.Dense(1, activation="linear"),
    ])
    opt = (keras.optimizers.Adam(learning_rate=lr) if optimizer == "adam"
           else keras.optimizers.SGD(learning_rate=lr))
    model.compile(optimizer=opt, loss="mse")
    return model


def count_params(model):
    return int(model.count_params())


def train(kind, optimizer, Xtr, ytr,
          epochs=150, batch=32, units=50, dropout=0.3, lr=0.001, seed=SEED):
    """
    Latih model; kembalikan (model, hist, waktu_detik, best_epoch).
    Seed diset sebelum build supaya bobot awal reproducible.
    """
    set_seed(seed)
    model = build_model(kind, units, dropout, optimizer, lr)
    t0 = time.time()
    hist = model.fit(Xtr, ytr, epochs=epochs, batch_size=batch,
                     validation_split=0.15, shuffle=False, verbose=0)
    elapsed = time.time() - t0
    best_epoch = int(np.argmin(hist.history["val_loss"])) + 1
    return model, hist, elapsed, best_epoch


# ================================================================ METRIK (tidak diubah)
def metrics(y_true, y_pred):
    e = y_true - y_pred
    mse = float(np.mean(e ** 2))
    return {"MSE": mse, "MAE": float(np.mean(np.abs(e))),
            "RMSE": float(np.sqrt(mse)),
            "MAPE": float(np.mean(np.abs(e / y_true)) * 100)}


def evaluate(model, Xte, yte_s, sc):
    pred = sc.inverse_transform(model.predict(Xte, verbose=0)).ravel()
    true = sc.inverse_transform(yte_s.reshape(-1, 1)).ravel()
    return metrics(true, pred), true, pred


# ================================================================ MULTI-SEED TRAINING
def train_multi_seed(name, kind, optimizer, Xtr_s, ytr_s, Xte_s, yte_s, sc,
                     cfg, seeds=SEEDS):
    """
    Latih model dengan N seed berbeda; kembalikan:
      agg        — dict statistik agregat (mean/std per metrik)
      m_final    — model seed=42 untuk plot & prediksi
      hist_final — history seed=42
      true_ref   — nilai aktual (sama untuk semua model)
      pred_final — prediksi seed=42
      all_metrics — list dict metrik tiap seed
    """
    all_m, all_elapsed, all_best_ep, all_pred = [], [], [], []

    for i, seed in enumerate(seeds):
        m, hist, elapsed, best_ep = train(
            kind, optimizer, Xtr_s, ytr_s,
            cfg["epochs"], cfg["batch"], cfg["units"], cfg["dropout"],
            seed=seed
        )
        res, true_v, pred_v = evaluate(m, Xte_s, yte_s, sc)
        all_m.append(res)
        all_elapsed.append(elapsed)
        all_best_ep.append(best_ep)
        all_pred.append(pred_v)
        print(f"    seed {seed}: MAPE={res['MAPE']:.4f}%  RMSE={res['RMSE']:.6f}", flush=True)

    # Agregasi
    agg = {}
    for k in ["MSE", "MAE", "RMSE", "MAPE"]:
        vals = [m[k] for m in all_m]
        agg[f"{k}_mean"] = float(np.mean(vals))
        agg[f"{k}_std"]  = float(np.std(vals, ddof=0))
    agg["waktu_detik"] = float(np.mean(all_elapsed))
    agg["best_epoch"]  = float(np.mean(all_best_ep))

    # Retrain dengan seed kanonik untuk plot yang reproducible
    m_final, hist_final, _, _ = train(
        kind, optimizer, Xtr_s, ytr_s,
        cfg["epochs"], cfg["batch"], cfg["units"], cfg["dropout"],
        seed=SEED
    )
    agg["n_params"] = count_params(m_final)
    _, true_ref, pred_final = evaluate(m_final, Xte_s, yte_s, sc)

    return agg, m_final, hist_final, true_ref, pred_final, all_m


# ================================================================ PLOTTING HELPERS
def _get_plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family":     "DejaVu Sans",
        "axes.titlesize":  11,
        "axes.labelsize":  10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.grid":       True,
        "grid.alpha":      0.3,
        "grid.linestyle":  "--",
    })
    return plt


# ---- 1. Kurva loss per model (panel 2×3)
def plot_loss_curves(histories_dict, out_dir):
    plt = _get_plt()
    names = list(histories_dict.keys())
    ncols = 3
    nrows = max(1, (len(names) + ncols - 1) // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, 4.5 * nrows), squeeze=False)
    flat = axes.ravel()

    for i, name in enumerate(names):
        hist = histories_dict[name]
        ax = flat[i]
        ax.plot(hist.history["loss"],     label="Training Loss",   lw=1.3, color="#1565C0")
        ax.plot(hist.history["val_loss"], label="Validation Loss", lw=1.3, color="#E53935", ls="--")
        ax.set_title(f"Loss — {name}")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("MSE Loss")
        ax.legend()

    for j in range(len(names), len(flat)):
        flat[j].set_visible(False)

    fig.suptitle("Kurva Training dan Validation Loss per Model (seed=42)",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    path = os.path.join(out_dir, "plot_loss_curves.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ---- 2. Aktual vs Prediksi (semua model, panel 2 kolom)
def plot_actual_vs_pred(true, preds_dict, out_dir):
    plt = _get_plt()
    names = list(preds_dict.keys())
    ncols = 2
    nrows = max(1, (len(names) + 1) // 2)
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows), squeeze=False)
    flat = axes.ravel()

    colors = ["#E53935", "#FF6F00", "#2E7D32", "#6A1B9A", "#00838F"]
    for i, name in enumerate(names):
        ax = flat[i]
        ax.plot(true, label="Aktual", lw=1.5, color="black", zorder=3)
        ax.plot(preds_dict[name], label="Prediksi", lw=1.2, ls="--",
                color=colors[i % len(colors)], alpha=0.9)
        ax.set_title(f"Aktual vs Prediksi — {name}")
        ax.set_xlabel("Indeks Sampel Uji 2024")
        ax.set_ylabel("Tingkat Partisipasi")
        ax.legend()

    for j in range(len(names), len(flat)):
        flat[j].set_visible(False)

    fig.suptitle("Aktual vs Prediksi Data Uji 2024 per Model (seed=42)",
                 fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(out_dir, "plot_aktual_vs_prediksi.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ---- 3. Bar chart MAPE & RMSE dengan error bar
def plot_metric_barchart(agg_dict, out_dir):
    plt = _get_plt()
    names = list(agg_dict.keys())
    color_map = {
        "GRU-Adam":              "#1565C0",
        "LSTM-Adam":             "#FF6F00",
        "BiLSTM-Adam":           "#2E7D32",
        "GRU-SGD (tanpa Adam)":  "#6A1B9A",
        "LSTM-SGD (tanpa Adam)": "#B71C1C",
        "Naif (nilai terakhir)": "#757575",
    }
    colors = [color_map.get(n, "#424242") for n in names]
    x = np.arange(len(names))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, metric in zip(axes, ["MAPE", "RMSE"]):
        means = [agg_dict[n].get(f"{metric}_mean", agg_dict[n].get(metric, 0)) for n in names]
        stds  = [agg_dict[n].get(f"{metric}_std",  0) for n in names]
        bars  = ax.bar(x, means, yerr=stds, capsize=5,
                       color=colors, alpha=0.87,
                       error_kw={"linewidth": 1.5, "ecolor": "black", "capthick": 1.5})
        ymax = max(m + s for m, s in zip(means, stds)) * 1.18 if means else 1
        ax.set_ylim(0, ymax)
        unit = " (%)" if metric == "MAPE" else ""
        ax.set_title(f"Perbandingan {metric} Semua Model\n"
                     f"(rata-rata ± std, {len(SEEDS)} seed)")
        ax.set_xlabel("Model")
        ax.set_ylabel(f"{metric}{unit}")
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=35, ha="right")
        for bar, mv, sv in zip(bars, means, stds):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    mv + sv + ymax * 0.012,
                    f"{mv:.4f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold")

    fig.suptitle("Perbandingan Metrik Semua Model", fontsize=13, fontweight="bold")
    plt.tight_layout()
    path = os.path.join(out_dir, "plot_metrik_barchart.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ---- 4. Bar chart MAE per kecamatan (GRU-Adam vs LSTM-Adam)
def plot_mae_per_kecamatan(meta_te, true, preds_dict, out_dir):
    plt = _get_plt()
    compare = [n for n in ["GRU-Adam", "LSTM-Adam"] if n in preds_dict]
    if not compare:
        return None

    kecs = sorted(meta_te["kec"].unique())
    x = np.arange(len(kecs))
    width = 0.38
    colors = ["#1565C0", "#FF6F00"]

    fig, ax = plt.subplots(figsize=(18, 7))
    for i, name in enumerate(compare):
        pred = preds_dict[name]
        maes = []
        for kec in kecs:
            idx = (meta_te["kec"] == kec).to_numpy()
            maes.append(float(np.mean(np.abs(true[idx] - pred[idx]))) if idx.sum() > 0 else 0.0)
        offset = (i - len(compare) / 2 + 0.5) * width
        ax.bar(x + offset, maes, width, label=name, color=colors[i], alpha=0.87)

    ax.set_title("MAE per Kecamatan: GRU-Adam vs LSTM-Adam (seed=42)")
    ax.set_xlabel("Kecamatan")
    ax.set_ylabel("MAE (Tingkat Partisipasi)")
    ax.set_xticks(x)
    ax.set_xticklabels([k.title() for k in kecs], rotation=50, ha="right", fontsize=7.5)
    ax.legend()
    plt.tight_layout()
    path = os.path.join(out_dir, "plot_mae_per_kecamatan.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ---- 5. Bar chart prediksi 2029 (GRU-Adam & LSTM-Adam)
def plot_prediksi_2029(pred29_dict, out_dir):
    plt = _get_plt()
    models = list(pred29_dict.keys())
    if not models:
        return None
    kecs = sorted(pred29_dict[models[0]])
    x = np.arange(len(kecs))
    width = 0.8 / max(len(models), 1)
    cmap_bars = ["#1565C0", "#FF6F00", "#2E7D32", "#6A1B9A"]

    fig, ax = plt.subplots(figsize=(18, 7))
    for i, name in enumerate(models):
        vals = [pred29_dict[name].get(k, 0) for k in kecs]
        offset = (i - len(models) / 2 + 0.5) * width
        ax.bar(x + offset, vals, width, label=name,
               color=cmap_bars[i % len(cmap_bars)], alpha=0.87)

    ax.set_title("Prediksi Tingkat Partisipasi Pemilu 2029 per Kecamatan")
    ax.set_xlabel("Kecamatan")
    ax.set_ylabel("Prediksi Partisipasi (%)")
    ax.set_xticks(x)
    ax.set_xticklabels([k.title() for k in kecs], rotation=50, ha="right", fontsize=7.5)
    ax.set_ylim(60, 100)
    ax.legend()
    plt.tight_layout()
    path = os.path.join(out_dir, "plot_prediksi_2029.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ---- 6. Scatter aktual vs prediksi GRU-Adam
def plot_scatter_gru_adam(true, pred, out_dir):
    plt = _get_plt()
    fig, ax = plt.subplots(figsize=(7, 7))
    t100, p100 = true * 100, pred * 100
    ax.scatter(t100, p100, alpha=0.65, s=40, color="#1565C0",
               edgecolors="white", linewidths=0.5, zorder=3)
    mn = min(t100.min(), p100.min()) - 2
    mx = max(t100.max(), p100.max()) + 2
    ax.plot([mn, mx], [mn, mx], "r--", lw=1.8, label="Ideal (y = x)", zorder=2)
    ax.set_title("Scatter Plot Aktual vs Prediksi — GRU-Adam (seed=42)")
    ax.set_xlabel("Aktual Tingkat Partisipasi (%)")
    ax.set_ylabel("Prediksi Tingkat Partisipasi (%)")
    ax.set_xlim(mn, mx)
    ax.set_ylim(mn, mx)
    ax.legend()
    ax.set_aspect("equal")
    plt.tight_layout()
    path = os.path.join(out_dir, "plot_scatter_gru_adam.png")
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return path


# ================================================================ ANALISIS ERROR
def error_analysis(meta_te, true, pred):
    """Kembalikan (per_kec, per_jenis, top5_worst, detail_df)."""
    df = meta_te.copy()
    df["aktual"]    = true
    df["prediksi"]  = pred
    df["abs_error"] = np.abs(true - pred)
    df["pct_error"] = np.abs((true - pred) / (true + 1e-10)) * 100

    per_kec = (df.groupby("kec")
               .agg(MAE=("abs_error", "mean"),
                    MAPE=("pct_error", "mean"),
                    N=("abs_error", "count"))
               .sort_values("MAPE").reset_index())
    per_kec["MAE"]  = per_kec["MAE"].round(6)
    per_kec["MAPE"] = per_kec["MAPE"].round(4)

    per_jenis = (df.groupby("jenis")
                 .agg(MAE=("abs_error", "mean"),
                      MAPE=("pct_error", "mean"),
                      N=("abs_error", "count"))
                 .sort_values("MAPE").reset_index())
    per_jenis["MAE"]  = per_jenis["MAE"].round(6)
    per_jenis["MAPE"] = per_jenis["MAPE"].round(4)

    top5 = (df.nlargest(5, "abs_error")
            [["kec", "tahun", "jenis", "aktual", "prediksi", "abs_error", "pct_error"]]
            .reset_index(drop=True))
    return per_kec, per_jenis, top5, df


# ================================================================ UJI WILCOXON
def wilcoxon_test(true, pred_a, pred_b,
                  name_a="GRU-Adam", name_b="LSTM-Adam"):
    from scipy.stats import wilcoxon
    err_a = np.abs(true - pred_a)
    err_b = np.abs(true - pred_b)
    try:
        stat, pval = wilcoxon(err_a, err_b)
        sig = pval < 0.05
        conclusion = (
            f"Perbedaan {name_a} vs {name_b} SIGNIFIKAN secara statistik "
            f"(W={stat:.2f}, p={pval:.4f} < 0.05)."
            if sig else
            f"Perbedaan {name_a} vs {name_b} TIDAK signifikan secara statistik "
            f"(W={stat:.2f}, p={pval:.4f} >= 0.05). "
            f"Selisih error antara kedua model tidak cukup konsisten."
        )
    except Exception as e:
        stat, pval, conclusion = 0.0, 1.0, f"Uji gagal: {e}"
    return {"statistik_W": float(stat), "p_value": float(pval),
            "kesimpulan": conclusion}


# ================================================================ EXCEL REPORT
def _style_header(ws, hex_color="1565C0"):
    from openpyxl.styles import PatternFill, Font, Alignment
    fill = PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")
    font = Font(bold=True, color="FFFFFF", size=10)
    for cell in ws[1]:
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _auto_width(ws, min_w=10, max_w=35):
    from openpyxl.utils import get_column_letter
    for col in ws.columns:
        length = max((len(str(c.value or "")) for c in col), default=min_w)
        ws.column_dimensions[get_column_letter(col[0].column)].width = \
            max(min_w, min(max_w, length + 3))


def _fmt_numbers(ws, start_row=2, fmt="0.000000"):
    for row in ws.iter_rows(min_row=start_row):
        for cell in row:
            if isinstance(cell.value, float):
                cell.number_format = fmt


def save_excel(out_path, ringkasan_df, per_seed_df,
               per_kec_gru, per_jenis_gru,
               per_kec_lstm, per_jenis_lstm,
               pred29_df):
    import openpyxl
    from openpyxl.utils.dataframe import dataframe_to_rows

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # Gabungkan per kecamatan untuk perbandingan langsung
    if per_kec_gru is not None and not per_kec_gru.empty and per_kec_lstm is not None and not per_kec_lstm.empty:
        g = per_kec_gru.rename(columns={"MAE": "MAE_GRU", "MAPE": "MAPE_GRU_%", "N": "N_sampel"})
        l = per_kec_lstm[["kec", "MAE", "MAPE"]].rename(columns={"MAE": "MAE_LSTM", "MAPE": "MAPE_LSTM_%"})
        per_kec_gabung = pd.merge(g, l, on="kec", how="outer")
    elif per_kec_gru is not None and not per_kec_gru.empty:
        per_kec_gabung = per_kec_gru
    else:
        per_kec_gabung = pd.DataFrame()

    # Gabungkan per jenis pemilihan
    if per_jenis_gru is not None and not per_jenis_gru.empty and per_jenis_lstm is not None and not per_jenis_lstm.empty:
        gj = per_jenis_gru.rename(columns={"MAE": "MAE_GRU", "MAPE": "MAPE_GRU_%", "N": "N_sampel"})
        lj = per_jenis_lstm[["jenis", "MAE", "MAPE"]].rename(columns={"MAE": "MAE_LSTM", "MAPE": "MAPE_LSTM_%"})
        per_jenis_gabung = pd.merge(gj, lj, on="jenis", how="outer")
    elif per_jenis_gru is not None and not per_jenis_gru.empty:
        per_jenis_gabung = per_jenis_gru
    else:
        per_jenis_gabung = pd.DataFrame()

    sheet_defs = [
        ("Ringkasan",             ringkasan_df,     "1565C0"),
        ("Metrik_per_Seed",       per_seed_df,      "1565C0"),
        ("Per_Kecamatan",         per_kec_gabung,   "2E7D32"),
        ("Per_Jenis_Pemilihan",   per_jenis_gabung, "2E7D32"),
        ("Error_Kec_GRU",         per_kec_gru,      "1A6E3C"),
        ("Error_Kec_LSTM",        per_kec_lstm,     "B45309"),
        ("Prediksi_2029",         pred29_df,        "5B21B6"),
    ]

    for title, df, color in sheet_defs:
        ws = wb.create_sheet(title)
        if df is None or df.empty:
            ws.append(["(tidak ada data)"])
            continue
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        ws.freeze_panes = "A2"
        _style_header(ws, color)
        _auto_width(ws)
        _fmt_numbers(ws)

    wb.save(out_path)
    return out_path


# ================================================================ RINGKASAN MD
def save_ringkasan(out_path, tbl_str, findings, limitations,
                   wilcoxon_res, improve_df, jurnal_df):
    try:
        jurnal_tbl = jurnal_df.to_markdown(index=False)
        improve_tbl = improve_df.to_markdown(index=False) if not improve_df.empty else "(tidak ada data)"
    except Exception:
        jurnal_tbl  = jurnal_df.to_string(index=False)
        improve_tbl = improve_df.to_string(index=False) if not improve_df.empty else "(tidak ada data)"

    lines = [
        "# RINGKASAN HASIL PENELITIAN",
        "## Prediksi Tingkat Partisipasi Pemilih Kab. Kampar — GRU + Adam",
        "",
        "---",
        "",
        "## Tabel Utama: Perbandingan Metrik (Rata-rata ± Std, 5 Seed)",
        "",
        "```",
        tbl_str,
        "```",
        "",
        "## Perbaikan GRU-Adam terhadap Pembanding",
        "",
        improve_tbl,
        "",
        "---",
        "",
        "## Perbandingan dengan Jurnal Acuan",
        "",
        "> ⚠️ **Catatan penting:** Angka jurnal menggunakan skema data, periode,",
        "> dan kecamatan yang **berbeda**. Perbandingan ini hanya menunjukkan arah",
        "> tren, bukan perbandingan langsung (apples-to-apples).",
        "",
        jurnal_tbl,
        "",
        "---",
        "",
        "## 5 Temuan Utama",
        "",
    ]
    for i, f in enumerate(findings, 1):
        lines.append(f"{i}. {f}")

    lines += [
        "",
        "---",
        "",
        "## Uji Signifikansi (Wilcoxon Signed-Rank Test)",
        "",
        "| Statistik W | p-value | Kesimpulan |",
        "|---|---|---|",
        f"| {wilcoxon_res['statistik_W']:.4f} | {wilcoxon_res['p_value']:.4f} | {wilcoxon_res['kesimpulan']} |",
        "",
        "---",
        "",
        "## Keterbatasan Penelitian",
        "",
    ]
    for lim in limitations:
        lines.append(f"- {lim}")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return out_path


# ================================================================ MODE LAPORAN LENGKAP
def run_report(args, Xtr, ytr, Xte, yte, meta_te, last_windows):
    out = args.out
    os.makedirs(out, exist_ok=True)

    print("\n" + "=" * 60)
    print("MODE LAPORAN LENGKAP — multi-seed training")
    print(f"Seeds: {SEEDS}  |  Epochs: {args.epochs}")
    print("=" * 60)

    Xtr_s, ytr_s, Xte_s, yte_s, last_s, sc = scale(Xtr, ytr, Xte, yte, last_windows)
    cfg = dict(units=50, dropout=0.3, batch=32, epochs=args.epochs)

    # True values (sama untuk semua model)
    true_ref = sc.inverse_transform(yte_s.reshape(-1, 1)).ravel()

    # ---- Baseline naif (tidak ada seed — deterministik)
    naive_pred = Xte[:, -1]  # nilai terakhir window, skala asli
    naive_m    = metrics(true_ref, naive_pred)
    naive_agg  = {}
    for k in ["MSE", "MAE", "RMSE", "MAPE"]:
        naive_agg[f"{k}_mean"] = naive_m[k]
        naive_agg[f"{k}_std"]  = 0.0
    naive_agg.update({"waktu_detik": 0.0, "n_params": 0, "best_epoch": 0.0})

    # ---- Daftar model yang akan dilatih
    runs = [
        ("LSTM-SGD (tanpa Adam)", "lstm", "sgd"),
        ("LSTM-Adam",             "lstm", "adam"),
        ("GRU-SGD (tanpa Adam)",  "gru",  "sgd"),
        ("GRU-Adam",              "gru",  "adam"),
    ]
    if args.with_bilstm:
        runs.append(("BiLSTM-Adam", "bilstm", "adam"))

    agg_all        = {"Naif (nilai terakhir)": naive_agg}
    models_final   = {}
    histories_dict = {}
    preds_dict     = {}
    all_m_dict     = {}
    per_seed_rows  = []

    for name, kind, opt in runs:
        print(f"\n[{name}]")
        agg, m_final, hist_final, true_v, pred_v, all_m = train_multi_seed(
            name, kind, opt, Xtr_s, ytr_s, Xte_s, yte_s, sc, cfg, SEEDS
        )
        agg_all[name]        = agg
        models_final[name]   = m_final
        histories_dict[name] = hist_final
        preds_dict[name]     = pred_v
        all_m_dict[name]     = all_m

        for seed, m in zip(SEEDS, all_m):
            per_seed_rows.append({"Model": name, "Seed": seed,
                                  **{k: round(m[k], 6) for k in ["MSE", "MAE", "RMSE", "MAPE"]}})
        print(f"  Rata-rata: MAPE={agg['MAPE_mean']:.4f}% (±{agg['MAPE_std']:.4f}%)  "
              f"RMSE={agg['RMSE_mean']:.6f}  Waktu≈{agg['waktu_detik']:.1f}s")

    per_seed_df = pd.DataFrame(per_seed_rows)

    # ---- Tabel ringkasan diurutkan MAPE_mean terkecil
    summary_rows = []
    for name, agg in agg_all.items():
        row = {"Model": name}
        for k in ["MSE", "MAE", "RMSE", "MAPE"]:
            row[f"{k}_mean"] = round(agg[f"{k}_mean"], 6)
            row[f"{k}_std"]  = round(agg[f"{k}_std"],  6)
        row["Waktu_detik"] = round(agg["waktu_detik"], 2)
        row["N_params"]    = agg["n_params"]
        row["Best_epoch"]  = round(agg["best_epoch"], 1)
        summary_rows.append(row)
    summary_df = pd.DataFrame(summary_rows).sort_values("MAPE_mean").reset_index(drop=True)

    # ---- Perbaikan GRU-Adam vs pembanding
    gru_agg = agg_all.get("GRU-Adam", {})
    improve_rows = []
    for cmp in ["LSTM-Adam", "LSTM-SGD (tanpa Adam)", "GRU-SGD (tanpa Adam)"]:
        if cmp not in agg_all:
            continue
        ca = agg_all[cmp]
        def pct_imp(cmp_v, gru_v):
            return round((cmp_v - gru_v) / (cmp_v + 1e-12) * 100, 2)
        improve_rows.append({
            "Pembanding":        cmp,
            "MAPE_perbaikan_%":  pct_imp(ca["MAPE_mean"], gru_agg.get("MAPE_mean", 0)),
            "RMSE_perbaikan_%":  pct_imp(ca["RMSE_mean"], gru_agg.get("RMSE_mean", 0)),
            "MAE_perbaikan_%":   pct_imp(ca["MAE_mean"],  gru_agg.get("MAE_mean",  0)),
            "MSE_perbaikan_%":   pct_imp(ca["MSE_mean"],  gru_agg.get("MSE_mean",  0)),
        })
    improve_df = pd.DataFrame(improve_rows)

    # ---- Simpan CSV ringkasan & perbaikan
    summary_df.to_csv(os.path.join(out, "perbandingan_metrik.csv"), index=False)
    improve_df.to_csv(os.path.join(out, "perbaikan_vs_pembanding.csv"), index=False)
    per_seed_df.to_csv(os.path.join(out, "metrik_per_seed.csv"), index=False)

    # ---- Simpan loss history tiap model
    for name, hist in histories_dict.items():
        fname = name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
        pd.DataFrame(hist.history).to_csv(
            os.path.join(out, f"loss_{fname}.csv"), index=False)

    # ---- Prediksi 2029
    print("\nMenghitung prediksi 2029 ...")
    kecs = sorted(last_s)
    Xnext = np.stack([last_s[k] for k in kecs])[..., None]
    pred29_dict = {}
    for name, m in models_final.items():
        pnext = sc.inverse_transform(m.predict(Xnext, verbose=0)).ravel()
        pred29_dict[name] = {k: round(float(v * 100), 2) for k, v in zip(kecs, pnext)}

    pred29_rows = []
    for k in kecs:
        row = {"kecamatan": k}
        row.update({n: pred29_dict[n][k] for n in pred29_dict})
        pred29_rows.append(row)
    pred29_df = pd.DataFrame(pred29_rows)
    pred29_df.to_csv(os.path.join(out, "prediksi_2029.csv"), index=False)

    # ---- Analisis error (GRU-Adam & LSTM-Adam)
    print("Analisis error ...")
    per_kec_gru = per_jenis_gru = None
    per_kec_lst = per_jenis_lst = None

    if "GRU-Adam" in preds_dict:
        pk_g, pj_g, t5_g, det_g = error_analysis(meta_te, true_ref, preds_dict["GRU-Adam"])
        per_kec_gru, per_jenis_gru = pk_g, pj_g
        pk_g.to_csv(os.path.join(out, "error_per_kecamatan_gru_adam.csv"), index=False)
        pj_g.to_csv(os.path.join(out, "error_per_jenis_gru_adam.csv"),     index=False)
        t5_g.to_csv(os.path.join(out, "top5_error_gru_adam.csv"),           index=False)
        det_g.to_csv(os.path.join(out, "aktual_vs_prediksi_2024_gru_adam.csv"), index=False)

    if "LSTM-Adam" in preds_dict:
        pk_l, pj_l, t5_l, det_l = error_analysis(meta_te, true_ref, preds_dict["LSTM-Adam"])
        per_kec_lst, per_jenis_lst = pk_l, pj_l
        pk_l.to_csv(os.path.join(out, "error_per_kecamatan_lstm_adam.csv"), index=False)
        pj_l.to_csv(os.path.join(out, "error_per_jenis_lstm_adam.csv"),     index=False)
        t5_l.to_csv(os.path.join(out, "top5_error_lstm_adam.csv"),           index=False)
        det_l.to_csv(os.path.join(out, "aktual_vs_prediksi_2024_lstm_adam.csv"), index=False)

    # ---- Uji Wilcoxon
    wilcox = {"statistik_W": 0.0, "p_value": 1.0,
               "kesimpulan": "Tidak ada LSTM-Adam untuk dibandingkan."}
    if "GRU-Adam" in preds_dict and "LSTM-Adam" in preds_dict:
        wilcox = wilcoxon_test(true_ref, preds_dict["GRU-Adam"], preds_dict["LSTM-Adam"])
    pd.DataFrame([wilcox]).to_csv(os.path.join(out, "uji_wilcoxon.csv"), index=False)

    # ---- Grafik
    print("Membuat grafik ...")
    plot_loss_curves(histories_dict, out)
    plot_actual_vs_pred(true_ref, preds_dict, out)
    plot_metric_barchart(agg_all, out)
    if "LSTM-Adam" in preds_dict:
        plot_mae_per_kecamatan(meta_te, true_ref, preds_dict, out)
    plot_prediksi_2029(
        {n: pred29_dict[n] for n in ["GRU-Adam", "LSTM-Adam"] if n in pred29_dict},
        out
    )
    if "GRU-Adam" in preds_dict:
        plot_scatter_gru_adam(true_ref, preds_dict["GRU-Adam"], out)

    # ---- Excel
    print("Menyimpan Excel ...")
    save_excel(
        os.path.join(out, "laporan_hasil.xlsx"),
        summary_df, per_seed_df,
        per_kec_gru if per_kec_gru is not None else pd.DataFrame(),
        per_jenis_gru if per_jenis_gru is not None else pd.DataFrame(),
        per_kec_lst if per_kec_lst is not None else pd.DataFrame(),
        per_jenis_lst if per_jenis_lst is not None else pd.DataFrame(),
        pred29_df,
    )

    # ---- Temuan untuk RINGKASAN.md
    gru_mape  = agg_all.get("GRU-Adam", {}).get("MAPE_mean", float("nan"))
    lstm_mape = agg_all.get("LSTM-Adam", {}).get("MAPE_mean", None)
    naif_mape = naive_m["MAPE"]
    gsgd_mape = agg_all.get("GRU-SGD (tanpa Adam)", {}).get("MAPE_mean", None)
    lsgd_mape = agg_all.get("LSTM-SGD (tanpa Adam)", {}).get("MAPE_mean", None)

    # Temuan 1: GRU-Adam vs LSTM-Adam
    if lstm_mape is not None:
        diff = lstm_mape - gru_mape
        if diff > 0:
            f1 = (f"GRU-Adam (MAPE={gru_mape:.4f}%) lebih baik dari LSTM-Adam "
                  f"(MAPE={lstm_mape:.4f}%) dengan selisih {diff:.4f} poin "
                  f"({diff/lstm_mape*100:.1f}% perbaikan relatif). "
                  f"Namun selisih ini tergolong kecil — lihat uji signifikansi.")
        else:
            f1 = (f"GRU-Adam (MAPE={gru_mape:.4f}%) TIDAK lebih baik dari LSTM-Adam "
                  f"(MAPE={lstm_mape:.4f}%); LSTM-Adam lebih unggul dengan selisih "
                  f"{abs(diff):.4f} poin MAPE. Hasil ini berbeda dari klaim jurnal acuan "
                  f"dan perlu dibahas jujur dalam skripsi.")
    else:
        f1 = "LSTM-Adam tidak dilatih pada mode ini."

    # Temuan 2: Peran Adam pada GRU
    if gsgd_mape is not None:
        d = gsgd_mape - gru_mape
        f2 = (f"Adam membantu GRU: GRU-Adam MAPE {gru_mape:.4f}% vs GRU-SGD "
              f"{gsgd_mape:.4f}% — perbaikan {d:.4f} poin ({d/gsgd_mape*100:.1f}%). "
              + ("Adam terbukti lebih efektif dari SGD untuk GRU." if d > 0
                 else "SGD ternyata lebih baik atau setara pada dataset ini."))
    else:
        f2 = "GRU-SGD tidak dilatih."

    # Temuan 3: Peran Adam pada LSTM
    if lstm_mape is not None and lsgd_mape is not None:
        d = lsgd_mape - lstm_mape
        f3 = (f"Adam membantu LSTM: LSTM-Adam MAPE {lstm_mape:.4f}% vs LSTM-SGD "
              f"{lsgd_mape:.4f}% — perbaikan {d:.4f} poin ({d/lsgd_mape*100:.1f}%). "
              + ("Adam konsisten mempercepat konvergensi." if d > 0
                 else "SGD ternyata lebih baik atau setara untuk LSTM pada dataset ini."))
    else:
        f3 = "LSTM-SGD atau LSTM-Adam tidak tersedia untuk dibandingkan."

    # Temuan 4: Baseline naif
    naif_beats_all = naif_mape < gru_mape
    if naif_beats_all:
        f4 = (
            f"Baseline naif (MAPE={naif_mape:.4f}%) MASIH mengalahkan semua model RNN "
            f"(GRU-Adam MAPE={gru_mape:.4f}%). "
            f"Penyebab utama: (1) dataset kecil — 136 sampel latih dari 24 kecamatan "
            f"tidak cukup untuk melatih RNN secara optimal; "
            f"(2) turnout antar jenis pemilihan dalam satu tahun sangat berkorelasi "
            f"sehingga 'tebak sama seperti terakhir' sudah akurat; "
            f"(3) window k=3 mungkin terlalu sempit. "
            f"Ini bukan kegagalan metode melainkan karakteristik data yang perlu "
            f"dibahas sebagai limitasi dalam skripsi."
        )
    else:
        f4 = (f"GRU-Adam (MAPE={gru_mape:.4f}%) berhasil mengungguli baseline naif "
              f"(MAPE={naif_mape:.4f}%) — model RNN mampu menangkap pola tambahan.")

    # Temuan 5: Signifikansi
    f5 = wilcox["kesimpulan"]

    findings = [f1, f2, f3, f4, f5]
    limitations = [
        "Dataset kecil (136 sampel latih, 24 kecamatan) membatasi kapasitas generalisasi model RNN.",
        "Fitur hanya turnout historis; faktor eksternal (demografi, kandidat, isu politik) diabaikan.",
        "Window k=3 dipilih tanpa grid search; nilai lain mungkin lebih optimal.",
        "Hanya dua titik uji (s.d. 2019 dan 2024); cross-validation temporal tidak dilakukan.",
        "Angka jurnal acuan tidak sebanding langsung karena perbedaan skema data dan kecamatan.",
        "Model dijalankan pada CPU — hasil bisa sedikit berbeda di GPU karena presisi floating point.",
    ]

    # Tabel tampilan terminal
    disp_cols = ["Model", "MAPE_mean", "MAPE_std", "RMSE_mean", "MAE_mean", "MSE_mean",
                 "Waktu_detik", "N_params", "Best_epoch"]
    tbl_str = summary_df[disp_cols].to_string(index=False)

    jurnal_df = pd.DataFrame(JURNAL_REF)
    save_ringkasan(
        os.path.join(out, "RINGKASAN.md"),
        tbl_str, findings, limitations, wilcox, improve_df, jurnal_df
    )

    # ================================================================ CETAK AKHIR
    print("\n" + "=" * 70)
    print("TABEL PERBANDINGAN METRIK (rata-rata ± std, 5 seed) — diurutkan MAPE")
    print("=" * 70)
    print(summary_df[disp_cols].to_string(index=False))

    if not improve_df.empty:
        print("\n" + "=" * 70)
        print("PERBAIKAN GRU-ADAM TERHADAP PEMBANDING (%)")
        print("=" * 70)
        print(improve_df.to_string(index=False))

    print("\n" + "=" * 70)
    print("UJI WILCOXON SIGNED-RANK (GRU-Adam vs LSTM-Adam)")
    print("=" * 70)
    print(f"  W = {wilcox['statistik_W']:.4f} | p = {wilcox['p_value']:.4f}")
    print(f"  → {wilcox['kesimpulan']}")

    if "GRU-Adam" in pred29_dict:
        print("\n" + "=" * 70)
        print("PREDIKSI PARTISIPASI 2029 — GRU-Adam (top 10 tertinggi)")
        print("=" * 70)
        for kec, pct in sorted(pred29_dict["GRU-Adam"].items(), key=lambda x: -x[1])[:10]:
            print(f"  {kec.title():<28} {pct:.2f}%")

    print(f"\nSemua file tersimpan di folder '{out}/'")
    print("\nDaftar file yang dihasilkan:")
    for fname in sorted(os.listdir(out)):
        fpath = os.path.join(out, fname)
        size  = os.path.getsize(fpath)
        print(f"  {fname:<52} {size:>9} bytes")


# ================================================================ MAIN
def main():
    ap = argparse.ArgumentParser(
        description="GRU Voter Turnout Prediction — Kab. Kampar (Web Dashboard & Multi-Seed)")
    ap.add_argument("--data",        default="Dataset_Yogi.xlsx")
    ap.add_argument("--out",         default="hasil")
    ap.add_argument("--prep-only",   action="store_true",
                    help="hanya bersihkan data, tanpa training")
    ap.add_argument("--grid",        action="store_true",
                    help="cari kombinasi hyperparameter GRU-Adam (mode lama)")
    ap.add_argument("--with-lstm",   action="store_true",
                    help="tambah LSTM-Adam sebagai pembanding (mode lama)")
    ap.add_argument("--with-bilstm", action="store_true", default=True,
                    help="tambah BiLSTM-Adam pada laporan komparasi (default: True)")
    ap.add_argument("--epochs",      type=int, default=150)
    ap.add_argument("--simple",      action="store_true",
                    help="jalankan mode lama (1-run 3 model)")
    ap.add_argument("--retrain",     action="store_true",
                    help="paksa latih ulang seluruh model 5 seed")
    ap.add_argument("--no-serve",    action="store_true",
                    help="jangan otomatis jalankan web server localhost")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    set_seed()

    df = load_and_clean(args.data)
    df.to_csv(os.path.join(args.out, "data_bersih.csv"), index=False)
    X, y, meta, last_windows = make_windows(df)
    Xtr, ytr, Xte, yte, meta_te = split_by_time(X, y, meta)
    print(f"Sampel latih: {len(Xtr)} | sampel uji (2024): {len(Xte)} | window k={WINDOW}")

    if args.prep_only:
        print(f"Data bersih disimpan di {args.out}/data_bersih.csv")
        return

    # ---- MODE LAMA: jika eksplisit diminta flag --simple
    if args.simple:
        Xtr_s, ytr_s, Xte_s, yte_s, last_s, sc = scale(Xtr, ytr, Xte, yte, last_windows)
        naive = metrics(yte, Xte[:, -1])
        rows  = [{"Model": "Naif (nilai terakhir)", **naive}]
        cfg = dict(units=50, dropout=0.3, batch=32, epochs=args.epochs)
        runs = [("GRU-Adam", "gru", "adam"), ("GRU-SGD (tanpa Adam)", "gru", "sgd")]
        if args.with_lstm:
            runs += [("LSTM-Adam", "lstm", "adam")]
        models = {}
        for name, kind, opt in runs:
            m, hist, elapsed, best_ep = train(
                kind, opt, Xtr_s, ytr_s,
                cfg["epochs"], cfg["batch"], cfg["units"], cfg["dropout"])
            res, true, pred = evaluate(m, Xte_s, yte_s, sc)
            rows.append({"Model": name, **res})
            models[name] = m
        tabel = pd.DataFrame(rows).round(6)
        print("\n", tabel.to_string(index=False))
        return

    # ---- MODE DEFAULT: Laporan Lengkap & Web Dashboard
    excel_path = os.path.join(args.out, "laporan_hasil.xlsx")
    plot_path = os.path.join(args.out, "plot_loss_curves.png")

    # Jika hasil lengkap belum ada atau dipaksa latih ulang via --retrain:
    if args.retrain or not os.path.exists(excel_path) or not os.path.exists(plot_path):
        run_report(args, Xtr, ytr, Xte, yte, meta_te, last_windows)
    else:
        print("\n" + "=" * 65)
        print("HASIL LENGKAP SUDAH TERSEDIA DI FOLDER 'hasil/'")
        print("Menyiapkan peluncuran Website Dashboard...")
        print("=" * 65)
        summary_path = os.path.join(args.out, "perbandingan_metrik.csv")
        if os.path.exists(summary_path):
            sdf = pd.read_csv(summary_path)
            disp = [c for c in ["Model", "MAPE_mean", "MAPE_std", "RMSE_mean", "MAE_mean"] if c in sdf.columns]
            print("\n", sdf[disp].to_string(index=False), "\n")

    # Buka Web Dashboard di Localhost
    if not args.no_serve:
        try:
            import app
            app.run_server(port=5000, open_browser=True)
        except Exception as e:
            print(f"\nUntuk membuka website kapan saja, jalankan: python app.py ({e})")


if __name__ == "__main__":
    main()
