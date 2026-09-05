# Prompt Evaluasi Validitas Data

Prompt ini dipakai untuk **menguji apakah dataset pendapatan harian juru parkir
liar layak dipakai** sebagai dasar permodelan & simulasi. Salin seluruh blok di
bawah ke Claude / ChatGPT / LLM lain, **lampirkan** `data/pendapatan_jukir_liar.csv`
dan `output/hasil_uji_distribusi.csv`, lalu jalankan.

Prompt sengaja disusun agar evaluator **mencari alasan untuk MENOLAK** data,
bukan mencari alasan untuk menerimanya. Prompt yang meminta "tolong cek apakah
data ini valid" hampir selalu dijawab "valid" — itu bias konfirmasi, bukan
evaluasi.

---

## PROMPT

````text
PERAN
Anda adalah penguji (reviewer) metodologi statistik untuk mata kuliah
Permodelan & Simulasi. Tugas Anda BUKAN membantu saya lulus, melainkan
menemukan cacat pada data dan analisis saya. Asumsikan ada kesalahan sampai
terbukti sebaliknya. Jika Anda tidak menemukan cacat apa pun, sebutkan secara
eksplisit apa yang sudah Anda periksa sehingga saya tahu Anda benar-benar
mencari.

BAHAN
1. data/pendapatan_jukir_liar.csv
   kolom: id_jukir, tipe_lokasi, hari, jumlah_kendaraan, pendapatan_harian_rp
2. output/hasil_uji_distribusi.csv  (hasil uji kecocokan distribusi)
3. Klaim saya: pendapatan harian juru parkir liar mengikuti DISTRIBUSI GAMMA
   dengan shape (alpha) = 3,3714 dan scale (beta) = 89.817, loc = 0.
4. Dataset ini adalah *calibrated process model* (Monte Carlo), BUKAN survei
   lapangan. Parameternya dikalibrasi terhadap angka publik berikut:
   - Rp 200.000/hari  (100 kendaraan x Rp 2.000) — CELIOS via detikFinance
   - Rp 400.000/hari kotor; Rp 250.000/hari bersih — Andy Nugroho via detikFinance
   - Rp 17.190.000/bulan per titik minimarket (= Rp 573.000/hari/titik;
     Rp 286.500/hari/jukir bila 2 orang) — Litbang Kompas via Tirto
   - Tarif Pergub DKI 31/2017: motor Rp 2.000, mobil Rp 5.000

JALANKAN LIMA LAPIS PEMERIKSAAN BERIKUT, BERURUTAN.
Untuk setiap butir beri vonis: LULUS / PERINGATAN / GAGAL, disertai angka.
Jangan menilai "kelihatannya wajar" — hitung.

--- LAPIS 1: INTEGRITAS STRUKTURAL ---
1.1  Berapa baris, berapa kolom? Cocok dengan yang saya klaim (300 x 5)?
1.2  Ada nilai hilang (NA), duplikat baris, atau id_jukir ganda pada hari sama?
1.3  Ada nilai negatif atau nol pada pendapatan_harian_rp?
     Nol itu mungkin secara fisik, tapi apakah ada di data? Jika ada, apakah
     analisis distribusi (yang butuh x > 0) menanganinya?
1.4  Apakah tipe data tiap kolom benar (pendapatan integer, hari kategorikal)?

--- LAPIS 2: KOHERENSI INTERNAL (yang paling sering terlewat) ---
2.1  Hitung tarif implisit = pendapatan_harian_rp / jumlah_kendaraan untuk
     tiap baris. Sebarannya harus masuk akal terhadap tarif Rp 2.000–5.000
     dengan sedikit ekor ke atas (pungutan menyimpang).
     - Berapa min, median, maks tarif implisit?
     - Adakah baris dengan tarif implisit < Rp 2.000? Itu MUSTAHIL bila tarif
       terendah adalah Rp 2.000. Kalau ada, data cacat.
     - Adakah tarif implisit > Rp 10.000 yang tak terjelaskan?
2.2  Apakah pendapatan_harian_rp selalu kelipatan Rp 1.000? Bila tarif hanya
     Rp 2.000/5.000/10.000/20.000/30.000, seluruh total HARUS kelipatan 1.000.
     Bila ada yang tidak, ada kebocoran dalam pembangkitan data.
2.3  Uji hubungan pendapatan vs jumlah_kendaraan: hitung korelasi Pearson dan
     Spearman. Korelasi harus sangat tinggi (> 0,95). Bila rendah, kedua kolom
     tidak konsisten satu sama lain.
2.4  Efek hari: apakah Jumat benar-benar lebih tinggi dari Senin? Uji dengan
     Kruskal-Wallis. Bila model mengklaim ada efek hari tapi uji tidak
     menemukannya, klaim itu tidak terdukung data.
2.5  Efek jukir: hitung intraclass correlation (ICC) antar id_jukir. Karena
     tiap jukir diamati 5 hari, observasi TIDAK independen. Seberapa besar
     pelanggaran independensi ini?

--- LAPIS 3: KEWAJARAN TERHADAP DUNIA NYATA ---
3.1  Bandingkan mean, median, p10, p90 data dengan empat jangkar publik di
     atas. Hitung selisih persentase tiap jangkar. Mana yang meleset > 25%?
3.2  Nilai maksimum dalam data: apakah masih dalam batas fisik yang mungkin?
     Bila maksimum Rp 971.000 dengan tarif rata-rata ~Rp 2.650, itu berarti
     ~366 kendaraan/hari = ~37 kendaraan/jam selama 10 jam. Mungkinkah untuk
     satu orang jukir? Berikan penilaian, bukan asumsi.
3.3  Bandingkan implikasi bulanan (pendapatan harian x 26 hari kerja) dengan
     UMP DKI Jakarta tahun berjalan. Apakah kesimpulannya konsisten dengan
     temuan Litbang Kompas dan CELIOS, atau justru melebih-lebihkan?
3.4  Apa yang TIDAK ditangkap model ini? Sebutkan minimal empat, misalnya:
     setoran ke preman/oknum, musim/cuaca hujan, razia Dishub, hari libur,
     shift malam, lokasi wisata musiman. Seberapa besar dampaknya terhadap
     kesimpulan?

--- LAPIS 4: VERIFIKASI KLAIM DISTRIBUSI ---
4.1  Fit ulang SENDIRI keenam distribusi (Normal, Lognormal, Gamma, Weibull,
     Eksponensial, Gumbel) dengan MLE. Apakah Anda mendapat parameter yang
     sama? Apakah Gamma tetap peringkat 1 menurut AIC?
4.2  Selisih AIC Gamma vs Gumbel hanya ~2,0 (bobot Akaike 0,73 vs 0,27).
     Apakah jujur menyebut Gamma "distribusi yang benar", atau seharusnya
     disebut "tidak terbedakan secara meyakinkan dari Gumbel"? Beri vonis.
4.3  Periksa apakah p-value KS dihitung dengan cara yang benar. Karena
     parameter diestimasi dari data yang sama, p-value KS baku terlalu besar
     (konservatif). Apakah analisis saya memakai parametric bootstrap? Bila
     ya, apakah 1.000 replikasi cukup?
4.4  Lihat Q-Q plot. Di kuantil mana penyimpangan terbesar terjadi — ekor
     bawah, tengah, atau ekor atas? Jelaskan artinya secara substantif.
4.5  Uji kekokohan: buang 5% nilai tertinggi lalu fit ulang. Apakah Gamma
     masih menang? Bila kesimpulan berubah, berarti kesimpulan digerakkan
     oleh segelintir outlier.

--- LAPIS 5: KEJUJURAN EPISTEMIK (paling penting) ---
5.1  Ini pertanyaan inti: data ini dibangkitkan oleh model Gamma-Poisson.
     Menemukan bahwa data cocok dengan distribusi Gamma karena itu bersifat
     SEBAGIAN TAUTOLOGIS — hasilnya sudah tertanam dalam cara data dibuat.
     Nyatakan secara eksplisit: seberapa besar temuan ini mengandung
     informasi tentang DUNIA NYATA, dan seberapa besar hanya memantulkan
     kembali asumsi saya sendiri?
5.2  Apa yang HARUS diukur di lapangan agar klaim ini bisa diuji sungguhan?
     Rancang protokol pengumpulan data minimum: berapa titik, berapa hari,
     variabel apa saja, bagaimana teknik pencatatannya, dan risiko etis/
     keamanan apa yang perlu diantisipasi saat mengamati aktivitas informal.
5.3  Bila data ini dipakai untuk merekomendasikan kebijakan (misalnya
     penertiban atau formalisasi jukir), kesalahan apa yang paling berbahaya
     yang bisa timbul dari kelemahan data ini?
5.4  Beri satu kalimat penilaian akhir yang jujur: untuk keperluan apa
     dataset ini SAH dipakai, dan untuk keperluan apa TIDAK BOLEH dipakai?

FORMAT KELUARAN
A. Tabel vonis: | Butir | Vonis | Angka bukti | Catatan |
B. Tiga cacat paling serius, diurutkan menurut tingkat keparahan.
C. Vonis akhir, pilih tepat satu:
   - VALID untuk tujuan yang dinyatakan
   - VALID DENGAN SYARAT (sebutkan syaratnya)
   - TIDAK VALID (sebutkan alasan yang menggugurkan)
D. Daftar perbaikan konkret, diurutkan menurut rasio dampak/usaha.

ATURAN
- Jangan memuji. Jangan menulis kalimat pembuka basa-basi.
- Setiap vonis wajib disertai angka. "Sepertinya wajar" tidak diterima.
- Bila Anda tidak bisa menghitung sesuatu dari bahan yang ada, katakan
  "tidak dapat diverifikasi dari bahan yang diberikan" — jangan menebak.
- Bila klaim saya benar, katakan benar. Bersikap skeptis bukan berarti
  bersikap negatif.
````

---

## Cara memakai

1. Buka Claude / ChatGPT.
2. Lampirkan `data/pendapatan_jukir_liar.csv` dan `output/hasil_uji_distribusi.csv`.
3. Salin blok PROMPT di atas (mulai dari `PERAN` sampai baris terakhir `ATURAN`).
4. Minta evaluator menjalankan kode (Code Interpreter/Analysis tool) untuk
   Lapis 1, 2, dan 4 — jangan biarkan ia menjawab dari "kesan" saja.

## Mengapa prompt ini disusun begini

| Prinsip | Penerapannya di sini |
|---|---|
| **Peran adversarial** | Evaluator diminta mencari cacat, bukan mengonfirmasi. Menghindari sycophancy LLM. |
| **Berlapis** | Struktur → koherensi internal → realitas → statistik → epistemik. Cacat murah ketahuan dulu sebelum yang mahal. |
| **Wajib berangka** | Tiap vonis harus disertai bukti kuantitatif, sehingga tidak bisa dijawab dengan kalimat kosong. |
| **Uji falsifikasi** | Butir 2.1, 2.2, 4.5 dirancang punya jawaban yang bisa SALAH — itulah yang membuatnya uji, bukan formalitas. |
| **Menyebut kelemahan sendiri** | Lapis 5.1 memaksa membahas sifat tautologis data sintetis. Kelemahan terbesar tugas ini disebut sendiri, tidak disembunyikan. |
| **Keluaran terstruktur** | Tabel + vonis tunggal + daftar perbaikan; mudah dinilai dosen, sulit dikaburkan. |
