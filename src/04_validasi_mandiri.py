"""
04_validasi_mandiri.py
======================
Menjalankan sendiri pemeriksaan Lapis 1, 2, dan 4 dari docs/PROMPT_EVALUASI.md,
supaya klaim dalam laporan sudah terverifikasi sebelum diserahkan.

Setiap pemeriksaan mencetak vonis LULUS / PERINGATAN / GAGAL disertai angka.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
TARIF_SAH = {2_000, 5_000, 10_000, 20_000, 30_000}
skor = {"LULUS": 0, "PERINGATAN": 0, "GAGAL": 0}


def vonis(label, status, bukti):
    skor[status] += 1
    tanda = {"LULUS": "[OK]  ", "PERINGATAN": "[WARN]", "GAGAL": "[FAIL]"}[status]
    print(f"{tanda} {label}")
    print(f"        {bukti}")


def main():
    df = pd.read_csv(ROOT / "data" / "pendapatan_jukir_liar.csv")
    x = df["pendapatan_harian_rp"]

    print("=" * 74)
    print("VALIDASI MANDIRI DATASET PENDAPATAN JURU PARKIR LIAR")
    print("=" * 74)

    # ---------------- LAPIS 1: INTEGRITAS STRUKTURAL ----------------
    print("\n--- LAPIS 1: INTEGRITAS STRUKTURAL ---")

    vonis("1.1 Dimensi dataset",
          "LULUS" if df.shape == (300, 5) else "GAGAL",
          f"shape = {df.shape}, diharapkan (300, 5)")

    na = df.isna().sum().sum()
    dup = df.duplicated(subset=["id_jukir", "hari"]).sum()
    vonis("1.2 Nilai hilang & duplikat kunci",
          "LULUS" if na == 0 and dup == 0 else "GAGAL",
          f"NA = {na}, duplikat (id_jukir, hari) = {dup}")

    neg = (x < 0).sum()
    nol = (x == 0).sum()
    vonis("1.3 Nilai negatif / nol",
          "GAGAL" if neg else ("PERINGATAN" if nol else "LULUS"),
          f"negatif = {neg}, nol = {nol}"
          + (f" -> {nol} baris dibuang saat fitting (distribusi butuh x>0)" if nol else ""))

    tipe_ok = (pd.api.types.is_integer_dtype(x)
               and pd.api.types.is_integer_dtype(df["jumlah_kendaraan"]))
    vonis("1.4 Tipe data kolom",
          "LULUS" if tipe_ok else "PERINGATAN",
          f"pendapatan={x.dtype}, jumlah_kendaraan={df['jumlah_kendaraan'].dtype}")

    # ---------------- LAPIS 2: KOHERENSI INTERNAL ----------------
    print("\n--- LAPIS 2: KOHERENSI INTERNAL ---")

    sub = df[df["jumlah_kendaraan"] > 0]
    tarif_implisit = sub["pendapatan_harian_rp"] / sub["jumlah_kendaraan"]
    di_bawah = (tarif_implisit < 2_000 - 1e-9).sum()
    vonis("2.1 Tarif implisit >= Rp 2.000 (tarif terendah)",
          "LULUS" if di_bawah == 0 else "GAGAL",
          f"min = Rp {tarif_implisit.min():,.0f} | median = Rp {tarif_implisit.median():,.0f} "
          f"| maks = Rp {tarif_implisit.max():,.0f} | pelanggaran = {di_bawah}")

    bukan_kelipatan = (x % 1_000 != 0).sum()
    vonis("2.2 Total pendapatan kelipatan Rp 1.000",
          "LULUS" if bukan_kelipatan == 0 else "GAGAL",
          f"baris bukan kelipatan 1.000 = {bukan_kelipatan} dari {len(x)}")

    r_p = df["pendapatan_harian_rp"].corr(df["jumlah_kendaraan"])
    r_s = df["pendapatan_harian_rp"].corr(df["jumlah_kendaraan"], method="spearman")
    vonis("2.3 Konsistensi pendapatan vs jumlah kendaraan",
          "LULUS" if r_p > 0.95 else "GAGAL",
          f"Pearson r = {r_p:.4f} | Spearman rho = {r_s:.4f} (ambang > 0,95)")

    grup = [g["pendapatan_harian_rp"].to_numpy()
            for _, g in df.groupby("hari", sort=False)]
    h_stat, p_kw = stats.kruskal(*grup)
    med = df.groupby("hari")["pendapatan_harian_rp"].median()
    vonis("2.4 Efek hari dalam seminggu (Kruskal-Wallis)",
          "LULUS" if p_kw < 0.05 else "PERINGATAN",
          f"H = {h_stat:.3f}, p = {p_kw:.4f} | median Jumat Rp {med.get('Jumat', 0):,.0f} "
          f"vs Senin Rp {med.get('Senin', 0):,.0f}"
          + ("" if p_kw < 0.05 else "  -> efek hari TIDAK terdeteksi meski dimodelkan"))

    # ICC(1): proporsi ragam yang berasal dari perbedaan antar-jukir
    k = df.groupby("id_jukir").size().mean()
    rata_grup = df.groupby("id_jukir")["pendapatan_harian_rp"].mean()
    ms_antar = k * rata_grup.var(ddof=1)
    ms_dalam = df.groupby("id_jukir")["pendapatan_harian_rp"].var(ddof=1).mean()
    icc = (ms_antar - ms_dalam) / (ms_antar + (k - 1) * ms_dalam)
    vonis("2.5 Independensi observasi (ICC antar-jukir)",
          "PERINGATAN" if icc > 0.10 else "LULUS",
          f"ICC = {icc:.3f} -> {icc*100:.1f}% ragam berasal dari perbedaan antar-jukir. "
          f"n efektif ~ {len(df)/(1+(k-1)*icc):.0f}, bukan {len(df)}")

    # ---------------- LAPIS 3: KEWAJARAN vs DUNIA NYATA ----------------
    print("\n--- LAPIS 3: KEWAJARAN TERHADAP JANGKAR PUBLIK ---")
    jangkar = [
        ("mean vs Litbang Kompas (Rp 286.500/hari/jukir)", x.mean(), 286_500),
        ("median vs Andy Nugroho bersih (Rp 250.000)", x.median(), 250_000),
        ("p90 vs omzet 1 titik (Rp 573.000/hari)", x.quantile(.90), 573_000),
    ]
    for label, nilai, target in jangkar:
        selisih = abs(nilai - target) / target * 100
        vonis(f"3.x {label}",
              "LULUS" if selisih <= 25 else "PERINGATAN",
              f"data = Rp {nilai:,.0f} | jangkar = Rp {target:,.0f} | selisih = {selisih:.1f}%")

    tarif_rata = x.sum() / df["jumlah_kendaraan"].sum()
    kend_maks = df.loc[x.idxmax(), "jumlah_kendaraan"]
    vonis("3.2 Batas fisik nilai maksimum",
          "PERINGATAN" if kend_maks / 10 > 40 else "LULUS",
          f"maks = Rp {x.max():,.0f} dari {kend_maks} kendaraan "
          f"= {kend_maks/10:.1f} kendaraan/jam bila kerja 10 jam "
          f"(tarif efektif rata-rata Rp {tarif_rata:,.0f})")

    # ---------------- LAPIS 4: KEKOKOHAN KLAIM DISTRIBUSI ----------------
    print("\n--- LAPIS 4: KEKOKOHAN KLAIM DISTRIBUSI ---")
    xa = x[x > 0].to_numpy(float)

    def aic(dist, data, **kw):
        p = dist.fit(data, **kw)
        k_par = len(p) - (1 if "floc" in kw else 0)
        return 2 * k_par - 2 * np.sum(dist.logpdf(data, *p)), p

    kandidat = [("Gamma", stats.gamma, {"floc": 0}),
                ("Gumbel", stats.gumbel_r, {}),
                ("Lognormal", stats.lognorm, {"floc": 0}),
                ("Weibull", stats.weibull_min, {"floc": 0}),
                ("Normal", stats.norm, {})]

    penuh = sorted(((aic(d, xa, **kw)[0], n) for n, d, kw in kandidat))
    vonis("4.1 Peringkat AIC pada data penuh",
          "LULUS" if penuh[0][1] == "Gamma" else "GAGAL",
          " < ".join(f"{n} ({a:,.1f})" for a, n in penuh[:3]))

    d_aic = penuh[1][0] - penuh[0][0]
    vonis("4.2 Ketegasan pemenang (delta-AIC juara vs runner-up)",
          "PERINGATAN" if d_aic < 4 else "LULUS",
          f"delta-AIC = {d_aic:.2f} vs {penuh[1][1]}. "
          + ("delta < 4 -> kedua model TIDAK terbedakan secara meyakinkan; "
             "klaim harus ditulis sebagai 'Gamma paling didukung', bukan 'Gamma benar'."
             if d_aic < 4 else "Pemenang tegas."))

    potong = xa[xa <= np.quantile(xa, 0.95)]
    dipangkas = sorted(((aic(d, potong, **kw)[0], n) for n, d, kw in kandidat))
    vonis("4.5 Kekokohan setelah 5% nilai teratas dibuang",
          "LULUS" if dipangkas[0][1] == penuh[0][1] else "PERINGATAN",
          f"pemenang jadi {dipangkas[0][1]} (semula {penuh[0][1]}); "
          f"n turun {len(xa)} -> {len(potong)}")

    # ---------------- RINGKASAN ----------------
    print("\n" + "=" * 74)
    print(f"RINGKASAN: {skor['LULUS']} LULUS | {skor['PERINGATAN']} PERINGATAN "
          f"| {skor['GAGAL']} GAGAL")
    if skor["GAGAL"]:
        print("VONIS: TIDAK VALID -- ada pemeriksaan yang gagal, perbaiki dahulu.")
    elif skor["PERINGATAN"]:
        print("VONIS: VALID DENGAN SYARAT -- lihat butir PERINGATAN di atas.")
        print("       Syarat utama: (a) sifat sintetis data disebut eksplisit,")
        print("       (b) klaim distribusi ditulis sebagai dukungan relatif, bukan kebenaran,")
        print("       (c) ketergantungan antar-hari pada jukir yang sama diakui.")
    else:
        print("VONIS: VALID untuk tujuan yang dinyatakan.")
    print("=" * 74)
    print("\nCatatan: Lapis 5 (kejujuran epistemik) TIDAK dapat diotomatiskan.")
    print("Jalankan docs/PROMPT_EVALUASI.md pada LLM untuk lapis tersebut.")


if __name__ == "__main__":
    main()
