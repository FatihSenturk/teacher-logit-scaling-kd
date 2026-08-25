# P6.1 erken okuması — T·τ çökme testi (2 Ağu 2026)

> **ERKEN OKUMA.** Kuyruk ~10/42'deyken, Fatih'in 2 Ağu isteğiyle üretildi. Yön bilgisidir; **makaleye girmez** (P6 → T11/T12, tez / 3. çalışma). Resmi hüküm kuyruk 42/42 bitince PREREGISTRATIONS A9'a işlenir; per-run önbellek aynı ölçümleri kullandığından sayılar orada birebir aynı çıkmalıdır.

Üretici: `diagnostics/p6_1_early_reading.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · bar 0.0012 (kaynak sd 0.001182, `denominator_table.json`) · 2×bar 0.0024

Kural beyandan kelimesi kelimesine (`rafdb_p6_tau_alpha_queue.ps1`, 1 Ağu, commit 3d9dbee): çift için |ort dECE| ≤ 2×bar VE işaretler 3/3 uyuşmuyor → ÇÖKME DOĞRULANDI (o çift için); iki çiftte birden 3/3 aynı işaret VE |ort| ≥ 2×bar → ÇÖKME YANLIŞLANDI; başka her durum → ÇÖZÜNMEDİ, genel iddia yazılmaz.

Yön sözleşmesi: d = ECE(küçük-τ) − ECE(büyük-τ); kural işaret-simetrik, sözleşme hükmü etkilemez.

## Çift T·τ = 5.10: (τ=3, T=1.70) − (τ=6, T=0.85)

| tohum | ECE küçük-τ | ECE büyük-τ | dECE |
|---|---|---|---|
| 42 | 0.0427 | 0.0781 | -0.0355 |
| 1 | 0.0402 | 0.0814 | -0.0411 |
| 43 | 0.0387 | 0.0795 | -0.0408 |

ort dECE **-0.0391 ± 0.0032** · işaretler 3/3 aynı · |ort|/2×bar = 16.30×

**YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar)**

## Çift T·τ = 10.20: (τ=6, T=1.70) − (τ=12, T=0.85)

| tohum | ECE küçük-τ | ECE büyük-τ | dECE |
|---|---|---|---|
| 42 | 0.0472 | 0.0806 | -0.0334 |
| 1 | 0.0415 | 0.0762 | -0.0347 |
| 43 | 0.0455 | 0.0746 | -0.0291 |

ort dECE **-0.0324 ± 0.0029** · işaretler 3/3 aynı · |ort|/2×bar = 13.50×

**YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar)**

## Genel

ÇÖKME YANLIŞLANDI — iki çiftte birden 3/3 aynı işaret ve |ort dECE| ≥ 2×bar. Beyanın kendi sözleriyle: ayrışmanın kendisi bulgu — sıra bilgisi ile yumuşaklık ayrı kanallar.

