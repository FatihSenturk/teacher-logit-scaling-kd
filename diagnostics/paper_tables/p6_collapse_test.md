# P6 — resmî hüküm: T·τ çökme testi ve α modülasyonu (T11 + T12)

Kuyruk **42/42** kapandı (5 Ağu 2026 16:16). Kurallar 1 Ağu'da `p6-predeclared` tag'iyle donduruldu (commit `3d9dbee`); bu tablo onları uygular, yeniden yorumlamaz.

Üretici: `diagnostics/p6_verdict.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · bar 0.0012 (kaynak sd 0.001182, `denominator_table.json`) · 2×bar 0.0024

P6.1'in karar mantığı ve çift tanımları `p6_1_early_reading.py`'den **ithal edilir**, kopyalanmaz — beyanın 'aynı üreticiyle' şartı böylece yapısal olarak sağlanır.

> **Hangi hakem itirazına karşılık geliyor.** Round-2 panelinin Devil's Advocate raporu, "yapılmamış belirleyici deney" olarak tam olarak bu testi gösteriyor: *"varying τ at fixed T (or α) would separate 'confidence structure' from composite-softness/optimization accounts within a single teacher"* (DA-C2 ve Ignored-Alternatives). P6 bu deneydir ve 42 koşuyla koşulmuştur; hüküm aşağıdadır. Beyan koşulardan önce (1 Ağu, `p6-predeclared`), itiraz ise sonra (5 Ağu) geldi — yani test itiraza göre tasarlanmadı, itirazdan bağımsız olarak zaten ön-kayıtlıydı.

---

## T11 — Grid 1: eşleşmiş T·τ çiftleri (P6.1)

### Çift T·τ = 5.10: (τ=3, T=1.70) − (τ=6, T=0.85)

| tohum | ECE küçük-τ | ECE büyük-τ | ΔECE |
|---|---|---|---|
| 42 | 0.0427 | 0.0781 | -0.0355 |
| 1 | 0.0402 | 0.0814 | -0.0411 |
| 43 | 0.0387 | 0.0795 | -0.0408 |

ort ΔECE **-0.0391 ± 0.0032** · işaretler 3/3 aynı · |ort|/2×bar = 16.30×

**YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar)**

### Çift T·τ = 10.20: (τ=6, T=1.70) − (τ=12, T=0.85)

| tohum | ECE küçük-τ | ECE büyük-τ | ΔECE |
|---|---|---|---|
| 42 | 0.0472 | 0.0806 | -0.0334 |
| 1 | 0.0415 | 0.0762 | -0.0347 |
| 43 | 0.0455 | 0.0746 | -0.0291 |

ort ΔECE **-0.0324 ± 0.0029** · işaretler 3/3 aynı · |ort|/2×bar = 13.50×

**YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar)**

### P6.1 hükmü

ÇÖKME YANLIŞLANDI — iki çiftte birden 3/3 aynı işaret ve |ort ΔECE| ≥ 2×bar. Beyanın kendi sözleriyle: ayrışmanın kendisi bulgu — sıra bilgisi ile yumuşaklık ayrı kanallar.

**Erken okuma birebir yeniden üretildi** (2 Ağu, kuyruk ~10/42): altı ΔECE değerinin tamamı ve iki çift statüsü aynı. Beyanın öngördüğü gibi — koşu-başına önbellek aynı ölçümleri taşıyor.

---

## T12 — Grid 2: α modülasyonu (P6.2, P6.3)

gap(α) := ECE(T=1) − ECE(T=1.3406), tohum-içi · τ=6 sabit

| α | tohum 42 | tohum 1 | tohum 43 | ort |
|---|---|---|---|---|
| 0.1 | +0.0197 | +0.0215 | +0.0262 | **+0.0224** |
| 0.3 | +0.0297 | +0.0296 | +0.0317 | **+0.0303** |
| 0.5 | +0.0344 | +0.0365 | +0.0271 | **+0.0327** |
| 0.7 | -0.0071 | +0.0003 | -0.0007 | **-0.0025** |
| 0.9 | -0.0307 | -0.0397 | -0.0351 | **-0.0352** |

_α=0.3 satırı beyan gereği mevcut doz-yanıt kollarından yeniden kullanıldı (`CURVES`), yeni koşu değil._

### P6.2 — monotonluk

Kural: gap(α) α arttıkça monoton azalır (ardıl adımlarda artmayan), 3/3 tohumda

| tohum | gap dizisi (α=0.1→0.9) | ardıl adımlar | artmayan? |
|---|---|---|---|
| 42 | +0.0197, +0.0297, +0.0344, -0.0071, -0.0307 | +0.0100, +0.0047, -0.0415, -0.0237 | ❌ 0.1→0.3 (+0.0100); 0.3→0.5 (+0.0047) |
| 1 | +0.0215, +0.0296, +0.0365, +0.0003, -0.0397 | +0.0081, +0.0069, -0.0363, -0.0399 | ❌ 0.1→0.3 (+0.0081); 0.3→0.5 (+0.0069) |
| 43 | +0.0262, +0.0317, +0.0271, -0.0007, -0.0351 | +0.0055, -0.0046, -0.0278, -0.0344 | ❌ 0.1→0.3 (+0.0055) |

**P6.2 DOĞRULANMADI** — 0/3 tohumda sağlandı.

### P6.3 — uçlar

Kural: gap(0.9) < gap(0.1), kesin eşitsizlik, 3/3 tohumda

| tohum | gap(0.1) | gap(0.9) | gap(0.9) − gap(0.1) | gap(0.9) < gap(0.1)? |
|---|---|---|---|---|
| 42 | +0.0197 | -0.0307 | -0.0504 | ✅ |
| 1 | +0.0215 | -0.0397 | -0.0611 | ✅ |
| 43 | +0.0262 | -0.0351 | -0.0613 | ✅ |

**P6.3 DOĞRULANDI** — 3/3 tohumda sağlandı.

---

Kaynak: `diagnostics/selection_audit/selection_audit_unfrozen.csv` @swa. Donmuş denetim dosyası (`selection_audit.csv`, N=131) bu turda **değişmedi** — ayrı dosyadır.

