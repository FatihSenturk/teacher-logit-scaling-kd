# B2 — §5.3'ün iki regresyon doğrusu: üreticisi ve spesifikasyonu

Üretici: `diagnostics/regression_line_provenance.py` · fit ve öğretmen ECE'leri `b015_verdict.py`'den **ithal** (`linfit`, `TEACHER`, `RAFDB_FIT`)

> İki doğru için iki ayrı cevap çıktı. Biri yayımlanabilir bir spesifikasyona sahip ama **yanlış checkpoint'te** fit edilmiş; diğerinin **üreticisi yok**.

| doğru | hüküm |
|---|---|
| FERPlus **0.582** | ✅ üreticisi var — `b015_verdict.py`, havuzlanmış OLS, **@best** |
| RAF-DB **0.765** | ❌ **üreticisi yok** — sabit olarak yazılı, hiçbir betik hesaplamıyor |

---

## 1 · FERPlus — tam spesifikasyon

| alan | değer |
|---|---|
| üretici | `diagnostics/b015_verdict.py` (ön-kayıt B-015, 2026-07-26 13:27:26) |
| yordayıcı | öğretmen ECE (ölçeklenmiş öğretmenin kendi ECE'si) |
| yanıt | öğrenci ECE |
| kollar | T ∈ {0.26, 0.5063, 1.0} — B-017'nin T=0.74 kolu **kapsam dışı** (ayrı ön-kayıt) |
| n | 9 koşu (3 kol × 3 tohum), havuzlanmış |
| ağırlıklandırma | yok — düz OLS |
| **checkpoint** | **@best** |

| checkpoint | eğim | kesme | Pearson | R² (9 koşu) | R² (3 grup ort.) |
|---|---|---|---|---|---|
| @swa ← **makalenin birincil checkpoint'i** | **0.4458** | +0.02464 | +0.8621 | 0.7431 | 0.7534 |
| @best ← **yayımlı** | **0.5824** | +0.02083 | +0.9388 | 0.8814 | 0.8934 |
| @last | **0.5062** | +0.02356 | +0.8894 | 0.7910 | 0.8164 |

> **Karşı-doğrulayıcının bulamamasının sebebi çok muhtemelen checkpoint.** Yayımlanan 0.582 @best'ten geliyor; makalenin birincil checkpoint'i @swa ve orada aynı fit **0.446** veriyor (%23 fark). Cümlede checkpoint yazmıyor.

> R² itirazı **ölçüldü**: 9 koşu üzerinde R² = 0.8814, 3 grup ortalaması üzerinde 0.8934. En büyük artık 0.0131, o hücrenin tohum sd'sinin **9.5 katı**.

| T | rol | öğretmen ECE | öğrenci ECE (ort ± sd) | n | artık | artık / tohum sd |
|---|---|---|---|---|---|---|
| 0.5063 | T*_NLL (calibrated) | 0.0156 | 0.0196 ± 0.0020 | 3 | -0.0103 | 5.1× |
| 0.26 | over-sharpened (sign flipped) | 0.0393 | 0.0568 ± 0.0014 | 3 | +0.0131 | 9.5× |
| 1.0 | native (under-confident) | 0.1282 | 0.0927 ± 0.0070 | 3 | -0.0028 | 0.4× |

---

## 2 · RAF-DB — **üreticisi yok**

Sayı `diagnostics/b015_verdict.py:68`'de bir **sabit**:

```python
# RAF-DB's fitted law, for the cross-dataset comparison
RAFDB_FIT = {"intercept": 0.0244, "slope": 0.7653}
```

Deponun hiçbir yerinde bu iki sayıyı hesaplayan bir kod yok; yalnız veri-kümeleri-arası karşılaştırma satırında **basılıyor**. Kaç noktadan, hangi checkpoint'te, hangi sınıf-ağırlığında fit edildiği kayıtlı değil — kayıtlı olan tek yan bilgi "Pearson +0.992, 3 teachers" yorumu.

Bu betik defterden sistematik olarak aradı: **18 spesifikasyon** (2 denetim dosyası × 3 checkpoint × 3 sınıf-ağırlığı seçeneği), her biri üç öğretmenin T=1 ECE'sine karşı kontrol kolunun öğrenci ECE'si.

| ölçüm | değer |
|---|---|
| üretilen eğim aralığı | **1.3522 … 1.8744** |
| hedef | 0.7653 |
| en yakın spesifikasyon | 1.3522 (`frozen / @best / effective_number`), **%77 uzak** |
| üretici bulundu mu | **HAYIR** |

| denetim | ckpt | sınıf ağırlığı | eğim | kesme | R² | hedeften uzaklık |
|---|---|---|---|---|---|---|
| frozen | @best | `effective_number` | 1.3522 | +0.00927 | 0.9873 | %77 |
| mechanism (unfrozen) | @best | `effective_number` | 1.3522 | +0.00927 | 0.9873 | %77 |
| frozen | @swa | `effective_number` | 1.5394 | +0.01228 | 0.9868 | %101 |
| mechanism (unfrozen) | @swa | `effective_number` | 1.5394 | +0.01228 | 0.9868 | %101 |
| frozen | @last | `effective_number` | 1.5599 | +0.00969 | 0.9964 | %104 |
| mechanism (unfrozen) | @last | `effective_number` | 1.5599 | +0.00969 | 0.9964 | %104 |
| frozen | @best | `havuz (iki mod ort.)` | 1.5823 | +0.00357 | 0.9995 | %107 |
| mechanism (unfrozen) | @best | `havuz (iki mod ort.)` | 1.5823 | +0.00357 | 0.9995 | %107 |
| frozen | @last | `havuz (iki mod ort.)` | 1.6112 | +0.00839 | 0.9999 | %111 |

> **Hüküm: bu sayının üreticisi yok ve bu veriden çıkmıyor.** Üç öğretmen üzerinden kurulan her doğrunun eğimi 1.35'in üstünde; 0.765 en yakın spesifikasyondan %77 uzak. Pearson +0.992 iddiası taranan spesifikasyonlarla uyumlu (hepsinde r ≈ 0.99), yani anlatı doğru ama **eğim değil**. Cümlenin işi zaten feragat olduğu için makaleden çıkarılması kayıpsız.

---

Kaynaklar: `diagnostics/selection_audit/b015_verdict.json` (FERPlus fit'i, havuzlanmış), `diagnostics/teacher_ece_grid/teacher_ece_grid.json` (öğretmen ECE'leri), `denominator_table.control_arms()` (öğrenci kontrol kolları).

