# G4.6 — denetim popülasyonunun kompozisyonu (N=131)

> **Panel G4.6.** Makale popülasyonu *"az sayıda legacy koşu"* içeren bir küme diye tarif ediyor. Bu betik sayıyı ölçüyor ve denetim istatistiğini epoch bütçesine göre katmanlı yeniden raporluyor.

**CEVAP: "az sayıda" = 28/131 koşu (%21).** Beşte bir; bu niceleyici daraltılmalı.

sample sd (n-1, Bessel-corrected), computed over seeds · kaynak: donmuş `selection_audit.csv` (yalnız okundu) + `runs.csv`

## Standart tarif dışı koşular

Standart tarif, önceden ve açıkça: `epochs=400`, `swa_start=200`, `alpha=0.3`, `kd_temperature=6.0`. Bu dört alanın herhangi birinde farklı olan koşu tarif dışı sayılır — "legacy" bir his değil, bir yordam.

| hangi alanlarda farklı | koşu |
|---|---|
| `epochs, swa_start` | 16 |
| `epochs` | 9 |
| `epochs, swa_start, kd_temperature` | 2 |
| `epochs, swa_start, alpha` | 1 |

**Dördünün de ortak paydası `epochs`**: tarif dışı 28 koşunun tamamı epoch bütçesinde farklı. Yani popülasyonu ayıran tek eksen aslında bütçe; α ve KD sıcaklığı sapmaları tek tük (sırasıyla 1 ve 2 koşu).

## Seçim iyimserliği, bütçeye katmanlı (`best` − `last`)

| epoch bütçesi | n | Δdoğruluk (pp) | ΔECE | hepsi aynı yönde mi |
|---|---|---|---|---|
| 400 **(makalenin kendi tarifi)** | 103 | +0.722 ± 0.270 | -0.0023 ± 0.0082 | ✅ |
| 200 | 19 | +1.016 ± 0.904 | -0.0060 ± 0.0145 | — |
| 500 | 9 | +0.746 ± 0.281 | -0.0031 ± 0.0048 | ✅ |
| **havuz (hepsi)** | 131 | +0.766 ± 0.431 | -0.0029 ± 0.0092 | |

### Katmanlamanın söylediği

- **Yön hiçbir katmanda değişmiyor.** Üç bütçenin üçünde de `best`, doğruluğu kayırıyor. Yani denetimin bulgusu legacy koşulardan gelmiyor — **popülasyonun her yerinde var.** Bu, iddiayı zayıflatmıyor, sağlamlaştırıyor.
- **Ama havuz sayısı makalenin tarifini temsil etmiyor.** Havuz +0.766 pp; 200-epoch katmanı (+1.016 pp, sd 0.904) ortalamayı yukarı çekiyor ve aynı zamanda en gürültülü katman. Makalenin kendi tarifi olan 400 epoch için doğru sayı **+0.722 ± 0.270 pp**.
- Kalibrasyon ekseninde de aynı yön: `best` ECE'yi de kayırıyor (ΔECE her katmanda negatif), yani seçim iyimserliği yalnız doğrulukta kalmıyor — bir kalibrasyon makalesi için asıl mesele bu.

## Popülasyon dökümü

**tarif ailesi** (`family`) — 6 değer

| değer | koşu |
|---|---|
| `mechanism_ablation` | 50 |
| `baseline` | 37 |
| `dose_response` | 28 |
| `width_frontier` | 9 |
| `miscal_causal` | 4 |
| `vich_isolation` | 3 |

**öğretmen** (`teacher`) — 4 değer

| değer | koşu |
|---|---|
| `vae9182` | 69 |
| `stage1` | 37 |
| `primary` | 19 |
| `unknown` | 6 |

**epoch bütçesi** (`epochs`) — 3 değer

| değer | koşu |
|---|---|
| `400` | 103 |
| `200` | 19 |
| `500` | 9 |

**SWA başlangıcı** (`swa_start`) — 3 değer

| değer | koşu |
|---|---|
| `200` | 112 |
| `(boş)` | 13 |
| `90` | 6 |

**α** (`alpha`) — 2 değer

| değer | koşu |
|---|---|
| `0.3` | 130 |
| `0.25` | 1 |

**KD sıcaklığı** (`kd_temperature`) — 2 değer

| değer | koşu |
|---|---|
| `6.0` | 129 |
| `4.0` | 2 |

**sınıf ağırlığı** (`class_weight_mode`) — 3 değer

| değer | koşu |
|---|---|
| `effective_number` | 111 |
| `none` | 18 |
| `(boş)` | 2 |

**ön-kayıt bloğu** (`preregistration_block`) — 11 değer

| değer | koşu |
|---|---|
| `(boş)` | 64 |
| `A1` | 12 |
| `A6` | 11 |
| `B3` | 9 |
| `B2` | 7 |
| `A7` | 6 |
| `A8-P4` | 6 |
| `A8` | 5 |
| `A2` | 4 |
| `B4` | 4 |
| `B1` | 3 |

> **Ön-kayıt bloğu sütunu ayrıca okunmalı.** Popülasyonun büyük bölümünün blok alanı boş: bu koşular bir ön-beyana bağlı DEĞİL ve denetim onları da içeriyor. Denetim zaten bir ön-kayıt iddiası değil, bir ölçüm; ama §4.5'in envanter sayısıyla bu tablo karıştırılmamalı.

---

Üretici: `diagnostics/audit_population.py` · veri: donmuş `diagnostics/selection_audit/selection_audit.csv` (N=131, yalnız okundu) · `runs.csv`

