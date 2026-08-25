# BULGULAR — RAF-DB Bilgi Damıtma Kampanyası

Bu dosya kampanyanın **tek kayıt defteri**dir. Her bulgu bir ID taşır, bir *durum*u vardır ve
her sayı bir artefakta dayanır. Sayısal iddia eklerken kaynağını da yaz — kaynağı olmayan
satır bu dosyaya girmez.

**Ham koşu tablosu:** [`runs.csv`](runs.csv) (**199 koşu**, `diagnostics/build_runs_ledger.py`
ile koşuların kendi `run_args.json` / `metrics_best.json` dosyalarından türetilir — elle yazılmaz).
*24 Ağu 2026: bu satırda uzun süre "89 koşu" yazıyordu; sayı üreticinin çıktısından ölçülerek
düzeltildi. Defter büyüdü, cümle büyümemişti.*

**Durum etiketleri:** `KAPALI` = karar verildi, yeniden açılmaz · `DEVAM` = koşu sürüyor ·
`AÇIK` = veri var, karar yok.

**Ölçüm sözleşmesi (istisnasız hepsinde aynı):** RAF-DB fold-3 doğrulama seti (n=3068),
`best_checkpoint.pth`, eval modu, VICH örnekleme kapalı, 15-kutulu confidence ECE
(`diagnostics/teacher_temperature_scaling_fit.py::confidence_ece`). Öğrenci tohumları {42, 1, 43}.
Belirtilen ± değerleri standart hata değildir. **Hangi sd olduğu bu dosyada tek tip DEĞİL,
ve bunu bilerek söylüyoruz:** aşağıdaki tabloların çoğu, kampanyanın ilk döneminde
`statistics.pstdev` (popülasyon sd, n bölen) ile hesaplandı; metodolojik düzeltme ve etkisinin
ölçümü aynı dosyanın içinde duruyor (bkz. *"⚠️ Metodolojik düzeltme"*, B-015 bölümü).
**Makalenin bağlayıcı sözleşmesi bu değildir:** `diagnostics/stats_convention.py` her tablo ve
şekil için **örneklem sd**'sini (n−1) zorunlu kılar, ve `diagnostics/paper_tables/`
altındaki üretilmiş tabloların hepsi onunla üretilir. Yani bu laboratuvar defterindeki bir ±
ile makaledeki bir ± aynı tahmin edici olmayabilir; makalede basılan sayının tanımı
`stats_convention.py`dedir.

---

## Öğretmen envanteri (fold-3 val, kendi metrikleri)

Üçünün de `ECE(T=1)` değeri head-compat denetimindeki değeri birebir yeniden üretti (tolerans 0.003) —
kalibrasyon boru hattı doğrulanmıştır.

| Öğretmen | Kendi acc | ECE(T=1) | T\* (NLL) | ECE(T\*) | **Öğretmen tarafı headroom ΔECE** |
|---|---|---|---|---|---|
| Stage1-VICH  | 92.24% | 0.0378 | 1.3494 | 0.0158 | **+0.0220** |
| Primary-VICH | 92.01% | 0.0396 | 1.2613 | 0.0197 | **+0.0199** |
| VAE9182-VAE  | 91.82% | 0.0136 | 0.9829 | 0.0146 | **−0.0011** |

`headroom ΔECE = ECE(T=1) − min_T ECE(T)`: post-hoc ölçeklemenin **sökebileceği** yanlış-kalibrasyon
miktarı. VAE9182'de bu sayı sıfır/negatif — yani zaten kalibrasyon tabanında, sökülecek bir şey yok.
Bu, B-007'nin nicel ifadesidir.

Öğretmen ECE'si, ızgaradaki her T'de (kaynak: [`diagnostics/teacher_ece_grid/teacher_ece_grid.json`](diagnostics/teacher_ece_grid/teacher_ece_grid.json)):

| T | Stage1 | Primary | VAE9182 |
|---|---|---|---|
| 0.85   | 0.0454 | 0.0495 | 0.0250 |
| 1.00   | 0.0378 | 0.0396 | **0.0136** |
| 1.3406 | **0.0159** | 0.0285 | 0.0627 |
| 1.70   | 0.0429 | 0.0702 | 0.1454 |
| 2.20   | 0.1270 | 0.1789 | 0.2622 |

İki VICH öğretmeni T>1'de **U** çizerken VAE9182 T>1'de **monoton bozuluyor**. Kurtarılacak bir
şeyi olmayan öğretmende her müdahale saf hasardır.

---

## B-001 — Öğretmen ECE'si (doğruluğu değil) öğrenci sonucunu yordar · `KAPALI` (gözlemsel)

3/3 öğretmende monotonik: en iyi kalibre olan öğretmen (VAE9182), **en düşük kendi doğruluğuna
sahip olmasına rağmen** en iyi öğrenciyi veriyor.

| Öğretmen | Kendi acc | Öğretmen ECE | Öğrenci acc (3 tohum) | Öğrenci ECE |
|---|---|---|---|---|
| VAE9182 | 91.82% (en düşük) | 0.0136 | **90.276 ± 0.156** (en iyi) | **0.0273 ± 0.0015** |
| Stage1  | 92.24% (en yüksek) | 0.0378 | 89.744 ± 0.055 | 0.0631 ± 0.0046 |
| Primary | 92.01% | 0.0396 | 89.570 ± 0.070 | 0.0608 ± 0.0073 |

**Uyarı (kendi erken ifademin düzeltmesi):** monotonluk öğretmen-ECE → **öğrenci doğruluğu**
ekseninde 3/3'tür. Öğretmen-ECE → **öğrenci ECE**'sinde Stage1 ile Primary yer değiştirir
(0.0378 < 0.0396 ama 0.0631 > 0.0608). "Her iki eksende de 3/3" demek yanlıştır.

**Sınır:** n=3 öğretmen, gözlemsel, ve üç öğretmen 3 karışık faktörde birbirinden ayrılıyor
(head mimarisi, augmentasyon yığını, tohum) — bkz. `diagnostics/P0_teacher_recipe_diff_report.md`.
Nedensellik iddiası tek başına buradan çıkarılamaz; B-005 bunun için var.

---

## B-002 — Gate (belirsizlik-kapılı alfa) ÖLÜ · `KAPALI` (D1 = B)

Üç sinyal kalitesinde test edildi, üçünde de kazanç yok:

| Sinyal | Kalite | Sonuç |
|---|---|---|
| `mean_logvar` (varsayılan) | AUROC < 0.5 (ters) | −0.33 / −0.39 / +0.03 pp |
| `target_logvar` (en iyi gerçek) | Stage1 AUROC 0.70 | +0.06 pp |
| `target_logvar` | **Primary AUROC 0.84 (en yüksek)** | **−0.46 pp (en kötü sonuç)** |
| **oracle (sentetik, kusursuz)** | mükemmel | **89.67 vs 90.06 baseline — yine kaybetti** |

**Karar:** kusursuz bilgiyle bile kaybettiği için sorun sinyal kalitesi değil, **mekanizmanın
kendisi**. Örnek-başına alfa-harmanlama ekseninde bu veri kümesinde headroom yoktur.
Sinyal kalitesini artırmaya yönelik hiçbir yeni koşu açılmayacak.

### ⚠️ GÜNCELLEME 2026-08-01 — kapanış gerekçesi DEĞİŞTİ, kapanış değil

Yukarıdaki "üçünde de kazanç yok" çerçevesi eksik. P2 (29-30 Tem) oracle kolunu **sınıf-ağırlığı
eşleşmiş temiz bir kontrole** karşı n=3'e çıkardı ve tablo değişti: eski (kirli) kontrole karşı
ECE-nötr *görünen* aynı koşular, temiz kontrole karşı **ΔECE +0.0056, 3/3 aynı işaret, kontrolün
tohum sd'sinin 2.08 katı** okuyor. Eksik kontrol gerçek bir kalibrasyon hasarını maskeliyormuş.
Yani **"hiçbir şey yapmıyor" değil, "kalibrasyonu bozuyor"**. Ön-kayıt: `PREREGISTRATIONS.md` A8.

P5 (31 Tem – 1 Ağu, 6 koşu) aynı manipülasyonu stage1 ve primary'de n=3'te tekrarladı.
**Tekrarlanmadı** — donmuş eşik harfiyen uygulandı ve iki kol da düştü:

| öğretmen | ΔECE @swa | işaretler | bar | \|ΔECE\|/bar | hüküm |
|---|---|---|---|---|---|
| stage1 | +0.0015 ± 0.0036 | `+-+` | 0.0021 | 0.74× | **ÇÖZÜNMEDİ** |
| primary | +0.0004 ± 0.0053 | `+-+` | 0.0033 | 0.11× | **ÇÖZÜNMEDİ** |
| *vae9182 (P2)* | *+0.0056* | `+++` | *0.0027* | *2.08×* | *KURULU* |

**ÇÖZÜNMEDİ ≠ etki yok** — bar kolun kendi tohum gürültüsünün iki katı; altındaki bir etki
ölçülemedi demektir. *"Gate stage1/primary'de kalibrasyonu bozmuyor"* cümlesi yazılamaz.

**Kapanış bundan sonra iki kollu yazılacak:**
1. **Koşulsuz:** kusursuz bilgiyle bile hiçbir öğretmende doğruluk kazancı yok
   (Δacc @swa: stage1 −0.22, primary −0.01, vae9182 −0.23). Kapanış asıl buna dayanıyor ve
   P5 bunu iki öğretmen ekleyerek **güçlendirdi**.
2. **VAE9182'ye koşullu:** kalibrasyon hasarı yalnız orada kuruldu.

"Hiçbir yeni koşu açılmayacak" cümlesi de aşıldı: P2 (5 koşu), P4 (6 kontrol) ve P5 (6 koşu)
tam olarak bu ekseni sınamak için açıldı. Artefaktlar:
`diagnostics/p2_gate_oracle/p2_verdict.md`, `diagnostics/p5_oracle_replication/p5_verdict.md`.

---

## B-003 — G2G (Gauss→Gauss) nötr · `KAPALI`

3-tohum eşleştirilmiş delta (baseline'a karşı): Stage1 **+0.087**, Primary **−0.261**,
VAE9182 **+0.022**. İşaret tutarsız, büyüklük tohum sd'sinin altında.

Sadece `kl` modu koşuldu; `w2` hiç denenmedi ve **denenmeyecek** — mod seçimi, üç öğretmende de
işaret tutmayan bir etkinin ikinci dereceden ayrıntısıdır.

---

## B-004 — F1.0 "combined" bileşimi gerçek bir kazanç DEĞİL · `KAPALI`

`combined_500e` = 90.569 ± 0.160 rakamı tek değişkenli bir kazanç gibi sunulamaz. 3-tohum
eşleştirilmiş marjinallere ayrıştırıldığında:

| Bileşen | Δacc (pp) | Δ ECE | Yorum |
|---|---|---|---|
| bütçe (400e→500e) | +0.043 ± 0.111 | +0.0026 | null |
| adaptive_t | +0.033 ± 0.053 | **−0.0034 (3/3 tohum aynı işaret)** | acc null, **ECE kaldıracı gerçek** |
| g2g | +0.217 ± 0.342 | +0.0047 | işaret değiştiriyor (+0.52 / −0.26 / +0.39) = gürültü |
| **TOPLAM** | **+0.293 ± 0.192** | +0.0312 | n=3, p ≈ 0.12 — anlamlı değil |

**Karar:** 90.57 bir başlık rakamı olarak kullanılamaz.

> ### ⚠️ DÜZELTME (26 Tem) — "adaptive_t bir kalibrasyon kaldıracıdır" iddiası GERİ ÇEKİLDİ
>
> Bu bölüm önce şöyle diyordu: *"Bu bloktan çıkan tek gerçek sinyal, adaptive_t'nin bir
> kalibrasyon kaldıracı olmasıdır."* Yukarıdaki **−0.0034** değeri **500e combined bloğunun
> içindeki bir marjinaldir** (karşılaştırılan iki kol da g2g içeriyor ve 500e bütçesinde).
>
> **Temiz, tek değişkenli 400e karşılaştırması (baseline ↔ adaptive_t, tohum-eşleştirmeli, 3
> öğretmen × 3 tohum) işareti TERSİNE çeviriyor** — bkz. B-013. adaptive_t o karşılaştırmada
> ECE'yi **kötüleştiriyor** (+0.0025 / +0.0047 / +0.0026).
>
> Yani −0.0034, kendi bağlamı (500e + g2g) dışına **genellenmiyor**. Genel bir "adaptive_t
> kalibrasyon kaldıracıdır" cümlesi bu veriyle desteklenmiyor ve makalede kullanılmayacak.

---

## B-005 — Öğretmen sıcaklığı → öğrenci kalibrasyonu: NEDENSEL doz-yanıt · `KAPALI` (11/11 koşu)

Makalenin pozitif çekirdeği. Stage1 öğretmeninin logitleri post-hoc T'ye bölünür; **mimari,
reçete, öğretmen doğruluğu sabittir** — sadece kalibrasyon değişir. 3 tohum:

| T | Öğretmen ECE | Öğrenci acc | Öğrenci ECE |
|---|---|---|---|
| 0.85 | 0.0454 | 89.787 ± 0.093 | 0.0762 ± 0.0003 |
| 1.00 | 0.0378 | 89.744 ± 0.055 | 0.0631 ± 0.0046 |
| **1.3406 (T\*)** | **0.0159** | **89.950 ± 0.055** | **0.0339 ± 0.0019** |
| 1.70 | 0.0429 | 89.646 ± 0.055 | 0.0561 ± 0.0047 |
| 2.20 | 0.1270 | 89.722 ± 0.252 | 0.1179 ± 0.0073 |

- Öğrenci ECE'de ders kitabı **U**; minimum tam olarak öğretmenin kendi T\*'ında.
- T\*'ta ECE **−0.0292 (−46%)**; sd'ler çok küçük (≤0.0073).
- Doğruluk **büyük ölçüde düz** (aralık ~0.30 pp). T\*'ta +0.206 pp var ve bu baseline sd'sini
  (0.055) ~3.7× aşıyor, ama asıl etki kalibrasyondadır.
- Öğretmen ECE ↔ öğrenci ECE aynı ızgarada birlikte hareket ediyor (Pearson ≈ 0.96,
  Spearman = 0.90, n=5).

**Tez cümlesindeki düzeltme:** "sıcaklık öğrenci **doğruluğunu** monotonik kaydırır" ifadesi
**kendi verimizle çelişir**. Doğru ifade: post-hoc sıcaklık ölçekleme öğrenci **kalibrasyonunu
(ECE)** kaydırır; **doğruluk büyük ölçüde değişmez**, T\*'ta küçük bir optimum dışında.

Figür: [`diagnostics/p1_dose_response/p1_dose_response.png`](diagnostics/p1_dose_response/p1_dose_response.png)

---

## B-006 — VICH head'i küçük öğrencide: KALİBRASYON ekseninde GO · `KAPALI` (3/3 koşu)

Tek değişken öğrenci head'i (`vich` ↔ `linear`); öğretmen, omurga, reçete, tohumlar aynı.

| tohum | vich acc | linear acc | Δacc | vich ECE | linear ECE | ΔECE |
|---|---|---|---|---|---|---|
| 42 | 90.059 | 90.156 | **+0.098** | 0.0285 | 0.0344 | +0.0059 |
| 1  | 90.352 | 90.319 | −0.033 | 0.0282 | 0.0361 | +0.0079 |
| 43 | 90.417 | 90.287 | −0.130 | 0.0251 | 0.0300 | +0.0049 |
| **ort** | **90.276 ± 0.156** | **90.254 ± 0.070** | **−0.022 ± 0.093** | **0.0273 ± 0.0015** | **0.0335 ± 0.0026** | **+0.0062 ± 0.0013** |

- **Doğruluk: NULL.** İşaretler `+ − −`, ortalama tohum gürültüsünün içinde.
- **ECE: GERÇEK.** İşaretler `+ + +` (3/3), sd yalnızca 0.0013. VICH, linear-head öğrencinin
  ECE'sinin **%18.6**'sını siliyor.

**Karar: GO — ama yalnızca kalibrasyon ekseninde.** VICH doğruluk katkısı olan bir bileşen
olarak sunulamaz; ucuz bir **öğrenci-tarafı kalibrasyon kaldıracı** olarak sunulur. Bu, POSTERv2
tarafında "büyük modelde verim artırmıyor" gözlemiyle çelişmez — orada doğruluk ölçülmüştü.

**Not — tek tohumun neden yeterli olmadığının kanıtı:** yalnız tohum 42'ye bakan biri
"linear head daha iyi (+0.098 pp)" sonucuna varırdı. 3 tohum işareti tersine çeviriyor.

Artefakt: [`diagnostics/vich_isolation/vich_isolation_verdict.json`](diagnostics/vich_isolation/vich_isolation_verdict.json)

---

## B-007 — Kalibrasyon-koşullu headroom yasası · `KAPALI` (12/12 koşu, 3 tohum)

**İddia:** bir mekanizmanın kazanabileceği pay, öğretmenin yanlış-kalibrasyonuyla orantılıdır.
İyi kalibre bir öğretmende düzeltilecek bir şey yoktur — dolayısıyla kalibrasyon-düzeltici her
mekanizma orada null çıkar.

Bu tek yasa, birbirinden bağımsız görünen dört null'u tek nedene bağlar: **B-002** (gate ölü),
**B-003** (G2G nötr), **B-004** (F1.0 null) — üçü de en iyi kalibre öğretmen (VAE9182, ECE 0.0136)
üzerinde ölçüldü — ve **B-005** (aynı mekanizma, kötü kalibre Stage1'de −46% ECE).

Öğretmen tarafı headroom zaten ölçüldü (yukarıdaki envanter): Stage1 **+0.0220**,
Primary **+0.0199**, VAE9182 **−0.0011**.

**Ön-kayıtlı, yanlışlanabilir tahmin:** VAE9182 doz-yanıt eğrisi Stage1'in derin U'sunu
**göstermeyecek**; minimumu T=1.0'da kalacak ve T>1 monoton bozulacak. Öğrenci tarafında
gerçekleşen ΔECE ≈ 0 olacak (Stage1'de +0.0292 idi).
**Yasa yanlışlanır eğer** VAE9182 öğrencisi T≠1'de kendi derin U'sunu gösterirse.

### Tohum-42 eğrisi tamamlandı (25 Tem 02:47) — tahmin KONFİRME, hem de daha güçlü biçimde

| T | Öğretmen ECE | Öğrenci ECE (tohum 42) | Öğrenci acc |
|---|---|---|---|
| 0.85 | 0.0250 | 0.0354 | 90.156 |
| **1.00** | **0.0136** | **0.0273 ← minimum** | 90.276 (3 tohum) |
| 1.3406 | 0.0627 | 0.0655 | 90.222 |
| 1.70 | 0.1454 | 0.1391 | 89.993 |
| 2.20 | 0.2622 | 0.2285 | 90.189 |

Öğrenci ECE'si öğretmen ECE'sinde **tam monoton** (Pearson = Spearman = **+1.000**, n=5).
**U yok**, minimum tam T=1.0'da. Tahmin "düz eğri" idi; gerçekleşen bundan daha keskin:
**T>1'de monoton hasar.**

**Yasanın çivisi — aynı düğme, ters işaret.** T=1.3406'da, birebir aynı müdahale:

| Öğretmen | Öğretmen ECE 1.0 → 1.34 | Öğrenci ECE 1.0 → 1.34 | Sonuç |
|---|---|---|---|
| Stage1 (kötü kalibre) | 0.0378 → 0.0159 | 0.0631 → **0.0339** | **−46% (iyileşme)** |
| VAE9182 (iyi kalibre) | 0.0136 → 0.0627 | 0.0273 → **0.0655** | **+140% (hasar)** |

Aynı düğmenin işaretini belirleyen tek şey, öğretmende **sökülecek yanlış-kalibrasyon olup
olmadığı**. Bu, B-002/B-003/B-004 null'larının neden null olduğunun doğrudan açıklamasıdır:
üçü de VAE9182 üzerinde, yani headroom'un sıfır olduğu yerde ölçüldü.

**Havuzlanmış (iki öğretmen, 10 nokta): Pearson +0.992, Spearman +0.976.** Tek yasa.
Doğruluk her iki öğretmende de duyarsız (U-derinliği 0.30 / 0.28 pp).

### FINAL — 12/12 koşu, 3 tohum (25 Tem 19:13). Yasa KONFİRME, kapatıldı.

| T | Öğretmen ECE | Öğrenci ECE (3 tohum) | Öğrenci acc (3 tohum) |
|---|---|---|---|
| 0.85 | 0.0250 | 0.0356 ± 0.0015 | 90.178 ± 0.015 |
| **1.00** | **0.0136** | **0.0273 ± 0.0015 ← minimum** | 90.276 ± 0.156 |
| 1.3406 | 0.0627 | 0.0767 ± 0.0124 | 90.222 ± 0.160 |
| 1.70 | 0.1454 | 0.1425 ± 0.0110 | 89.765 ± 0.218 |
| 2.20 | 0.2622 | 0.2285 ± 0.0054 | 90.113 ± 0.055 |

Tam monoton, **Spearman = +1.000** (n=5), minimum tam T=1.0'da. Tohum-42'deki tek-tohum okuması
3 tohumda aynen doğrulandı; hiçbir nokta işaret değiştirmedi.

**Yasanın çivisi — aynı düğme, ters işaret (her ikisi de 3 tohum):**

| Öğretmen | Öğretmen headroom | Öğrenci ECE, T=1 → T=1.3406 | Sonuç |
|---|---|---|---|
| Stage1 (kötü kalibre) | **+0.0220** | 0.0631 → **0.0339** | **−46% iyileşme** |
| VAE9182 (iyi kalibre) | **−0.0011** | 0.0273 → **0.0767** | **+181% hasar** |

**Headroom tablosu (ikisi de tam):**

| Öğretmen | Öğretmen tarafı headroom ΔECE | Öğrenci tarafı gerçekleşen ΔECE | Öğrenci en iyi T | acc U-derinliği |
|---|---|---|---|---|
| Stage1 | 0.0220 | **0.0292** | 1.3406 | 0.304 pp |
| VAE9182 | 0.0017 | **0.0000** | **1.00** | 0.511 pp |

**Havuzlanmış (2 öğretmen × 5 nokta): Pearson +0.992, Spearman +0.988.** Tek yasa; iki öğretmen,
iki head tipi, tüm sıcaklık aralığı.

**Doğruluk tarafı — dürüst sınır:** acc U-derinlikleri (0.30 / 0.51 pp) küçük *ama* tohum
sd'leri de büyük (0.156–0.218). Yani doğruluk bu ızgarada **duyarsız ve gürültülü**; yasa bir
**kalibrasyon** yasasıdır ve doğruluk için aynı güçte iddia edilemez.

**Sonuç:** B-002 (gate ölü), B-003 (G2G nötr), B-004 (F1.0 null) — üçü de VAE9182 üzerinde, yani
headroom'un ölçülü olarak **sıfır** olduğu yerde ölçülmüştü. Dört bağımsız null tek nedene bağlandı.

**Seçim dayanıklılığı (B-014, 26 Tem):** yasa üç checkpoint'te de aynı — Stage1 ρ=+0.900 /
argmin T=1.3406, VAE9182 ρ=+1.000 / argmin T=1.0, **best, swa ve last'ta değişmeksizin**.
Yani B-007 `best_epoch` seçim yanlılığından **etkilenmiyor**; raporlama SWA'dan yapılabilir.

**Kalan sınır:** headroom *büyüklüklerinin* karşılaştırması öğretmenler arasıdır ve iki öğretmen
head/augmentasyon/tohumda da farklıdır (METHODS_DATA §3.2). Ancak **her iki eğrinin kendisi
öğretmen-içi bir manipülasyondur**, dolayısıyla nedensellik confound'lardan bağımsızdır.
(Mekanizma tarafında öğretmen-içi test: **B-010**, sonuç NULL.)

Figür: [`diagnostics/p1_dose_response/two_teacher_overlay.png`](diagnostics/p1_dose_response/two_teacher_overlay.png)
· üretici: [`diagnostics/p1_two_teacher_overlay.py`](diagnostics/p1_two_teacher_overlay.py)

---

## B-008 — FERPlus insan-oyu hizalaması: kalibrasyon ≠ insan dağılımı · `KAPALI` (0 GPU)

FER'in neredeyse hiçbir görü görevinde bulunmayan avantajı: FERPlus **ham 10-oylayıcı dağılımını**
verir, yani ölçülmüş bir *ground-truth dağılımı*. Bu, "kalibrasyon" tartışmasını soyut olmaktan
çıkarır.

FERPlus VICH öğretmeni (kendi acc **91.37%**, n=3153), aynı bölme üzerinde üç ayrı ölçüt:

| Ölçüt | En iyi T | Değer @ o T | Değer @ T=1 |
|---|---|---|---|
| ECE (15-kutu, sert etiket) | **0.46** | 0.0084 | 0.1282 |
| NLL (sert etiket) | **0.50** | 0.2563 | 0.3399 |
| **JSD (10-oylayıcı dağılımı)** | **0.74** | 0.0440 | 0.0492 |

**Bulgu 1 — öğretmen aşırı yumuşak.** Üç optimum da 1.0'ın **altında**: yumuşak-hedefle
(`ce_kld_loss`) eğitilen bu öğretmen hem sert etiketlere hem insan oylarına göre
**az-güvenli**. ECE(T=1) = 0.1282, %91.4 doğrulukta bir model için çok yüksek.

**Bulgu 2 (asıl bulgu) — üç ölçüt ÇAKIŞMIYOR.** Sert-etiket kalibrasyonu (0.46–0.50) insan
dağılımının gerektirdiğinden (**0.74**) belirgin biçimde daha fazla keskinleştiriyor — aradaki
fark ~%60. Yani **ECE'yi argmax etiketlere karşı optimize etmek, insan mutabakatının ötesine
taşar.** "Kalibre etmek = insanlarla hizalamak" demek bu veriyle **yanlış** olur; ikisi ilişkili
ama ayrı hedeflerdir. Bunu ancak ham oyu olan FER veri kümeleri gösterebilir.

**Bulgu 3 — entropi hizalaması.** T=0.74'te öğretmenin ortalama entropisi (**0.412**) insan
ortalama entropisine (**0.440**) neredeyse oturuyor; T=1'de 0.612 ile fazla belirsiz.
Örnek-başına insan-entropisi ↔ öğretmen-entropisi: **Pearson 0.724 / Spearman 0.732** — öğretmen
insanların nerede anlaşamadığını gerçekten biliyor.

**Oy normalizasyonu — denetlendi, eğitimde HATA YOK (25 Tem):**
`configs/FERPlus_majority_metadata.csv`'de 8 duygu oyu satırların **%37.3'ünde** 10'a toplanmıyor
(FERPlus 'unknown'/'NF' oyları önceden atılmış) ve veri katmanı gerçekten sabit `votes_sum`'a
bölüyor (`dataset_utils/image_dataset.py:63-70`) → bu katmanın çıktısı alt-normalize bir vektör.

**Ancak iki tüketicinin ikisi de satır-bazlı yeniden normalize ediyor:**
- öğretmen eğitimi: `loss_encoder.py:22-26` (`labels_em / labels_em.sum(dim=1)`)
- KD öğrenci eğitimi: `train_affectnetplus_kd.py:263` → `kd_common.py:485-488`
  (`normalize_probability_targets`)

Sabit 10'a bölüp ardından satır toplamına normalize etmek, doğrudan satır toplamına normalize
etmeye **birebir eşittir** (10 sadeleşir). Dolayısıyla veri katmanındaki sabit bölme ispatlı
biçimde **etkisiz**; **hiçbir FERPlus koşusu etkilenmemiştir**, işaretlenecek koşu ve düzeltme
pilotu yoktur.

Etkilenen tek yer bu analizin ilk sürümüydü: CSV'yi doğrudan okuyup her iki normalizasyon
katmanını da atlıyordu. Düzeltildi (satır-bazlı normalizasyon) ve yukarıdaki sayılar düzeltilmiş
sürümden gelmektedir.

Artefakt: [`diagnostics/ferplus_jsd/ferplus_jsd.json`](diagnostics/ferplus_jsd/ferplus_jsd.json)

---

## B-010 — Kasıtlı miskalibrasyon: öğretmen-İÇİ nedensellik · `KAPALI` — sonuç **NULL** (4 koşu)

> **Bu bölüm sonuçlar gelmeden yazıldı (25 Tem 14:36).** Tahmin ve kill-switch önceden sabit;
> sonuç geldiğinde bu metin **değiştirilmeyecek**, altına sonuç eklenecek.

**Boşluk:** B-007 şu an *öğretmenler arası* bir yasa (Stage1 vs VAE9182). Ama iki öğretmen head
mimarisi, augmentasyon ve tohumda da farklı (bkz. `diagnostics/P0_teacher_recipe_diff_report.md`).
Yasayı **tek öğretmen içinde** kurmak, bu üç karışık faktörü tamamen eler.

**Tasarım:** iyi kalibre VAE9182'nin logitleri **sabit** T0 ile ön-ölçeklenir; T0, önbelleklenmiş
öğretmen logitleri üzerinde kapalı-form bisection ile seçildi:

> `confidence_ece(vae9182_logits, labels, T0 = 0.7311) = 0.0378` = **Stage1'in doğal ECE'si**

Sonra `--adaptive-t-enable` AÇ/KAPA × 2 tohum (42, 1). T0 iki kolda da aynı; **tek değişken
mekanizmanın varlığı**.

**T0 neden 1'in ALTINDA (kritik nokta):** ECE 0.0378'i veren **iki** sıcaklık var — T0=0.731
(aşırı-**güvenli**) ve T0≈1.25 (aşırı-**yumuşak**). ECE'nin *büyüklüğünü* eşitlemek
yanlış-kalibrasyonun *yönünü* eşitlemez. Stage1 doğal olarak aşırı-güvenlidir (T\*=1.35 > 1, yani
yumuşatılmaya ihtiyacı var). Stage1'in rejimini üretmek için VAE9182'yi de aşırı-güvenli yapmak
gerekir → **keskinleştirme, T0 < 1**. T0=1.25 seçmek **ters** patolojiyi enjekte eder ve Stage1
hakkında hiçbir şey test etmez.

**Dejenerasyon neden yok:** KD softmax'ı `softmax(z / (T0 · T_mek))` — iki sıcaklık **çarpımsal**
birleşir. Bu yüzden mekanizma açıkken T0'ı **süpürmek** dejeneredir (mekanizmanın kendi
sıcaklığını süpürmekle aynı şey) ve doz-yanıt olarak raporlanamaz. Burada T0 **sabit**, mekanizma
toggle'lanıyor → tek değişkenli, temiz karşılaştırma. `train_rafdb_kd.py`'deki guard bu yüzden
silinmedi; açık opt-in (`--allow-tempscale-with-mechanism`) ile aşıldı ve istisna `run_args.json`
+ manifest'e yazılıyor.

**Ön-kayıtlı tahmin (ve çerçevenin dürüst düzeltmesi):** adaptive_t doğal VAE9182'de **ölü
değildi** — zayıftı: acc +0.054 pp (null) ama **ECE −0.0034, 3/3 tohum tutarlı** (B-004). Yani
doğru çerçeve "**ölü → canlı**" değil, "**zayıf → güçlü**". Enjekte edilmiş miskalibrasyon
altında ECE faydasının büyümesi bekleniyor (Stage1'in gerçek miskalibrasyonu söküldüğünde görülen
−0.0292'ye doğru). **Gerçekten ölü olanlar gate ve G2G'dir**; bu pilot geçerse asıl keskin takip
gate olur (B-002'nin oracle testi yalnızca *sıfır headroom* rejiminde yapıldığı için gate'in
miskalibrasyon altında da ölü olduğunu **dışlamıyor**).

**KILL-SWITCH:** önce 2 tohum. ECE deltası **her iki tohumda da** doğal −0.0034'ü geçmezse dur,
3. tohum harcanmaz.

**Yanlışlanma koşulu:** T0=0.7311 ile öğretmen ECE'si Stage1 seviyesine çekildiği hâlde adaptive_t
hâlâ ≈−0.0034'te kalırsa, "headroom mekanizmayı besler" iddiası öğretmen-içi düzeyde çöker ve
B-007 yalnızca öğretmenler-arası (karışık faktörlü) bir gözlem olarak kalır.

Launcher: [`rafdb_p3_then_miscal_chain.ps1`](rafdb_p3_then_miscal_chain.ps1) (Faz MISCAL, 4 koşu)

### FINAL SONUÇ (26 Tem 11:47) — **NULL**, kill-switch tetiklendi, 3. tohum harcanmayacak

> Ön-kayıt metni yukarıda **değiştirilmedi**. Bu bölüm sonucu ekler.

| tohum | adaptive_t KAPALI (acc / ECE) | AÇIK (acc / ECE) | d_ECE |
|---|---|---|---|
| 42 | 90.156 / 0.0464 | 90.449 / 0.0475 | **+0.0011** |
| 1 | 90.515 / 0.0442 | 90.385 / 0.0389 | **−0.0053** |
| **ort** | | | **−0.0021 ± 0.0032, işaretler `+ −`** |

**Karar: NULL.** İşaretler tohumlar arasında çelişiyor ve sd (0.0032) |ortalama|'yı (0.0021)
aşıyor. Bu, kampanyanın kendi ölçütüyle gürültüdür — G2G'yi B-003'te öldüren kuralın aynısı.
seed-1'deki umut verici −0.0053 **seed-42'de replike olmadı**.

**Kendi kill-switch kodumdaki kusur (kayda geçsin):** ilk sürüm "PASS: 3. tohumu harca" dedi,
çünkü barı *yeni ölçülen doğal değere* (+0.0026) göre kuruyordu — pozitif (kötü) bir sayıya. Böyle
bir barda **ECE'yi kötüleştiren** bir etki ("kötü bir referanstan daha az kötü") geçer sayılıyordu.
Düzeltilen kural iki ölçüt istiyor: (1) her tohum **ön-kayıtlı** −0.0034 barının altında,
(2) işaret tohumlar arasında tutarlı. İkisi de sağlanmıyor.

**Ön-kaydımdaki iki fazla-iddianın düzeltmesi:**
1. Ön-kayıt "doğal adaptive_t zayıf bir ECE kaldıracı (−0.0034)" diyordu. B-013 bunu çürüttü —
   doğal değer aslında **+0.0026** (kötüleştiriyor). Yani testin çıkış noktası baştan hatalıydı.
2. Ön-kayıt "B-007 şu an *öğretmenler arası* bir yasa" diyordu. Bu **fazla temkinliydi**: hem
   Stage1 hem VAE9182 doz-yanıt eğrisi **tek öğretmen içinde** sıcaklık manipülasyonudur, yani
   öğretmen-içi nedensellik B-007'de **zaten vardı**. Öğretmenler arası olan tek şey headroom
   *büyüklüklerinin karşılaştırılmasıydı*. Dolayısıyla **B-007 bu testin sonucundan bağımsız
   olarak ayakta** — B-010'un null çıkması B-007'yi zayıflatmıyor.

**Net katkı:** B-010, B-013'ü pekiştiriyor. adaptive_t, sıcaklık-biçimli miskalibrasyonu bile
tutarlı biçimde düzeltemiyor. "Headroom mekanizmayı besler" iddiası **mekanizmalar için
kurulamadı**; headroom'u hasat edebilen tek araç post-hoc sıcaklık ölçeklemedir (B-007).

**Yapılmayacak:** bu ekseni 3. tohumla veya gate ile uzatmak. Gate zaten B-002'de oracle
sinyaliyle bile ölüydü; adaptive_t buradaki en umutlu mekanizmaydı ve o da tutmadı.

> Ön-kayıt metni yukarıda **değiştirilmedi**; sonuç buraya eklendi.

Ön-ölçeklenmiş öğretmen: T0=0.7311 → ECE **0.0378** (= Stage1 seviyesi), headroom **0.0260**
(doğal VAE9182: ECE 0.0136, headroom 0.0017).

| tohum | adaptive_t KAPALI (acc / ECE) | adaptive_t AÇIK (acc / ECE) | d_ECE |
|---|---|---|---|
| 1 | 90.515 / 0.0442 | 90.385 / 0.0389 | **−0.0053** |
| 42 | 90.156 / 0.0464 | *(koşuyor, ~11:45)* | — |

**Yön tahminle uyumlu ve ön-kayıttan daha güçlü — ama n=1, karar YOK.** Karşılaştırma:

| Koşul | Öğretmen headroom | adaptive_t d_ECE |
|---|---|---|
| Doğal VAE9182 (B-013) | 0.0017 | **+0.0026** (kötüleştiriyor) |
| Miskalibre VAE9182 (T0=0.7311) | 0.0260 | **−0.0053** (iyileştiriyor, n=1) |

Yani beklenen "zayıf → güçlü" değil, **işaret DÖNMESİ**. Eğer seed 42'de de tutarsa, bu B-013'ün
yanlışlamasıyla birlikte anlamlı bir mekanizma açıklaması verir:

> adaptive_t **sıcaklık-biçimli** yanlış-kalibrasyonu düzeltebiliyor (T0 ile enjekte edilen tam
> olarak budur), ama gerçek bir öğretmenin **doğal** yanlış-kalibrasyonunu düzeltemiyor
> (Stage1/Primary'de başarısız) — çünkü doğal miskalibrasyon global bir sıcaklık kayması değil.

**Ek doğrulama (B-007 ile tutarlı):** miskalibrasyon enjekte etmek öğrencinin ECE'sini
0.0282 → 0.0442'ye çıkardı (öğretmen ECE 0.0136 → 0.0378). B-011'in doğrusal kestirimi 0.0533
öngörüyordu; gerçekleşen 0.0442 — yön doğru, büyüklük kestirimin altında.

**seed 42 gelince** kill-switch kuralı uygulanacak ve sonuç buraya eklenecek.

---

## B-013 — "Mekanizma faydası ∝ headroom" NAİF OKUMASI YANLIŞLANDI · `KAPALI` (9 koşu çifti)

P3 tamamlandı: adaptive_t artık **3 öğretmende de 3 tohum**. Temiz, tek değişkenli 400e
karşılaştırma (baseline ↔ adaptive_t, tohum-eşleştirmeli). Negatif d_ece = adaptive_t daha iyi.

| Öğretmen | Öğretmen headroom | d_ECE (3 tohum) | İşaretler | d_acc (3 tohum) |
|---|---|---|---|---|
| Stage1 | **0.0220** (yüksek) | **+0.0025 ± 0.0026** | `+ + −` | +0.217 ± 0.156 |
| Primary | **0.0206** (yüksek) | **+0.0047 ± 0.0031** | `+ + +` | **−0.435 ± 0.081** |
| VAE9182 | **0.0017** (sıfır) | **+0.0026 ± 0.0028** | `+ + −` | +0.043 ± 0.409 |

Yukarıdaki tablo **best (doğrulukla seçilmiş) checkpoint'tendir**.

> ### ⚠️ DÜZELTME (26 Tem) — "adaptive_t ECE'yi kötüleştiriyor" YÖN iddiası geri çekildi
>
> B-014'ün seçim denetimi gösterdi ki bu tablodaki yön **checkpoint seçimine bağlı**:
>
> | | @best | @swa | @last |
> |---|---|---|---|
> | Stage1 | +0.0029 `[++-]` NULL | −0.0011 `[++-]` NULL | −0.0046 `[+--]` NULL |
> | **Primary** | **+0.0047 `[+++]` KÖTÜ** | **+0.0023 `[+++]` KÖTÜ** | **−0.0043 `[---]` İYİ** |
> | VAE9182 | +0.0024 `[++-]` NULL | −0.0042 `[--+]` NULL | +0.0009 `[-++]` NULL |
>
> Primary'de etki **best ve swa'da 3/3 tutarlı KÖTÜ, last'ta 3/3 tutarlı İYİ**. Aynı koşular,
> aynı tohumlar, zıt sonuç. Dolayısıyla "kötüleştiriyor" denemez.
>
> **B-013'ün ASIL SONUCU AYAKTA ve daha güçlü:** adaptive_t hiçbir checkpoint'te **tutarlı bir
> iyileşme** üretmiyor ve yönü bile sabit değil. Yani headroom'u yüksek öğretmenlerde de
> mekanizma headroom'u hasat edemiyor — naif genişletme yanlışlanmış durumda. Değişen tek şey:
> "kötüleştiriyor" yerine **"yönü bile çözünmüyor; etki checkpoint artefaktının altında"**.

**Bu, B-007'nin naif genişletmesini yanlışlıyor.** "Öğretmen headroom'u varsa kalibrasyon-düzeltici
her mekanizma kazanır" **doğru değil**. B-007 (post-hoc sıcaklık ölçekleme) headroom'u kullanabiliyor;
adaptive_t kullanamıyor. Yani headroom bir **üst sınır**dır, bir garanti değil:

> headroom = mekanizmanın kazanabileceği **potansiyel**; onu gerçekten hasat etmek mekanizmanın
> yanlış-kalibrasyonun **yapısına** uymasını gerektirir.

Ayrıca doğruluk tarafı da güvenilmez: Primary'de adaptive_t **−0.435 pp, 3/3 tutarlı**.

**Yapılmayacak:** adaptive_t'yi hiçbir tabloda "kalibrasyon bileşeni" olarak sunmak.

Üretici: [`diagnostics/adaptive_t_headroom_table.py`](diagnostics/adaptive_t_headroom_table.py) ·
artefakt: [`diagnostics/adaptive_t_headroom/adaptive_t_headroom.json`](diagnostics/adaptive_t_headroom/adaptive_t_headroom.json)

---

## B-014 — Seçim denetimi: epoch seçimi mekanizma etkilerinden BÜYÜK · `KAPALI` (290 ölçüm)

Kullanıcının işaret ettiği metodolojik açık. `best_epoch`, raporlamanın yapıldığı **aynı 3068
görüntü** üzerinde **top-1 doğrulukla** seçiliyor ([train_rafdb_kd.py:895-900](train_rafdb_kd.py#L895-L900),
[:960-977](train_rafdb_kd.py#L960-L977)) ve ayrı test kümesi yok (METHODS_DATA §1). Seçimden
bağımsız iki checkpoint zaten mevcuttu: `last` (son epoch) ve `swa` (SWA ortalaması).
101 RAF-DB koşusu × 3 checkpoint = **290 ölçüm**, hata yok.

> **⚠️ GÜNCELLEME 2026-08-01 — bu bölümdeki n=101 sayıları ARTIK ALINTILANMIYOR.** Denetim
> kümesi 101 → 116 → 125 → **131**'de donduruldu (`AUDIT_CUTOFF 2026-07-31-06-00-00`,
> `selection_audit_table.py`). Makalede geçen sayı **n=131: best−last +0.766 ± 0.431 pp**,
> best−swa +0.129 ± 0.262 pp (n=118). Aşağıdaki tablo tarihsel kayıt olarak duruyor.
>
> Tahminin dahil etme kümesine duyarsızlığı asıl bulgudur ve tek bir N'den güçlüdür:
> 116/125/131 → +0.781 / +0.769 / **+0.766** pp, toplam yayılım **0.015 pp**. P5'in altı koşusu
> kesmenin dışında kaldı; donmamış üst kümede (n=137) tahmin +0.773 ± 0.426 pp, yani kesmeyi
> kaldırmak da sonucu 0.007 pp oynatıyor. Ayrıntı: `diagnostics/selection_audit/README.md`.

### Seçim optimizmi ne kadar? — üç ayrı sayı, üçü de gerekli

| # | Ölçüm | Ne izole eder | Δacc | ΔECE |
|---|---|---|---|---|
| **(a)** | **saf seçim kazancı** (aşağıda) | yalnız sıra-istatistiği | **+0.643 … +0.769 pp** | *hesaplanamaz* |
| (b) | best − last (n=101) | ÜST SINIR (seçim + geç bozulma) | +0.792 ± 0.464 pp | −0.0036 ± 0.0092 |
| (c) | best − swa (n=88) | seçimsiz **farklı** modele karşı | +0.127 ± 0.249 pp | −0.0018 ± 0.0109 |

**(a) saf seçim kazancı — iki varyant, ve ayrım önemli.** İstenen tanım
`max(TÜM epoch) − mean(son K)` idi; ama bu saf sıra-istatistiği **değil**: global maksimum son-K
penceresinin dışındaysa karşılaştırma iki farklı eğitim rejimini kapsar. Ölçtüm:
**global argmax son-K içinde yalnızca %29 (K=50) / %64 (K=100) koşuda.** Yani endişe gerçekti.
Savunulabilir sayı aynı pencere içindeki saf sıra-istatistiğidir:

| K | **a2 = max(son K) − mean(son K)** ← *ana sayı* | a1 = max(TÜM) − mean(son K) | argmax son-K'da |
|---|---|---|---|
| 50 | **+0.643 ± 0.221 pp** | +0.869 ± 0.492 pp | %29 |
| 100 | **+0.769 ± 0.290 pp** | +0.816 ± 0.288 pp | %64 |

> **Sert cümle (a2 ile kurulur):** *doğrulukla epoch seçmek, hiçbir model değişikliği olmadan,
> yalnızca 50–100 gürültülü değerlendirmenin maksimumunu almaktan **+0.64 – +0.77 pp** doğruluk
> kazandırır (n=101 koşu) — bu, test ettiğimiz her mekanizmanın doğruluk etkisinden büyüktür.*

> **YAYIMLANAN SÜRÜM (11 Ağu 2026).** Yukarıdaki cümle n=101'in tarihsel kaydıdır. Makaledeki
> §2 manşeti donmuş 131 koşudan gelir ve aralık **+0.65 – +0.76 pp**'dir (+0.645 ± 0.203 /
> +0.764 ± 0.259, K=50/100; `diagnostics/selection_audit/selection_gain.json` → `per_k`,
> üretici `selection_gain_estimator.py`). `argmax son-K'da` oranları da güncel kümede
> **%34,4 / %67,2** (yukarıdaki %29 / %64 değil).

**ECE için (a) HESAPLANAMAZ, ve nedeni kayda geçmeli:** `training_log.csv` epoch-başına ECE
tutmuyor (kolonlar: epoch, train/val loss, train/val acc, lr) ve epoch-başına checkpoint
saklanmıyor (yalnız best/last/swa). Bunun için ya epoch-başına ECE loglanmalı ya da epoch-başına
checkpoint tutulmalıydı; ikisi de yok. **Mevcut en yakın kalibrasyon-duyarlı vekil** loglanan
`val_loss` (NLL, proper scoring rule):

| K | val_loss(seçilen epoch) − mean val_loss(son K) |
|---|---|
| 50 | **−0.0169 ± 0.0268** |
| 100 | **−0.0147 ± 0.0175** |

**Negatif** → doğrulukla seçilen epoch'un NLL'i tipik bir geç epoch'tan biraz **daha iyi**.
Bu, ECE tarafındaki bulguyla tutarlı (b/c satırlarında ΔECE de negatif ve küçük). Yani:
**doğruluk şişmesi büyük, kalibrasyon kontaminasyonu ihmal edilebilir** — makalenin kalibrasyon
çekirdeği için tam olarak istenen sonuç.

Üretici: [`diagnostics/selection_gain_estimator.py`](diagnostics/selection_gain_estimator.py) ·
artefakt: `diagnostics/selection_audit/selection_gain.json`

**+0.792 pp**, bu makalede tartışılan neredeyse **her doğruluk etkisinden büyük** (VICH −0.022,
T\* kazancı +0.206, adaptive_t +0.217). ECE tarafında optimizm küçük ve gürültülü
(−0.0036 ± 0.0092) — kalibrasyon iddiaları için iyi haber. SWA hem seçimden bağımsız hem
best'in yalnızca 0.127 pp altında → **raporlama checkpoint'i SWA olmalı.**

### B-007 seçime tamamen DAYANIKLI ✓

| Öğretmen | @best | @swa | @last |
|---|---|---|---|
| Stage1 | ρ +0.900, argmin T=1.3406, ΔECE +0.0289 | ρ +0.900, argmin **T=1.3406**, +0.0303 | ρ +0.900, argmin **T=1.3406**, +0.0336 |
| VAE9182 | ρ +1.000, argmin T=1.0, ΔECE 0.0000 | ρ **+1.000**, argmin **T=1.0**, 0.0000 | ρ **+1.000**, argmin **T=1.0**, 0.0000 |

Üç checkpoint'te de aynı sıralama korelasyonu, aynı argmin, aynı headroom sonucu. **Makalenin
pozitif çekirdeği epoch seçiminden bağımsız.** Bu, B-007'yi zayıflatmıyor — güçlendiriyor.

### Mekanizma iddiaları seçime DAYANIKSIZ ✗

Checkpoint'e göre sonucu değişenler:

| Karşılaştırma | @best | @swa | @last |
|---|---|---|---|
| stage1 / g2g_kl | NULL `[+--]` −0.0017 | **İYİ** `[---]` −0.0042 | NULL `[+-+]` −0.0015 |
| **primary / adaptive_t** | **KÖTÜ** `[+++]` +0.0047 | **KÖTÜ** `[+++]` +0.0023 | **İYİ** `[---]` −0.0043 |
| primary / g2g_kl | NULL `[--+]` −0.0043 | NULL `[+--]` −0.0016 | **İYİ** `[---]` −0.0111 |

> **En önemli tek satır:** `primary/adaptive_t` best **ve** swa'da **3/3 tutarlı kötü**, last'ta
> **3/3 tutarlı iyi**. Aynı koşular, aynı tohumlar. Yani **3 tohumda işaret tutarlılığı, bu
> büyüklükteki etkiler için yeterli kanıt DEĞİL** — aynı karşılaştırma, yalnızca hangi
> checkpoint'in okunduğuna bağlı olarak iki yönde de 3/3 tutarlı çıkabiliyor.

**Bu, negatif bulguları zayıflatmıyor, GÜÇLENDİRİYOR.** İfade artık "etki bulamadık" değil:
**"bu mekanizmaların etkisi, checkpoint seçimi artefaktının altında"** — nicel bir üst sınır.

**Yapılacak:** tüm mekanizma tabloları SWA'da raporlanacak ve checkpoint-kararsızlığı açıkça
belirtilecek. `best` sayıları yalnızca "accuracy-selected" etiketiyle verilecek.

**Aracımdaki boşluk (kayda geçsin):** flip-dedektörünün ilk sürümü yalnızca best↔swa
karşılaştırıyordu ve en keskin çelişkiyi (`primary/adaptive_t`, swa↔last) **kaçırıyordu**. Tüm
checkpoint çiftlerini karşılaştıracak şekilde düzeltildi.

Üretici: [`diagnostics/selection_audit_table.py`](diagnostics/selection_audit_table.py) →
[`diagnostics/selection_robustness.py`](diagnostics/selection_robustness.py) ·
artefaktlar: `diagnostics/selection_audit/selection_audit.csv`, `.../selection_robustness.json`

---

## B-017 — Kalibre etmek ≠ insanla hizalamak · `KAPALI` (P2 ✅, **P1 ❌ YANLIŞLANDI**)

> **3/3 tohum (42, 43, 1) tamamlandı, üç checkpoint'te de ölçüldü.** Duvar saati: 2 eşli koşu
> 4.78 h, solo koşu 2.79 h (eşli/solo oranı yine ~1.71×). Ön-kayıt:
> [`ferplus_tjsd_queue.ps1`](ferplus_tjsd_queue.ps1) başlığında, sonuçlardan önce yazıldı.
> Kesinti sonrası sıfırdan koşturuldu (kısmi checkpoint kullanılmadı).

**Neden T=0.74.** FERPlus ham 10-oylayıcı dağılımı taşıyan çok az görü veri kümesinden biri.
Öğretmen tarafında üç ölçüt zaten çakışmıyordu: T\*_ECE 0.46, T\*_NLL 0.5063, **T\*_JSD 0.74**.
Soru: insan-oyu hizalı sıcaklıkta damıtılan öğrenci insan belirsizliğini daha iyi taklit ediyor mu,
ve sert-etiket kalibrasyonundan ne kadar ödün vererek?

**Zorunlu kural (brief'ten, ve doğru kural):** öğrenciyi yalnız sert-etiket ECE'siyle
değerlendirmek hileli test olurdu — o metrik argmax etiketlere göre tanımlı ve T\*_ECE kolunu
tanım gereği kazandırır. Her kol **iki eksende** puanlandı.

### Sonuçlar (n=3 tohum, @swa birincil; öğrenci softmax'ı T=1'de, yani konuşlandırılan çıktı)

| T | öğretmen ECE | \|işaretli açık\| | yön | öğretmen JSD | **öğrenci ECE** | **öğrenci JSD** | öğrenci H | ρ(H,insan) |
|---|---|---|---|---|---|---|---|---|
| 0.5063 | 0.0156 | 0.0117 | az-güvenli | 0.0490 | **0.0185** ± 0.0016 | 0.0587 ± 0.0005 | 0.2548 | 0.683 |
| **0.74** | 0.0665 | 0.0649 | az-güvenli | **0.0440** | 0.0344 ± 0.0012 | **0.0536** ± 0.0004 | **0.3840** | 0.702 |
| 1.0 | 0.1282 | 0.1277 | az-güvenli | 0.0492 | 0.0783 ± 0.0046 | 0.0551 ± 0.0005 | 0.5465 | 0.704 |
| 0.26 | 0.0393 | 0.0393 | **aşırı-güvenli** | 0.0659 | 0.0587 ± 0.0031 | 0.0737 ± 0.0007 | 0.1244 | 0.667 |

**P2 ✅ DOĞRULANDI, üç checkpoint'in ÜÇÜNDE de.** Öğrenci JSD argmin'i her yerde T=0.74:
@swa 0.0536, @best 0.0541, @last 0.0544 — üçünde de diğer üç kolun altında. **İnsan hizalaması
damıtmayla aktarılıyor**, öğretmene özgü bir özellik değil. Öğrenci entropisi de T=0.74'te insana
en yakın (@swa 0.3840 / @best 0.4200 / @last 0.4088 vs insan **0.4401**) — yine üçünde de.

**Takas nicelleştirildi** (ECE-optimal T=0.5063 → JSD-optimal T=0.74):

| checkpoint | ECE maliyeti | JSD kazancı |
|---|---|---|
| @swa | **+0.0159** (1.9×) | **−0.0051** (−8.7%) |
| @best | +0.0287 | −0.0045 (−7.7%) |
| @last | +0.0186 | −0.0047 (−8.0%) |

Öğretmende aynı geçiş **+0.0508 ECE**'ye mal oluyordu — yani **takas öğrencide ~3× daha ucuz.**
Damıtma, insan-hizalamasını sert-etiket kalibrasyonundan daha az ödünle taşıyor.

**Yan bulgu:** ρ(öğrenci entropisi, insan entropisi) sıcaklıkla neredeyse hiç değişmiyor
(0.667 → 0.683 → 0.702 → 0.704). Öğretmende de öyleydi (0.732 → 0.734). Yani model
"insanların **nerede** anlaşamadığını" T'den bağımsız devralıyor; T yalnızca belirsizliğin
**büyüklüğünü** ayarlıyor. Bu, JSD'nin neden entropi eşleşmesiyle birlikte hareket ettiğini
açıklıyor.

### ⚠️ P1 ❌ YANLIŞLANDI — ve ön-kaydım kendi bulgumla çelişiyordu

Ön-kayıt: "öğrenci ECE'si öğretmen ECE'sinde monoton kalır, T=0.74 T=0.26 ile T=1.0 **arasına**
düşer" → sıralama 0.5063 < 0.26 < 0.74 < 1.0 olacaktı.

**Gerçekleşen** (@swa): 0.0185 (T=0.5063) < **0.0344 (T=0.74)** < 0.0587 (T=0.26) < 0.0783 (T=1.0).
Öğretmen ECE sıralaması 0.0156 < 0.0393 (**T=0.26**) < 0.0665 (**T=0.74**) < 0.1282 iken
**T=0.26 ile T=0.74 yer değiştirdi.** Yani **öğrenci ECE'si öğretmen ECE'sinde monoton değil** —
B-015'in monotonluğunun bir ara-nokta karşı-örneği var, ve launcher'daki ön-kayıt bunun
"yasanın gerçek bir kısıtlaması olarak raporlanacağını, açıklanıp geçiştirilmeyeceğini" yazıyordu.

**Yanlışlanma checkpoint'e dayanıklı** — takas üç checkpoint'te de aynı yönde:
@swa 0.0344 < 0.0587 · @best 0.0483 < 0.0568 · @last 0.0377 < 0.0591. Yani bu bir seçim
artefaktı değil.

**Bunu geçiştirmiyorum, ama nedeni bilinen:** T=0.26, ızgaradaki **tek aşırı-güvenli** noktadır
(işaretli açık **+0.0393**), diğer üçü az-güvenlidir. Ve **yön asimetrisini bu koşu bitmeden
ölçüp deftere yazmıştım** (ana figür bölümü, 1.78 ± 0.02): aşırı-güvenlilik öğrenci için eşit
büyüklükteki az-güvenlilikten ~1.8× daha zararlı. **Kendi ön-kaydımı yazarken kendi bulgumu
uygulamadım.** Uygulasaydım tam bu sonucu öngörürdüm. Hata ön-kayıttaydı, yasada değil.

**Rafine edilmiş yasa — bu noktanın DOĞRULADIĞI hâli:** öğrenci ECE'si, **her yön içinde**
|işaretli miskalibrasyon|'da monoton. Az-güvenli dal artık **üç noktalı ve üç checkpoint'te de
monoton**:

| \|açık\| | T | @swa | @best | @last |
|---|---|---|---|---|
| 0.0117 | 0.5063 | 0.0185 | 0.0196 | 0.0191 |
| 0.0649 | 0.74 | 0.0344 | 0.0483 | 0.0377 |
| 0.1277 | 1.0 | 0.0783 | 0.0927 | 0.0852 |

Öğretmen ECE'si **işaret-kör** olduğu için ızgarada iki tarafta da nokta bulunduğunda tek başına
öngörücü olmaktan çıkıyor. Bu, B-015'in *reddi* değil, **kapsamının kesinleşmesi:** yasa
işaretli eksende geçerli; ECE ekseninde yalnızca **tek yönlü ızgaralarda** geçerli. B-015'in
RAF-DB ve FERPlus ızgaraları tam olarak öyleydi (her biri tek taraftan yaklaşıyordu), bu yüzden
orada 9/9 tutmuştu. Makalede yasa **işaretli eksende** ifade edilmeli; ECE ekseni yalnızca
pratik bir vekil olarak, bu koşulla birlikte sunulmalı.

**Asimetri tahmini güncellendi.** T=0.74 az-güvenli dala üçüncü noktayı ekledi, yani FERPlus'ın
negatif dal fiti artık 3 noktalı (`0.0082 + 0.521·|açık|`). Bu, aşırı-güvenli T=0.26 noktasıyla
eşit-genlikli karşılaştırmayı keskinleştiriyor:

| kol | \|açık\| | aşırı-güvenli | eşit genlikte az-güvenli | oran |
|---|---|---|---|---|
| RAF-DB / Stage1 | 0.0431 | 0.0797 | 0.0450 | **1.77×** |
| FERPlus | 0.0393 | 0.0587 | 0.0287 | **2.04×** (önce 1.79×, 2 noktalı fitle) |

**Ortalama 1.91 ± 0.19** (yalnızca ekstrapole edilmemiş iki karşılaştırma; önceki değer
1.78 ± 0.02'ydi). Yön aynı, büyüklük arttı ve belirsizliği de arttı — dürüst olan bunu böyle
yazmak.

**Havuzlanmış Spearman düştü, ve nedeni açıkça yazılmalı:** iki veri kümesi + 14 nokta üzerinde
Spearman(|işaretli açık|, öğrenci ECE) @swa **+0.907 → +0.789** oldu (T=0.74 eklendikten sonra).
Sebep, havuzlanmış istatistiğin farklı eğimli kolları karıştırması: FERPlus'ın negatif dal eğimi
0.521, VAE9182'nin 0.724, Stage1'in 0.665, ve kesişimleri de farklı. **Sağlam olan kol-içi
monotonluk** (yukarıdaki tablo); havuzlanmış sayı bir özet, kanıt değil. Makalede ikisi ayrı
sunulmalı.

Betikler: [`ferplus_selection_audit.py`](diagnostics/ferplus_selection_audit.py) (sert etiket) ·
[`ferplus_student_jsd.py`](diagnostics/ferplus_student_jsd.py) (insan ekseni)

---

## B-016 — Köprü öğretmeni: kalibrasyonu head mi belirliyor, reçete mi? · `KAPALI · REÇETE`

> **Bu sonuç 21 Tem'de ölçülmüş ama deftere hiç işlenmemişti** — 27 Tem'de elektrik kesintisi
> sonrası "devam ettirilebilecek eğitim var mı" taraması sırasında
> `diagnostics/bridge_teacher/bridge_teacher_check.json` içinde bulundu. Eğitim tamamlanmış,
> ölçüm yapılmış, hiçbir tabloya girmemiş. Ölçüm sıfır GPU (CPU çıkarımı).

**Neden gerekliydi.** B-001 (öğretmen ECE → öğrenci sonucu) gözlemseldir: en yakın eşleşen çift
olan Primary ↔ VAE9182 bile **3 alanda** ayrılıyor — head (VICH↔VAE), transforms
(RAFDB_RECIPE↔QCS-rafdb), tohum (1↔0). Hakemin ilk sorusu bu: "kalibrasyon mu, head mi?"

**Tasarım.** `RAFDB_posterv2_vae_recipe_seed1.yaml` = Primary'nin config'inin bire bir kopyası,
**yalnızca iki satır** çevrilmiş (`vae_head: True`, `vich_head: False`). `diff` ile doğrulandı:
başka hiçbir alan farklı değil. Eğitim `results/teacher_logs/RAFDB/POSTERv2/2026-07-21-13-36-38/`.
Ön-kayıtlı karar kuralı (sonuçtan önce sabitlenmiş, JSON'da `decision_bands`):
ECE ≈**0.015** ± 0.01 → **head mimarisi**; ECE ≈**0.038** ± 0.01 → **reçete/augmentasyon**.

| öğretmen | reçete | head | tohum | kendi acc | **ECE(T=1)** | T\* | ECE(T\*) |
|---|---|---|---|---|---|---|---|
| Primary | RAFDB_RECIPE | VICH | 1 | 92.01% | 0.0396 | 1.261 | 0.0197 |
| **Köprü** | **RAFDB_RECIPE** | **VAE** | **1** | **92.47%** | **0.0391** | **1.253** | **0.0169** |
| VAE9182 | QCS-rafdb | VAE | 0 | 91.82% | **0.0136** | 0.983 | 0.0146 |
| Stage1 | RAFDB_RECIPE | VICH | 1 | 92.24% | 0.0378 | 1.349 | 0.0158 |

**Sonuç: head'i çevirmek kalibrasyonu DÜZELTMEDİ.** Köprü 0.0391'e düştü — Primary'nin
0.0396'sıyla pratikte aynı (Δ = 0.0005), VAE9182'nin 0.0136'sından **2.9× uzak**. Reçete bandının
merkezinde, head bandının tamamen dışında. T\* de aynı hikâyeyi anlatıyor: 1.253 ≈ Primary'nin
1.261'i, VAE9182'nin 0.983'ü değil. **Kalibrasyon profilinin tamamı reçeteyi izliyor, head'i değil.**

**Makaleye üç etkisi:**
1. **Confound kapandı.** "Head mi, X mi?" sorusunun cevabı artık var: head **değil**. B-001'in
   gözlemsel doğası bundan sonra daha az zarar veriyor, çünkü en akla yatkın alternatif açıklama
   deneysel olarak dışlandı.
2. **"İyi olasılıksal öğretmen head'i" hikâyesi bu makale için ölü** — plan bunu zaten ikinci
   makaleye ertelemişti, bulgu o kararı doğruluyor.
3. **Doğruluk–kalibrasyon ayrışmasının bir örneği daha:** köprü dört öğretmenin **en yükseği**
   (92.47%) ama kalibrasyonu Primary seviyesinde kötü. P4'ün "öğretmen ECE'si öğrenci sonucunu
   öngörür, öğretmen doğruluğu öngörmez" bulgusuyla aynı yönde.

**Dürüst sınırlar:**
- Köprü, VAE9182'den **iki** alanda ayrılıyor (transforms + tohum), dolayısıyla sonuç
  "**head değil**" ve "reçete **ve/veya** tohum" — reçeteyi tohumdan ayırmıyor. Tohumu dışlamak
  için VAE9182 reçetesinin tohum-1 kopyası gerekirdi (koşulmadı, deney dondurma kapsamında).
- **n=1 öğretmen, tek tohum.** Öğretmen eğitimi ~8.4 h olduğu için çok-tohumlu öğretmen
  karşılaştırması bu kampanyada yapılmadı.
- Köprü öğretmeniyle **hiç öğrenci eğitilmedi** (`runs.csv`'de 0 satır). Deneyin amacı
  öğretmen-tarafı ECE ölçümüydü ve o tamamlandı; öğrenci tarafı gerekmiyor.

Betik: `diagnostics/bridge_teacher_check.py` → `diagnostics/bridge_teacher/bridge_teacher_check.json`

---

## B-015 — FERPlus doz-yanıt: yasa ikinci veri kümesinde de geçerli mi? · `KAPALI · DOĞRULANDI`

> **Sonuçlar gelmeden yazıldı (26 Tem 13:5x).** Tahmin ve yanlışlanma koşulu önceden sabit;
> sonuç geldiğinde bu metin değiştirilmeyecek, altına eklenecek.

**Neden:** tek veri kümesinde nedensel iddia, en sık ret gerekçelerinden biri. B-007 şu an
RAF-DB'ye özgü. Bu, dış-geçerlilik testi.

**Bu test GÜÇLÜ, çünkü FERPlus öğretmeni TERS patolojide.** Stage1 (RAF-DB) doğal olarak
**aşırı-güvenli**: ECE(T=1)=0.0378, işaretli açık **+0.0338**, T\*=1.349 (>1, yumuşatma gerek).
FERPlus VICH öğretmeni — yumuşak 10-oylayıcı hedefleriyle eğitildiği için — doğal olarak
**az-güvenli**: ECE(T=1)=**0.1282**, işaretli açık **−0.1277**, T\*_NLL=**0.5063** (<1,
**keskinleştirme** gerek). Yani yasa, düzeltmenin ters yöne işlediği bir rejimde test ediliyor.

**Öğretmen tarafı headroom = 0.1282 − 0.0084 = 0.1198** — Stage1'in 0.0220'sinin **5.4 katı**,
yani çok daha büyük bir doz. Tüm ızgara önbelleklenmiş logitlerden kapalı-formda tasarlandı
(GPU maliyeti sıfır).

| T | rol | öğretmen ECE | işaretli açık | patoloji |
|---|---|---|---|---|
| **1.0000** | doğal | **0.1282** | **−0.1277** | ciddi **az-güvenli** |
| **0.5063** | T\*_NLL | **0.0156** | −0.0117 | kalibre |
| **0.2600** | aşırı-keskin | **0.0393** | **+0.0393** | **aşırı-güvenli** (işaret döndü) |

T=0.26, Stage1'in T=2.20'sinin aynadaki karşılığı: T\*'ın öteki yanına geçip **zıt** patolojiye
düşüyor (Stage1'de aşırı-güvenli → aşırı-yumuşak; burada az-güvenli → aşırı-güvenli).

**Ön-kayıtlı tahmin:** öğrenci ECE'si T\*≈0.51'de **minimum**, iki uçta da yükseliyor, en kötüsü
T=1.0 (en büyük |öğretmen açığı|). Eşdeğer ifade: öğrenci ECE'si öğretmen ECE'sinde ve
|işaretli öğretmen miskalibrasyonu|'nda **monoton** — RAF-DB'deki gibi.
**YANLIŞLANIR EĞER:** öğrenci-ECE argmin'i T\*'ta değilse veya sıralama öğretmen ECE'sini
izlemiyorsa. O durumda yasanın kapsamı dürüstçe RAF-DB ile sınırlanacak.

**Reçete — RAF-DB ile aynı MANTIK, dürüst farklar** (üçü de her kolda aynı olduğu için tek
manipüle edilen değişkeni karıştıramazlar):
- **200 epoch / SWA@100** (400/200 değil): FERPlus train 28259 vs RAF-DB 12271 (2.3×), 400 epoch
  ~9.5 h/koşu = 9 koşu için ~85 h olurdu. SWA'nın bütçenin %50'sinde olma oranı korundu.
- **Sınıf ağırlığı YOK**: `--class-weight-mode` / `--class-weight-beta`
  `train_affectnetplus_kd.py`'de **mevcut değil** (`--help`'e karşı doğrulandı). FERPlus zaten
  yumuşak oy dağılımlarıyla eğitiliyor, sınıf yeniden-ağırlıklandırma daha az anlamlı.
- **`--gamma` YOK**: o bayrak da bu scriptte yok.
- `label_smoothing` 0.0'a ve `supervision` "soft"a **zorlanıyor** (`train_ferplus_kd.py:1-19`).

**Kod değişikliği:** `--teacher-temperature-scale` FERPlus yolunda **yoktu**; RAF-DB'deki
uygulamayla birebir aynı mantıkta eklendi (iki çıkarım noktası, karşılıklı-dışlama guard'ı ve
`--allow-tempscale-with-mechanism` opt-in'i dahil).

### ⚠️ DÜZELTME (26 Tem 18:4x) — "best/last/swa metrikleri baştan loglanıyor" iddiam YANLIŞTI

Yukarıda bir önceki sürümde "üç checkpoint'in metrikleri baştan yazılıyor, RAF-DB'de sonradan
kurtarma durumu tekrarlanmayacak" yazmıştım. **Checkpoint'ler için doğru, metrikler için değil.**
Paylaşılan yazıcıyı okuduğumda:

- `kd_common.py:855-877` `write_metrics_json` → yalnızca accuracy / precision / recall /
  macro_f1 / weighted_f1 / params / flops / size. **`ece` yok, `nll` yok, `brier` yok.**
- `kd_common.py:652-680` `evaluate_detailed` → olasılıkları hiç biriktirmiyor, dolayısıyla
  olasılık-tabanlı hiçbir metrik oradan **türetilemez**.

`kd_common.py`'nin tamamında `ece`/`nll`/`brier` diye bir şey yok. Yani
`metrics_{best,last,swa}.json` doğruluk ve macro-F1 taşıyor, kalibrasyon metriği **hiç** taşımıyor
— briefteki "ZORUNLU: acc, ECE, NLL, Brier, macro-F1 baştan loglanacak" şartı karşılanmadı.

**Kayıp yok**, çünkü üç checkpoint'in üçü de diskte (`best_student.pth`, `last_student.pth`,
`swa_student.pth` — sonuncusu `train_affectnetplus_kd.py:763`). Metrikler yeniden puanlamayla
geri geliyor: [`diagnostics/ferplus_selection_audit.py`](diagnostics/ferplus_selection_audit.py),
RAF-DB'nin 290 ölçümüyle **aynı metrik tanımlarını** kullanıyor (iki veri kümesini
karşılaştırılabilir kılan şey bu). `write_metrics_json`'ı yamalamak yerine bunun seçilme nedeni:
yama yalnızca 3–9. koşuları kapsardı (1–2 modülü çoktan import etmişti), 1–2 için yine bu pas
gerekirdi → diskte iki metrik şeması, kazanç sıfır.

**Doğrulama kancası:** denetim, öğrencinin *kendi* val hattını yeniden kuruyor
(`build_data_args` + `--img-size 224`, öğretmen YAML'ının çözünürlüğü değil) ve yeniden hesaplanan
`best` doğruluğunun koşunun `metrics_best.json`'ıyla ≤0.05 pp içinde eşleşmesini şart koşuyor.
Eşleşmezse ECE "DOĞRULANMAMIŞ" damgası alıyor, sessizce raporlanmıyor.

Launcher: [`ferplus_dose_response_queue.ps1`](ferplus_dose_response_queue.ps1) · 3 T × 3 tohum = 9 koşu

### ✅ VERDICT 9/9 (27 Tem 11:20) — `KAPALI · DOĞRULANDI`

**B-015 = CONFIRMED.** Üç ön-kayıtlı tahminin üçü de geçti, üç checkpoint'in üçünde de.
Betik: [`diagnostics/b015_verdict.py`](diagnostics/b015_verdict.py) →
`diagnostics/selection_audit/b015_verdict.json`

| tahmin | havuzlanmış | tohum-içi |
|---|---|---|
| **P1** argmin T\*=0.5063'te | ✅ (3/3 checkpoint) | ✅ **9/9 eğri** |
| **P2** öğretmen ECE'sinde monotonluk | ✅ grup-ortalaması Spearman **+1.000** (üç checkpoint) + gruplar hiç örtüşmüyor | ✅ **9/9 eğri** |
| **P3** en kötü uç T=1.0 | ✅ (3/3 checkpoint) | — |

#### Asıl kanıt: 9/9 tohum-içi eğri, sıfır tohum karışması

Her tohum üç sıcaklığın hepsinde koştu; sabit tohumda başlangıç ağırlıkları, veri sırası ve
augmentasyon çekilişleri **birebir aynı**, tek değişen öğretmen ön-ölçeklemesi. 3 tohum × 3
checkpoint = **9 bağımsız monotonluk testi, hiçbirinde tohum karışması yok.**

| tohum | ckpt | T=0.5063 (öğr 0.0156) | T=0.26 (öğr 0.0393) | T=1.0 (öğr 0.1282) |
|---|---|---|---|---|
| 1 | best / last / swa | **0.0218 / 0.0218 / 0.0193** | 0.0564 / 0.0587 / 0.0632 | 0.1008 / 0.0927 / 0.0826 |
| 42 | best / last / swa | **0.0178 / 0.0235 / 0.0167** | 0.0556 / 0.0578 / 0.0568 | 0.0896 / 0.0765 / 0.0734 |
| 43 | best / last / swa | **0.0192 / 0.0121 / 0.0195** | 0.0583 / 0.0607 / 0.0563 | 0.0879 / 0.0863 / 0.0789 |

**9/9 monoton, 9/9 argmin T\*'ta.** Ayrıca kollar arasında **hiç örtüşme yok**: @best
max(T\*)=0.0218 < min(T=0.26)=0.0556 ve max(T=0.26)=0.0583 < min(T=1.0)=0.0879. Yani hiçbir
tohum ataması sıralamayı bozamaz.

#### Havuzlanmış tablo (3 tohum/nokta, örneklem sd n−1)

| T | rol | öğretmen ECE | öğrenci ECE @best | @last | @swa | doğruluk @best |
|---|---|---|---|---|---|---|
| **0.5063** | kalibre (T\*_NLL) | 0.0156 | **0.0196 ± 0.0020** | 0.0191 ± 0.0061 | **0.0185 ± 0.0016** | 89.206 ± 0.102 |
| **0.26** | aşırı-keskin (işaret döndü) | 0.0393 | 0.0568 ± 0.0014 | 0.0591 ± 0.0015 | 0.0587 ± 0.0038 | 89.322 ± 0.256 |
| **1.0** | doğal (az-güvenli) | 0.1282 | 0.0927 ± 0.0070 | 0.0852 ± 0.0082 | 0.0783 ± 0.0046 | 89.069 ± 0.354 |

Etki büyüklüğü (havuzlanmış örneklem sd → Cohen d), kalibre → doğal: **d = 14.2 @best,
17.4 @swa, 9.2 @last**. En zayıf karşılaştırma (T=0.26 → T=1.0 @last) bile d = 4.5.

#### Neden bu GÜÇLÜ bir dış-geçerlilik testi, aynı rejimin tekrarı değil

Stage1 (RAF-DB) doğal olarak **aşırı-güvenli**, düzeltme **yumuşatma** yönünde (T\*=1.349 > 1).
FERPlus öğretmeni yumuşak 10-oylayıcı hedefleriyle eğitildiği için doğal olarak
**az-güvenli**, düzeltme **keskinleştirme** yönünde (T\*=0.5063 < 1). Yasa, düzeltmenin **ters
yöne işlediği** bir rejimde, farklı veri kümesinde ve farklı sınıf sayısında (8 vs 7) sınandı.

**Regresyon katsayıları örtüşmüyor, örtüşmesi de beklenmemeli:**
RAF-DB `student_ECE = 0.0244 + 0.7653 × teacher_ECE` (Pearson +0.992) vs
FERPlus `0.0208 + 0.5824 × teacher_ECE` (Pearson +0.939, @best). Test edilen şey **monoton
ilişki**, paylaşılan bir regresyon doğrusu değil.

#### ⚠️ Kendi analizimdeki hata — verdicti neredeyse ters çeviriyordu

`b015_verdict.py`'nin ilk sürümü havuzlanmış Spearman'ı **9 koşu üzerinde** hesaplıyordu, ama
x yalnızca 3 farklı değer alıyor (3'erli bağlı gruplar) ve `rank()` fonksiyonum bağlı değerlere
keyfî olarak 1,2,3 veriyordu — var olmayan bir sıralama uydurup ρ'yu **+0.867**'ye düşürdü.
Eşiği (>0.99) o bozuk sayıya uygulayınca P2 "FAIL" oldu ve betik **FALSIFIED** yazdı. Gruplar
hiç örtüşmezken. Düzeltme: (a) orta-sıra (midrank) bağ düzeltmesi, (b) birincil havuzlanmış
istatistik olarak **3 grup ortalaması üzerinde** bağsız Spearman (+1.000), (c) korelasyondan
güçlü olan **grup ayrışma testi**. Bağlı x ile ρ yapısal olarak 1.0'a ulaşamaz — o sayı artık
yalnızca bütünlük için raporlanıyor, karara girmiyor.

#### Kayda geçen kapsam sınırları

1. Veri kümesi başına **3 sıcaklık noktası**, yoğun sweep değil: monotonluk 3'lü bir sıralamada
   kuruldu, ızgara noktaları **arasında** monoton olmayan bir sapma dışlanamaz.
2. Veri kümesi başına **tek öğretmen**. Yasa artık veri-kümesi-arası ve patoloji-arası, ama
   **mimari-arası değil** — buradaki her öğretmen POSTERv2.
3. **Doğruluk düz DEĞİL** ve öğretmen ECE'sinde monoton değil (aralık 0.25–0.49 pp; @best
   sıralama T=0.26 > T\* > T=1.0). Tek düzenli örüntü: en kötü kalibre kol doğrulukta da en
   kötü. İddia kalibrasyon hakkında.
4. Öğretmen ön-ölçeklemesi yalnızca öğretmen **kalibrasyonunu** değiştirir; eğitim reçetesiyle
   birbirinden ayrışan öğretmenler hakkında konuşamaz.

**Seçim optimizmi (n=9, FERPlus):** best−last d_acc **+0.458 ± 0.199 pp**, best−swa
**+0.183 ± 0.212 pp**; d_ece +0.0019 ± 0.0058 / +0.0045 ± 0.0078. RAF-DB (n=101: +0.792 /
+0.127; d_ece −0.0036 ± 0.0092) ile aynı örüntü: **seçim doğruluğu şişirir, kalibrasyona
ölçülebilir etkisi yok** (sd ortalamanın ~3 katı). B-014 ikinci veri kümesinde tekrarlandı.

**Duvar saati:** 8 eşli koşu 4.71–4.75 h, son koşu solo **2.79 h** → eşli/solo oranı
**1.70×** (RAF-DB'de 1.69× ölçülmüştü; oran veri kümesinden değil GPU paylaşımından geliyor).

---

### ARA SONUÇ 6/9 (27 Tem 03:50) — tohum-İÇİ eksiksiz eğri geldi, tahmin tutuyor

Duvar saati **4.71–4.74 h/koşu** (eşli). Denetim altı koşunun da logladığı doğruluğu ≤0.05 pp'de
birebir yeniden üretti, dolayısıyla ECE güvenilir. Her T noktası artık n=2.

| T | rol | öğretmen ECE | \|işaretli açık\| | n | öğrenci ECE @best | @last | @swa | doğruluk @best |
|---|---|---|---|---|---|---|---|---|
| **0.5063** | kalibre | 0.0156 | 0.0117 | 2 (42,43) | **0.0185 ± 0.0010** | 0.0178 ± 0.0080 | **0.0181 ± 0.0020** | 89.185 |
| **0.26** | aşırı-keskin | 0.0393 | 0.0393 | 2 (1,42) | **0.0560 ± 0.0005** | 0.0582 ± 0.0006 | **0.0600 ± 0.0045** | 89.343 |
| **1.0** | doğal (az-güvenli) | 0.1282 | 0.1277 | 2 (42,43) | **0.0887 ± 0.0012** | 0.0814 ± 0.0069 | **0.0762 ± 0.0038** | 88.868 |

(± değerleri artık **örneklem sd (n−1)** — aşağıdaki metodolojik nota göre düzeltildi.)

#### Asıl kanıt: TOHUM-İÇİ eksiksiz eğri (tohum karışıklığı sıfır)

Tohum 42 üç T noktasının **hepsinde** koştu, yani üç noktalı eğri tek tohum içinde tam eşli —
tohum, veri sırası, başlangıç ağırlıkları hepsi sabit, **tek değişen öğretmen ön-ölçeklemesi**:

| tohum | checkpoint | T=0.5063 (öğr 0.0156) | T=0.26 (öğr 0.0393) | T=1.0 (öğr 0.1282) | monoton? |
|---|---|---|---|---|---|
| **42** | best | **0.0178** | 0.0556 | 0.0896 | ✅ |
| **42** | last | **0.0235** | 0.0578 | 0.0765 | ✅ |
| **42** | swa | **0.0167** | 0.0568 | 0.0734 | ✅ |
| 43 | best | **0.0192** | — | 0.0879 | ✅ |
| 43 | last | **0.0121** | — | 0.0863 | ✅ |
| 43 | swa | **0.0195** | — | 0.0789 | ✅ |

**Öğrenci ECE'si, öğretmen ECE'sinde monoton — tohum-içinde, üç checkpoint'in üçünde de.**
Ön-kayıtlı tahminin en güçlü doğrulaması bu satırlar: karşılaştırma hiçbir tohum farkı
içermiyor.

#### Etki büyüklüğü (havuzlanmış örneklem sd)

| checkpoint | kalibre → doğal fark | havuzlanmış sd | Cohen d |
|---|---|---|---|
| best | +0.0702 | 0.0011 | **61.7** |
| swa  | +0.0581 | 0.0031 | **18.9** |
| last | +0.0636 | 0.0075 | **8.5** |

En **gevşek** checkpoint'te bile d≈8.5. Sonuç hangi checkpoint'e ya da hangi σ tahminine
baktığınıza bağlı değil. **Ama n=2'den çıkan sd, sd'nin kendisi için zayıf bir tahmindir**;
3. tohumlar (T051_seed1, T100_seed1, T026_seed43) geldiğinde yerine konacak.

#### ⚠️ Doğruluk "düz" DEĞİL — önceki ifademi daralttım

2/9'da "doğruluk üç hanede birebir aynı" yazmıştım; o iki koşunun tesadüfüydü. 6 koşuda
doğruluk aralığı **0.48–0.73 pp** ve **öğretmen ECE'sinde monoton değil**: @best sıralama
T=0.26 (89.343) > T=0.5063 (89.185) > T=1.0 (88.868), yani en iyi kalibre öğretmen en iyi
doğruluğu vermiyor. Tek düzenli örüntü, **en kötü kalibre öğretmenin (T=1.0) doğrulukta da en
kötü olması** — üç checkpoint'te de.

Doğru ifade şu: manipülasyon **ECE'yi 5 katına** çıkarıyor (0.0178 → 0.0896, tohum 42 içinde),
doğruluğu ise ≤0.73 pp oynatıyor ve monoton bir örüntü kurmuyor. Ayrışma iddianın özü; ama
"doğruluk sabit" demek fazla olur.

#### ⚠️ Metodolojik düzeltme — bütün ± değerleri `pstdev` (n bölen), `stdev` (n−1) değil

σ-tabanlı iddiaya geçtiğimiz için bunu açıkça söylemek gerekiyor: bu kampanyadaki tüm
diagnostics betikleri `statistics.pstdev` kullanıyor, yani **popülasyon** sd'si. Küçük n'de
konvansiyonel örneklem sd'sinden (Bessel düzeltmeli) sistematik olarak küçüktür:
n=2'de %29, n=3'te %18. Yön: σ'yı küçük gösterdiği için **σ katlarını iyimser** yapar.
Örneklem sd'siyle yukarıdaki tablo 71× / 7.3× / 28× olur — taban ~7σ, sonuç değişmiyor.

**Hangi sonuçları etkiler:** yalnızca n=2–3'lük ± değerlerinin *genişliğini* (VICH izolasyonu
d_ece ±0.0013, adaptive_t blokları, bu tablo). **Hiçbir sonucun yönünü değiştirmez**, çünkü
kampanyanın taşıyıcı ölçütleri σ kullanmıyor: B-007 Spearman'a, B-010 kill-switch'i işaret
tutarlılığı + ön-kayıtlı bara dayanıyor. n=101'lik B-014 tablolarında fark %0.5, ihmal edilebilir.

**UYGULANDI (6/9, 27 Tem):** yukarıdaki B-015 tabloları örneklem sd'sine (n−1) çevrildi ve etki
büyüklüğü havuzlanmış örneklem sd'siyle Cohen d olarak verildi. Diğer bulguların tabloları
makale yazımında aynı dönüşümden geçirilecek; hangi ± değerinin hangi tanımda olduğu her tabloda
belirtilecek.

**Ön-kayıtlı iki tahmin de şimdiye kadar tutuyor, üç checkpoint'in ÜÇÜNDE de:**
1. **argmin T\*=0.5063'te** — best, last, swa: üçünde de.
2. **Öğretmen ECE'sinde monotonluk** — 0.0156 < 0.0393 < 0.1282 sıralaması öğrenci ECE'sinde
   birebir korunuyor: @best 0.0178 < 0.0564 < 0.0896, @last 0.0235 < 0.0587 < 0.0765,
   @swa 0.0167 < 0.0632 < 0.0734. **Spearman +1.000, üç checkpoint'te de.**
   Tahminin eşdeğer ifadesi (|işaretli miskalibrasyon|'da monotonluk) de aynı şekilde tutuyor.
3. Öngörüldüğü gibi **en kötü nokta T=1.0** (en büyük |öğretmen açığı|).

**TOHUM-EŞLİ NEDENSEL KARŞILAŞTIRMA (asıl kanıt, artık mevcut):** tohum 42'de
T=0.5063 → **0.0178** vs T=1.0 → **0.0896** — aynı tohum, aynı reçete, tek fark öğretmen
ön-ölçeklemesi. **5.03× ECE farkı**, doğruluk ise 89.090 vs 88.931 (**0.16 pp**). Tohum
karışıklığı olmadan: manipülasyon doğruluğu kıpırdatmıyor, kalibrasyonu 5 katına çıkarıyor.

**Hâlâ eksik olan (dürüst sınırlar):**
- Her T noktasında **n=1**. Tohum 1 ve 43 çoğu nokta için bekliyor; saçılım henüz ölçülmedi.
- **T=0.26 tohum 1'de**, diğer ikisi tohum 42'de → monotonluğun *tamamı* henüz tohum-eşli değil.
  Tohum-42'nin T=0.26 koşusu şu an sırada (Stream A, 3. iş) — bittiğinde tek tohum içinde
  eksiksiz 3-noktalı eğri çıkacak, monotonluk iddiası o zaman tohum-bağımsız hâle gelir.
- FERPlus'ta tohum-arası ECE σ'sı ölçülmedi; RAF-DB'nin ~0.0015'i ödünç referans, yerine
  gerçeği 3 tohum gelince konacak.

**Yan kayıt — seçim optimizmi FERPlus'ta da tekrarlanıyor** (n=3): best−last d_acc
**+0.507 ± 0.181 pp**, best−swa **+0.275 ± 0.187 pp** (RAF-DB, n=101: +0.792 / +0.127).
d_ece ise n=2→n=3'te işaret değiştirdi (−0.0040 → +0.0017), yani gürültülü — bu da RAF-DB'yi
tekrarlıyor (orada −0.0036 ± 0.0092, sd ortalamanın 2.5 katı). Yani **seçim doğruluğu şişiriyor,
kalibrasyona etkisi ölçülemez** sonucu ikinci veri kümesinde de aynı.

Verdict 9/9'da, ön-kayıtlı ölçüte (argmin T\*=0.5063'te + öğretmen ECE'sinde monotonluk) karşı.

---

## B-009 — Köken/provenance altyapısı · `KAPALI`

`poster-var` bir git deposu **değil** — commit SHA yok. Yerine her koşuya
[`diagnostics/run_manifest.py`](diagnostics/run_manifest.py) ile `manifest.json` yazıldı:
numeriği belirleyen 8 kaynak dosyanın içerik hash'i (`combined_code_sha256`), `run_args.json`'ın
kanonik hash'i, veri kümesi SHA-256'sı (15339 görüntü + metadata, `5dfed142d4b737d0…`),
öğretmen checkpoint hash'i ve tohum.

**Geriye dönük hash'in dürüst sınırı:** araç bittikten sonra yazıldığı için, kaynak dosya
mtime'ları koşunun bitiş zamanıyla karşılaştırılır; sonrasında düzenlenmiş dosya varsa koşu
`code_state_verified: false` ile işaretlenir. Sonuç: **28 doğrulanmış, 62 geriye dönük.**

Makalenin çekirdek koşularının **tamamı doğrulanmış** (bütün `tempscale_*` ve `pluslinear_*`),
tek istisna: `RAFDB_stage1_tempscale_T1341_halfA_baseline` (B3 pilotu, T=1.34 tohum 42).

Bu tek istisna **adli olarak kapatıldı**: pilotun `run_args.json`'ında `student_arch` anahtarı
**yok**, sonradan koşan T=1.34 tohum1/tohum43'te **var** → koşudan sonraki tek düzenleme
`--student-arch` eklenmesiydi. O dal `if getattr(args, "student_arch", "plus") == "vanilla_mnv2"`
(varsayılan `"plus"`) olduğundan **her plus-head koşusu için ispatlı biçimde etkisizdir**.
Ayrıca aynı T'deki diğer iki tohum bağımsız koşuldu ve üçünün sd'si 0.055 — pilot farklı bir kod
rejiminden gelseydi beklenmeyecek kadar dar.

**Araç sınırı (kayda geçsin):** mtime tavsiye niteliğindedir, içerik hash'i kesindir. Kampanya
sırasında `train_rafdb_kd.py`'nin mtime'ı ile düzenleme sırası birebir örtüşmedi; bu yüzden
staleness bayrağı bir **soru işareti**dir, kanıt değil — yukarıdaki gibi ayrıca kapatılmalıdır.

---

## B-011 — Öğretmen-seçim reçetesi: ECE ile seç, doğrulukla seçme · `KAPALI` (0 GPU)

Pratik problem: K aday öğretmen, tek GPU. Her adaydan öğrenci damıtarak seçmek K×(4.3h × 3 tohum).
Doğrulukla seçmek bedava — **ve bu ölçütte yanlış**.

| Öğretmen | Öğretmen acc | Öğretmen ECE | T\* | Öğrenci acc (3 tohum) |
|---|---|---|---|---|
| **VAE9182** | 91.82 (en **düşük**) | **0.0136** | 0.983 | **90.276 ± 0.156 (en iyi)** |
| Stage1 | **92.24 (en yüksek)** | 0.0378 | 1.349 | 89.744 ± 0.055 |
| Primary | 92.01 | 0.0396 | 1.261 | 89.570 ± 0.070 |

| Seçim ölçütü | Sıra korelasyonu (→ öğrenci acc) | Seçtiği | Doğru mu? |
|---|---|---|---|
| Öğretmen doğruluğu | **−0.500** (ters yönlü) | Stage1 | ✗ |
| Öğretmen ECE'si | **+1.000** (kusursuz, 3/3) | VAE9182 | ✓ |

Doğruluk ölçütünün hatasının bedeli: **0.532 pp** öğrenci doğruluğu. Reçetenin tasarrufu: 3 aday ×
3 tohum × 4.3 h = **39 GPU-saat** → 3 CPU çıkarım geçişi (~15 dk/öğretmen).

**Öğrenci ECE'sini eğitmeden önce kestirme** (doz-yanıt noktalarına fit, n=10):

> `öğrenci_ECE = 0.0244 + 0.7653 × öğretmen_ECE`  ·  Pearson +0.992, Spearman +0.976
> **Leave-one-out ortalama |hata| = 0.0063**, kapsanan aralığın (0.0273–0.2252) yalnızca **%3.2**'si

Yorum: eğim 0.765 < 1 ve sabit terim +0.0244 → öğrenci, öğretmenin miskalibrasyonunun ~%77'sini
devralıyor, üstüne kendi ~0.024'lük tabanını ekliyor.

**Önemli ayrım:** aynı ilişki *gözlemsel* (3 öğretmen arası) düzeyde yalnızca Spearman **+0.500**
verirken, *manipüle edilmiş* (10 nokta, öğretmen-içi sıcaklık) düzeyde **+0.976**. Aradaki fark
öğretmenler-arası karışık faktörlerdir — nedensel ilişki, gözlemsel olandan çok daha sıkı.

**Sınır:** RAF-DB'ye özgü fit; sıralama iddiası K=3, kestirim n=10 (4'ü henüz <3 tohum, tamamlanınca
yeniden fit edilecek). Veri kümeleri arası genelleme **iddia edilmiyor**.

Üretici: [`diagnostics/p4_teacher_selection_recipe.py`](diagnostics/p4_teacher_selection_recipe.py)

---

## B-012 — Verimlilik: sıkıştırma oranı VAR, frontier YOK · `KAPALI` (0 GPU)

**Raporlanabilir olan — öğretmen→öğrenci sıkıştırma (kesin, deterministik):**

| | POSTERv2 öğretmen | MobileNetV2Plus öğrenci | Oran |
|---|---|---|---|
| Parametre | 58.334 M | 2.248 M | **25.9× küçük** |
| FLOPs | 8.4827 G | 0.3286 G | **25.8× az** |
| Boyut | 555.0 MB | 8.83 MB | **62.9× küçük** |
| Doğruluk | 91.82% | 90.276 ± 0.156% | **%98.32 korunma** (1.54 pp veriliyor) |

### Gecikme — yeniden ölçüldü (26 Tem, boş makine) ✓

Eski üç CSV *aynı* mimariyi **249.8 / 89.2 / 47.5 ms** olarak ölçmüştü (**5.3× yayılım**, aynı
FLOPs'ta imkânsız) — KD kuyrukları koşarken alınmış, **atıldı**. Yeni protokol: 50 warmup + 200
ölçüm, `torch.cuda.synchronize`, **medyan ± IQR** (ortalama değil; dağılım sağa çarpık).

| Cihaz | Model | batch | dtype | medyan (ms) | IQR | img/s |
|---|---|---|---|---|---|---|
| RTX 5070 | öğrenci | 1 | fp32 | **5.41** | 2.59 | 185 |
| RTX 5070 | öğretmen | 1 | fp32 | **10.46** | 0.48 | 96 |
| RTX 5070 | öğrenci | 32 | fp32 | **9.87** | 0.63 | 3244 |
| RTX 5070 | öğretmen | 32 | fp32 | **38.59** | 0.65 | 829 |
| RTX 5070 | öğrenci | 32 | fp16 | **6.19** | 0.34 | 5167 |
| RTX 5070 | öğretmen | 32 | fp16 | **24.15** | 0.47 | 1325 |
| Ryzen 7950X | öğrenci | 1 | fp32 | **11.23** | 1.08 | 89 |
| Ryzen 7950X | öğretmen | 1 | fp32 | **44.98** | 1.68 | 22 |
| Ryzen 7950X | öğrenci | 32 | fp32 | **161.6** | 10.4 | 198 |
| Ryzen 7950X | öğretmen | 32 | fp32 | **716.7** | 13.7 | 45 |

**Hızlanma:** GPU b1 fp32 **1.93×** · GPU b32 fp32 **3.91×** · GPU b32 fp16 **3.90×** ·
CPU b1 **4.01×** · CPU b32 **4.43×**

> ### ⚠️ Makale için kritik: FLOPs oranı hızlanmayı ÇOK abartıyor
> **25.8× daha az FLOPs, yalnızca 1.9–4.4× duvar-saati hızlanma** veriyor. Nedenleri: (a) batch=1'de
> iki model de kernel-başlatma sınırlı, hesap sınırlı değil; (b) POSTERv2'nin maliyeti saf FLOPs
> değil (dikkat + landmark işlemleri, çok sayıda küçük kernel). Verimlilik bölümünde FLOPs oranını
> hızlanma gibi sunmak **yanlış** olur; ikisi ayrı ayrı raporlanacak.

> **fp16 batch=1'de DAHA YAVAŞ** (öğrenci 6.52 vs 5.41; öğretmen 13.97 vs 10.46) — autocast cast
> maliyeti başlatma-sınırlı rejimde kazancı yiyor. fp16 yalnızca batch=32'de kazandırıyor
> (öğrenci 1.59×, öğretmen 1.60×). Bu bir hata değil, beklenen davranış; belirtilmeli.

**Ölçüm koşulları (manifest'te):** torch 2.10.0+cu128, cuDNN 91002, sürücü 610.62, RTX 5070
(11.94 GB, SM 12.0), güç limiti 250 W, Windows "High performance". **Yük altında** ölçülen saatler:
SM 2662→2842 MHz, bellek 13801 MHz, 187–196 W, 51–59 °C. (İlk sürümde manifest **boştaki** saati
(240 MHz) kaydediyordu — ölçüm koşulunu yanlış temsil ediyordu, düzeltildi ve yük-altı örneklemesi
eklendi.) İki bağımsız koşunun medyanları %2–6 içinde tekrarlandı.

Artefaktlar: `diagnostics/p5_efficiency/latency_benchmark.{csv,json}` ·
üretici [`diagnostics/latency_benchmark.py`](diagnostics/latency_benchmark.py)

### Hâlâ raporlanamayan: "frontier"

**"Frontier" diye sunulabilecek bir şey yok.** Öğrenci parametreleri 2.239–2.251 M aralığında,
   yani **%0.5** yayılım — bu kafa boyutu farkı (vich↔linear), kapasite noktası değil. Doğruluk-maliyet
   eğrisi çizilemez. Gerekli eksik koşular: `--student-arch vanilla_mnv2` kontrolü (Plus yığınını
   izole eder) ve `--width-mult 0.5 / 0.75` süpürmesi (kapasiteyi izole eder).

**Not:** ilk sürümde kendi kontrolüm "3 farklı parametre değeri var → frontier var" diyordu; sayı
yerine **yayılım** eşiği (≥1.15×) koyunca doğru sonuç çıktı. Teknik olarak doğru ama anlamsız bir
sayımdan yanlış bir iddia üretilebilirdi.

Üretici: [`diagnostics/p5_efficiency_frontier.py`](diagnostics/p5_efficiency_frontier.py)

---

## Yapılmayacaklar listesi (gerekçeli)

| Yapılmayacak | Gerekçe |
|---|---|
| Gate'i daha iyi sinyalle kurtarmak | B-002: oracle sinyalle bile kaybetti — mekanizma ölü |
| G2G `w2` modunu denemek | B-003: `kl` üç öğretmende işaret tutturamadı; mod ikincil ayrıntı |
| 90.57'yi (combined_500e) kazanç diye raporlamak | B-004: n=3'te p ≈ 0.12, bileşenler ayrı ayrı null |
| n=3 öğretmenle "M kriteri korelasyonu" iddiası | 3 nokta korelasyon taşımaz; ayrıca 3 karışık faktör var |
| Gate/G2G ızgarasını yeni veri kümelerine yaymak | Null'u çoğaltmak; B-007 zaten *neden* null olduğunu söylüyor |
| MobileNetV2Plus'ı birincil yenilik saymak | Bileşenlerin hepsi ödünç, bileşen ablasyonu yok — destekleyici bacak olarak kullan |

---

## Açık riskler

1. **B-007 henüz kapanmadı.** Yasa 8 koşuya bağlı. VAE9182 öğrencisi kendi derin U'sunu
   gösterirse yasa düşer ve makalenin birleştirici çerçevesi B-005'e (tek öğretmen, nedensel
   doz-yanıt) geriler — bu hâlâ yayınlanabilir ama daha dar.
2. **Tek veri kümesi.** B-005/B-006/B-007'nin tamamı RAF-DB. FERPlus + AffectNet+ üzerinde
   "negatifler genelleşiyor" kanıtı hâlâ eksik ve en büyük kalan blok.
3. **n=3 tohum.** Tüm kararlar 3 tohumun işaret tutarlılığına dayanıyor. Bu, ~0.05–0.15 pp
   büyüklüğündeki etkiler için sınırda; ECE etkileri (sd ~0.001–0.007) çok daha sağlam.
4. **Primary öğretmende adaptive_t hâlâ n=2** — B-007'nin 3/3 öğretmene tamamlanması için
   eksik parça (~7.5 saat).

> **Not (2026-08-01):** yukarıdaki risk listesi 28 Temmuz tarihlidir ve en az iki kalemi aşıldı
> (B-007 kapandı; FERPlus doz-yanıtı B-015 ile indi). Tazelenmeden alıntılanmamalı.

---

# P1–P5 kampanyaları (23 Tem – 1 Ağu 2026) — özet kayıt

Bu dosyanın gövdesi 28 Temmuz'da yazıldı ve P kampanyalarını içermiyor. Her birinin tam kaydı
`diagnostics/PREREGISTRATIONS.md` ile ilgili verdict artefaktındadır; burada yalnız ne sorulduğu
ve ne çıktığı duruyor.

| kuyruk | soru | koşu | sonuç | artefakt |
|---|---|---|---|---|
| **P1** | `logit_std` n=1 → n=3; Stage1 doz-yanıtı; VAE9182 düz-kontrol | 12+6 | **CONFIRMED 3/3** — `logit_std` doğrulukta görünmez, kalibrasyonda yıkıcı (ΔECE +0.086…+0.139, kendi kolunun paydasında 57–77×) | A6/A7/A1 |
| **P2** | `gate:oracle_error` n=3, **sınıf-ağırlığı eşleşmiş** temiz kontrole karşı | 5 | **KISMEN YANLIŞLANDI (1/3)** — "iki eksen de null" tahmini kalibrasyon ekseninde düştü: ΔECE +0.0056, 3/3 işaret, 2.08× bar | A8 · `p2_gate_oracle/` |
| **P3** | kapasite eğimi ikinci bir kapasitede; sıcaklık ekseni w050'de | 4 | kalem (i) **KURULU** (yasa 0.712 M'de de geçerli); kalem (ii) **ÇÖZÜNMEDİ** + init confound'u | B3/B4 |
| **P4** | stage1/primary için eksik `cw=none` kontrolleri | 6 | 4 gate satırı temiz kontrolle T5'e girdi; gerçek-sinyal hasarı **tekrarlanmadı** (n=1) | A8-P4 |
| **P5** | oracle hasarı stage1+primary'de tekrarlanıyor mu (n=3) | 6 | **0/2 KURULU — iki kolda da ÇÖZÜNMEDİ** (stage1 0.74× bar, primary 0.11× bar, işaretler `+-+`) | A8-P5 · `p5_oracle_replication/` |

**Kampanyanın net etkisi iki cümlede.** (1) `logit_std` bu makalenin en büyük tek mekanizma
etkisi ve etki **kalibrasyonda**, doğrulukta değil — üç öğretmende de aynı yönde. (2) Gate
kapandı, ama gerekçesi P2 ile değişti ve P5 ile sınırlandı: doğruluk kazancının yokluğu
**koşulsuz** (kusursuz bilgiyle bile, üç öğretmende de Δacc ≤ 0), kalibrasyon hasarı ise
**VAE9182'ye koşullu** (stage1/primary'de çözünmedi — yok değil, ölçülemedi).

**Seçim denetimi** bu süreçte 101 → 116 → 125 → **131**'de donduruldu; tahmin 0.015 pp içinde
sabit kaldı (bkz. B-014 güncellemesi).
