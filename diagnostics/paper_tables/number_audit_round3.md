# B10 — Round-3'ün on ondalık uyuşmazlığı: doğru değerler

Üretici: `diagnostics/number_audit_round3.py` · her satır bir üretici artefaktından okunuyor, hiçbiri elle yazılmıyor

> Panelin önerdiği değer de yazılıyor, çünkü onun **tutmaması da bilgi**: iki taraf birden yanlış olabilir ve bu turda birkaç kez öyle oldu.

| hüküm | adet |
|---|---|
| yayımlı doğru | 4 |
| panel haklı | 1 |
| kollarla eşleştirilmeli | 1 |
| ~40× doğru, 37× yeniden üretilemiyor | 1 |
| ikisi de değil — üç sayı üç FARKLI şey | 1 |
| ikisi de değil | 1 |
| ikisi de doğru, ama aynı şeyi ölçmüyorlar | 1 |

| # | iddia | yayımlı | panelin ölçümü | **ölçülen** | hüküm |
|---|---|---|---|---|---|
| 1 | "spans 57–77 units" | 57–77 | 57–75.5 | **56.6764 – 76.6244** | yayımlı doğru |
| 2 | "13–14 times smaller" (T* ölçüt seçiminin maliyeti) | 13–14× | 13.2–14.7 | **13.31 – 14.32** | yayımlı doğru |
| 3 | FERPlus best−last SE | 0.0022 | 0.0021 | **0.00215** | panel haklı |
| 4 | `tab_efficiency` boyut oranı | 62.9× | 63.1× (555.0/8.8) | **62.8847×** | yayımlı doğru |
| 5 | §5.4 eğim sıralaması "0.655, 0.716, 0.649" | 0.655, 0.716, 0.649 | 0.655, 0.649, 0.716 | **scratch0712 0.655 · pretrained2248 0.716 · scratch2248 0.649** | kollarla eşleştirilmeli |
| 6 | baş-izolasyonu "%19" | %19 | %16 (doğrusal referansla) | **%18.58 (doğrusal payda) / %22.82 (varyasyonel payda)** | yayımlı doğru |
| 7 | "37× collapse" vs "roughly forty times the noise" | 37× ve ~40× (aynı 0.0005) | hangisi? | **açıklık 0.020083 · ~39.8×** | ~40× doğru, 37× yeniden üretilemiyor |
| 8 | FERPlus T*_ECE (metinde 0.453 / 0.46 / ≈0.46–0.51) | üç değer birden | kesin değer? | **0.45305** | ikisi de değil — üç sayı üç FARKLI şey |
| 9 | Ek B yoğun grid alt sınırı "0.5" | 0.5 | FERPlus optimumu 0.453 bunun altında → sınır-kısıtlı mı? | **RAF-DB [0.60, 2.95] adım 0.05 (48 nokta) · FERPlus [0.10, 4.00] adım 0.02 (196 nokta) · sürekli fit [0.1, 3.0] adım 0.005** | ikisi de değil |
| 10 | "bar" terimi (§5.5'te 1×, `tab_collapse`'ta 2×) | iki farklı kullanım | hangisi nerede doğru? | **bar = 1× kontrol sd = 0.0012** | ikisi de doğru, ama aynı şeyi ölçmüyorlar |

---

### 1 · "spans 57–77 units"

**Ölçülen: 56.6764 – 76.6244** — *yayımlı doğru*

@swa, ECE ekseninin gürültü birimi, üç öğretmen. Tam sayıya yuvarlandığında 57 ve 77. Panelin 75.5'i hiçbir hücreye karşılık gelmiyor (ölçülen maksimum 76.62, stage1).

Kaynak: `diagnostics/paper_tables/noise_units.json → nine_cell_grid.swa|*.ece_units`

### 2 · "13–14 times smaller" (T* ölçüt seçiminin maliyeti)

**Ölçülen: 13.31 – 14.32** — *yayımlı doğru*

ölçeklemenin kaldırdığı ECE ÷ iki ölçüt arasındaki ECE farkı. ferplus 13.31× · primary 13.60× · stage1 14.32×. vae9182 dışarıda: onda ölçekleme ECE'yi kaldırmıyor (removed < 0), oran anlamsız olurdu.

Kaynak: `diagnostics/paper_tables/tstar_sensitivity.json → results.*`

### 3 · FERPlus best−last SE

**Ölçülen: 0.00215** — *panel haklı*

ECE ekseni, n=12, ort +0.0041, SD 0.0074 → SE = SD/√n = 0.00215. Dört ondalığa **0.0021**.

Kaynak: `diagnostics/paper_tables/selection_audit_inference.json`

### 4 · `tab_efficiency` boyut oranı

**Ölçülen: 62.8847×** — *yayımlı doğru*

payda öğrencinin GERÇEK boyutu 8.8259 MB, 8.8 değil; 555.0155/8.8259 = 62.8847. Panelin 63.1'i paydayı yuvarlamaktan geliyor (555.0/8.8 = 63.07).

Kaynak: `diagnostics/paper_tables/efficiency_retention.json → compression.size_ratio`

### 5 · §5.4 eğim sıralaması "0.655, 0.716, 0.649"

**Ölçülen: scratch0712 0.655 · pretrained2248 0.716 · scratch2248 0.649** — *kollarla eşleştirilmeli*

Sayılar doğru; sıra KOL ADIYLA yazılmadıkça belirsiz. Kollar: **scratch0712** = 0.655 · **pretrained2248** = 0.716 · **scratch2248** = 0.649. Kontrastlar: scratch2248 vs pretrained2248 -0.067 (BAŞLATMA) · scratch2248 vs scratch0712 -0.006 (KAPASİTE) · pretrained2248 vs scratch0712 +0.061 (ikisi birden (B4'ün mevcut, confound'lu karşılaştırması)). Üçü toplamsal olarak tutarlı.

Kaynak: `diagnostics/a13_scratch_dose/a13_verdict.json`

### 6 · baş-izolasyonu "%19"

**Ölçülen: %18.58 (doğrusal payda) / %22.82 (varyasyonel payda)** — *yayımlı doğru*

Δ = 0.00622; **doğrusal** öğrencinin ECE'si 0.03348 → %18.58 (≈19). Varyasyonel öğrencininki 0.02725 → %22.82. Panelin %16'sı hiçbir paydadan çıkmıyor. AYRICA: bu kol **@best**'te ölçülmüş, makalenin birincil checkpoint'i @swa.

Kaynak: `diagnostics/vich_isolation/vich_isolation_verdict.json`

### 7 · "37× collapse" vs "roughly forty times the noise"

**Ölçülen: açıklık 0.020083 · ~39.8×** — *~40× doğru, 37× yeniden üretilemiyor*

Öğrenci JSD açıklığı @swa = 0.073681 − 0.053598 = **0.020083**. Tohum sd'si konvansiyona göre: ortalama sd 0.000504 → 39.8× · medyan sd 0.000456 → 44.1× · en büyük sd 0.000733 → 27.4× · en küçük sd 0.000373 → 53.9× · havuzlanmış sd 0.000523 → 38.4×. **37× hiçbirinden çıkmıyor**; yayımlı ~40 ortalama sd'ye karşılık geliyor. Metin tek bir konvansiyon seçip yazmalı.

Kaynak: `diagnostics/ferplus_jsd/ferplus_student_jsd.json`

### 8 · FERPlus T*_ECE (metinde 0.453 / 0.46 / ≈0.46–0.51)

**Ölçülen: 0.45305** — *ikisi de değil — üç sayı üç FARKLI şey*

**0.4530** = sürekli argmin (sınırlı Brent, `tstar_sensitivity`). **0.46** = aynı optimumun kaba ızgaradaki hâli (adım 0.02, 196 nokta). **0.5000** ise T*_ECE DEĞİL, **T*_NLL** — dağıtılan sıcaklık. Metindeki "≈0.46–0.51" iki farklı ölçütü tek aralık gibi gösteriyor.

Kaynak: `diagnostics/paper_tables/tstar_sensitivity.json · diagnostics/ferplus_jsd/ferplus_jsd.json`

### 9 · Ek B yoğun grid alt sınırı "0.5"

**Ölçülen: RAF-DB [0.60, 2.95] adım 0.05 (48 nokta) · FERPlus [0.10, 4.00] adım 0.02 (196 nokta) · sürekli fit [0.1, 3.0] adım 0.005** — *ikisi de değil*

**0.5 hiçbir ızgaranın sınırı değil.** İki ayrı ızgara var ve alt sınırları 0.60 ile 0.10. Sınır-kısıtlılık sorusunun cevabı: **hayır** — RAF-DB optimumları 1.350, 1.050, 1.250 ve FERPlus optimumu 0.46, hepsi kendi ızgaralarının İÇİNDE. Headroom aralığı sınır-kısıtlı değil; düzeltilmesi gereken tek şey Ek B'nin ızgarayı tek bir sayıyla anması.

Kaynak: `diagnostics/teacher_ece_grid/teacher_ece_grid.json · diagnostics/paper_tables/tstar_sensitivity.json`

### 10 · "bar" terimi (§5.5'te 1×, `tab_collapse`'ta 2×)

**Ölçülen: bar = 1× kontrol sd = 0.0012** — *ikisi de doğru, ama aynı şeyi ölçmüyorlar*

`p6_verdict.py` "bar"ı **1× kontrol tohum sd'si** diye tanımlıyor ve hükmü `|ort| ≥ **2×bar**` ile veriyor; `criterion_applied.py` aynı eşiği doğrudan `2σ_kontrol` diye yazıyor. Yani tanım tek: **bar = 1× sd, eşik = 2×bar**. `tab_collapse` oranı 2×bar'a bölerek basıyor (eşiğin kaç katı), §5.5 ise 1×bar'a bölüyor (gürültünün kaç katı) — ikisi de meşru ama **aynı sayı değil, tam iki katı**. Metin hangi birimi kullandığını her iki yerde de yazmalı.

Kaynak: `diagnostics/paper_tables/p6_collapse_test.json · diagnostics/criterion_applied.py`

