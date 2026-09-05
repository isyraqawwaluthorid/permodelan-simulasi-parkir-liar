"""
03_plot_histogram.py
====================
Plot histogram pendapatan harian juru parkir liar + diagnostik kecocokan
distribusi.

Menghasilkan:
  output/histogram_pendapatan.png   -- histogram utama (deliverable tugas no.3)
  output/diagnostik_distribusi.png  -- panel 2x2: histogram, Q-Q, ECDF, boxplot
  output/histogram_per_lokasi.png   -- small multiples per tipe lokasi

Aturan visual mengikuti pedoman data-viz:
  - satu sumbu, tanpa dual-axis
  - warna kategorikal urutan tetap (biru, oranye, aqua), tidak diputar
  - garis 2px, marker >= 8px, grid & sumbu recessive
  - legenda selalu ada untuk >= 2 seri; identitas tidak pernah lewat warna saja
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# ---- Palet (light mode, tervalidasi) ----------------------------------
SURFACE   = "#fcfcfb"
INK       = "#0b0b0b"
INK_2     = "#52514e"
MUTED     = "#898781"
GRID      = "#e1e0d9"
AXIS      = "#c3c2b7"
SERIES_1  = "#2a78d6"   # biru   -- data empiris
SERIES_2  = "#eb6834"   # oranye -- distribusi terpilih
SERIES_3  = "#1baf7a"   # aqua   -- pembanding

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.grid": True,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "figure.dpi": 130,
})

rupiah = FuncFormatter(lambda v, _: f"{v/1000:,.0f}rb")


def aturan_sturges_vs_fd(x):
    """Bandingkan jumlah bin: Sturges vs Freedman-Diaconis. FD lebih tahan outlier."""
    n = len(x)
    sturges = int(np.ceil(np.log2(n) + 1))
    iqr = np.subtract(*np.percentile(x, [75, 25]))
    h_fd = 2 * iqr / n ** (1 / 3)
    fd = int(np.ceil((x.max() - x.min()) / h_fd))
    return sturges, fd


def muat():
    df = pd.read_csv(ROOT / "data" / "pendapatan_jukir_liar.csv")
    x = df["pendapatan_harian_rp"].to_numpy(float)
    return df, x[x > 0]


# =======================================================================
# 1. HISTOGRAM UTAMA
# =======================================================================
def histogram_utama(x, par_gamma, par_lognorm):
    sturges, fd = aturan_sturges_vs_fd(x)
    nbin = fd

    fig, ax = plt.subplots(figsize=(10, 5.8))

    # Densitas diskalakan x1e6 => "peluang per Rp 1 juta", agar sumbu-y terbaca
    # sebagai angka biasa, bukan notasi ilmiah 1e-6.
    S = 1e6
    n_bar, tepi = np.histogram(x, bins=nbin, density=True)
    ax.bar(tepi[:-1], n_bar * S, width=np.diff(tepi), align="edge",
           color=SERIES_1, alpha=0.75, edgecolor=SURFACE, linewidth=1.2,
           label="Data empiris (histogram)")

    grid_x = np.linspace(x.min() * 0.85, x.max() * 1.08, 600)
    ax.plot(grid_x, stats.gamma.pdf(grid_x, *par_gamma) * S, color=SERIES_2,
            lw=2.4, label="Gamma (terpilih)", zorder=3)
    ax.plot(grid_x, stats.lognorm.pdf(grid_x, *par_lognorm) * S, color=SERIES_3,
            lw=2.0, ls="--", label="Lognormal (pembanding)", zorder=3)

    ymax = max(n_bar.max(), stats.gamma.pdf(grid_x, *par_gamma).max()) * S
    ax.set_ylim(0, ymax * 1.32)

    # Penanda mean & median -- garis vertikal recessive, diberi label langsung
    for nilai, teks, frac in [(np.median(x), f"median\nRp {np.median(x):,.0f}", 1.22),
                              (x.mean(), f"mean\nRp {x.mean():,.0f}", 1.06)]:
        ax.axvline(nilai, color=MUTED, lw=1.2, ls=":", zorder=1)
        ax.annotate(teks, xy=(nilai, ymax * frac), xytext=(7, 0),
                    textcoords="offset points", color=INK_2, fontsize=8.5,
                    va="center")

    ax.set_title("Distribusi Pendapatan Harian Juru Parkir Liar",
                 fontsize=14, fontweight="bold", pad=26, loc="left")
    ax.text(0, 1.035, f"n = {len(x)} observasi jukir-hari  |  bin = {nbin} "
                      f"(aturan Freedman-Diaconis; Sturges menyarankan {sturges})",
            transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.set_xlabel("Pendapatan harian (Rupiah)", fontsize=10.5)
    ax.set_ylabel("Densitas peluang  (per Rp 1 juta)", fontsize=10.5)
    ax.xaxis.set_major_formatter(rupiah)
    ax.grid(axis="x", visible=False)
    h, l = ax.get_legend_handles_labels()
    urut = [l.index("Data empiris (histogram)"), l.index("Gamma (terpilih)"),
            l.index("Lognormal (pembanding)")]
    ax.legend([h[i] for i in urut], [l[i] for i in urut],
              loc="upper right", fontsize=9.5)

    fig.tight_layout()
    fig.savefig(OUT / "histogram_pendapatan.png", bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)
    return nbin, sturges


# =======================================================================
# 2. PANEL DIAGNOSTIK 2x2
# =======================================================================
def panel_diagnostik(df, x, par_gamma, ks_d):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    (a, b), (c, d) = axes

    # -- (a) histogram + PDF -------------------------------------------
    S = 1e6
    nbin = aturan_sturges_vs_fd(x)[1]
    n_bar, tepi = np.histogram(x, bins=nbin, density=True)
    a.bar(tepi[:-1], n_bar * S, width=np.diff(tepi), align="edge",
          color=SERIES_1, alpha=0.75, edgecolor=SURFACE, linewidth=1.1,
          label="Data empiris")
    gx = np.linspace(x.min() * 0.85, x.max() * 1.08, 600)
    a.plot(gx, stats.gamma.pdf(gx, *par_gamma) * S, color=SERIES_2, lw=2.4,
           label="PDF Gamma")
    a.set_title("(a) Histogram & PDF terpilih", loc="left", fontweight="bold",
                fontsize=11)
    a.set_xlabel("Pendapatan harian (Rp)")
    a.set_ylabel("Densitas (per Rp 1 juta)")
    a.xaxis.set_major_formatter(rupiah); a.grid(axis="x", visible=False)
    a.legend(fontsize=9)

    # -- (b) Q-Q plot --------------------------------------------------
    n = len(x)
    p = (np.arange(1, n + 1) - 0.5) / n
    teoretis = stats.gamma.ppf(p, *par_gamma)
    empiris = np.sort(x)
    b.scatter(teoretis, empiris, s=22, color=SERIES_1, alpha=0.65,
              edgecolor=SURFACE, linewidth=0.6, label="Kuantil sampel")
    lim = [min(teoretis.min(), empiris.min()), max(teoretis.max(), empiris.max())]
    b.plot(lim, lim, color=SERIES_2, lw=2, label="Garis referensi y = x")
    b.set_title("(b) Q-Q plot terhadap Gamma", loc="left", fontweight="bold",
                fontsize=11)
    b.set_xlabel("Kuantil teoretis (Rp)"); b.set_ylabel("Kuantil empiris (Rp)")
    b.xaxis.set_major_formatter(rupiah); b.yaxis.set_major_formatter(rupiah)
    b.legend(fontsize=9)

    # -- (c) ECDF vs CDF teoretis --------------------------------------
    ecdf_y = np.arange(1, n + 1) / n
    c.step(empiris, ecdf_y, where="post", color=SERIES_1, lw=2,
           label="ECDF empiris")
    c.plot(gx, stats.gamma.cdf(gx, *par_gamma), color=SERIES_2, lw=2,
           label="CDF Gamma")
    # tandai lokasi selisih maksimum (statistik KS)
    cdf_at = stats.gamma.cdf(empiris, *par_gamma)
    idx = np.argmax(np.abs(ecdf_y - cdf_at))
    c.vlines(empiris[idx], cdf_at[idx], ecdf_y[idx], color=MUTED, lw=2.5)
    c.annotate(f"D = {ks_d:.4f}", xy=(empiris[idx], (cdf_at[idx] + ecdf_y[idx]) / 2),
               xytext=(12, -4), textcoords="offset points", fontsize=9.5,
               color=INK_2)
    c.set_title("(c) ECDF vs CDF teoretis (jarak KS)", loc="left",
                fontweight="bold", fontsize=11)
    c.set_xlabel("Pendapatan harian (Rp)"); c.set_ylabel("Peluang kumulatif")
    c.xaxis.set_major_formatter(rupiah); c.legend(fontsize=9, loc="lower right")

    # -- (d) boxplot per tipe lokasi -----------------------------------
    tipe = df.groupby("tipe_lokasi")["pendapatan_harian_rp"].median().sort_values().index
    data = [df.loc[df.tipe_lokasi == t, "pendapatan_harian_rp"].to_numpy() for t in tipe]
    bp = d.boxplot(data, vert=False, patch_artist=True, widths=0.55,
                   tick_labels=[t.replace("/", "/\n") for t in tipe])
    for patch in bp["boxes"]:
        patch.set(facecolor=SERIES_1, alpha=0.55, edgecolor=SERIES_1, linewidth=1.4)
    for elem in ("whiskers", "caps"):
        for it in bp[elem]:
            it.set(color=AXIS, linewidth=1.4)
    for md in bp["medians"]:
        md.set(color=SERIES_2, linewidth=2.4)
    for fl in bp["fliers"]:
        fl.set(marker="o", markersize=4.5, markerfacecolor=MUTED,
               markeredgecolor="none", alpha=0.7)
    d.set_title("(d) Sebaran menurut tipe lokasi", loc="left",
                fontweight="bold", fontsize=11)
    d.set_xlabel("Pendapatan harian (Rp)")
    d.xaxis.set_major_formatter(rupiah); d.grid(axis="y", visible=False)
    d.tick_params(labelsize=8.5)

    fig.suptitle("Diagnostik Kecocokan Distribusi — Pendapatan Harian Juru Parkir Liar",
                 fontsize=14, fontweight="bold", x=0.012, ha="left", y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUT / "diagnostik_distribusi.png", bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)


# =======================================================================
# 3. SMALL MULTIPLES PER TIPE LOKASI
# =======================================================================
def small_multiples(df):
    tipe = list(df["tipe_lokasi"].unique())
    fig, axes = plt.subplots(1, len(tipe), figsize=(4 * len(tipe), 3.4),
                             sharex=True, sharey=True)
    xmax = df["pendapatan_harian_rp"].max()
    for ax, t in zip(np.atleast_1d(axes), tipe):
        sub = df.loc[df.tipe_lokasi == t, "pendapatan_harian_rp"]
        ax.hist(sub, bins=12, range=(0, xmax), color=SERIES_1, alpha=0.8,
                edgecolor=SURFACE, linewidth=1.0)
        ax.axvline(sub.median(), color=SERIES_2, lw=2)
        ax.set_title(f"{t}\nn={len(sub)}  median Rp {sub.median():,.0f}",
                     fontsize=9.5, loc="left", color=INK_2)
        ax.xaxis.set_major_formatter(rupiah)
        ax.grid(axis="x", visible=False)
        ax.tick_params(labelsize=8)
    np.atleast_1d(axes)[0].set_ylabel("Frekuensi")
    fig.suptitle("Pendapatan Harian menurut Tipe Lokasi Parkir "
                 "(garis oranye = median)", fontsize=12, fontweight="bold",
                 x=0.008, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    fig.savefig(OUT / "histogram_per_lokasi.png", bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)


def main():
    df, x = muat()
    par_gamma = stats.gamma.fit(x, floc=0)
    par_lognorm = stats.lognorm.fit(x, floc=0)
    ks_d = stats.kstest(x, "gamma", args=par_gamma).statistic

    nbin, sturges = histogram_utama(x, par_gamma, par_lognorm)
    panel_diagnostik(df, x, par_gamma, ks_d)
    small_multiples(df)

    print("Gambar tersimpan di", OUT)
    for f in sorted(OUT.glob("*.png")):
        print("  -", f.name)
    print(f"\nGamma: shape(alpha) = {par_gamma[0]:.4f}, loc = {par_gamma[1]:.0f}, "
          f"scale(beta) = {par_gamma[2]:,.0f}")
    print(f"KS D = {ks_d:.4f} | jumlah bin = {nbin} (FD), Sturges = {sturges}")


if __name__ == "__main__":
    main()
