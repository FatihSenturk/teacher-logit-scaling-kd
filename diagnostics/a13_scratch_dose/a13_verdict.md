# A13 — 2.248 M scratch doz-yanıtı

> **ÖN-BEYANLI.** `PREREGISTRATIONS.md` A13, commit `b71e6ad`, etiket `a12-a13-predeclared`. Analiz planı B4'ten harfiyen devralındı; tahmin ve üç sonuç-cümlesi koşulardan önce yazıldı. Bu betik de ilk sonuç okunmadan commit'lendi.

**HÜKÜM: BAŞLATMA TAHMİNİ YANLIŞLANDI — eğim başlatmaya duyarlı · T10a (ii) SONUÇSUZ KALIYOR — ama artık confound yüzünden değil, gürültü yüzünden**

Üretici: `diagnostics/a13_scratch_dose_verdict.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · fit ve zarf `capacity_law_check`'ten ithal

> **Donmuş denetim dosyasına dokunulmadı.** A13 koşuları 2026-07-31 kesmesinin dışında; hüküm `selection_audit_unfrozen.csv`'den okundu. Makalenin N=131 alıntısını taşıyan `selection_audit.csv` ne okundu ne yazıldı.

## Üç eğim, aynı üç sıcaklıkta

| kol | başlatma | kapasite | eğim b | R² | zarf |
|---|---|---|---|---|---|
| w050 | scratch | 0.712 M | **0.655** | 0.99996 | ±0.058 |
| 2248 ön-eğitimli | ön-eğitimli | 2.248 M | **0.716** | 0.99997 | ±0.022 |
| w100ns | **scratch** | 2.248 M | **0.649** | 0.99882 | ±0.014 |

Fit desteği üç sıcaklıkta da aynı (T = 1.0 / 1.7 / 2.2) — 5-noktalı fit'e karşı 3-noktalı fit koymak kapasiteyi fit desteğiyle karıştırırdı (B4'ün 1. şartı).

## Üç karşılaştırma

| karşılaştırma | izole ettiği | Δb | birleşik zarf | çözünüyor mu |
|---|---|---|---|---|
| scratch2248 vs pretrained2248 | **BAŞLATMA** | -0.067 | ±0.036 | ✅ evet |
| scratch2248 vs scratch0712 | **KAPASİTE** | -0.006 | ±0.072 | ❌ hayır |
| pretrained2248 vs scratch0712 | **ikisi birden (B4'ün mevcut, confound'lu karşılaştırması)** | +0.061 | ±0.080 | ❌ hayır |

**Zarf bir güven aralığı DEĞİLDİR.** İki hücrede n=2, tek serbestlik derecesi. Zarf, yalnız tohum gürültüsünün fit edilen eğimi en çok ne kadar oynatabileceğinin bir sınırıdır. **"Eğim kapasiteyle değişmiyor" cümlesi yazılmayacak** — çözünmemek yokluk göstermez.

## Hücre envanteri (scratch kolu)

| kapasite | T | öğretmen ECE | n | öğrenci ECE ort | sd | tohumlar |
|---|---|---|---|---|---|---|
| 0.712 M (w050) | 1 | 0.0136 | 3 | 0.0365 | 0.0057 | [1, 42, 43] |
| 0.712 M (w050) | 1.7 | 0.1454 | 2 | 0.1236 | 0.0040 | [1, 42] |
| 0.712 M (w050) | 2.2 | 0.2622 | 2 | 0.1992 | 0.0087 | [1, 42] |
| 1.380 M (w075) | 1 | 0.0136 | 3 | 0.0388 | 0.0042 | [1, 42, 43] |
| 2.248 M (w100ns) | 1 | 0.0136 | 3 | 0.0374 | 0.0030 | [1, 42, 43] |
| 2.248 M (w100ns) | 1.7 | 0.1454 | 2 | 0.1183 | 0.0011 | [1, 42] |
| 2.248 M (w100ns) | 2.2 | 0.2622 | 2 | 0.1989 | 0.0003 | [1, 42] |

Tohum tekilliği kapısı geçildi: hiçbir hücrede aynı tohumdan iki koşu yok (olsaydı hüküm `RuntimeError` ile dururdu — tekrar, hücrede tohum dışında bir değişkenin de oynadığı anlamına gelirdi).

