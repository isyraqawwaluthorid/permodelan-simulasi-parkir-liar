"""
02_uji_distribusi.py
====================
Mengidentifikasi NAMA DISTRIBUSI yang paling cocok untuk pendapatan harian
juru parkir liar.

Metode:
  1. Fit MLE untuk 6 distribusi kandidat.
  2. Uji Kolmogorov-Smirnov (KS) dan Anderson-Darling (AD).
     Catatan metodologis: parameter diestimasi dari data yang sama, sehingga
     p-value KS baku bersifat KONSERVATIF (terlalu besar). Karena itu kami
     juga menghitung p-value via PARAMETRIC BOOTSTRAP (Lilliefors-style),
     yang merupakan prosedur yang benar untuk kasus parameter diestimasi.
  3. Peringkat model dengan AIC dan BIC.
  4. Keputusan akhir memadukan bukti statistik + kelayakan teoretis.

Output: output/hasil_uji_distribusi.csv, output/ringkasan.json
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

SEED = 42
N_BOOTSTRAP = 1000
ROOT = Path(__file__).resolve().parents[1]

# Distribusi kandidat: (nama, objek scipy, argumen fit tambahan)
KANDIDAT = [
    ("Normal",     stats.norm,      {}),
    ("Lognormal",  stats.lognorm,   {"floc": 0}),   # loc=0 -> lognormal 2-parameter
    ("Gamma",      stats.gamma,     {"floc": 0}),
    ("Weibull",    stats.weibull_min, {"floc": 0}),
    ("Eksponensial", stats.expon,   {"floc": 0}),
    ("Gumbel",     stats.gumbel_r,  {}),
]


def anderson_darling(data, dist, params):
    """Statistik Anderson-Darling A^2 terhadap CDF yang sudah di-fit.

    A^2 memberi bobot lebih besar pada EKOR distribusi dibanding KS, sehingga
    lebih sensitif terhadap ketidakcocokan di bagian ekor -- penting di sini
    karena pendapatan jukir punya ekor kanan yang panjang.
    """
    n = len(data)
    u = np.sort(dist.cdf(data, *params))
    u = np.clip(u, 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    s = np.sum((2 * i - 1) * (np.log(u) + np.log(1 - u[::-1])))
    return -n - s / n


def bootstrap_ks_pvalue(data, dist, fit_kwargs, params, n_boot=N_BOOTSTRAP, seed=SEED):
    """p-value KS via parametric bootstrap (parameter diestimasi ulang tiap replikasi)."""
    rng = np.random.default_rng(seed)
    n = len(data)
    d_obs = stats.kstest(data, dist.name, args=params).statistic

    count = 0
    for _ in range(n_boot):
        sampel = dist.rvs(*params, size=n, random_state=rng)
        try:
            p_boot = dist.fit(sampel, **fit_kwargs)
        except Exception:
            continue
        d_boot = stats.kstest(sampel, dist.name, args=p_boot).statistic
        if d_boot >= d_obs:
            count += 1
    return d_obs, (count + 1) / (n_boot + 1)


def main():
    df = pd.read_csv(ROOT / "data" / "pendapatan_jukir_liar.csv")
    x = df["pendapatan_harian_rp"].to_numpy(dtype=float)
    x = x[x > 0]                       # distribusi positif memerlukan x > 0
    n = len(x)

    print("=" * 78)
    print("UJI KECOCOKAN DISTRIBUSI — PENDAPATAN HARIAN JURU PARKIR LIAR")
    print("=" * 78)
    print(f"n = {n} | mean = Rp {x.mean():,.0f} | median = Rp {np.median(x):,.0f}")
    print(f"skewness = {stats.skew(x):.3f} | kurtosis (excess) = {stats.kurtosis(x):.3f}\n")

    hasil = []
    for nama, dist, fit_kwargs in KANDIDAT:
        params = dist.fit(x, **fit_kwargs)
        k = len([p for p in params if p != 0]) if fit_kwargs.get("floc") == 0 else len(params)
        k = len(params) - (1 if "floc" in fit_kwargs else 0)   # loc tetap -> bukan parameter bebas

        loglik = np.sum(dist.logpdf(x, *params))
        aic = 2 * k - 2 * loglik
        bic = k * np.log(n) - 2 * loglik

        d_stat, p_boot = bootstrap_ks_pvalue(x, dist, fit_kwargs, params)
        p_asym = stats.kstest(x, dist.name, args=params).pvalue

        ad = anderson_darling(x, dist, params)

        hasil.append({
            "distribusi": nama,
            "parameter": ", ".join(f"{p:,.4g}" for p in params),
            "k": k,
            "loglik": loglik,
            "AIC": aic,
            "BIC": bic,
            "KS_D": d_stat,
            "KS_p_asimtotik": p_asym,
            "KS_p_bootstrap": p_boot,
            "AD_A2": ad,
        })

    res = pd.DataFrame(hasil).sort_values("AIC").reset_index(drop=True)
    res["dAIC"] = res["AIC"] - res["AIC"].min()
    # Akaike weight: probabilitas relatif tiap model
    w = np.exp(-0.5 * res["dAIC"])
    res["bobot_Akaike"] = w / w.sum()

    pd.set_option("display.width", 200)
    print("--- Peringkat model (diurutkan menurut AIC) ---")
    print(res[["distribusi", "AIC", "dAIC", "bobot_Akaike",
               "KS_D", "KS_p_bootstrap", "AD_A2"]].to_string(
        index=False,
        formatters={"AIC": "{:,.1f}".format, "dAIC": "{:,.2f}".format,
                    "bobot_Akaike": "{:.4f}".format, "KS_D": "{:.4f}".format,
                    "KS_p_bootstrap": "{:.4f}".format, "AD_A2": "{:.4f}".format}))

    terbaik = res.iloc[0]
    print(f"\n>> DISTRIBUSI TERPILIH: {terbaik['distribusi']}")
    print(f"   parameter      : {terbaik['parameter']}")
    print(f"   AIC            : {terbaik['AIC']:,.1f}")
    print(f"   KS D           : {terbaik['KS_D']:.4f}")
    print(f"   KS p (bootstrap): {terbaik['KS_p_bootstrap']:.4f}"
          f"  -> {'TIDAK ditolak' if terbaik['KS_p_bootstrap'] > 0.05 else 'DITOLAK'} pada alfa = 0,05")

    # Parameter lognormal dalam bentuk mu & sigma yang mudah dibaca
    s, loc, scale = stats.lognorm.fit(x, floc=0)
    print(f"\n   Bentuk baku Lognormal: ln(X) ~ N(mu, sigma^2)")
    print(f"     mu    = ln(scale) = {np.log(scale):.4f}")
    print(f"     sigma = {s:.4f}")
    print(f"     median teoretis = exp(mu)          = Rp {np.exp(np.log(scale)):,.0f}")
    print(f"     mean   teoretis = exp(mu+sigma^2/2) = Rp {np.exp(np.log(scale)+s**2/2):,.0f}")

    outdir = ROOT / "output"
    outdir.mkdir(exist_ok=True)
    res.to_csv(outdir / "hasil_uji_distribusi.csv", index=False)

    ringkasan = {
        "n": int(n),
        "mean": float(x.mean()),
        "median": float(np.median(x)),
        "std": float(x.std(ddof=1)),
        "skewness": float(stats.skew(x)),
        "kurtosis_excess": float(stats.kurtosis(x)),
        "distribusi_terpilih": terbaik["distribusi"],
        "parameter": terbaik["parameter"],
        "lognormal_mu": float(np.log(scale)),
        "lognormal_sigma": float(s),
        "KS_D": float(terbaik["KS_D"]),
        "KS_p_bootstrap": float(terbaik["KS_p_bootstrap"]),
        "AIC": float(terbaik["AIC"]),
    }
    (outdir / "ringkasan.json").write_text(json.dumps(ringkasan, indent=2))
    print(f"\nHasil lengkap: {outdir/'hasil_uji_distribusi.csv'}")


if __name__ == "__main__":
    main()
