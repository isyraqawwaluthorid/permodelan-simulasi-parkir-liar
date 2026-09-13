"""
07_tabel_poster.py
==================
Membuat gambar tabel siap-tempel untuk poster Canva.

Menghasilkan (folder output/poster/):
  tabel_dataset.png     cuplikan dataset (10 baris pertama + baris terakhir)
  tabel_statistik.png   statistik deskriptif
  tabel_pdf_cdf.png     nilai f(x), F(x), dan 1-F(x)
  tabel_sumber.png      empat jangkar kalibrasi dari sumber publik
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "poster"
OUT.mkdir(parents=True, exist_ok=True)

TEAL = "#17788a"
TEAL_MUDA = "#e3f0f3"
INK = "#1f2933"
GARIS = "#c7d0d6"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "figure.facecolor": "white",
    "figure.dpi": 200,
})


def rb(v):
    """Format Rupiah gaya Indonesia: 302.807"""
    return f"{v:,.0f}".replace(",", ".")


def gambar_tabel(judul, kolom, baris, nama, lebar_kolom, tinggi_baris=0.30,
                 fontsize=9.5, rata=None, catatan=None):
    """Render satu tabel sebagai PNG.

    Tinggi gambar dihitung dari jumlah baris, lalu tabel ditempatkan dengan
    bbox eksplisit supaya judul di atas dan catatan di bawah punya ruang
    sendiri -- tidak menimpa isi tabel.
    """
    n = len(baris)
    rata = rata or ["left"] * len(kolom)
    lebar = sum(lebar_kolom)

    t_judul = 0.46                      # pita judul (inci)
    t_catatan = 0.34 if catatan else 0.10
    t_tabel = tinggi_baris * (n + 1)
    tinggi = t_judul + t_tabel + t_catatan

    fig = plt.figure(figsize=(lebar, tinggi))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")

    tabel = ax.table(cellText=baris, colLabels=kolom,
                     colWidths=[w / lebar for w in lebar_kolom],
                     cellLoc="left",
                     bbox=[0, t_catatan / tinggi, 1, t_tabel / tinggi])
    tabel.auto_set_font_size(False)
    tabel.set_fontsize(fontsize)

    for (r, c), sel in tabel.get_celld().items():
        sel.set_edgecolor(GARIS)
        sel.set_linewidth(0.6)
        sel.get_text().set_ha(rata[c])
        sel.PAD = 0.05
        if r == 0:                                  # baris judul kolom
            sel.set_facecolor(TEAL)
            sel.set_text_props(color="white", fontweight="bold")
        else:
            sel.set_facecolor("white" if r % 2 else TEAL_MUDA)
            sel.get_text().set_color(INK)

    fig.text(0.5, 1 - t_judul / (2 * tinggi), judul, ha="center", va="center",
             fontsize=12, fontweight="bold", color=INK)
    if catatan:
        fig.text(0.5, t_catatan / (2 * tinggi), catatan, ha="center",
                 va="center", fontsize=8, color="#5b6670", style="italic")

    fig.savefig(OUT / nama, bbox_inches="tight", facecolor="white",
                pad_inches=0.20, dpi=300)
    plt.close(fig)


def main():
    df = pd.read_csv(ROOT / "data" / "pendapatan_jukir_liar.csv")
    x = df["pendapatan_harian_rp"]
    alpha, _, beta = stats.gamma.fit(x[x > 0].to_numpy(float), floc=0)
    G = stats.gamma(alpha, loc=0, scale=beta)

    # ---- 1. cuplikan dataset ------------------------------------------
    cuplik = df.head(10)
    baris = [[r.id_jukir, r.tipe_lokasi, r.hari, f"{r.jumlah_kendaraan}",
              rb(r.pendapatan_harian_rp)] for r in cuplik.itertuples()]
    baris.append(["⋮", "⋮", "⋮", "⋮", "⋮"])
    akhir = df.iloc[-1]
    baris.append([akhir.id_jukir, akhir.tipe_lokasi, akhir.hari,
                  f"{akhir.jumlah_kendaraan}", rb(akhir.pendapatan_harian_rp)])

    gambar_tabel(
        "Cuplikan Dataset Pendapatan Harian Juru Parkir Liar",
        ["ID Jukir", "Tipe Lokasi", "Hari", "Kendaraan", "Pendapatan (Rp)"],
        baris, "tabel_dataset.png",
        lebar_kolom=[1.35, 1.85, 1.15, 1.25, 1.75],
        rata=["left", "left", "left", "right", "right"],
        catatan=f"Total {len(df)} observasi jukir-hari "
                f"({df.id_jukir.nunique()} juru parkir x 5 hari kerja)")

    # ---- 2. statistik deskriptif --------------------------------------
    stat = [
        ["Jumlah observasi (n)", f"{len(df)}"],
        ["Rata-rata (mean)", f"Rp {rb(x.mean())}"],
        ["Median", f"Rp {rb(x.median())}"],
        ["Modus (dari model)", f"Rp {rb((alpha-1)*beta)}"],
        ["Simpangan baku", f"Rp {rb(x.std(ddof=1))}"],
        ["Minimum", f"Rp {rb(x.min())}"],
        ["Maksimum", f"Rp {rb(x.max())}"],
        ["Persentil 25 (Q1)", f"Rp {rb(x.quantile(.25))}"],
        ["Persentil 75 (Q3)", f"Rp {rb(x.quantile(.75))}"],
        ["Kemencengan (skewness)", f"{x.skew():.4f}".replace(".", ",")],
    ]
    gambar_tabel("Statistik Deskriptif", ["Ukuran", "Nilai"], stat,
                 "tabel_statistik.png", lebar_kolom=[2.45, 1.75],
                 rata=["left", "right"],
                 catatan="Modus < median < mean → sebaran menceng ke kanan")

    # ---- 3. nilai PDF & CDF -------------------------------------------
    titik = [50_000, 100_000, 150_000, 200_000, 250_000, 300_000,
             400_000, 500_000, 600_000, 800_000, 1_000_000]
    nilai = [[rb(t), f"{G.pdf(t):.3e}".replace(".", ","),
              f"{G.cdf(t):.4f}".replace(".", ","),
              f"{G.sf(t):.4f}".replace(".", ",")] for t in titik]
    gambar_tabel("Nilai PDF dan CDF Model Gamma",
                 ["x (Rp)", "f(x)", "F(x)", "1 − F(x)"], nilai,
                 "tabel_pdf_cdf.png", lebar_kolom=[1.45, 1.60, 1.30, 1.35],
                 rata=["right", "right", "right", "right"],
                 catatan="F(x) = P(X ≤ x) · dihitung numerik dengan fungsi gamma tak lengkap")

    # ---- 4. sumber & jangkar kalibrasi ---------------------------------
    sumber = [
        ["Rp 200.000/hari", "100 kendaraan x Rp 2.000", "CELIOS via detikFinance"],
        ["Rp 250.000/hari", "bersih setelah setoran", "Andy Nugroho via detikFinance"],
        ["Rp 286.500/hari", "per jukir, 1 titik 2 orang", "Litbang Kompas via Tirto"],
        ["Rp 2.000 / 5.000", "tarif motor / mobil", "Pergub DKI No. 31/2017"],
    ]
    gambar_tabel("Jangkar Kalibrasi dari Sumber Publik",
                 ["Angka", "Keterangan", "Sumber"], sumber,
                 "tabel_sumber.png", lebar_kolom=[1.60, 2.35, 2.75],
                 catatan="Dataset disusun lewat calibrated process model, bukan survei lapangan")

    print("Tabel poster tersimpan di", OUT)
    for f in sorted(OUT.glob("tabel_*.png")):
        print("  -", f.name)


if __name__ == "__main__":
    main()
