# Proyek Data Sains: Prediksi Jumlah Penumpang Kereta Api (Indonesia, 2024)

Proyek ini membuat ringkasan tren dan prediksi jangka pendek (1–3 bulan) untuk jumlah penumpang kereta api per kategori menggunakan model tren linier sederhana.

## Konteks Bisnis

Memprediksi jumlah penumpang kereta api penting untuk perencanaan kapasitas, alokasi sumber daya, dan strategi pendapatan. Proyek ini memberikan pandangan cepat mengenai tren jangka pendek sebagai dasar pengambilan keputusan operasional.

## Sumber Data

Data historis bulanan bersumber dari portal data publik Badan Pusat Statistik (BPS):
https://www.bps.go.id/id/statistics-table/2/NzIjMg==/jumlah-penumpang-kereta-api--ribu-orang-.html

File CSV 2024 dan 2025 pada repo ini adalah ekstraksi/penyusunan ulang dengan format kolom: `tipe kendaraan, Januari..Desember, Tahunan` untuk keperluan analisis.

### Contoh Visual

Contoh plot hasil model (kategori dengan kecocokan tren tinggi):
![Contoh: LRT (R² relatif tinggi)](output_2024_2025/plots/lrt.png)

## Ringkasan Jawaban

- Pertanyaan: "Apakah ke depan naik atau menurun?"
- Jawaban singkat: berdasarkan tren linier per kategori atas data 2024, kategori “Total” menunjukkan kecenderungan NAIK tipis dalam 1–3 bulan ke depan. Kategori lain dinilai secara mandiri; detail arah tiap kategori tercantum pada output ringkasan setelah Anda menjalankan skrip.

Catatan: ini adalah pemodelan ringkas berbasis tren linier pada 12 titik data (1 tahun), sehingga efek musiman atau kebijakan besar tidak tertangkap.

## Struktur Proyek

```
.
├─ README.md
├─ requirements.txt
├─ Jumlah Penumpang Kereta Api, 2024.csv
└─ src/
   └─ forecast.py
```

## Persiapan Lingkungan

Disarankan menggunakan virtual environment (Windows):

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Jika sudah punya environment aktif, cukup pasang dependency:

```
pip install -r requirements.txt
```

Dependency utama:

- pandas, numpy
- scikit-learn
- matplotlib, seaborn

Versi minimum tidak di-pin; gunakan versi stabil terbaru.

## Menjalankan

Contoh perintah (Windows, dari root proyek):

```
python src/forecast.py --input "Jumlah Penumpang Kereta Api, 2024.csv" --horizon 3 --output_dir output
```

Argumen:

- `--input`: path CSV input (default: "Jumlah Penumpang Kereta Api, 2024.csv")
- `--horizon`: jumlah bulan ke depan untuk diprediksi (default: 3)
- `--output_dir`: folder hasil keluaran (default: output)
- `--year`: tahun data pada CSV (default: 2024)

## Keluaran

Setelah berhasil jalan, Anda akan mendapatkan:

1. File ringkasan: `output/forecast_summary.csv`  
   Kolom:

   - `tipe_kendaraan`: nama kategori (contoh: Total, Jabodetabek, dsb.)
   - `n_obs`: jumlah observasi (harus 12 untuk data 2024 per kategori)
   - `last_month_actual`: nilai aktual bulan terakhir (Desember 2024)
   - `slope_per_bulan`: kemiringan tren linier (perubahan rata-rata per bulan)
   - `intercept`: intercept model linier
   - `r2`: koefisien determinasi pada data historis
   - `arah_prediksi_vs_bulan_terakhir`: klasifikasi arah prediksi bulan depan terhadap bulan terakhir aktual (naik/turun/tetap) dengan toleransi 0.5% (min 10)
   - `pred_next_1..pred_next_H`: nilai prediksi bulan ke-1..H
   - `pred_next_1_label..pred_next_H_label`: label waktu ringkas untuk tiap prediksi (misal 2025-Jan)

2. Plot per kategori: `output/plots/*.png`  
   Grafik menampilkan:

   - garis aktual (12 bulan 2024)
   - garis tren linier pada domain historis
   - titik prediksi 1..H bulan ke depan beserta label bulan

3. Ringkasan di konsol  
   Skrip juga mencetak tabel ringkasan ke terminal setelah selesai.

## Metodologi Singkat

- Data dibaca dengan encoding `utf-8-sig` untuk mengatasi BOM pada header.
- Data diformat dari lebar (kolom bulan) menjadi long time series (1 baris per kategori-bulan).
- Untuk tiap kategori, kita membangun model `y = a + b * t` (t = 1..12) menggunakan `sklearn.linear_model.LinearRegression`.
- Prediksi ke depan dilakukan untuk t = n+1..n+H (H = horizon).
- Arah prediksi bulan berikutnya diklasifikasikan:
  - "naik" jika `pred_next_1` > `last_month_actual + tol`
  - "turun" jika `pred_next_1` < `last_month_actual - tol`
  - "tetap" jika berada dalam rentang toleransi
  - Toleransi `tol = max(0.5% * last_actual, 10)`

Keterbatasan:

- Data hanya 12 titik (1 tahun), sehingga pola musiman/mingguan tidak tertangkap.
- Linear trend tidak memodelkan libur panjang, promosi, kebijakan tarif, atau kejadian eksternal.
- Untuk akurasi lebih baik dengan data multi-tahun, pertimbangkan Holt-Winters/Exponential Smoothing, SARIMA, atau Prophet.

## Reproduksi Cepat

1. Aktifkan virtualenv Anda (Windows):

```
.\.venv\Scripts\activate
```

2. Install dependency (jika belum):

```
pip install -r requirements.txt
```

3. Jalankan:

```
python src/forecast.py --input "Jumlah Penumpang Kereta Api, 2024.csv" --horizon 3 --output_dir output
```

4. Cek:

- `output/forecast_summary.csv` untuk tabel prediksi dan arah
- `output/plots/*.png` untuk visualisasi tiap kategori

## FAQ

- File CSV ber-BOM? Sudah ditangani (`utf-8-sig`) dan pembersihan header otomatis.
- Kolom "Tahunan" ikut dihitung? Tidak, kolom tersebut diabaikan saat fitting.
- Bisa mengubah horizon? Bisa, ubah `--horizon` (misal 1 atau 6).
- Prediksi level negatif? Dengan tren linier murni itu bisa terjadi pada kategori dengan tren menurun tajam. Interpretasi dengan hati-hati; tambahkan pembatas atau gunakan model alternatif jika perlu.

## Lisensi

Penggunaan bebas untuk analisis internal. Mohon cantumkan atribusi jika dipublikasikan.

## hasil-analisis-2025-akhir

Berikut ringkasan analisis untuk gabungan data 2024–2025 dengan horizon prediksi Agustus 2025 hingga Januari 2026.

- Sumber angka: [output_2024_2025/forecast_summary.csv](output_2024_2025/forecast_summary.csv)
- Grafik referensi:
  - [output_2024_2025/plots/jabodetabek.png](output_2024_2025/plots/jabodetabek.png)
  - [output_2024_2025/plots/mrt.png](output_2024_2025/plots/mrt.png)
  - [output_2024_2025/plots/lrt.png](output_2024_2025/plots/lrt.png)

Intisari temuan

- Secara umum, model tren linier memperkirakan koreksi pada Agustus 2025 dari level puncak Juli 2025, lalu lintasan kembali menanjak bertahap hingga Januari 2026.
- Pola ini konsisten dengan “kembali ke tren” setelah puncak di bulan Juli pada beberapa kategori.

Detail per kategori (Agustus 2025 s.d. Januari 2026)

1. Jabodetabek

- Historis & kecocokan:
  - n_obs = 19 (Jan 2024–Jul 2025)
  - R² = 0.38 (kecocokan moderat)
  - Slope = +170.20 penumpang/bulan
- Titik acuan terbaru: Jul-2025 = 31,401
- Prediksi:
  - 2025-Agu: 29,363.70
  - 2025-Sep: 29,533.90
  - 2025-Okt: 29,704.09
  - 2025-Nov: 29,874.29
  - 2025-Des: 30,044.49
  - 2026-Jan: 30,214.68
- Interpretasi:
  - Klasifikasi vs bulan terakhir: “turun” untuk Agustus (koreksi dari puncak Juli).
  - Namun lintasan 6 bulan menunjukkan kenaikan bertahap kembali mendekati 30 ribuan.

2. MRT

- Historis & kecocokan:
  - n_obs = 19
  - R² = 0.40 (kecocokan sedang)
  - Slope = +47.93 penumpang/bulan
- Titik acuan terbaru: Jul-2025 = 4,354
- Prediksi:
  - 2025-Agu: 3,898.91
  - 2025-Sep: 3,946.84
  - 2025-Okt: 3,994.77
  - 2025-Nov: 4,042.70
  - 2025-Des: 4,090.62
  - 2026-Jan: 4,138.55
- Interpretasi:
  - “Turun” di Agustus dari puncak Juli, kemudian naik bertahap mendekati 4.1 ribu awal 2026.
- Visual: [output_2024_2025/plots/mrt.png](output_2024_2025/plots/mrt.png)

3. LRT

- Historis & kecocokan:
  - n_obs = 19
  - R² = 0.81 (paling kuat dari tiga kategori)
  - Slope = +68.15 penumpang/bulan
- Titik acuan terbaru: Jul-2025 = 3,219
- Prediksi:
  - 2025-Agu: 3,085.79
  - 2025-Sep: 3,153.94
  - 2025-Okt: 3,222.08
  - 2025-Nov: 3,290.23
  - 2025-Des: 3,358.38
  - 2026-Jan: 3,426.53
- Interpretasi:
  - “Turun” pada Agustus, tetapi tren 6 bulan menunjukkan kenaikan konsisten. Dengan R² tinggi, tren linier cukup representatif.
- Visual: [output_2024_2025/plots/lrt.png](output_2024_2025/plots/lrt.png)

Narasi manajerial singkat

- Juli 2025 tampak sebagai titik tinggi; model memproyeksikan penyesuaian di Agustus 2025 dan pemulihan gradual sampai awal 2026.
- Jabodetabek: koreksi jangka pendek lalu kembali naik perlahan; permintaan relatif resilient.
- LRT: indikasi tren naik paling kuat (R² ~ 0.81); kenaikan bertahap lebih meyakinkan.
- MRT: pola serupa, namun dengan kecocokan tren sedang (R² ~ 0.40) sehingga ketidakpastian relatif lebih tinggi.
- Implikasi operasional: atur kapasitas/penjadwalan untuk antisipasi pelemahan Agustus dan kenaikan bertahap akhir 2025. Perlu monitoring realisasi Agustus–September.

Keterbatasan

- Model linier tanpa musiman; efek libur panjang, promosi, tarif, atau faktor eksternal lain tidak dimodelkan.
- Klasifikasi “naik/turun” hanya membandingkan prediksi bulan pertama vs nilai aktual terakhir; lintasan 3–6 bulan perlu diperhatikan untuk konteks.
