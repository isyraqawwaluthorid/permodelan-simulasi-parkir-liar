"""
05_pdf_cdf.py
=============
Permodelan PDF dan CDF distribusi Gamma untuk pendapatan harian juru parkir liar.

Model:
    X ~ Gamma(alpha = 3,3714 ; beta = 89.817)      x > 0, satuan Rupiah

    PDF:  f(x) = x^(alpha-1) * exp(-x/beta) / ( beta^alpha * Gamma(alpha) )
    CDF:  F(x) = gamma_bawah(alpha, x/beta) / Gamma(alpha)
               = P(alpha, x/beta)      (fungsi gamma tak lengkap ternormalisasi)

CDF Gamma tidak punya bentuk tertutup elementer, jadi dihitung numerik
(scipy.special.gammainc / scipy.stats.gamma.cdf).

Menghasilkan:
  output/pdf_cdf_gamma.png     kurva PDF & CDF berdampingan
  output/tabel_pdf_cdf.csv     tabel nilai f(x) dan F(x)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from pathlib import Path
from scipy import stats, special

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

# ---- Palet (sama dengan skrip 03) -------------------------------------
SURFACE, INK, INK_2 = "#fcfcfb", "#0b0b0b", "#52514e"
MUTED, GRID, AXIS = "#898781", "#e1e0d9", "#c3c2b7"
SERIES_1, SERIES_2, SERIES_3 = "#2a78d6", "#eb6834", "#1baf7a"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
    "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.grid": True,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "figure.dpi": 130,
})
rupiah = FuncFormatter(lambda v, _: f"{v/1000:,.0f}rb")


def main():
    df = pd.read_csv(ROOT / "data" / "pendapatan_jukir_liar.csv")
    x = df["pendapatan_harian_rp"].to_numpy(float)
    x = x[x > 0]

    alpha, loc, beta = stats.gamma.fit(x, floc=0)
    G = stats.gamma(alpha, loc=0, scale=beta)

    print("=" * 70)
    print("MODEL DISTRIBUSI GAMMA — PENDAPATAN HARIAN JURU PARKIR LIAR")
    print("=" * 70)
    print(f"  alpha (shape) = {alpha:.4f}")
    print(f"  beta  (scale) = Rp {beta:,.0f}")
    print(f"  Gamma(alpha)  = {special.gamma(alpha):.6f}")
    print()
    print("  PDF : f(x) = x^(alpha-1) * e^(-x/beta) / (beta^alpha * Gamma(alpha))")
    print("  CDF : F(x) = P(alpha, x/beta)   [gamma tak lengkap ternormalisasi]")
    print()
    print("  Momen teoretis:")
    print(f"    mean     = alpha*beta            = Rp {alpha*beta:,.0f}")
    print(f"    varians  = alpha*beta^2          -> sd = Rp {np.sqrt(alpha)*beta:,.0f}")
    print(f"    modus    = (alpha-1)*beta        = Rp {(alpha-1)*beta:,.0f}")
    print(f"    median   = F^-1(0,5)             = Rp {G.ppf(0.5):,.0f}")
    print(f"    skewness = 2/sqrt(alpha)         = {2/np.sqrt(alpha):.4f}")
    print()
    print("  Pembanding empiris:")
    print(f"    mean empiris   = Rp {x.mean():,.0f}   | median empiris = Rp {np.median(x):,.0f}")
    print(f"    sd empiris     = Rp {x.std(ddof=1):,.0f}   | skew empiris   = {stats.skew(x):.4f}")

    # ---- tabel nilai --------------------------------------------------
    titik = np.array([50_000, 100_000, 150_000, 200_000, 250_000, 300_000,
                      400_000, 500_000, 600_000, 800_000, 1_000_000], float)
    tabel = pd.DataFrame({
        "x_rupiah": titik.astype(int),
        "pdf_f_x": G.pdf(titik),
        "cdf_F_x": G.cdf(titik),
        "sisa_1_min_F": G.sf(titik),
    })
    tabel.to_csv(OUT / "tabel_pdf_cdf.csv", index=False)

    print("\n  Tabel nilai (x dalam Rupiah):")
    print("    x            f(x)          F(x)      1-F(x)")
    for _, r in tabel.iterrows():
        print(f"    {r.x_rupiah:>9,.0f}   {r.pdf_f_x:.3e}   {r.cdf_F_x:>7.4f}   {r.sisa_1_min_F:>7.4f}")

    print("\n  Peluang yang mudah dibaca:")
    print(f"    P(X < 200.000)            = {G.cdf(200_000):.4f}  ({G.cdf(200_000)*100:.1f}%)")
    print(f"    P(200.000 < X < 400.000)  = {G.cdf(400_000)-G.cdf(200_000):.4f}"
          f"  ({(G.cdf(400_000)-G.cdf(200_000))*100:.1f}%)")
    print(f"    P(X > 500.000)            = {G.sf(500_000):.4f}  ({G.sf(500_000)*100:.1f}%)")
    print(f"    P(X > 1.000.000)          = {G.sf(1_000_000):.4f}  ({G.sf(1_000_000)*100:.2f}%)")

    print("\n  Kuantil (F^-1):")
    for p in (0.05, 0.25, 0.50, 0.75, 0.95, 0.99):
        print(f"    q{int(p*100):<3} = Rp {G.ppf(p):>9,.0f}")

    # ---- gambar -------------------------------------------------------
    gx = np.linspace(1, 1_150_000, 1200)
    fig, (a, b) = plt.subplots(1, 2, figsize=(13.2, 5.2))
    S = 1e6

    # (a) PDF
    a.fill_between(gx, 0, G.pdf(gx) * S, color=SERIES_1, alpha=0.13, zorder=1)
    a.plot(gx, G.pdf(gx) * S, color=SERIES_1, lw=2.4, zorder=3,
           label="f(x) — PDF Gamma")
    # label distaggered supaya tidak saling tumpang tindih
    for nilai, teks, warna, dx, dy, ha in [
            ((alpha - 1) * beta, "modus", SERIES_3, -10, 46, "right"),
            (G.ppf(0.5), "median", MUTED, 10, 46, "left"),
            (alpha * beta, "mean", SERIES_2, 14, 14, "left")]:
        a.vlines(nilai, 0, G.pdf(nilai) * S, color=warna, lw=1.8, ls=":", zorder=2)
        a.annotate(f"{teks}\nRp {nilai:,.0f}", xy=(nilai, G.pdf(nilai) * S),
                   xytext=(dx, dy), textcoords="offset points", ha=ha,
                   fontsize=8.5, color=INK_2, linespacing=1.35)
    a.set_title("(a) Fungsi Densitas Peluang — PDF", loc="left",
                fontweight="bold", fontsize=12, pad=10)
    a.set_xlabel("Pendapatan harian x (Rupiah)")
    a.set_ylabel("f(x)  (peluang per Rp 1 juta)")
    a.set_xlim(0, 1_150_000); a.set_ylim(0, G.pdf(gx).max() * S * 1.32)
    a.xaxis.set_major_formatter(rupiah); a.grid(axis="x", visible=False)
    a.legend(fontsize=9.5, loc="upper right")

    # (b) CDF
    b.plot(gx, G.cdf(gx), color=SERIES_2, lw=2.4, zorder=3, label="F(x) — CDF Gamma")
    xs = np.sort(x)
    b.step(xs, np.arange(1, len(xs) + 1) / len(xs), where="post",
           color=SERIES_1, lw=1.6, alpha=0.85, zorder=2, label="ECDF data empiris")
    for p in (0.25, 0.50, 0.75):
        q = G.ppf(p)
        b.hlines(p, 0, q, color=MUTED, lw=1, ls=":", zorder=1)
        b.vlines(q, 0, p, color=MUTED, lw=1, ls=":", zorder=1)
        b.plot([q], [p], "o", ms=6.5, color=SERIES_2, mec=SURFACE, mew=1.4, zorder=4)
        b.annotate(f"q{int(p*100)} = Rp {q:,.0f}", xy=(q, p), xytext=(9, -11),
                   textcoords="offset points", fontsize=8.5, color=INK_2)
    b.set_title("(b) Fungsi Distribusi Kumulatif — CDF", loc="left",
                fontweight="bold", fontsize=12, pad=10)
    b.set_xlabel("Pendapatan harian x (Rupiah)")
    b.set_ylabel("F(x) = P(X ≤ x)")
    b.set_xlim(0, 1_150_000); b.set_ylim(0, 1.04)
    b.xaxis.set_major_formatter(rupiah)
    b.legend(fontsize=9.5, loc="lower right")

    fig.suptitle(f"Model Gamma  ·  α = {alpha:.4f}   β = Rp {beta:,.0f}",
                 fontsize=13.5, fontweight="bold", x=0.008, ha="left", y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT / "pdf_cdf_gamma.png", bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)
    print(f"\nGambar : {OUT/'pdf_cdf_gamma.png'}")
    print(f"Tabel  : {OUT/'tabel_pdf_cdf.csv'}")


if __name__ == "__main__":
    main()
