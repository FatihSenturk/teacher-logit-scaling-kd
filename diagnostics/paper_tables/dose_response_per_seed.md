# B8 — doz-yanıt eğrilerinin tohum başına tablosu (ek tablo)

Üretici: `diagnostics/dose_response_per_seed.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · eğri tanımı `two_dataset_overlay.build()`'den **ithal**

> Özetin en güçlü niceleyicisi *"all nine seed curves"*. Yayımlanan her şey `ort ± sd` olduğu için o cümlenin doğrulanabileceği bir yüzey yoktu — ortalama bir eğrinin monoton olması, dokuz eğrinin **ayrı ayrı** monoton olduğunu göstermez. Bu ek tablo o yüzeyi kuruyor.

> **Hangi eksende monoton?** Burada yeniden tanımlanmıyor: G2.2 (`monotonicity_test.py`) o soruyu çözdü ve hükmü buraya **ithal ediliyor**. İkinci bir monotonluk tanımı yazmak, G2.2'nin kapattığı belirsizliği geri açardı.

| eksen (G2.2 tanımı) | geçen tohum eğrisi |
|---|---|
| (a) ham T ekseni | **0/9** |
| (b) işaretli gap, **branş içi** ← iddianın ekseni | **9/9** |
| (c) işaretsiz \|gap\|, havuzlanmış | **3/9** |

Bu tablonun kendi ölçtüğü T-ekseni sayıları G2.2 (a) ile **tutuyor**: katı monoton 0/9, ρ(T, ECE) > 0 olan 8/9. ρ'nun pozitif ama monotonluğun sıfır olması çelişki değil: eğriler T\* civarında **U biçimli**, yani sıralama korelasyonu yönü verir, monotonluğu vermez.

| seri | tohum | nokta | ρ(T, ECE) | T'de monoton | G2.2 (b) branş içi | ECE (en küçük T) | ECE (en büyük T) | fark |
|---|---|---|---|---|---|---|---|---|
| `rafdb_stage1` | 1 | 5 | +0.000 | hayır | ✓ | 0.0814 | 0.1013 | +0.0199 |
| `rafdb_stage1` | 42 | 5 | +0.100 | hayır | ✓ | 0.0781 | 0.1030 | +0.0249 |
| `rafdb_stage1` | 43 | 5 | +0.100 | hayır | ✓ | 0.0795 | 0.0980 | +0.0185 |
| `rafdb_vae9182` | 1 | 5 | +0.900 | hayır | ✓ | 0.0460 | 0.2090 | +0.1630 |
| `rafdb_vae9182` | 42 | 5 | +0.900 | hayır | ✓ | 0.0434 | 0.2148 | +0.1714 |
| `rafdb_vae9182` | 43 | 5 | +0.900 | hayır | ✓ | 0.0446 | 0.2090 | +0.1644 |
| `ferplus` | 1 | 4 | +0.400 | hayır | ✓ | 0.0632 | 0.0826 | +0.0194 |
| `ferplus` | 42 | 4 | +0.400 | hayır | ✓ | 0.0568 | 0.0734 | +0.0167 |
| `ferplus` | 43 | 4 | +0.400 | hayır | ✓ | 0.0563 | 0.0789 | +0.0226 |

---

## Tam tablo: her seri × her T × her tohum

### `rafdb_stage1` — RAF-DB / Stage1 teacher  (native ECE 0.0378, T*=1.35, OVER-confident)

| T | öğretmen ECE | işaretli fark | öğrenci ECE (tohum 1) | öğrenci ECE (tohum 42) | öğrenci ECE (tohum 43) | ort ± sd | n |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.0454 | +0.0431 | 0.0814 | 0.0781 | 0.0795 | 0.0797 ± 0.0016 | 3 |
| 1 | 0.0378 | +0.0338 | 0.0721 | 0.0728 | 0.0744 | 0.0731 ± 0.0012 | 3 |
| 1.3406 | 0.0159 | +0.0040 | 0.0425 | 0.0432 | 0.0428 | 0.0428 ± 0.0003 | 3 |
| 1.7 | 0.0429 | -0.0427 | 0.0415 | 0.0472 | 0.0455 | 0.0447 ± 0.0029 | 3 |
| 2.2 | 0.1270 | -0.1270 | 0.1013 | 0.1030 | 0.0980 | 0.1008 ± 0.0025 | 3 |

### `rafdb_vae9182` — RAF-DB / VAE9182 teacher (native ECE 0.0136, T*=0.98, already calibrated)

| T | öğretmen ECE | işaretli fark | öğrenci ECE (tohum 1) | öğrenci ECE (tohum 42) | öğrenci ECE (tohum 43) | ort ± sd | n |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.0250 | +0.0248 | 0.0460 | 0.0434 | 0.0446 | 0.0447 ± 0.0013 | 3 |
| 1 | 0.0136 | +0.0042 | 0.0343 | 0.0340 | 0.0307 | 0.0330 ± 0.0020 | 3 |
| 1.3406 | 0.0627 | -0.0605 | 0.0628 | 0.0682 | 0.0632 | 0.0647 ± 0.0030 | 3 |
| 1.7 | 0.1454 | -0.1453 | 0.1270 | 0.1260 | 0.1316 | 0.1282 ± 0.0030 | 3 |
| 2.2 | 0.2622 | -0.2622 | 0.2090 | 0.2148 | 0.2090 | 0.2109 ± 0.0034 | 3 |

### `ferplus` — FERPlus / VICH teacher   (native ECE 0.1282, T*=0.51, UNDER-confident)

| T | öğretmen ECE | işaretli fark | öğrenci ECE (tohum 1) | öğrenci ECE (tohum 42) | öğrenci ECE (tohum 43) | ort ± sd | n |
|---|---|---|---|---|---|---|---|
| 0.26 | 0.0393 | +0.0393 | 0.0632 | 0.0568 | 0.0563 | 0.0587 ± 0.0038 | 3 |
| 0.5063 | 0.0156 | -0.0117 | 0.0193 | 0.0167 | 0.0195 | 0.0185 ± 0.0016 | 3 |
| 0.74 | 0.0665 | -0.0649 | 0.0332 | 0.0356 | 0.0343 | 0.0344 ± 0.0012 | 3 |
| 1 | 0.1282 | -0.1277 | 0.0826 | 0.0734 | 0.0789 | 0.0783 ± 0.0046 | 3 |

