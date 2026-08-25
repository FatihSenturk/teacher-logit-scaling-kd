# B3(a) + B6 — kontrol tohum sd'leri (paydalar) ve ölçütün minimum saptanabilir etkisi

Üretici: `diagnostics/control_sd_mde.py` · sample sd (n-1, Bessel-corrected), computed over seeds · payda tanımı `denominator_table.control_arms()`'tan **ithal**

> İki soru aynı 18 sayıya bakıyor. **B3(a):** yayımda 27×/23×/52×/2.6× oranları var ama paydaları yok, yani okuyucu oranı yeniden kuramıyor. **B6:** ölçüt `|Δ| ≥ 2σ_kontrol` olduğuna göre **2σ**, o hücrede saptanabilecek en küçük etkidir — `unresolved` bir hücre "etki yok" demek değil, **"bu tabanın altında"** demektir, ve taban yazılmadan cümle yorumlanamaz.

## Özet

| kalem | değer |
|---|---|
| payda satırı (öğretmen × checkpoint × eksen × sınıf-ağırlığı) | 36 |
| bunların 27× ailesine ait olanı (`effective_number`) | **18** |
| **2σ (ECE) @swa** — ölçütün tabanı | **0.0024 … 0.0067** |
| aynı taban, kontrol kolunun ECE düzeyine oran | **%3.2 … %19.4** |
| 2σ (ECE), üç checkpoint birlikte | 0.0021 … 0.0170 |

---

## 1 · Paydalar — 27× ailesinin 18 sayısı

`logit_std` `effective_number` modunda koştuğu için ailenin paydaları o kontrol kolundan gelir: **3 öğretmen × 3 checkpoint × 2 eksen = 18**. Aile dışındaki 18 sayı (`none` kolu) hemen altında — 12 `unresolved` hücrenin beşi gate hücresi ve onların tabanı o koldan çıkar.

| ckpt | öğretmen | cw | eksen | kontrol düzeyi | **σ (payda)** | n | tohumlar | 27× ailesi |
|---|---|---|---|---|---|---|---|---|
| swa | primary | `effective_number` | ECE | 0.0707 | **0.0015** | 3 | [1, 42, 43] | ✅ |
| swa | primary | `effective_number` | ACC | 89.602 | **0.130** | 3 | [1, 42, 43] | ✅ |
| swa | primary | `none` | ECE | 0.0755 | **0.0033** | 3 | [1, 42, 43] | — |
| swa | primary | `none` | ACC | 89.266 | **0.394** | 3 | [1, 42, 43] | — |
| swa | stage1 | `effective_number` | ECE | 0.0731 | **0.0012** | 3 | [1, 42, 43] | ✅ |
| swa | stage1 | `effective_number` | ACC | 89.602 | **0.340** | 3 | [1, 42, 43] | ✅ |
| swa | stage1 | `none` | ECE | 0.0745 | **0.0021** | 3 | [1, 42, 43] | — |
| swa | stage1 | `none` | ACC | 89.657 | **0.100** | 3 | [1, 42, 43] | — |
| swa | vae9182 | `effective_number` | ECE | 0.0330 | **0.0020** | 3 | [1, 42, 43] | ✅ |
| swa | vae9182 | `effective_number` | ACC | 89.950 | **0.366** | 3 | [1, 42, 43] | ✅ |
| swa | vae9182 | `none` | ECE | 0.0278 | **0.0027** | 3 | [1, 42, 43] | — |
| swa | vae9182 | `none` | ACC | 90.146 | **0.207** | 3 | [1, 42, 43] | — |
| best | primary | `effective_number` | ECE | 0.0606 | **0.0085** | 3 | [1, 42, 43] | ✅ |
| best | primary | `effective_number` | ACC | 89.570 | **0.086** | 3 | [1, 42, 43] | ✅ |
| best | primary | `none` | ECE | 0.0707 | **0.0048** | 3 | [1, 42, 43] | — |
| best | primary | `none` | ACC | 89.070 | **0.191** | 3 | [1, 42, 43] | — |
| best | stage1 | `effective_number` | ECE | 0.0627 | **0.0054** | 3 | [1, 42, 43] | ✅ |
| best | stage1 | `effective_number` | ACC | 89.754 | **0.082** | 3 | [1, 42, 43] | ✅ |
| best | stage1 | `none` | ECE | 0.0651 | **0.0037** | 3 | [1, 42, 43] | — |
| best | stage1 | `none` | ACC | 89.820 | **0.075** | 3 | [1, 42, 43] | — |
| best | vae9182 | `effective_number` | ECE | 0.0274 | **0.0021** | 3 | [1, 42, 43] | ✅ |
| best | vae9182 | `effective_number` | ACC | 90.276 | **0.191** | 3 | [1, 42, 43] | ✅ |
| best | vae9182 | `none` | ECE | 0.0225 | **0.0012** | 3 | [1, 42, 43] | — |
| best | vae9182 | `none` | ACC | 90.385 | **0.267** | 3 | [1, 42, 43] | — |
| last | primary | `effective_number` | ECE | 0.0701 | **0.0031** | 3 | [1, 42, 43] | ✅ |
| last | primary | `effective_number` | ACC | 88.494 | **0.259** | 3 | [1, 42, 43] | ✅ |
| last | primary | `none` | ECE | 0.0737 | **0.0048** | 3 | [1, 42, 43] | — |
| last | primary | `none` | ACC | 88.353 | **0.303** | 3 | [1, 42, 43] | — |
| last | stage1 | `effective_number` | ECE | 0.0701 | **0.0081** | 3 | [1, 42, 43] | ✅ |
| last | stage1 | `effective_number` | ACC | 88.994 | **0.100** | 3 | [1, 42, 43] | ✅ |
| last | stage1 | `none` | ECE | 0.0691 | **0.0052** | 3 | [1, 42, 43] | — |
| last | stage1 | `none` | ACC | 89.124 | **0.191** | 3 | [1, 42, 43] | — |
| last | vae9182 | `effective_number` | ECE | 0.0307 | **0.0011** | 3 | [1, 42, 43] | ✅ |
| last | vae9182 | `effective_number` | ACC | 89.820 | **0.167** | 3 | [1, 42, 43] | ✅ |
| last | vae9182 | `none` | ECE | 0.0297 | **0.0039** | 3 | [1, 42, 43] | — |
| last | vae9182 | `none` | ACC | 89.602 | **0.267** | 3 | [1, 42, 43] | — |

### Çapraz kontrol — aynı paydalarla `noise_units`'in dokuz oranı

Paydalar basılmakla kalmıyor, oranlar bu paydalardan **yeniden kuruluyor** ve `noise_units.json` ile karşılaştırılıyor. Sonuç: **GEÇTİ**, en büyük sapma `0.00e+00`. Tutmasaydı bu betik çıkış kodu 1 verirdi — iki üretici arasında sessiz ayrışma, bu tablonun kapatmak için var olduğu şeyin ta kendisi.

| ckpt | öğretmen | `noise_units` | buradan yeniden kurulan | sapma |
|---|---|---|---|---|
| swa | stage1 | 114.2848× | 114.2848× | 0.00e+00 |
| swa | primary | 23.4523× | 23.4523× | 0.00e+00 |
| swa | vae9182 | 213.0219× | 213.0219× | 0.00e+00 |
| best | stage1 | 6.0630× | 6.0630× | 0.00e+00 |
| best | primary | 2.7831× | 2.7831× | 0.00e+00 |
| best | vae9182 | 27.3441× | 27.3441× | 0.00e+00 |
| last | stage1 | 2.5568× | 2.5568× | 0.00e+00 |
| last | primary | 32.3075× | 32.3075× | 0.00e+00 |
| last | vae9182 | 43.1637× | 43.1637× | 0.00e+00 |

## 2 · B6 — ölçütün minimum saptanabilir etkisi (2σ)

Aynı satırlar, bu kez ölçüt tarafından okunuşuyla. **2σ**, o öğretmen-checkpoint hücresinde ölçütün `established` diyebileceği en küçük |Δ|'dır; ikinci sütun onu kontrol kolunun kendi düzeyine oranlar, çünkü ECE 0.028 olan bir öğrenci ile 0.075 olan bir öğrenci için aynı mutlak taban aynı şeyi ifade etmez.

| ckpt | öğretmen | cw | eksen | **2σ (mutlak)** | kontrol düzeyi | **2σ / düzey** |
|---|---|---|---|---|---|---|
| swa | primary | `effective_number` | ECE | **0.0030** | 0.0707 | **%4.3** |
| swa | primary | `effective_number` | ACC | **0.261** | 89.602 | **%0.3** |
| swa | primary | `none` | ECE | **0.0067** | 0.0755 | **%8.8** |
| swa | primary | `none` | ACC | **0.789** | 89.266 | **%0.9** |
| swa | stage1 | `effective_number` | ECE | **0.0024** | 0.0731 | **%3.2** |
| swa | stage1 | `effective_number` | ACC | **0.681** | 89.602 | **%0.8** |
| swa | stage1 | `none` | ECE | **0.0042** | 0.0745 | **%5.7** |
| swa | stage1 | `none` | ACC | **0.199** | 89.657 | **%0.2** |
| swa | vae9182 | `effective_number` | ECE | **0.0040** | 0.0330 | **%12.1** |
| swa | vae9182 | `effective_number` | ACC | **0.733** | 89.950 | **%0.8** |
| swa | vae9182 | `none` | ECE | **0.0054** | 0.0278 | **%19.4** |
| swa | vae9182 | `none` | ACC | **0.414** | 90.146 | **%0.5** |
| best | primary | `effective_number` | ECE | **0.0170** | 0.0606 | **%28.0** |
| best | primary | `effective_number` | ACC | **0.172** | 89.570 | **%0.2** |
| best | primary | `none` | ECE | **0.0097** | 0.0707 | **%13.7** |
| best | primary | `none` | ACC | **0.382** | 89.070 | **%0.4** |
| best | stage1 | `effective_number` | ECE | **0.0108** | 0.0627 | **%17.2** |
| best | stage1 | `effective_number` | ACC | **0.164** | 89.754 | **%0.2** |
| best | stage1 | `none` | ECE | **0.0074** | 0.0651 | **%11.4** |
| best | stage1 | `none` | ACC | **0.151** | 89.820 | **%0.2** |
| best | vae9182 | `effective_number` | ECE | **0.0042** | 0.0274 | **%15.4** |
| best | vae9182 | `effective_number` | ACC | **0.382** | 90.276 | **%0.4** |
| best | vae9182 | `none` | ECE | **0.0024** | 0.0225 | **%10.8** |
| best | vae9182 | `none` | ACC | **0.534** | 90.385 | **%0.6** |
| last | primary | `effective_number` | ECE | **0.0062** | 0.0701 | **%8.8** |
| last | primary | `effective_number` | ACC | **0.517** | 88.494 | **%0.6** |
| last | primary | `none` | ECE | **0.0095** | 0.0737 | **%12.9** |
| last | primary | `none` | ACC | **0.606** | 88.353 | **%0.7** |
| last | stage1 | `effective_number` | ECE | **0.0163** | 0.0701 | **%23.2** |
| last | stage1 | `effective_number` | ACC | **0.199** | 88.994 | **%0.2** |
| last | stage1 | `none` | ECE | **0.0103** | 0.0691 | **%15.0** |
| last | stage1 | `none` | ACC | **0.382** | 89.124 | **%0.4** |
| last | vae9182 | `effective_number` | ECE | **0.0021** | 0.0307 | **%7.0** |
| last | vae9182 | `effective_number` | ACC | **0.335** | 89.820 | **%0.4** |
| last | vae9182 | `none` | ECE | **0.0079** | 0.0297 | **%26.5** |
| last | vae9182 | `none` | ACC | **0.534** | 89.602 | **%0.6** |

> @swa, ECE ekseninde taban **0.0024 … 0.0067**, yani kontrol kolunun kendi ECE düzeyinin **%3.2 … %19.4**'i. `unresolved` bir hücre için söylenebilecek doğru cümle şu: *bu tasarım, o hücrede bu büyüklüğün altındaki bir etkiyi üç tohumla ayırt edemez.* @best ve @last'te taban daha yüksek — kontrol kolunun tohum yayılımı o checkpoint'lerde daha geniş, yani aynı ölçüt orada daha kördür.

---

Üretici: `diagnostics/control_sd_mde.py` · payda: `diagnostics/denominator_table.py::control_arms` (ithal) · eşik 2× (`criterion_applied.py` ile aynı sabit)

