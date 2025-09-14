"""
Forecast jumlah penumpang kereta api per kategori menggunakan tren linier sederhana.

Fitur:
- Load CSV dengan encoding 'utf-8-sig' (menghapus BOM jika ada)
- Transformasi dari format wide (kolom bulan) ke long time series
- Estimasi tren linier per kategori (sklearn LinearRegression)
- Prediksi 1..H bulan ke depan (default 3)
- Klasifikasi arah prediksi (naik/turun/tetap) relatif terhadap bulan terakhir aktual
- Ekspor ringkasan ke output/forecast_summary.csv
- Simpan grafik per kategori ke output/plots/

Cara pakai:
    python src/forecast.py --input "Jumlah Penumpang Kereta Api, 2024.csv" --horizon 3 --output_dir output

Catatan:
- Dataset berisi satu tahun (2024) dengan kolom bulan Januari..Desember.
- Prediksi akan memperkirakan bulan-bulan setelah Desember (misal Jan, Feb, Mar 2025).
"""

import argparse
import os
import re
from typing import List, Tuple, Dict, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


INDO_MONTHS = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]

NEXT_MONTHS_MAP = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "Mei",
    6: "Jun",
    7: "Jul",
    8: "Agu",
    9: "Sep",
    10: "Okt",
    11: "Nov",
    12: "Des",
}


def _strip_bom_and_clean(col: str) -> str:
    """Hilangkan BOM dan rapikan nama kolom."""
    if not isinstance(col, str):
        return col
    return col.replace("\ufeff", "").strip()


def load_and_transform(input_path: str, year: int = 2024) -> pd.DataFrame:
    """
    Load CSV dan transformasi ke format long.
    Output kolom: ['tipe_kendaraan', 'bulan', 'month_num', 'tanggal', 'jumlah']
    """
    df = pd.read_csv(input_path, encoding="utf-8-sig")
    df.columns = [_strip_bom_and_clean(c) for c in df.columns]

    # Identifikasi kolom kategori (asumsikan kolom pertama)
    if len(df.columns) < 2:
        raise ValueError("CSV tidak memiliki format yang diharapkan (minimal 2 kolom).")

    first_col = df.columns[0]
    # Standarisasi nama kolom kategori
    df = df.rename(columns={first_col: "tipe_kendaraan"})

    # Pilih kolom bulan yang valid
    bulan_kolom = [b for b in INDO_MONTHS if b in df.columns]
    if len(bulan_kolom) == 0:
        raise ValueError("Tidak ditemukan kolom bulan (Januari..Desember) dalam CSV.")

    # Buang kolom 'Tahunan' bila ada (tidak dipakai untuk fitting bulanan)
    drop_cols = [c for c in df.columns if c.lower() == "tahunan"]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # Melt ke long format
    long_df = df.melt(
        id_vars=["tipe_kendaraan"],
        value_vars=bulan_kolom,
        var_name="bulan",
        value_name="jumlah",
    )

    # Konversi jumlah ke numerik
    long_df["jumlah"] = pd.to_numeric(long_df["jumlah"], errors="coerce")

    # Urut bulan sesuai urutan Indonesia
    month_map = {m: i + 1 for i, m in enumerate(INDO_MONTHS)}
    long_df["month_num"] = long_df["bulan"].map(month_map)

    # Buat tanggal (pakai tanggal 1 setiap bulan)
    long_df["tanggal"] = pd.to_datetime(
        {"year": year, "month": long_df["month_num"], "day": 1}, errors="coerce"
    )

    # Buang baris invalid
    long_df = long_df.dropna(subset=["jumlah", "month_num", "tanggal"]).copy()

    # Urutkan
    long_df = long_df.sort_values(["tipe_kendaraan", "month_num"]).reset_index(
        drop=True
    )
    return long_df


def infer_year_from_filename(path: str) -> Optional[int]:
    """
    Coba infer tahun dari nama file, misal: '... 2024.csv' -> 2024.
    """
    base = os.path.basename(path)
    m = re.search(r"(20\d{2})", base)
    if m:
        y = int(m.group(1))
        if 1900 <= y <= 2100:
            return y
    return None


def _normalize_years_for_inputs(
    paths: List[str],
    years: Optional[List[int]],
    default_year: Optional[int],
) -> List[int]:
    """
    Normalisasi daftar tahun untuk setiap input.
    Aturan:
      - Jika years diberikan dan hanya 1 nilai, broadcast ke semua input.
      - Jika years panjangnya sama dengan jumlah input, gunakan berurutan.
      - Jika tidak ada, coba infer dari nama file.
      - Jika tetap gagal, gunakan default_year.
      - Jika masih gagal, raise error.
    """
    result: List[int] = []
    for i, p in enumerate(paths):
        y: Optional[int] = None
        if years is not None:
            if len(years) == 1:
                y = int(years[0])
            elif i < len(years):
                y = int(years[i])
        if y is None:
            y = infer_year_from_filename(p)
        if y is None:
            y = default_year
        if y is None:
            raise ValueError(
                f"Tidak bisa menentukan tahun untuk file '{p}'. Berikan --year atau --default_year."
            )
        result.append(int(y))
    return result


def load_and_transform_multi(
    paths: List[str],
    years: Optional[List[int]] = None,
    default_year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load banyak CSV dan gabungkan ke long time series lintas tahun.
    Setiap file di-assign tahun sesuai argumen/hasil infer, lalu dikonversi
    menggunakan load_and_transform(..., year=...).
    """
    if not paths:
        raise ValueError("Daftar input kosong.")

    norm_years = _normalize_years_for_inputs(paths, years, default_year)
    frames: List[pd.DataFrame] = []
    for p, y in zip(paths, norm_years):
        df_i = load_and_transform(p, year=y)
        frames.append(df_i)

    df_all = pd.concat(frames, ignore_index=True)
    # Pastikan urutan global per kategori adalah kronologis lintas tahun
    df_all = df_all.sort_values(["tipe_kendaraan", "tanggal"]).reset_index(drop=True)
    return df_all


def _fit_linear_trend(y: np.ndarray) -> Tuple[float, float, float]:
    """
    Fit tren linier y ~ a + b*t, t = 1..n.
    Return: (intercept a, slope b, r2)
    """
    n = len(y)
    t = np.arange(1, n + 1).reshape(-1, 1)
    model = LinearRegression()
    model.fit(t, y)
    y_hat = model.predict(t)
    r2 = r2_score(y, y_hat) if n >= 2 else 1.0
    return float(model.intercept_), float(model.coef_[0]), float(r2)


def _predict_future(a: float, b: float, n: int, horizon: int) -> List[float]:
    """
    Prediksi ke depan: t = n+1..n+horizon untuk y = a + b*t
    """
    future_t = np.arange(n + 1, n + horizon + 1)
    preds = a + b * future_t
    return preds.tolist()


def _classify_direction(last_actual: float, next_pred: float) -> str:
    """
    Klasifikasi arah: 'naik' jika prediksi jelas naik, 'turun' jika jelas turun, selain itu 'tetap'.
    Gunakan ambang toleransi relatif 0.5% dari last_actual dengan minimum absolut 10.
    """
    if pd.isna(last_actual) or pd.isna(next_pred):
        return "tidak diketahui"

    tol = max(0.005 * abs(last_actual), 10.0)
    if next_pred > last_actual + tol:
        return "naik"
    elif next_pred < last_actual - tol:
        return "turun"
    else:
        return "tetap"


def _sanitize_filename(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "kategori"


def _month_labels_after(last_date: pd.Timestamp, horizon: int) -> List[str]:
    """
    Buat label singkat untuk bulan prediksi setelah last_date.
    Contoh: last_date=2024-12-01, horizon 3 => ['2025-Jan', '2025-Feb', '2025-Mar']
    """
    labels = []
    y = int(last_date.year)
    m = int(last_date.month)
    for _ in range(horizon):
        m += 1
        if m > 12:
            m = 1
            y += 1
        labels.append(f"{y}-{NEXT_MONTHS_MAP[m]}")
    return labels


def fit_trend_and_forecast(
    df_long: pd.DataFrame, horizon: int = 3
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, List[float]]]]:
    """
    Fit tren per kategori dan hasilkan ringkasan serta prediksi per kategori.

    Return:
      - summary_df: ringkasan metrik dan prediksi
      - detail_forecasts: dict kategori -> {'future_values': [...], 'future_labels': [...]}
    """
    summaries = []
    detail_forecasts: Dict[str, Dict[str, List[float]]] = {}

    for tipe, grp in df_long.groupby("tipe_kendaraan", sort=False):
        grp = grp.sort_values("tanggal")
        y = grp["jumlah"].to_numpy(dtype=float)
        n = len(y)

        if n < 2:
            # Tidak cukup titik untuk tren linier
            a, b, r2 = float(y.mean()) if n else 0.0, 0.0, 1.0
        else:
            a, b, r2 = _fit_linear_trend(y)

        preds = _predict_future(a, b, n, horizon) if horizon > 0 else []
        last_actual = y[-1] if n > 0 else np.nan
        direction = _classify_direction(last_actual, preds[0] if preds else np.nan)

        # Simpan detail
        last_date = grp["tanggal"].max()
        future_labels = _month_labels_after(last_date, horizon)
        detail_forecasts[tipe] = {
            "future_values": preds,
            "future_labels": future_labels,
        }

        # Ringkasan
        row = {
            "tipe_kendaraan": tipe,
            "n_obs": n,
            "last_month_actual": (
                float(last_actual) if not pd.isna(last_actual) else np.nan
            ),
            "slope_per_bulan": b,
            "intercept": a,
            "r2": r2,
            "arah_prediksi_vs_bulan_terakhir": direction,
        }
        # Tambahkan kolom next_1..next_h
        for i in range(horizon):
            row[f"pred_next_{i+1}"] = preds[i] if i < len(preds) else np.nan
            row[f"pred_next_{i+1}_label"] = (
                future_labels[i] if i < len(future_labels) else ""
            )
        summaries.append(row)

    summary_df = pd.DataFrame(summaries)
    # Urutkan: Total di atas jika ada
    if "Total" in summary_df["tipe_kendaraan"].values:
        summary_df["__order"] = (summary_df["tipe_kendaraan"] != "Total").astype(int)
        summary_df = summary_df.sort_values(["__order", "tipe_kendaraan"]).drop(
            columns="__order"
        )
    else:
        summary_df = summary_df.sort_values("tipe_kendaraan")

    return summary_df, detail_forecasts


def plot_category(
    grp: pd.DataFrame, preds: List[float], preds_labels: List[str], out_dir: str
) -> None:
    """
    Plot historis dan tren linier dengan titik prediksi ke depan.
    """
    os.makedirs(out_dir, exist_ok=True)
    tipe = grp["tipe_kendaraan"].iloc[0]
    safe_name = _sanitize_filename(tipe)

    # Data untuk fitting ulang garis tren agar visual selaras
    y = grp["jumlah"].to_numpy(dtype=float)
    n = len(y)
    if n >= 2:
        a, b, _ = _fit_linear_trend(y)
        t_all = np.arange(1, n + 1)
        y_hat = a + b * t_all
    else:
        t_all = np.arange(1, n + 1)
        y_hat = y.copy()

    # Plot
    sns.set(style="whitegrid")
    plt.figure(figsize=(9, 4.5))
    # Garis aktual
    plt.plot(grp["tanggal"], grp["jumlah"], marker="o", label="Aktual")
    # Garis tren (di atas domain aktual)
    if n >= 1:
        plt.plot(grp["tanggal"], y_hat, linestyle="--", color="C1", label="Tren linier")

    # Titik prediksi
    if preds:
        # Buat sumbu waktu untuk prediksi melanjutkan dari bulan terakhir
        last_date = grp["tanggal"].max()
        future_dates = []
        y_val = last_date.year
        m_val = last_date.month
        for _ in preds:
            m_val += 1
            if m_val > 12:
                m_val = 1
                y_val += 1
            future_dates.append(pd.Timestamp(year=y_val, month=m_val, day=1))

        plt.plot(
            future_dates,
            preds,
            marker="x",
            linestyle="-.",
            color="C3",
            label="Prediksi",
        )

        # Anotasi label ringkas di tiap titik prediksi
        for d, val, lab in zip(future_dates, preds, preds_labels):
            plt.annotate(
                lab,
                (d, val),
                textcoords="offset points",
                xytext=(0, 6),
                ha="center",
                fontsize=8,
                color="C3",
            )

    plt.title(f"Tren & Prediksi: {tipe}")
    plt.xlabel("Bulan")
    plt.ylabel("Jumlah Penumpang")
    plt.legend()
    plt.tight_layout()

    out_path = os.path.join(out_dir, f"{safe_name}.png")
    plt.savefig(out_path, dpi=150)
    plt.close()


def run(
    inputs: List[str],
    output_dir: str,
    horizon: int,
    years: Optional[List[int]] = None,
    default_year: Optional[int] = None,
) -> Tuple[pd.DataFrame, Dict[str, Dict[str, List[float]]]]:
    """
    Pipeline end-to-end untuk satu atau banyak file input.
    """
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)

    df_long = load_and_transform_multi(
        paths=inputs, years=years, default_year=default_year
    )
    summary_df, detail = fit_trend_and_forecast(df_long, horizon=horizon)

    # Simpan ringkasan
    out_csv = os.path.join(output_dir, "forecast_summary.csv")
    # Bulatkan angka untuk keterbacaan
    to_save = summary_df.copy()
    num_cols = to_save.select_dtypes(include=[np.number]).columns
    to_save[num_cols] = to_save[num_cols].round(2)
    to_save.to_csv(out_csv, index=False, encoding="utf-8")

    # Plot per kategori
    for tipe, grp in df_long.groupby("tipe_kendaraan", sort=False):
        preds = detail[tipe]["future_values"]
        labels = detail[tipe]["future_labels"]
        plot_category(grp, preds, labels, plots_dir)

    return summary_df, detail


def _print_console_summary(summary_df: pd.DataFrame, horizon: int) -> None:
    """
    Cetak ringkasan ke konsol.
    """
    print("\nRingkasan Tren & Prediksi:")
    print("-" * 60)
    cols = [
        "tipe_kendaraan",
        "n_obs",
        "last_month_actual",
        "slope_per_bulan",
        "r2",
        "arah_prediksi_vs_bulan_terakhir",
    ]
    cols += [f"pred_next_{i+1}" for i in range(horizon)]
    cols += [f"pred_next_{i+1}_label" for i in range(horizon)]

    # Pastikan kolom ada
    cols = [c for c in cols if c in summary_df.columns]

    disp = summary_df.loc[:, cols].copy()
    # Pembulatan untuk tampilan
    for c in disp.columns:
        if disp[c].dtype.kind in {"f", "i"}:
            disp[c] = disp[c].round(2)
    print(disp.to_string(index=False))
    print("-" * 60)
    print("Keterangan arah: naik/turun/tetap dibanding bulan aktual terakhir.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Forecast penumpang kereta api berbasis tren linier sederhana (mendukung multi-file)."
    )
    parser.add_argument(
        "--input",
        "-i",
        action="append",
        help="Path ke file CSV input. Dapat diulang beberapa kali (-i file1 -i file2). Jangan gunakan daftar dipisah koma karena nama file mengandung koma.",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="output",
        help="Direktori output untuk ringkasan dan grafik.",
    )
    parser.add_argument(
        "--horizon", type=int, default=3, help="Jumlah bulan ke depan untuk diprediksi."
    )
    parser.add_argument(
        "--year",
        "-y",
        action="append",
        type=int,
        help="Tahun data untuk masing-masing --input (boleh diulang). Jika tidak diisi, akan coba diinfer dari nama file, lalu fallback ke --default_year.",
    )
    parser.add_argument(
        "--default_year",
        type=int,
        default=None,
        help="Tahun fallback jika tidak bisa infer dari nama file dan --year tidak diberikan.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Normalisasi daftar input: gunakan multiple -i; jangan split koma karena nama file mengandung koma
    inputs: List[str] = []
    if args.input is None:
        # fallback kompatibel: pakai file default 2024 jika tidak ada argumen
        inputs = ["Jumlah Penumpang Kereta Api, 2024.csv"]
    else:
        for entry in args.input:
            if entry is None:
                continue
            inputs.append(entry)

    years = args.year if args.year else None

    summary_df, _ = run(
        inputs=inputs,
        output_dir=args.output_dir,
        horizon=args.horizon,
        years=years,
        default_year=args.default_year,
    )
    _print_console_summary(summary_df, args.horizon)


if __name__ == "__main__":
    main()
