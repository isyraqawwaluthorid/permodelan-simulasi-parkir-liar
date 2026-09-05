"""
01_generate_dataset.py
======================
Membangun dataset PENDAPATAN HARIAN JURU PARKIR LIAR (Rp/hari/jukir).

STATUS DATA
-----------
Data mikro (per-jukir, per-hari) untuk aktivitas parkir liar TIDAK tersedia
sebagai open data -- aktivitasnya informal dan tidak tercatat resmi. Yang
tersedia publik hanyalah ANGKA AGREGAT dari liputan media, riset Litbang, dan
laporan Dishub.

Karena itu dataset di sini dibangun dengan pendekatan *calibrated process
model* (Monte Carlo): proses fisik pungutan parkir disimulasikan, lalu
parameternya DIKALIBRASI agar statistik ringkasannya cocok dengan angka
publik yang terverifikasi. Ini praktik standar dalam permodelan & simulasi
ketika data mikro tidak tersedia.

Dataset ini BUKAN hasil sensus dan BUKAN data resmi. Dataset ini adalah
realisasi dari model proses yang jangkarnya adalah data publik di bawah.

JANGKAR KALIBRASI (public anchors)
----------------------------------
A1. Rp 200.000/hari  -- asumsi 100 kendaraan x Rp 2.000
    Nailul Huda (CELIOS), via detikFinance 2024
A2. Rp 400.000/hari kotor; Rp 250.000/hari bersih setelah setoran ~Rp 150.000
    Andy Nugroho (perencana keuangan), via detikFinance 2024
A3. Rp 17.190.000/bulan omzet kotor satu titik minimarket
    => Rp 573.000/hari/titik; jika dikelola 2 jukir => Rp 286.500/hari/jukir
    Litbang Kompas, via Tirto 2026
A4. Tarif rujukan Pergub DKI 31/2017: motor Rp 2.000, mobil Rp 5.000
A5. Pungutan menyimpang terdokumentasi: Rp 10.000 (Bundaran HI, Juli 2025),
    Rp 30.000 (Bandung, Okt 2025), Rp 60.000-100.000 (Tanah Abang, Feb 2026)
    -> dimodelkan sebagai kejadian jarang (heavy right tail)

TARGET KALIBRASI
----------------
median  ~ Rp 250.000   (A2 bersih)
mean    ~ Rp 285.000   (A3 per-jukir)
p10     ~ Rp 120.000   (titik sepi)
p90     ~ Rp 520.000   (titik ramai, mendekati A3 per-titik)

STRUKTUR PROSES
---------------
Untuk setiap observasi (satu jukir, satu hari):
  1. Tipe lokasi ditarik dari distribusi kategori.
  2. Intensitas kedatangan harian lambda ~ Gamma(k, theta) per tipe lokasi.
     (Gamma mixing pada Poisson => Negative Binomial: menangkap heterogenitas
      antar-lokasi, bukan sekadar keacakan hari.)
  3. Jumlah kendaraan N ~ Poisson(lambda * faktor_hari).
  4. Tiap kendaraan: motor atau mobil (proporsi per tipe lokasi),
     bayar tarif normal, atau -- dengan peluang kecil -- pungutan menyimpang.
  5. Pendapatan harian = total pungutan.

Struktur berlapis ini (Gamma-Poisson + campuran tarif) secara teoretis
menghasilkan distribusi bernilai positif dan menceng-kanan; hipotesis awal
kami adalah LOGNORMAL. Skrip 02 yang mengujinya secara formal.

Output: data/pendapatan_jukir_liar.csv
Seed tetap (42) => dataset selalu identik dan dapat direproduksi.
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 42
N_JUKIR = 60          # jumlah juru parkir yang "diamati"
N_HARI = 5            # hari pengamatan per jukir
N_OBS = N_JUKIR * N_HARI   # 300 observasi jukir-hari

rng = np.random.default_rng(SEED)

# --- 1. Tipe lokasi -----------------------------------------------------
# proporsi, Gamma(shape, scale) untuk lambda kendaraan/hari, proporsi mobil
TIPE_LOKASI = {
    "Minimarket":        dict(p=0.45, shape=5.5, scale=17.0, p_mobil=0.10),
    "Ruko/Pertokoan":    dict(p=0.25, shape=5.0, scale=21.0, p_mobil=0.22),
    "Pasar/Kuliner":     dict(p=0.20, shape=4.5, scale=27.5, p_mobil=0.18),
    "Kawasan Komersial": dict(p=0.10, shape=4.0, scale=36.0, p_mobil=0.35),
}

# --- 2. Tarif (Rp) ------------------------------------------------------
TARIF_MOTOR = 2_000
TARIF_MOBIL = 5_000
P_MENYIMPANG = 0.02                                  # peluang pungutan tidak wajar
TARIF_MENYIMPANG = np.array([10_000, 20_000, 30_000])
P_TARIF_MENYIMPANG = np.array([0.70, 0.22, 0.08])

# --- 3. Efek hari dalam seminggu ---------------------------------------
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
FAKTOR_HARI = {"Senin": 0.92, "Selasa": 0.95, "Rabu": 0.98,
               "Kamis": 1.02, "Jumat": 1.18}


def simulasi_satu_hari(cfg, faktor_hari):
    """Simulasikan satu hari kerja seorang jukir. Return (pendapatan, n_kendaraan)."""
    lam = rng.gamma(cfg["shape"], cfg["scale"]) * faktor_hari
    n = rng.poisson(lam)
    if n == 0:
        return 0, 0

    is_mobil = rng.random(n) < cfg["p_mobil"]
    tarif = np.where(is_mobil, TARIF_MOBIL, TARIF_MOTOR).astype(float)

    # sebagian kecil kendaraan dipungut tarif tidak wajar
    menyimpang = rng.random(n) < P_MENYIMPANG
    if menyimpang.any():
        tarif[menyimpang] = rng.choice(
            TARIF_MENYIMPANG, size=menyimpang.sum(), p=P_TARIF_MENYIMPANG
        )
    return int(tarif.sum()), int(n)


def main():
    nama_tipe = list(TIPE_LOKASI)
    prob_tipe = [TIPE_LOKASI[t]["p"] for t in nama_tipe]

    baris = []
    for j in range(1, N_JUKIR + 1):
        tipe = rng.choice(nama_tipe, p=prob_tipe)
        cfg = TIPE_LOKASI[tipe]
        # "personal effect": kualitas titik masing-masing jukir, tetap lintas hari
        mutu_titik = rng.lognormal(mean=0.0, sigma=0.28)
        cfg_jukir = dict(cfg, scale=cfg["scale"] * mutu_titik)

        for hari in HARI:
            pendapatan, n_kend = simulasi_satu_hari(cfg_jukir, FAKTOR_HARI[hari])
            baris.append({
                "id_jukir": f"JKR-{j:03d}",
                "tipe_lokasi": tipe,
                "hari": hari,
                "jumlah_kendaraan": n_kend,
                "pendapatan_harian_rp": pendapatan,
            })

    df = pd.DataFrame(baris)

    out = Path(__file__).resolve().parents[1] / "data" / "pendapatan_jukir_liar.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)

    x = df["pendapatan_harian_rp"]
    print(f"Dataset tersimpan: {out}")
    print(f"n = {len(df)} observasi (jukir-hari)\n")
    print("=== Statistik Deskriptif Pendapatan Harian (Rp) ===")
    print(f"  mean    : {x.mean():>12,.0f}   (target A3: ~285.000)")
    print(f"  median  : {x.median():>12,.0f}   (target A2: ~250.000)")
    print(f"  std dev : {x.std(ddof=1):>12,.0f}")
    print(f"  min     : {x.min():>12,.0f}")
    print(f"  p10     : {x.quantile(.10):>12,.0f}   (target: ~120.000)")
    print(f"  p90     : {x.quantile(.90):>12,.0f}   (target: ~520.000)")
    print(f"  max     : {x.max():>12,.0f}")
    print(f"  skewness: {x.skew():>12.3f}")
    print(f"  kurtosis: {x.kurt():>12.3f}")
    print(f"  CV      : {x.std(ddof=1)/x.mean():>12.3f}")


if __name__ == "__main__":
    main()
