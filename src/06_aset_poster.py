"""
06_aset_poster.py
=================
Membuat aset siap-tempel untuk poster Canva: kurva PDF & CDF terpisah,
plus gambar rumus berlatar transparan.

Gaya visual mengikuti format poster akademik: latar putih, garis teal,
penanda merah putus-putus, tanpa grid berat.

Menghasilkan (folder output/poster/):
  kurva_pdf.png          kurva PDF berdiri sendiri
  kurva_cdf.png          kurva CDF berdiri sendiri
  rumus_pdf_umum.png     f(x) bentuk umum
  rumus_pdf_isi.png      f(x) setelah parameter dimasukkan
  rumus_cdf_umum.png     F(x) bentuk umum
  rumus_cdf_isi.png      F(x) setelah parameter dimasukkan
  parameter.png          kotak nilai alpha & beta
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
OUT = ROOT / "output" / "poster"
OUT.mkdir(parents=True, exist_ok=True)

TEAL = "#17788a"      # warna kurva
MERAH = "#e05c4a"     # penanda
INK = "#1f2933"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "mathtext.fontset": "dejavusans",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#9aa3ab",
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "text.color": INK,
    "xtick.color": "#5b6670",
    "ytick.color": "#5b6670",
    "axes.grid": False,
    "figure.dpi": 200,
})

rupiah = FuncFormatter(lambda v, _: f"{v/1000:,.0f}rb".replace(",", "."))


def rumus(teks, nama, fontsize=26, pad=0.30):
    """Render satu rumus mathtext sebagai PNG berlatar transparan."""
    fig = plt.figure(figsize=(0.1, 0.1))
    fig.text(0, 0, teks, fontsize=fontsize, color=INK)
    fig.savefig(OUT / nama, transparent=True, bbox_inches="tight",
                pad_inches=pad, dpi=300)
    plt.close(fig)


def kurva(kind, G, alpha, beta):
    fig, ax = plt.subplots(figsize=(6.4, 4.3))
    gx = np.linspace(0, 1_150_000, 1000)

    if kind == "pdf":
        ax.plot(gx, G.pdf(gx), color=TEAL, lw=2.2)
        penanda = (alpha - 1) * beta            # modus = puncak kurva
        ax.axvline(penanda, color=MERAH, lw=1.6, ls="--")
        ax.set_title("Kurva PDF", fontsize=12, pad=10)
        ax.set_ylabel("Kepadatan Probabilitas", fontsize=10)
        ax.set_ylim(0, G.pdf(gx).max() * 1.12)
        ax.ticklabel_format(axis="y", style="sci", scilimits=(-6, -6))
    else:
        ax.plot(gx, G.cdf(gx), color=TEAL, lw=2.2)
        penanda = G.ppf(0.5)                    # median, F(x) = 0,50
        ax.axvline(penanda, color=MERAH, lw=1.6, ls="--")
        ax.axhline(0.5, color=MERAH, lw=1.6, ls="--")
        ax.plot([penanda], [0.5], "o", ms=7, color=MERAH, zorder=5)
        ax.set_title("Kurva CDF", fontsize=12, pad=10)
        ax.set_ylabel("Probabilitas Kumulatif", fontsize=10)
        ax.set_ylim(-0.04, 1.06)

    ax.set_xlabel("Pendapatan Harian (Rupiah)", fontsize=10)
    ax.set_xlim(0, 1_150_000)
    ax.xaxis.set_major_formatter(rupiah)
    ax.tick_params(labelsize=9)
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT / f"kurva_{kind}.png", facecolor="white",
                bbox_inches="tight", dpi=300)
    plt.close(fig)
    return penanda


def main():
    df = pd.read_csv(ROOT / "data" / "pendapatan_jukir_liar.csv")
    x = df["pendapatan_harian_rp"].to_numpy(float)
    x = x[x > 0]
    alpha, _, beta = stats.gamma.fit(x, floc=0)
    G = stats.gamma(alpha, loc=0, scale=beta)
    K = beta ** alpha * special.gamma(alpha)     # konstanta penormal

    modus = kurva("pdf", G, alpha, beta)
    median = kurva("cdf", G, alpha, beta)

    # ---- rumus -------------------------------------------------------
    rumus(r"$f(x)=\dfrac{x^{\alpha-1}\,e^{-x/\beta}}"
          r"{\beta^{\alpha}\,\Gamma(\alpha)}$", "rumus_pdf_umum.png")

    rumus(r"$f(x)=\dfrac{x^{2{,}3714}\,e^{-x/89.817}}"
          r"{1{,}4485\times10^{17}}$", "rumus_pdf_isi.png")

    rumus(r"$F(x)=\dfrac{\gamma\left(\alpha,\;x/\beta\right)}{\Gamma(\alpha)}$",
          "rumus_cdf_umum.png")

    rumus(r"$F(x)=\dfrac{\gamma\left(3{,}3714,\;x/89.817\right)}"
          r"{\Gamma(3{,}3714)}$", "rumus_cdf_isi.png")

    # ---- kotak parameter ---------------------------------------------
    fig = plt.figure(figsize=(5.0, 1.25))
    fig.text(0.02, 0.66, r"$\alpha$ = parameter bentuk = ", fontsize=15,
             va="center")
    fig.text(0.615, 0.66, "3,3714", fontsize=15, va="center", fontweight="bold")
    fig.text(0.02, 0.24, r"$\beta$ = parameter skala = ", fontsize=15,
             va="center")
    fig.text(0.585, 0.24, "Rp 89.817", fontsize=15, va="center",
             fontweight="bold")
    fig.savefig(OUT / "parameter.png", transparent=True, bbox_inches="tight",
                pad_inches=0.25, dpi=300)
    plt.close(fig)

    print("Aset poster tersimpan di", OUT)
    for f in sorted(OUT.glob("*.png")):
        print("  -", f.name)
    print()
    print(f"Cek angka: modus (puncak PDF) = Rp {modus:,.0f}")
    print(f"           median (F = 0,50)  = Rp {median:,.0f}")
    print(f"           beta^alpha*Gamma   = {K:.4e}")


if __name__ == "__main__":
    main()
