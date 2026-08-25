# Ön-kayıt envanteri — hangi tahmin nerede donduruldu, sonuçtan önce mi?

Üretici not: bu dosya elle yazıldı ama içindeki her tarih dosya sisteminden okundu
(`stat` mtime + koşu dizini adı). Yeniden doğrulamak için:
`stat -c '%y' <artefakt>` ile `ls -1d results/unified_students/<koşu>/*/` karşılaştırılır.

---

## ⚠️ Önce kanıtın sınırı — bunu makalede de böyle yazacağız

`poster-var` **git deposu** (ilk commit 2026-07-11 22:37:46). Ama **hiçbir ön-kaydın commit
hash'i yok**, ve bunun sebebi git'in yokluğu değil: 14 Temmuz 17:41 ile 31 Temmuz 17:04 arasında
**tek bir commit yok**, ve aşağıdaki ön-kayıtların hepsi tam o boşlukta donduruldu. Onunun da
git'e ilk girişi aynı commit'tir (`9b2d31c`, 31 Tem 17:04) — A1–A8 için bu, sonuçlar elde
edildikten *sonra*dır. Yani commit geçmişi bu ön-kayıtlar için kanıt üretmiyor; ölçümü
`diagnostics/reports/2026-07-31_git_provenance.md`'de. Elimizdeki iki bağımsız zaman damgası
değişmedi:

1. **Artefaktın mtime'ı** — tahmin metnini taşıyan `.ps1` / `.py` dosyasının son değiştirilme anı.
   Zayıf yön: mtime elle değiştirilebilir ve dosyayı sonradan düzenlemek onu ileri taşır.
2. **Koşu dizininin adı** — `results/unified_students/<ad>/<YYYY-MM-DD-HH-MM-SS>/`. Bu damgayı
   eğitim betiği kendi başlangıcında üretir; sonradan yazılamaz ve düzenlenemez.

**Kural:** bir ön-kayıt ancak (1) < (2) ise "sonuçtan önce donduruldu" sayılır, ve tahmin metni
o artefaktın **içinde** olmalıdır. Aşağıda ikisi de gösteriliyor.

**`BULGULAR.md` ön-kayıt kanıtı DEĞİLDİR.** Sürekli düzenlenen tek bir dosya olduğu için mtime'ı
(28 Tem 05:59) yalnız en son düzenlemeyi gösterir; içindeki hiçbir bölümün ne zaman yazıldığını
kanıtlamaz. BULGULAR'daki tahmin metinleri aşağıdaki artefaktların **kopyasıdır**, kaynağı değil.
Makalede yalnızca **artefaktı olan** ön-kayıtlar "pre-registered" diye anılacak.

---

## A. Artefaktı olan ön-kayıtlar (makalede "pre-registered" denebilir)

### A1 · B-007 — düz-kontrol tahmini (VAE9182 doz-yanıtı)

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p1_vae9182_flatcontrol_queue.ps1`, satır 16-20 |
| **donduruldu** | 2026-07-24 18:05:30 |
| **ilk koşu başladı** | `2026-07-24-18-05-50` (**+20 saniye**) |
| **sonuçtan önce mi** | ✅ **evet** |
| **sonuç** | T2 tablosu · doğrulandı (T=1.0'da minimum, T>1 monoton hasar) |

> "Prediction (calibration-conditioned headroom law, B-007): because there is little
> miscalibration to correct, this curve should be FLAT/shallow with its minimum near T=1.0 --
> NO deep dip like Stage1's (which improved -46% ECE at T\*=1.34). If VAE9182 at T=1.34 does NOT
> improve (or worsens), that is the headroom-proportional-to-miscalibration evidence..."

**Dürüst bağlam:** bu tahmin Stage1 kolunun sonucu **bilinerek** yazıldı (Stage1 ızgarası
23-24 Tem'de koştu). Bu bir kusur değil — tahmin *başka bir öğretmen* hakkında ve yasadan
türetiliyor — ama "her iki kol da kör tahmin edildi" diye yazılamaz. Kör olan VAE9182 kolu.

---

### A2 · B-010 — miskalibrasyon enjeksiyonu kill-switch'i

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p3_then_miscal_chain.ps1`, satır 42-49 |
| **donduruldu** | 2026-07-25 14:35:43 |
| **ilk koşu başladı** | `2026-07-25-23-19-09` (**+8 sa 43 dk**) |
| **sonuçtan önce mi** | ✅ **evet** |
| **sonuç** | **NULL** — kill-switch tetiklendi, 3. tohum harcanmadı |

> "KILL-SWITCH: 2 seeds first. If the ECE delta does not clear the native -0.0034 in BOTH
> seeds, stop -- do not spend the 3rd seed."

**Kritik detay — kendi kuralımı ilk uygulayışımda hata yaptım.** Kill-switch kodunun ilk sürümü
"PASS, 3. tohumu harca" dedi; çünkü *ortalamayı* bara karşı test ediyordu, oysa ön-kayıt "her iki
tohumda da" diyordu. Düzeltilmiş kural iki ölçüt istiyor: (1) **her tohum** −0.0034 barının
altında, (2) işaretler tutarlı. Ölçülen: `['+', '-']`, ortalama −0.0021 ± 0.0045 (n=2, örneklem
sd) → **iki ölçüt de düşüyor**. Bu bir "sonuca göre kuralı gevşetme" değil, tersi:
kural sıkılaştırıldı ve sonuç NULL'a döndü. Makalede bu hikâye kısaca anlatılmalı.

---

### A3 · B-015 — FERPlus doz-yanıtı, üç tahmin birden

| alan | değer |
|---|---|
| **artefakt** | `ferplus_dose_response_queue.ps1`, satır 38-41 |
| **donduruldu** | 2026-07-26 13:27:26 |
| **ilk koşu başladı** | `2026-07-26-13-27-45` (**+19 saniye**) |
| **sonuçtan önce mi** | ✅ **evet** |
| **sonuç** | **CONFIRMED** — 3/3 tahmin, 3/3 checkpoint, 9/9 tohum-içi eğri |

> "PRE-REGISTERED PREDICTION: student ECE is minimised at T=T\*~0.51, and rises at BOTH ends,
> with the T=1.0 end worst (largest |teacher gap|). Equivalently: student ECE is monotone in
> teacher ECE, and monotone in |signed teacher miscalibration|, exactly as on RAF-DB.
> FALSIFIED IF: the student-ECE argmin is not at T\*, or the ordering does not follow teacher ECE."

Üç tahmin tek paragrafta: **P1** argmin T\*'ta · **P2** öğretmen ECE'sinde monotonluk ·
**P3** en kötü uç T=1.0. Doğrulama betiği `diagnostics/b015_verdict.py`, sonuç
`diagnostics/selection_audit/b015_verdict.json` (`verdict.overall = "CONFIRMED"`).

**Bu ön-kaydın en güçlü yanı FERPlus'ın ters işaretli olması:** RAF-DB öğretmeni aşırı-güvenli,
FERPlus öğretmeni az-güvenli. Tahmin RAF-DB'den türetildi ve **düzeltmenin ters yöne işlediği**
bir rejimde sınandı.

---

### A4 · B-017 — insan-oyu hizalı sıcaklık (T=0.74), iki tahmin + zorunlu değerlendirme kuralı

| alan | değer |
|---|---|
| **artefakt** | `ferplus_tjsd_queue.ps1`, satır 38-58 |
| **donduruldu** | 2026-07-27 12:56:29 |
| **ilk koşu başladı** | `2026-07-27-12-56-47` (**+18 saniye**) |
| **sonuçtan önce mi** | ✅ **evet** |
| **sonuç** | **P1 YANLIŞLANDI**, **P2 DOĞRULANDI** (3/3 checkpoint) |

> "PRE-REGISTERED PREDICTION 1 ... student ECE at T=0.74 lands BETWEEN the T=0.26 and T=1.0
> students, preserving the ordering ECE(0.5063) < ECE(0.26) < ECE(0.74) < ECE(1.0)."
> "PRE-REGISTERED PREDICTION 2 ... student JSD is MINIMISED at T=0.74."

Ölçülen @swa: ECE(0.5063)=0.0185 < **ECE(0.74)=0.0344** < ECE(0.26)=0.0587 < ECE(1.0)=0.0783.
Yani T=0.74, T=0.26'nın **altında** kaldı → P1 düştü. JSD argmin'i T=0.74'te → P2 geçti.

**Hata ön-kayıttaydı, yasada değil.** P1'i yazarken öğretmen ECE'sini işaret-kör bir sıralayıcı
gibi kullandım; oysa **yön asimetrisini (T4) zaten kendim belgelemiştim**. T=0.26 aşırı-güvenli
dalda, T=0.74 az-güvenli dalda; asimetri uygulansaydı tam bu sonucu öngörürdüm. Yasanın
düzeltilmiş ifadesi: **öğrenci ECE'si |işaretli açık|'ta monotondur, her dal içinde ayrı ayrı.**

Ayrıca aynı artefakt **zorunlu çift-eksen değerlendirme kuralını** da donduruyor
("Do NOT score these students on hard-label ECE alone... a rigged test"), yani T7'nin iki eksenli
oluşu da ön-kayıtlıdır, sonuç görüldükten sonra eklenmiş bir savunma değil.

---

### A5 · B-016 — köprü öğretmeni, iki bantlı karar kuralı

| alan | değer |
|---|---|
| **artefakt** | `diagnostics/bridge_teacher_check.py`, satır 46-47 (`HEAD_CENTER, RECIPE_CENTER, BAND = 0.015, 0.038, 0.010`) + `diagnostics/P0_teacher_recipe_diff_report.md` (2026-07-20 13:26) |
| **donduruldu** | 2026-07-20 13:41:12 |
| **öğretmen eğitimi başladı** | `2026-07-21-13-36-38` (**+23 sa 55 dk**) |
| **sonuçtan önce mi** | ✅ **evet** — ölçüm betiği, ölçülecek modelin eğitimi *başlamadan* yazıldı |
| **sonuç** | ECE 0.0391 → **reçete bandının merkezinde**, head bandının tamamen dışında |

⚠️ **Kanıt olarak `bridge_teacher_check.json` KULLANILAMAZ.** O dosya bantları içeriyor ama
21 Tem 21:59'da, yani `best.pt`'den (18:52) sonra yazıldı — çıktı, ön-kayıt değil. Bantların
ön-kayıt kanıtı **betiğin kendisidir**.

---

### A6 · B-001/B-005 — Stage1 doz-yanıtı

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p1_temperature_doseresponse_queue.ps1`, satır 25 |
| **donduruldu** | 2026-07-23 10:34 |
| **ilk ızgara koşusu** | `2026-07-23-10-35-11` (**+~1 dk**) |
| **sonuçtan önce mi** | ⚠️ **kısmen** |

> "Prediction (calibration thesis): student ECE is a U in T with a minimum near T\*=1.34"

**Neden "kısmen":** T=1.34 noktası ızgaradan **önce** tek başına koşmuştu —
`RAFDB_stage1_tempscale_T1341_halfA_baseline_.../2026-07-21-11-14-32`, B3 yarı-bölme deneyi.
Yani "minimum T\*=1.34 civarında" ifadesi kör bir tahmin değil, bilinen bir noktanın
genellemesiydi. **U'nun şekli** (iki uçta da yükselme) kördü; **minimumun yeri** değildi.
Makalede bu ayrım açıkça yazılmalı; aksi hâlde fazla iddialı olur.

### A7 · P1 — `logit_std` n=1 → n=3 (2026-07-29) — **CONFIRMED 3/3**

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p1_logit_std_seeds_queue.ps1`, satır 15-42 |
| **donduruldu** | 2026-07-29 01:23:40 |
| **ilk koşu başladı** | `2026-07-29-01-24-08` (**+28 saniye**) |
| **sonuçtan önce mi** | ✅ **evet** |
| **tahmin** | P1.1 ΔECE > 0 üç öğretmende de · P1.2 3/3 tohumda aynı işaret · P1.3 \|Δacc\|/acc_sd < \|ΔECE\|/ece_sd |
| **yanlışlanırsa** | "en yıkıcı müdahale" ifadesi geri çekilir; P1.3 düşerse "yalnız doğruluğa bakmak yanıltır" çerçevesi bu satır için düşer |
| **sonuç** | ✅ **P1.1, P1.2, P1.3 üçü de doğrulandı** (6 koşu bitti 2026-07-29 14:06) |

### A8 · P2 — gate:oracle_error n=1 → n=3 + eksik kontrol (2026-07-29) — **KISMEN YANLIŞLANDI (1/3)**

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p2_gate_oracle_seeds_queue.ps1`, satır 15-38 |
| **donduruldu** | 2026-07-29 01:26:59 |
| **ilk koşu başladı** | `2026-07-29-14-24-13` |
| **sonuçtan önce mi** | ✅ **evet** (dondurma anında koşu başlamamıştı) |
| **tahmin** | P2.1 ve P2.2 NULL (\|Δ\| ≤ kontrolün tohum sd'si) · P2.3 işaretler tutarsız |
| **yanlışlanırsa** | "weighting ekseni kapalı" iddiası düşer, makale yeniden çerçevelenir |
| **koşular** | 5/5 bitti (`exit 0`), son koşu 2026-07-30 01:56:48 |
| **sonuç** | ❌ **P2.1 yanlışlandı (1.10×)** · ❌ **P2.2 yanlışlandı (2.08×)** · ✅ **P2.3 doğrulandı** |

**Ölçüm** (@swa, 3 tohum, sınıf-ağırlığı eşleşmiş kontrole karşı — `diagnostics/p2_gate_oracle/p2_verdict.md`):

| # | bar (kontrolün tohum sd'si) | ölçülen | oran | hüküm |
|---|---|---|---|---|
| P2.1 Δacc | 0.207 pp | 0.228 pp | 1.10× | ❌ yanlışlandı |
| P2.2 ΔECE | 0.0027 | 0.0056 | 2.08× | ❌ yanlışlandı |
| P2.3 işaretler | — | acc `--+`, ECE `+++` | — | ✅ doğrulandı |

**Bu hüküm nasıl okunmalı — iki eksen aynı şeyi söylemiyor.**

- **Doğruluk ekseninde tahmin harfiyen düştü, ruhen durdu.** Bar 0.207 pp, ölçülen 0.228 pp:
  aşım **0.021 pp**, yani tasarımın çözebileceğinin çok altında. Aynı eksende işaretler de
  tutarsız (`--+`, P2.3 tam bunu yakalıyor). Yani "gate doğruluğu değiştiriyor" **denemez**;
  donmuş kural harfiyen çiğnendiği için P2.1 yine de yanlışlanmış sayılır ve öyle raporlanacak.
  Barı sonradan gevşetmek ön-kaydı anlamsızlaştırırdı.
- **Kalibrasyon ekseninde tahmin gerçekten düştü.** ΔECE = **+0.0056 ± 0.0040**, kontrolün tohum
  sd'sinin 2.08 katı ve **3/3 tohumda aynı işaret**. Bu bir null değil: **gate, kusursuz sinyalle
  bile kalibrasyonu tutarlı biçimde bozuyor.**

**Çerçeveleme buna göre düzeltildi.** "Weighting ekseni kapalı çünkü etkisi yok" ifadesi yanlış;
doğrusu **"weighting ekseni kapalı çünkü kusursuz bilgiyle bile kalibrasyona zarar veriyor"**.
Gate bir katkı olarak yine ölü — ama nötr olduğu için değil, zararlı olduğu için. Makaledeki
"no headroom" cümleleri bu ayrımı taşıyacak biçimde yazılacak.

> **Eksik kontrol gerçek bir hasarı maskeliyordu — onarımın ölçülmüş gerekçesi.** Aynı koşular,
> aynı tohumlar, tek fark hangi kontrole farklandığı:
>
> | kontrol | ΔECE | işaretler | okuma |
> |---|---|---|---|
> | `effective_number` (P2'den önce) | +0.0004 ± 0.0011 | `+-+` | ECE-nötr *görünüyor* |
> | `none` (P2'nin ürettiği temiz kontrol) | +0.0056 ± 0.0040 | `+++` | kalibrasyonu bozuyor |
>
> Sınıf ağırlıklandırması kontrolün **kendi** ECE'sini 0.0052 kötüleştirdiği için (ölçüm:
> `none − effective_number` = −0.0052 ± 0.0038, n=3), gate'in aynı büyüklükteki hasarı farkta
> sıfıra yakın çıkıyor ve işaretler karışıyordu. A8'in kontrol onarımı bir titizlik jesti değil,
> sonucu değiştiren bir düzeltmeydi.

> **A8'in ikinci amacı — altı gate satırının yeniden farklanması — YALNIZ 4/8 KARŞILANDI.**
> `kd_common.py` gate + sınıf-ağırlıklı CE'yi hard-error verdiği için **bütün** gate koşuları
> `--class-weight-mode none` ile koşuldu, ama T5 onları `effective_number` baseline'a karşı
> farklıyordu. P2 eksik kontrolü üretti — **ama yalnız VAE9182 öğretmeni için.** 400e/SWA@200
> bütçesindeki 8 gate koşusundan 4'ü (hepsi VAE9182) temiz kontrole taşındı; stage1 ve primary'nin
> 4 satırı (`{stage1, primary} × {mean_logvar, target_logvar}`, tohum 42) kendi sınıf-ağırlığı
> kipinde kontrolü olmadığı için **T5'ten düşürüldü** ve yukarıdaki confound boyuyla birlikte
> supplementary'de raporlanacak. Tamamlaması 2 öğretmen × 3 tohum = **6 koşu** gerektirir;
> deney dondurma yürürlükte, başlatılmadı.
>
> Gate iddiası bu 4 satıra dayanmıyor: `gate:oracle_error` **kusursuz** sinyalle, **temiz**
> kontrole karşı, **3 tohumda** ölçülen üst sınırdır — kusursuz bilgi bile kazanç getirmiyorsa
> daha zayıf sinyaller getiremez.

#### A8-tamamlama · P4 — stage1 + primary için eksik `class_weight_mode=none` kontrolü (30 Tem 2026)

**Bu bir tahmin beyanı DEĞİL, bir kontrol tamamlamasıdır.** Yazıldığı an: koşular başlamadan önce.

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p4_noclassweight_controls_queue.ps1` |
| **kapsam** | 2 öğretmen (stage1, primary) × 3 tohum (42, 1, 43) = **6 koşu** |
| **tek değişen** | `--class-weight-mode none` (karşılık gelen baseline'da `effective_number`); tarif başka hiçbir yerde farklı değil, öğretmen/bütçe/α/τ/SWA aynı |
| **niçin** | A8'in ürettiği temiz kontrol yalnız VAE9182 içindi; T5'in dört gate satırı (`{stage1, primary} × {mean_logvar, target_logvar}`) kendi sınıf-ağırlığı kipinde kontrolü olmadığı için tablodan düştü |

**Ön-kayıt statüsü — açıkça:** bu koşulara **hiçbir yeni tahmin bağlı değildir**. Ne çıkarsa
çıksın, dört gate satırı T5'e temiz kontrolle girecek ve `diagnostics/paper_tables/section54_numbers.md`
B1/B3 buna göre güncellenecek. Tahmin yazmıyoruz çünkü yazacak bir şey yok: ölçülecek nicelik
zaten raporlanmış bir kolun eksik kontrolü, yeni bir hipotez değil. Dolayısıyla makalede bu altı
koşu için "pre-registered prediction" **denmeyecek**; "pre-declared control completion" denecek.

**Sonuç-avı kapısı kapalı, gerekçesiyle:** sonucun hangi yöne çıktığı, satırların tabloya
girip girmeyeceğini değiştirmiyor. Dört satır, ΔECE pozitif de çıksa negatif de çıksa, `†` işareti
olmadan ve tam hâliyle T5'e yazılacak. Beyanın amacı tam olarak bu taahhüdü koşulardan önce
kilitlemek.

**Niçin şimdi, dondurma yürürlükteyken:** A8'in hükmünden sonra gate iddiası artık "nötr" değil
**işaretli hasar**, ve şu an tek öğretmende — tek koşulda — ölçülmüş durumda. Makalenin doz-yanıt
yasası zıt patolojili iki veri kümesinde tuttuğu için inandırıcı; hasar iddiasının da aynı
muameleyi görmesi gerekiyor. Tek koşullu bir hasar iddiası, makalenin baştan sona karşı çıktığı
şeyin kendisi olurdu.

**Süre — iki kez yanlış ölçtüm, üçüncüde doğru; ikisi de kayda geçiyor.**

1. **İlk tahmin (≈10.5–11 sa) yanlıştı**, çünkü P3'ün ölçülmüş 3.4–3.7 sa'lik eşli koşularından
   çıkarılmıştı ve **P3 width 0.5'ti**; bunlar width 1.0.
2. **İkinci "ölçüm" de yanlıştı.** Eşli başlatıp 9–10 epoch üzerinden duvar saati aldım ve
   49.8 s/epoch buldum; sonra sıralıda 3 epoch üzerinden 57.5 s/epoch. **İkisi de süreç başlatma
   maliyetiyle kirlenmişti** (556 MB öğretmen yükleme + cudnn ısınma + dataloader kurulumu, ~100 s;
   9 epoch'a bölününce epoch başına ~11 s şişme). Az epoch üzerinden duvar saati, oran ölçmez.
3. **Doğru yöntem** iki noktalı fark, ve pencere ne kadar uzunsa o kadar iyi: epoch 6 → 26,
   7.0 dakikada 20 epoch → **21.0 s/epoch → 2.33 sa/koşu**. (8 epoch'luk daha kısa pencere
   21.3 s/epoch veriyordu; %1.4 fark, uzun pencere esas alınıyor.) Bu, P2'nin dört sıralı
   koşusuyla (2.34/2.29/2.31/2.28 sa) birebir tutarlı — asıl doğrulama buydu.

**Düzeltme: sıralıya geçme kararımın verim gerekçesi hatalıydı.** Startup'tan arınmış hâliyle:

| yerleşim | koşu başına | 6 koşunun tamamı | kanıt gücü | risk |
|---|---|---|---|---|
| eşli, workers 8 | ~4.2 sa (≈38 s/epoch) | **≈12.7 sa** (iki akış eşzamanlı, 3+3) | ⚠️ **zayıf** — tqdm'in bildirdiği 36 s eğitim + ~2 s doğrulamadan *çıkarım*; koşu durdurulduğu için uzun pencereli duvar saati doğrulaması **yok** | çökme yarıçapı 2 koşu; hata 1455 (ERROR_COMMITMENT_LIMIT) **P2'de tam bu yerleşimde çıktı** |
| **sıralı, workers 12** *(kullanılan)* | 2.33 sa | **14.0 sa** | ✅ **güçlü** — 20 epoch'luk iki noktalı duvar saati ölçümü, ayrıca P2'nin dört bağımsız koşusuyla uyumlu | çökme yarıçapı 1 koşu |

Yani eşli, iddia ettiğim gibi 2.8 sa yavaş değil, **~1.5 sa hızlıydı** — ama bu 1.5 sa'lik üstünlük
sıralı sayısıyla aynı sağlamlıkta ölçülmedi, çıkarımdır. Buna rağmen sıralıda
kalınıyor, ama artık **doğru gerekçeyle**: 14 saatlik bir işte marjinal 1.5 sa için yerleşimi
ikinci kez değiştirmek, hâlihazırda yapılmış ~15 dakikayı çöpe atıp bu kampanyada **bir kez
gerçekleşmiş** bir başarısızlık kipini (1455) geri davet etmek olurdu; `train_rafdb_kd.py`'de
`--resume` de yok. Karar hız değil **risk** gerekçesiyle savunulabilir; hız gerekçesi geri
çekiliyor.

| alan | değer |
|---|---|
| **başlatıldı** | 2026-07-30 14:32:03, sıralı `-Stream S -Workers 12`, `p4_noclassweight_sequential.log` |
| **ölçülmüş hız** | 21.0 s/epoch (20 epoch'luk pencere) → 2.33 sa/koşu |
| **bitti** | 2026-07-31 04:29:14, **6/6 `exit 0`** (2.29–2.39 sa/koşu, toplam 13.95 sa — 14.0 sa tahmini 3 dakika içinde tuttu) |
| **sonuç** | ✅ dört gate satırı temiz kontrolle T5'e girdi · ⚠️ **hasar iddiası öteki iki öğretmende tekrarlanmadı** |

#### P4'ün sonucu — ön-beyan tam da bunun için yazılmıştı

Dört onarılan satır (@swa, kendi sınıf-ağırlığı kipindeki kontrole karşı, **hepsi n=1**), ve
yargılandıkları bar (o öğretmenin `cw=none` kontrol kolunun kendi ECE tohum sd'si, artık n=3):

| satır | ΔECE | bar | oran | okuma |
|---|---|---|---|---|
| stage1 · `gate:mean_logvar` | +0.0000 | 0.0021 | 0.00× | gürültü içinde |
| stage1 · `gate:target_logvar` | −0.0028 | 0.0021 | 1.32× | gürültü dışında ama **ters yönde** (ECE iyileşmiş) |
| primary · `gate:mean_logvar` | −0.0027 | 0.0033 | 0.80× | gürültü içinde |
| primary · `gate:target_logvar` | +0.0019 | 0.0033 | 0.57× | gürültü içinde |
| *(karşılaştırma)* vae9182 · `gate:mean_logvar` | +0.0067 | 0.0027 | 2.48× | gürültü dışında, hasar yönünde |
| *(karşılaştırma)* vae9182 · `gate:oracle_error` **n=3** | +0.0056 | 0.0027 | 2.08× | gürültü dışında, **3/3 aynı işaret** |

**Hüküm: kalibrasyon hasarı yalnız VAE9182'de kurulu, öteki iki öğretmende tekrarlanmıyor.**
Dördün işaretleri karışık (`+`, `−`, `−`, `+`) ve üçü kendi kontrolünün tohum gürültüsünün içinde.
Tek istisna ters yönde. Yani A8'den sonra yazdığım **"kusursuz sinyalle bile, tutarlı biçimde
kalibrasyonu bozuyor"** ifadesi **her öğretmen için genelleştirilemez**; kurulu olan şey daha dar:

> **İyi kalibre edilmiş öğretmende (VAE9182), kusursuz sinyalle bile gate kalibrasyonu bozuyor
> (+0.0056, kontrolün tohum sd'sinin 2.08 katı, 3/3 aynı işaret, ön-kayıtlı).** Aşırı-güvenli iki
> öğretmende gerçek öğrenilmiş sinyallerle bu **tekrarlanmıyor**.

**"Tekrarlanmadı", "çürütüldü" demek değil** — dördü de n=1, ve n=1 hiçbir şeyi ne kurar ne yıkar.
Ayrıca gözden kaçmaması gereken bir ölçek farkı var: stage1/primary kontrollerinin **kendi** ECE'si
0.0745 / 0.0755, VAE9182'ninkinin (0.0278) **2.7 katı**. Aynı mutlak hasar orada bağıl olarak
%7.5, VAE9182'de %20 eder — yani etki orada da olabilir ama daha büyük ve daha gürültülü bir
tabanın içinde görünmez kalır. Bunu ayırmak o iki kolda n=3 gerektirir (**4 koşu**, başlatılmadı).

**Makalede nasıl yazılacak:** hasar iddiası **iyi kalibre edilmiş öğretmene koşullanarak**
verilecek; "her öğretmende" ya da "tutarlı biçimde" gibi genelleyici ifadeler kullanılmayacak.
Dört satır T5'te tam hâliyle, `†` (n=1) işaretiyle duruyor — beyanın taahhüdü buydu ve sonuç
elverişsiz çıktığı hâlde uygulandı.

> **Eşli başlatma 10. epoch'ta durduruldu ve iki yarım koşu dizini silindi** (her ikisi de
> `metrics_best.json` içermiyordu, yani ledger onları zaten atlıyordu; ama `best_checkpoint.pth`
> yazmışlardı ve seçim denetimi 10 epoch'luk bir checkpoint'i toplayabilirdi).

#### A8-tamamlama · P5 — `gate:oracle_error`'ün stage1 ve primary'de tekrarlanma denemesi (31 Tem 2026)

**Bu bir ÇÖZÜM DENEMESİDİR (resolution attempt), tahmin değil.** Yazıldığı an: koşular başlamadan
önce.

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p5_oracle_replication_queue.ps1` |
| **kapsam** | `gate:oracle_error` × {stage1, primary} × {42, 1, 43} = **6 koşu** |
| **tek değişen** | `--gate-enable --gate-uncertainty-source oracle_error`; kontrolü P4'ün ürettiği aynı öğretmenin `class_weight_mode=none` baseline'ı, tarif başka hiçbir yerde farklı değil |

**Neyi ayırmaya çalışıyor.** P4'ten sonra elimizde şu var: VAE9182'de kusursuz sinyalli gate
ECE'yi +0.0056 bozuyor (kontrolün tohum sd'sinin 2.08 katı, 3/3 aynı işaret, ön-kayıtlı A8);
stage1/primary'de ise **gerçek öğrenilmiş sinyallerle** n=1'de bir şey görünmüyor. İki açıklama
ayırt edilemiyor: **(a)** hasar VAE9182'ye özgü, **(b)** hasar orada da var ama stage1/primary
öğrencilerinin kendi ECE'si 0.0745/0.0755 — VAE9182'nin 0.0278'inin **2.7 katı** — olduğu için
aynı mutlak hasar bağıl olarak %20 yerine %7.5 ediyor ve daha gürültülü bir tabanın içinde
görünmez kalıyor.

**⚠️ Tasarım düzeltmesi: bu 6 koşu, benim daha önce yazdığım "4 koşu" değil.** O rakam bir
aritmetik hataydı ve buraya kaydı düzeltilmiş hâliyle geçiyor. Doğru sayı iki nedenle 6:
stage1 ve primary'de **hiç** `oracle_error` koşusu yok (mevcut gate satırları `mean_logvar` ve
`target_logvar`), yani 2 öğretmen × 3 tohum tamamen yeni. Ve **replikasyon aynı müdahaleyi
gerektirir**: kurulu bulgu oracle'la kurulmuşken onu gerçek-sinyal satırlarına karşı sınamak
elmayla armut olurdu — P4'ün null'ını yorumlamayı zorlaştıran asimetri tam olarak buydu.
Mevcut gerçek-sinyal hücrelerini n=3'e çıkarmak ayrı ve **farklı** bir soru (10 koşu); bu kuyruk
onu sormuyor.

**Ön-kayıt statüsü:** hiçbir yeni tahmin bağlı değildir. Oracle **üst sınırdır** — kusursuz
bilgiyle hasar çıkmıyorsa gerçekleştirilebilir hiçbir sinyalle çıkmaz — o yüzden bu kuyruk
"kazanılacak" bir sonuç taşımıyor.

**KARAR EŞİĞİ — şimdi yazılıyor, sonradan seçilmeyecek.** Her kol kendi öğretmeninin
`cw=none` kontrolünün **kendi ECE tohum sd'sine** karşı ölçülür (@swa, tohum içinde eşleştirilmiş;
barlar P4'ten: stage1 **0.0021**, primary **0.0033**):

| ölçüt | sonuç |
|---|---|
| 3/3 tohumda aynı işaret **ve** \|ΔECE\| ≥ 2× kendi kontrolünün ECE tohum sd'si | **KURULU** — o öğretmende hasar var |
| aksi hâlde | **ÇÖZÜNMEDİ** |

**Her iki sonuç da metne girer, ikisinin de nasıl yazılacağı şimdi sabitleniyor:**

- **Hasar çıkarsa:** iddia genişler — *"kusursuz sinyalle bile, birden fazla öğretmende
  kalibrasyonu bozuyor"* — ve koşullanma kaldırılır.
- **Null kalırsa:** koşullanmış iddia (*"iyi kalibre edilmiş öğretmende"*) korunur, **ve null
  pozitif bir bulgu olarak yazılır**: headroom'u olan (kötü kalibre) öğretmende gate'in hasarı
  çözünmüyor, yani hasar öğretmenin kalibrasyon başlangıcına koşullu — bu, makalenin
  kalibrasyon-koşullu aktarım çerçevesiyle **uyumlu**, ona rağmen değil.

**Tahmini süre:** sıralı, `--workers 12`, ölçülmüş 2.33 sa/koşu → **6 × 2.33 ≈ 14.0 sa.**
(Kullanıcının beklediği ~9.2 sa 4 koşuya göreydi; 6 koşu 14.0 sa.)

| alan | değer |
|---|---|
| **beyan donduruldu** | 2026-07-31 14:14:11 (`rafdb_p5_oracle_replication_queue.ps1` mtime) |
| **ilk koşu başladı** | `2026-07-31-14-14-40` (**+29 saniye**) |
| **sonuçtan önce mi** | ✅ **evet** |
| **kuyruk bitti** | 2026-08-01 04:12:28, 6/6 exit 0, hepsi 400/400 epoch |
| **sonuç** | **0/2 KURULU — iki kolda da ÇÖZÜNMEDİ** |

### P5 hükmü (donmuş eşik harfiyen uygulandı)

| öğretmen | ΔECE @swa | işaretler | bar | 2×bar | \|ΔECE\|/bar | hüküm |
|---|---|---|---|---|---|---|
| stage1 | **+0.0015** ± 0.0036 | `+-+` | 0.0021 | 0.0042 | 0.74× | **ÇÖZÜNMEDİ** |
| primary | **+0.0004** ± 0.0053 | `+-+` | 0.0033 | 0.0066 | 0.11× | **ÇÖZÜNMEDİ** |
| *referans: vae9182 (A8/P2)* | *+0.0056* | `+++` | *0.0027* | — | *2.08×* | *KURULU* |

Kural bir **VE** bağlacıydı ve her iki kol **iki koşulda birden** düştü: işaretler 3/3 değil
(`+-+`), ve büyüklükler 2×bar'ın altında. Marjinal bir düşüş değil — stage1 barın 0.74'ünde,
primary 0.11'inde. Beyan edilen barlar veriden yeniden ölçülenle uyuştu (stage1 0.0021,
primary 0.0033), yani hüküm bar seçimine bağlı değil.

**Yukarıda önceden yazılmış "null kalırsa" metni yürürlüğe girdi** ve olduğu gibi uygulanıyor:
koşullanmış iddia (*"iyi kalibre edilmiş öğretmende"*) korunur. Ek olarak, aynı metinde
taahhüt edilen okuma: hasar öğretmenin kalibrasyon başlangıcına koşullu; stage1/primary
öğrencilerinin kendi ECE'si (0.0745/0.0755) VAE9182'ninkinin (0.0278) 2.7 katı olduğu için
aynı mutlak hasar bu gürültü tabanında çözünmüyor. Beyandaki (a)/(b) ayrımı **ayrılamadı** —
bu kuyruk (a)'yı seçmiyor, yalnız (b)'yi dışlayamadığını gösteriyor.

> ⚠️ **ÇÖZÜNMEDİ ≠ etki yok.** Bar, kolun kendi tohum gürültüsünün **iki katıdır**; altında
> kalan bir etki ölçülemedi demektir, yoktur demek değil. *"Gate stage1 ve primary'de
> kalibrasyonu bozmuyor"* cümlesi bu veriyle **yazılamaz**.

**D1 kapanış gerekçesi buna göre iki kollu yazılacak:**
1. **Koşulsuz:** kusursuz bilgiyle bile gate **hiçbir** öğretmende doğruluk kazandırmıyor
   (Δacc @swa: stage1 −0.22, primary −0.01, vae9182 −0.23 — üçü de ≤ 0). Kapanış asıl bu
   satıra dayanır ve P5 onu iki öğretmen ekleyerek **güçlendirdi**.
2. **VAE9182'ye koşullu:** kalibrasyon hasarı yalnız orada kuruldu.

Artefaktlar: `diagnostics/p5_oracle_replication/p5_verdict.{md,json}`,
`diagnostics/p5_oracle_replication_verdict.py`.

---

> **Kalıcı onarım (kod).** `class_weight_mode` artık `runs.csv`'de bir sütun ve `paper_tables.py`'de
> **eşleştirme anahtarının parçası**. Bunun sebebi sadece gate satırları değil: P2 diske ikinci bir
> yasal kontrol koyduğu için, kip anahtara girmeseydi her (öğretmen, tohum) hücresinde iki kontrol
> olur ve hangisinin kazandığı **sözlük sırasına** kalırdı. Belirsizlik artık sessizce geçmiyor,
> `RuntimeError` veriyor.

---

### A9 · P6 — τ×T faktöriyeli + α modülasyonu: yasa hangi değişkenin yasası? (1 Ağu 2026)

**İlk tam-zincir ön-kayıt: beyan → commit → tag → koşu.** Önceki tüm ön-kayıtlar yalnız
mtime + koşu-dizini damgası taşıyor (bkz. dosya başındaki git notu); bu beyan koşudan önce
commit'lenip `p6-predeclared` tag'iyle sabitlendi — commit hash'i ilk kez kanıt zincirinin
parçası.

| alan | değer |
|---|---|
| **artefakt** | `rafdb_p6_tau_alpha_queue.ps1` (karar kuralları başlıkta, harfiyen) |
| **kapsam** | Stage1 · RAF-DB · 3 tohum {42, 1, 43} · **42 yeni koşu** (Grid 1: 18, Grid 2: 24) |
| **tek değişenler** | yalnız τ (`--temperature`), α (`--alpha`), T (`--teacher-temperature-scale`); tarif P1 doz-yanıt kuyruğundan aynen |
| **yeniden kullanılan** | τ=6 kolonu (T∈{0.85, 1.3406, 1.70} × 3 tohum, diskte doğrulandı) ve α=0.3 çifti (baseline + tempscale_T134, 3'er tohum) |

**Grid 1 — τ×T (indirgeme testi).** İki eşleşmiş T·τ çifti: (τ=3, T=1.70)↔(τ=6, T=0.85) →
5.10 ve (τ=6, T=1.70)↔(τ=12, T=0.85) → 10.20.

- **P6.1 (çökme):** öğrenci ECE'si (T,τ)'ya yalnız **T·τ çarpımı** üzerinden bağlıdır.
  Karar kuralı (@swa, tohum-içi eşleştirilmiş): her çift için |ort ΔECE| ≤ 2×bar VE işaretler
  3/3 uyuşmuyor → **ÇÖKME DOĞRULANDI** (o çift); iki çiftte birden 3/3 aynı işaret VE ≥2×bar →
  **ÇÖKME YANLIŞLANDI** (ayrışmanın kendisi bulgu: sıra bilgisi ile yumuşaklık ayrı kanallar);
  başka her durum → **ÇÖZÜNMEDİ**, çift başına raporlanır, genel iddia yazılmaz.
  **Bar şimdi donuyor: 0.0012** (stage1/`effective_number` kontrol kolunun ECE tohum sd'si
  @swa, `denominator_table.json`) → 2×bar **0.0024**.

**Grid 2 — α modülasyonu (dinleme kanalı).** Gap(α) := ECE(T=1) − ECE(T=1.3406), tohum-içi.

- **P6.2 (monotonluk):** gap(α), α arttıkça monoton azalır — 5 α noktasında {0.1, 0.3, 0.5,
  0.7, 0.9}, her tohumda ardıl her adımda artmayan; **3/3 tohumda** sağlanırsa DOĞRULANDI.
- **P6.3 (uçlar):** gap(0.9) < gap(0.1), kesin eşitsizlik, **3/3 tohumda**.

**Çerçeve:** iki sonuç da yayımlanabilir; eşikler sonradan seçilmeyecek. Koşular denetim
kesmesinin dışında — T8'e girmezler (kod engelliyor), T1–T5'e de girmezler (T1/T2 açık isim
sözlüğü; T5 kontrol havuzu α=0.3 + t_scale=1.0 şartlı). Kendi tabloları olacak (**T11/T12**).
Tahmini yük 42 × ~2.33 sa ≈ 98 sa ≈ 2–6 Ağu; makale gönderimini beklemez/bloklamaz.

| alan | değer |
|---|---|
| **beyan donduruldu** | 2026-08-01 14:21:57 (`rafdb_p6_tau_alpha_queue.ps1` mtime) |
| **commit + tag** | `3d9dbee` · 2026-08-01 14:23:31 · tag `p6-predeclared` |
| **ilk koşu başladı** | `2026-08-01-14-23-45` (**commit'ten +14 sn**) |
| **sonuçtan önce mi** | ✅ **evet — ve ilk kez üç bağımsız damgayla:** mtime < commit < koşu |
| **kuyruk bitti** | 2026-08-05 16:16 · **42/42**, hepsi 400/400 epoch, 0 yeniden deneme |
| **sonuç** | **P6.1 ÇÖKME YANLIŞLANDI · P6.2 DOĞRULANMADI (0/3) · P6.3 DOĞRULANDI (3/3)** |

**HÜKÜM (6 Ağu 2026, kuyruk 42/42 kapandıktan sonra).** Uygulayıcı sonuç okunmadan ÖNCE
commit'lendi (`5f78cee`; anahtar-tipi düzeltmesi `18a33ef`, o da okumadan önce). Üretici:
`diagnostics/p6_verdict.py` → `diagnostics/paper_tables/p6_collapse_test.md` (T11/T12).

- **P6.1 — ÇÖKME YANLIŞLANDI.** İki eşleşmiş çiftte de işaretler 3/3 aynı ve |ort ΔECE|
  bardan büyük: T·τ=5.10 için −0.0391 ± 0.0032 (**16.30×** 2×bar), T·τ=10.20 için
  −0.0324 ± 0.0029 (**13.50×**). Öğrenci ECE'si T·τ çarpımına indirgenmiyor; τ ve T ayrı
  kanallar. Beyanın kendi sözleriyle: *ayrışmanın kendisi bulgu.*
- **2 Ağu erken okuması BİREBİR yeniden üretildi.** Altı ΔECE değerinin tamamı ve iki çift
  statüsü aynı çıktı (fark toleransı 1e-12). Beyan bunu şart koşuyordu; karar mantığı
  `p6_1_early_reading.py`'den ithal edildiği için kopya-kayması yapısal olarak imkânsız.
- **P6.2 — DOĞRULANMADI (0/3 tohum).** gap(α) monoton azalmıyor: üç tohumda da α=0.1→0.3
  adımı ARTIYOR (+0.0100 / +0.0081 / +0.0055), iki tohumda 0.3→0.5 de artıyor. Eğri
  monoton değil, **α≈0.5'te iç bükümlü bir tepe** yapıp sonra dikçe düşüyor.
- **P6.3 — DOĞRULANDI (3/3 tohum).** gap(0.9) < gap(0.1), üçünde de kesin: −0.0504 /
  −0.0611 / −0.0613.
- **Uçlar tuttu ama gerekçe tutmadı — bu ayrıca yazılıyor.** Beyanın gerekçesi "α arttıkça
  öğrenci öğretmeni daha az dinler, dolayısıyla müdahalenin etkisi **sönümlenir**" idi
  (α sert-etiket ağırlığı: `kd_common.py:440`, `loss = α·hard + (1−α)·soft`). Gerçekte etki
  sönümlenmiyor, **işaret değiştiriyor**: gap α=0.5'te +0.0327 ile tepe yapıp α=0.9'da
  −0.0352'ye iniyor; yani yüksek α'da öğretmen-tarafı ön-ölçekleme öğrenciye **zarar
  veriyor** ve zararın büyüklüğü faydanın tepe değeriyle kıyaslanabilir. P6.3'ün hükmü
  DOĞRULANDI'dır — kural uçları karşılaştırır, yolu değil — ama tahmin edilen mekanizma
  gerçekleşmedi. Ön-kayıt disiplini gereği hüküm ile mekanizma ayrı ayrı raporlanır.

> **Kapsam değişikliği (4 Ağu 2026, veriden önce).** A9 başlangıçta tez / 3. çalışma
> kapsamındaydı; makaleye girmesi planlanmıyordu. 3 Ağu 2026 tarihli dış inceleme
> (`paper_review.md`, Reject→Major) kimliklendirmeyi birinci eksik olarak işaretledi ve P6
> çökme testi buna doğrudan cevap olduğu için **makaleye alındı**. Değişen yalnız kapsamdır:
> P6.1/P6.2/P6.3 kuralları ve 0.0012 barı 1 Ağu'da `p6-predeclared` tag'iyle sabitlendi, bu
> not yazılırken kuyruk **26/42**'de ve hiçbir hüküm okunmadı. Yani kural veriden önce
> beyanlıydı; makaleye alma kararı sonuçtan değil, hakem eksiğinden geldi.

---

### A10 · R3 — dış inceleme robustluk turu: çok-metrik envanter (4 Ağu 2026)

**Tam zincir, ikinci kez: beyan → commit → tag → hesap.** Hiçbir metrik bu commit'ten önce
hesaplanmadı; `robustness_metrics.py`, `tstar_sensitivity.py`, `jsd_sensitivity.py` ve
FERPlus logit önbelleği bu beyandan **sonra** yazılacak.

**Kaynak:** `paper_review.md` (dış inceleme) üç hesaplanabilir eksik gösterdi: tek ECE
spesifikasyonu, T* fit-kriteri duyarlılığının nicelenmemiş olması, FERPlus JSD hedefinin
koşullu dağılımda test edilmemiş olması. Üçü de kayıtlı önbellekten çıkar — **eğitim yok**,
P6 kuyruğu etkilenmiyor.

#### Beyan edilen çerçeve (kilitli)

- **BAŞARI ÖLÇÜTÜ YOKTUR.** Bu bir robustluk envanteridir, hipotez testi değildir. Hiçbir
  eşik, hiçbir "doğrulandı/yanlışlandı" hükmü yoktur. Ne çıkarsa makaleye o girer.
- **Hesaplanan hiçbir metrik rapor dışı bırakılamaz.** Aşağıdaki liste kapalıdır; bir metrik
  hesaplanıp da tabloda görünmüyorsa bu bir ihlaldir.
- **Monotonluk her metrik için ayrı raporlanır.** Bozulan varsa açıkça listelenir: hangi
  çift, hangi tohum, hangi metrik. Bozulmanın gizlenmesi veya "gürültü" diye geçilmesi yok.
- Metrik seçimi, kutu sayıları ve kesitler **şimdi** donuyor; hesaptan sonra eklenmeyecek.

#### Kapsam düzeltmesi — hesaptan ÖNCE, diske bakarak

Görev metnindeki kapsam satırı (*primary 5 kol · stage1 3 kol · VAE9182 5 kol · FERPlus
3 kol*) depodaki hiçbir yapıyla eşleşmiyor. Diskte ölçülen gerçek doz-cevap serisi:

| seri | T noktaları | tohum | koşu | önbellek |
|---|---|---|---|---|
| stage1 | 0.85 · 1.00 · 1.3406 · 1.70 · 2.20 | 42, 1, 43 | 15 | ✅ var (`logits_swa.npz`) |
| vae9182 | 0.85 · 1.00 · 1.3406 · 1.70 · 2.20 | 42, 1, 43 | 15 | ❌ üretilecek |
| ferplus | 0.26 · 0.5063 · 0.74 · 1.00 | 42, 1, 43 | 12 | ❌ üretilecek |
| **toplam** | | | **42** | |

`primary` öğretmeninin doz-cevap serisi **yoktur** — tüm `tempscale_T*` koşuları stage1 ve
vae9182'ye aittir; primary'de yalnız mekanizma kolları vardır (T5). Mekanizma-kolu okuması da
sayıları tutmuyor (her üç öğretmende n=3 olan kol sayısı 4). Kapsam bu tabloya sabitlendi;
düzeltme **tek bir metrik hesaplanmadan önce** yazıldı ve karar Fatih'e sorularak alındı.

#### R3-1 · Çok-metrik doz-cevap (@swa)

Her koşu için, o koşunun kendi örnek-başına logit önbelleğinden, 7 sütun:

| metrik | spesifikasyon | kaynak |
|---|---|---|
| NLL | ortalama, doğal log | yeni |
| Brier | çok-sınıflı, tam olasılık vektörü, one-hot hedef | yeni |
| ECE eşit-genişlik, 10 kutu | max-prob üzerinde, ilk kutu solda kapalı | `confidence_ece(n_bins=10)` |
| ECE eşit-genişlik, 15 kutu | *(kampanyanın mevcut spesifikasyonu — referans sütun)* | `confidence_ece(n_bins=15)` |
| ECE eşit-genişlik, 25 kutu | | `confidence_ece(n_bins=25)` |
| ECE eşit-kütle (adaptif), 15 kutu | kutu sınırları güven kuantillerinde; son kutu sağda kapalı | yeni |
| Classwise-ECE | sınıf-başına top-1 ECE'nin düz ortalaması, 15 eşit-genişlik kutu | yeni |

Eşit-genişlik ECE **yeniden yazılmayacak**, mevcut `confidence_ece` çağrılacak (tek kaynak
kuralı); 15-kutu sütunu bu yüzden yayımlanmış ECE değerlerini birebir yeniden üretmelidir ve
bu bir doğrulama kapısı olarak raporlanacak.

Çıktı: `diagnostics/paper_tables/robustness_metrics.{md,json}` — kol × tohum ham değerler,
kol ortalamaları (sd ile), her metrik için tohum-içi monotonluk sayımı **9/9 biçiminde**
(stage1 ve vae9182 için 4 ardıl T adımı × 3 tohum = 12/12; FERPlus için 3 × 3 = 9/9 — gerçek
payda tabloda yazılır), ve her satırda kaynak dosya yolu.

**Önbellek üretimi ve cihaz kararı (beyan).** Eksik 27 önbellek `student_logit_cache.py`'nin
mevcut denetim kapısıyla üretilecek: her yazım, o koşunun `selection_audit.json`'ından
bağımsız üretilmiş acc/ECE değerine karşı doğrulanır, sapma varsa dosya **yazılmaz**.
Üretim **CUDA**'da yapılacak, CPU'da değil: modül belgesinde ölçülmüş olduğu gibi CPU, kutulu
bir istatistik olan ECE'de ~3e-4'lük cihaz tabanı taşıyor ve mevcut 15 stage1 önbelleği
CUDA'da üretilmişti — yarısı CPU, yarısı CUDA bir tabloda kollar arası 3e-4 fark ölçüm değil
donanım artefaktı olurdu. GPU'da 7.4 GB boş; çıkarım P6'yı birkaç dakika yavaşlatır,
bellek riski yok.

> **Düzeltme (4 Ağu, hâlâ hiçbir metrik okunmadan).** Yukarıdaki "her yerde CUDA" kararı
> FERPlus'ta **yanlıştı ve kapı bunu kendisi yakaladı**. FERPlus önbelleği CUDA'da
> üretilmeye çalışıldığında denetim kapısı ilk koşuda durdurdu: doğruluk 88.9629 vs
> denetimin 88.9312'si — fark tam **0.0317 pp = 1/3153**, yani tek bir örnek tahmin
> değiştirmiş. Sebep: `ferplus_selection_audit.py` varsayılan olarak **CPU**'da koşuyor
> (kendi belgesi öyle diyor), dolayısıyla yayımlanmış FERPlus sayıları CPU sayılarıdır;
> CUDA önbelleği makaledeki FERPlus tablosuyla çelişirdi.
>
> Doğru kural, beyandaki gerekçenin kendisinden çıkar — amaç "her yerde aynı cihaz" değil,
> **her serinin kendi yayımlanmış denetimini yeniden üretebilmesi**ydi. O hâlde: RAF-DB
> serileri CUDA'da (denetimleri CUDA), FERPlus serisi CPU'da (denetimi CPU). Karşılaştırmalar
> zaten seri içindedir; seriler arası mutlak ECE farkı bu envanterde bir büyüklük değildir.
> Ayrıca batch, her seride kendi denetiminin batch'ine eşitlendi (RAF-DB 256, FERPlus 64),
> çünkü farklı toplama sırası son hanede oynuyor.

#### R3-2 · T* duyarlılığı (dört öğretmen)

Öğretmen başına tek satır: `T*_NLL` (dağıtılan değer) · `argmin-ECE(T)` (sürekli, Brent ile
ECE(T) üzerinde) · iki noktadaki ECE farkı · `|T*_NLL − T*_ECE|`. **Beklenti yoktur**; fark
ne çıkarsa yazılır. FERPlus'ta 0.120/0.113 zaten bilindiği için o satır aynı zamanda
üreticinin doğruluk kontrolüdür. Çıktı: `diagnostics/paper_tables/tstar_sensitivity.{md,json}`.

#### R3-3 · FERPlus JSD duyarlılığı

Değerlendirme fold'unda üç kesit: **(a)** tüm satırlar (mevcut sonuç, referans) · **(b)**
yalnız oy-toplamı = 10 olan satırlar · **(c)** katmanlar {6–7, 8–9, 10}. Her kesit için:
`T*_JSD`, kol sıralaması (ECE-optimal ve JSD-optimal noktaların **ayrışması korunuyor mu**),
ve n. Ayrışmanın kaybolması da, korunması da yazılır. Çıktı:
`diagnostics/paper_tables/jsd_sensitivity.{md,json}`.

#### R3-4 · P6 kapanışı (42/42 sonrası, ~5 Ağu)

Kuyruk bitince A9'un T11/T12 resmî hükmü, **erken okumayla aynı üreticiyle** ve tam örneklemle
uygulanacak; P6.1 erken okumayı koşu-başına önbellekten birebir yeniden üretmelidir. Çıktı:
`diagnostics/paper_tables/p6_collapse_test.md`. Kapsam değişikliği yukarıda A9'un altına
işlendi.

| alan | değer |
|---|---|
| **beyan donduruldu** | 2026-08-04 00:59:56 |
| **commit + tag** | `0b8ef2f` · 2026-08-04 00:59:56 · tag `r3-predeclared` |
| **hesap başladı** | commit'ten sonra (ilk üretici dosyası bu commit'te henüz yoktu) |
| **sonuçtan önce mi** | ✅ evet — hiçbir metrik commit'ten önce hesaplanmadı |
| **sonuç** | *(4 Ağu hesaplandı; `paper_tables/robustness_metrics.md`, `tstar_sensitivity.md`, `jsd_sensitivity.md` ve `RESULTS_TABLES.md` içinde T13/T14/T15)* |

---

### A11 · R3-W1 — çift-eksen alt yazısının "aynı anda sağlanamaz" iddiası (6 Ağu 2026)

**Neden.** 5 Ağu 2026 tarihli Round-2 panel incelemesinde R3 koltuğu (Perspektif) BÜYÜK bir
kalem açtı: `fig_ferplus_dual.tex` alt yazısı *"no arm occupies the lower-left corner: the two
objectives cannot be satisfied at once"* diyor. Bu bir **imkânsızlık iddiası**, ama dayanağı
dört koldan ibaret bir grid. Hakem ayrıca ucuz bir çürütme adayı önerdi: insan-hizalı T=0.74
kolunda damıt, sonra ECE'yi onarmak için öğrenci-tarafı sıcaklık ölçeklemesini çapraz-uyarla.

**Ne hesaplanacak.** R0-1'in protokolünün **birebir aynısı** (`student_ts_baseline.py`):
dosya adı sha256'lanıp hex'e göre sıralanır, ilk yarı A / ikinci yarı B; T_s bir yarıda NLL
küçültmeyle fit edilir, diğerinde ölçülür, sonra yön değişir; birleşik satırda her örnek tam
bir kez, karşı yarıda fit edilmiş T ile ölçülür. Fark yalnız kapsamda: R0-1 bunu tek kola
(T=1) uygulamıştı, burada **dört doz-yanıt kolunun hepsine** uygulanır (T ∈ {0.26, 0.5063,
0.74, 1.0}), @swa, 3 tohum. İki eksen: sert-etiket ECE ve insan-JSD; raporlama kümesi
`ferplus_student_jsd` ile aynı.

**Hipotez testi DEĞİL, alt yazı yeterlilik kontrolü.** Başarı ölçütü yok; hesaplanan hiçbir
nokta rapor dışı bırakılmaz, dört kolun dördü de yazılır.

**"Sol alt köşe"nin tanımı — sayı görülmeden burada sabitleniyor.** Köşe, kolların kendi
ulaştığı iki en iyiden oluşur: `ECE_min` := kollar arasındaki en düşük öğrenci ECE'si
(T=0.51 kolu) ve `JSD_min` := kollar arasındaki en düşük öğrenci JSD'si (T=0.74 kolu). Bir
nokta köşeyi **işgal eder** demek: `ECE ≤ ECE_min + bar_ECE` **VE** `JSD ≤ JSD_min + bar_JSD`,
burada her bar = ilgili iki büyüklüğün tohum sd'lerinin büyüğünün 2 katı.

**Karar kuralı (üç kol, önceden yazıldı):**
- Herhangi bir (kol + öğrenci-TS) noktası köşeyi işgal ederse → alt yazının *"cannot be
  satisfied at once"* cümlesi **post-hoc ölçekleme içeren tarifler için YANLIŞLANMIŞ** olur ve
  yeniden yazılır. Hangi kolun yaptığı ve marjı raporlanır.
- Hiçbiri işgal etmezse → cümle bu aile için de **ayakta kalır**; bu, alt yazıyı zayıflatan
  değil güçlendiren bir sonuçtur ve öyle raporlanır (dört kol + dört TS varyantı sınandı).
- Sınırda kalırsa (bir eksende geçip diğerinde bardan taşarsa) → **çözünmedi**; nokta nokta
  raporlanır, genel iddia yazılmaz, alt yazı "no *evaluated* arm" diye daraltılır.

**Kapsam sınırı, şimdiden.** Bu kontrol yalnız FERPlus'ta yapılabilir: RAF-DB'de TS'i fit
edecek temiz bir bölme yok (§5.7'nin kendi gerekçesi). Sonuç FERPlus'a özgüdür ve öyle yazılır.

**GPU yok, eğitim yok.** Dört kolun @swa logitleri koşu dizinlerinde önbellekli (4 Ağu, R3-3
turunda üretildi); hesap CPU'da salt-okunur.

| alan | değer |
|---|---|
| **beyan donduruldu** | 2026-08-06 00:38:04 (bu blok, üretici dosyası yazılmadan önce) |
| **commit** | `2d6bed2` · 2026-08-06 00:38:04 — `r3w1_joint_optimum.py` bu commit'te henüz YOKTU |
| **sonuçtan önce mi** | ✅ evet — köşe tanımı ve üç karar kolu tek sayı görülmeden yazıldı |
| **sonuç** | **ALT YAZI YANLIŞLANDI** — `paper_tables/r3w1_joint_optimum.md` |

**HÜKÜM (6 Ağu 2026).** Köşe: `ECE_min = 0.0185` (T=0.5063 kolu), `JSD_min = 0.0536`
(T=0.74 kolu). Dört (kol + öğrenci-TS) noktasından **biri** köşeyi işgal ediyor: **native
T=1 + öğrenci-TS**, ECE 0.0203 (bar 0.0035 içinde) ve JSD 0.0545 (bar 0.0010 içinde).
Dolayısıyla alt yazının *"the two objectives cannot be satisfied at once"* cümlesi, post-hoc
öğrenci ölçeklemesi içeren tarifler için **doğru değil** ve yeniden yazılacak.

- **Marj dar, ve öyle yazılıyor.** Kazanan nokta iki eksende de en iyi kolun *üstünde*
  duruyor (+0.0018 ECE, +0.0009 JSD) ve testi yalnız tohum gürültüsünün içinde kaldığı için
  geçiyor. Savunulabilir cümle **"iki optimumdan da tohum gürültüsü içinde ayırt edilemez"**;
  "ikisini de dövdü" DEĞİL. İmkânsızlık iddiasını yanlışlamaya bu yeter — alt yazı
  *cannot* diyor — ama bir üstünlük sonucu değildir ve öyle yazılmayacak.
- **Hakemin kendi adayı geçmedi.** Önerilen T=0.74+TS, ECE'yi +0.0022 ile geçiyor ama JSD'yi
  −0.0002 ile kaçırıyor. Alt yazıyı çürüten kol, tahtadaki **en ucuz tarif**: öğretmen
  tarafında hiçbir müdahale içermeyen native T=1.
- **İstenmeyen ama daha önemli bulgu: TS, JSD eksenini çökertiyor.** Ölçeklemeden önce dört
  kol JSD'de 0.0201 aralığa yayılıyor (0.0536–0.0737); tek bir çapraz-uyarlanmış öğrenci
  skaleri sonrası aralık 0.0005'e iniyor (0.0540–0.0546) — **37×** daralma, dördü de aynı
  değere düşüyor. Yani bu veri kümesinde kollar arası insan-hizası farkının neredeyse tamamı
  bir **güven-ölçeği** etkisi ve tek bir öğrenci-tarafı skaler onu yeniden üretiyor. §5.7 bunun
  T=1 hâlini zaten raporlamıştı; dört kola genişletilince bulgu tek karşılaştırma değil,
  örüntünün kendisi oluyor. Öğretmen-tarafı kaldıracın aleyhine; yine de yazılıyor.
- **R0-1 birebir yeniden üretildi** (T=1 satırı, ham ve TS, iki eksen, üç tohum) — bölme/fit/
  ölçüm fonksiyonları `student_ts_baseline.py`'den ithal edildiği için kod yolu aynı.
- **Kapsam:** yalnız FERPlus. RAF-DB'de TS'i fit edecek temiz bölme yok (§5.7'nin kendi
  gerekçesi).

---

### A12 · gerçek-sinyal gate hücreleri n=1 → n=3 (6 Ağu 2026)

**Neden.** Round-2 panelinde DA-3 ve R1-W12 aynı yere bastı: özet *"beş mekanizma başarısız"*
diyor, ama o beşin **iki hücresi tek tohumlu**. P5 (1 Ağu) yalnız **oracle** kolunu n=3'e
çıkarmıştı; *gerçekleştirilebilir* sinyallerle koşan hücreler (`mean_logvar`, `target_logvar`)
üç öğretmende de hâlâ n=1. Tek tohum hiçbir şeyi çürütemez — bu, P4'ün kendi kaydında zaten
yazılı. Dolayısıyla özetteki başlık iddiası **kendi kanıtından daha güçlü**; bu tur onu ya
gerçek bir n=3 zeminine oturtacak ya da cümleyi yeniden yazdıracak.

**Ne koşulacak.** Beş hücre × iki yeni tohum (1, 43) = **10 koşu**. Hücreler: stage1 ×
{`mean_logvar`, `target_logvar`}, primary × {`mean_logvar`, `target_logvar`}, vae9182 ×
{`mean_logvar`}. **Yeni kontrol koşusu yok** — her kolun `baseline_noclassweight` kontrolü
zaten n=3 (P5 için koşulmuştu), farklar aynı tohum içinde eşleştirilecek.

**Tarif özdeşliği yapısal, anlatılan değil.** Her koşunun komut satırı o hücrenin **kendi
seed-42 `run_args.json`'undan** üretildi (`diagnostics/build_replicate_queue.py`), bayrak
adları `train_rafdb_kd.py`'nin kendi argparse nesnesinden okundu, ve üretilen komut satırı
parser'a **geri verilip** referans namespace'e birebir çözüldüğü doğrulandı. Gidiş-dönüş
sınaması geçmeseydi kuyruk dosyası hiç yazılmayacaktı. Üretim raporu:
`diagnostics/replicate_queue_build.md` (hangi anahtarın varsayılana düştüğü dahil).

**Ölçüt — yeni değil, ithal.** G3.1'de resmîleşen 2×-kontrol-sd ölçütünün aynısı,
`diagnostics/criterion_applied.py`'den **ithal edilerek** uygulanacak (yeniden yazılmayacak):
n=3 tohumun tamamı aynı işarette **VE** |ortalama eşleştirilmiş fark| ≥ 2 × o kolun **kendi**
`cw=none` kontrolünün aynı metrikteki tohum sd'si. Birincil kontrol noktası @swa; best ve last
duyarlılık olarak raporlanır. İki eksen ayrı ayrı: ΔECE ve Δdoğruluk.

**Tahminler (sayı görülmeden):**
1. **Doğruluk kolu — hiçbir hücre ölçütü karşılamayacak.** D1'in kapanışı bu koluna dayanıyor
   ve *mükemmel* sinyal bile üç öğretmenin hiçbirinde doğruluk kazandırmadı (P2/P5); gerçek
   sinyalin kazandırması bu yüzden beklenmiyor.
2. **vae9182 × `mean_logvar` — kalibrasyon zararı ÇÖZÜNMEYECEK.** Oracle kolunda kurulan
   +0.0056'lık zararın burada tekrarlanması beklenmiyor, çünkü `mean_logvar`'ın vae9182'deki
   ölçülmüş AUROC'u 0.46 — tesadüften kötü. Zarar sinyal kalitesine bağlıysa bu hücrede
   görünmemeli.
3. **stage1/primary × `target_logvar` — asıl sınav bu.** `target_logvar` primary'de 0.84,
   stage1'de 0.70 AUROC ile sınanan en iyi gerçek sinyal. Tahmin: **yine de ölçütü
   karşılamayacak** — yani mekanizmanın başarısızlığı sinyal kalitesinden bağımsız.
   **Yanlışlayıcı:** bu iki hücreden biri 3/3 işaret + 2× bar ile geçerse, "sinyal kalitesinden
   bağımsız" cümlesi düşer ve D1'in kapanış gerekçesi daralır.

**Sonucun cümleye ne yapacağı — şimdiden yazılı:**
- Bir hücre ölçütü **zarar** yönünde karşılarsa → özet cümlesi ayakta kalır ve o hücre için
  ilk kez gerçek bir n=3 dayanağı kazanır.
- Bir hücre ölçütü **fayda** yönünde karşılarsa → *"beş mekanizma başarısız"* o hücre için
  **yanlışlanmış** olur ve cümle yeniden yazılır.
- **Hiçbiri karşılamazsa** → cümle *"başarısız"*tan **"n=3'te kurulamadı"**a çevrilir.
  **ÇÖZÜNMEDİ ≠ etkisiz** — bar tek bir kolun tohum gürültüsünün iki katı; altında kalan bir
  etki *ölçülmemiştir*, *yok gösterilmemiştir*. Bu ayrım P5'te de yazılıydı ve burada da
  aynen korunuyor.

**Kapsam sınırı.** Yalnız RAF-DB, yalnız `gate` mekanizması. Diğer dört mekanizmanın tohum
durumu bu turda değişmiyor; özet cümlesi onlar için ayrıca denetlenmeli.

| alan | değer |
|---|---|
| **beyan donduruldu** | 2026-08-06 12:04:41 (bu blok + kuyruk dosyası, koşulardan önce) |
| **kuyruk** | `rafdb_a12_realsignal_gate_queue.ps1` (üretilmiş, elle yazılmamış) |
| **koşu** | 10 × 400 epoch, ölçülen 2.214 sa/koşu → **~22 sa**, G0 bittikten sonra |
| **sonuçtan önce mi** | ✅ evet — ölçüt, üç tahmin ve üç cümle-sonucu tek sayı görülmeden yazıldı |
| **sonuç** | *(8 Ağu 2026 hesaplandı; `diagnostics/a12_realsignal_gate/a12_verdict.{md,json}`)* **HİÇBİR HÜCRE ÖLÇÜTÜ KARŞILAMADI** — 5 hücre × 2 eksen = 10 hükmün onu da ÇÖZÜNMEDİ. Üç tahminin üçü de tuttu; cümle *"başarısız"*tan **"n=3'te kurulamadı"**a çevrilir. |

**Sonucun ayrıntısı — ve tahmin 3'ün kıl payı tutması.**

@swa, 10 koşu, donmuş paydalar altı ölçümde de birebir yeniden ölçüldü (stage1 0.00211 /
0.0996, primary 0.00333 / 0.3943, vae9182 0.00270 / 0.2070).

| hücre | ΔECE ort | işaret | oran | Δdoğruluk ort | işaret | oran |
|---|---|---|---|---|---|---|
| stage1 × `mean_logvar` | −0.00117 | `+--` | 0.55× | −0.098 pp | `---` | 0.98× |
| stage1 × `target_logvar` | **−0.00415** | **`---`** | **1.965×** | +0.250 pp | `++-` | **2.509×** |
| primary × `mean_logvar` | −0.00558 | `--+` | 1.67× | +0.196 pp | `++-` | 0.50× |
| primary × `target_logvar` | −0.00078 | `+--` | 0.24× | −0.087 pp | `-+-` | 0.22× |
| vae9182 × `mean_logvar` | +0.00148 | `+--` | 0.55× | −0.272 pp | `-++` | 1.31× |

**İki hücre ölçütün iki koşulundan tam birini sağladı, her biri diğerinde düştü** — ve bunu
yumuşatmadan yazmak gerekiyor, çünkü beyandaki yanlışlayıcı buraya bakıyordu:

* `stage1 × target_logvar`, ΔECE: **3/3 tohumda aynı işaret** (`---`) ve oran **1.965×**.
  Eşik 2.0. |ortalama| = 0.00415, 2×bar = 0.00422 — **barın %1.74'ü kadar eksik.** İşaret
  negatif, yani yön **kalibrasyon FAYDASI**. Geçseydi beyandaki yanlışlayıcı tetiklenir ve
  *"başarısızlık sinyal kalitesinden bağımsız"* cümlesi düşerdi. Geçmedi, ama kıl payı
  geçmedi ve metinde de böyle durmalı: bu hücre *"etkisiz"* diye anılamaz.
* `stage1 × target_logvar`, Δdoğruluk: oran **2.509×** ile barın üstünde, ama işaretler
  `++-` — üç tohum aynı yönde değil. Ölçütün işaret koşulu düşürüyor.

**ÇÖZÜNMEDİ ≠ etkisiz** ayrımı bu blokta yalnız bir ihtiyat cümlesi değil, ölçülmüş bir
durum: en güçlü gerçek sinyal (`target_logvar`, stage1'de AUROC 0.70) barın %98'ine ulaştı.

**Aileye etkisi.** Beş hücre G3.2 ailesine katıldı: **12 → 17 hücre**, aile-bazlı FPR
**0.3892 → 0.4540**, gözlenen k medyanı 1.7487 → 1.6956, hücre-başı FPR 0.0402 → 0.0350.
Makalede yazılı 0.389 bu turda **0.454** olur.

---

### A13 · 2.248 M scratch doz-yanıtı — 76× kaldıracın başlatma uyuşmazlığı (6 Ağu 2026)

**Neden.** Panel R1-W7: 76×'lik kaldıraç oranında **kapasite kolu scratch, sıcaklık kolu
ön-eğitimli**. Aynı uyuşmazlık B4'ün eğim karşılaştırmasında da var ve orada koşulardan önce
yazılmıştı: `b_w050` scratch, `b_2248` ön-eğitimli — iki eğim kapasitede *ve* başlatmada
farklı. B4 bunu confound olarak ilan etmiş ve ayrıştırmanın 2.248 M'de scratch bir doz-yanıtı
gerektirdiğini (4 koşu) yazmıştı. Bu blok tam o dört koşu.

**Ne koşulacak.** Scratch 2.248 M öğrenci (`--no-student-pretrained`, `width_mult 1.0`),
T ∈ {1.7, 2.2} × tohum {42, 1} = **4 koşu**. T=1.0 noktası **zaten var** (`w100ns`, n=3) ve
yeniden koşulmayacak. Sıcaklıklar ve tohumlar `w050` kolunun tasarımıyla **aynı** seçildi, ki
iki kapasite aynı destek üzerinde karşılaştırılabilsin.

**Analiz planı — B4'ün planı, harfiyen, ithal edilerek.** Eğim aynı üç sıcaklık {1.0, 1.7,
2.2} üzerinde fit edilir (5-noktalı fit'e karşı 3-noktalı fit koymak kapasiteyi fit desteğiyle
karıştırırdı — B4'ün 1. şartı). Belirsizlik yine **en-kötü-durum tohum-gürültüsü zarfı**,
ve yine **güven aralığı DEĞİL** diye etiketlenir (2. şart): iki hücre n=2, tek serbestlik
derecesi, eğime hata çubuğu uydurulmaz. Hücre başına tohum tekilliği kapısı (`RuntimeError`)
yürürlükte kalır. Fit kodu `capacity_law_check.py`'den ithal edilir, kopyalanmaz.

**Üç karşılaştırma, üçü de raporlanacak:**
| karşılaştırma | sabit | değişen | ne izole eder |
|---|---|---|---|
| `b_scratch2248` vs `b_pretrained2248` | kapasite | başlatma | **başlatma etkisi** |
| `b_scratch2248` vs `b_scratch0712` | başlatma | kapasite | **kapasite etkisi** — T10a'nın iddia etmek isteyip edemediği |
| `b_pretrained2248` vs `b_scratch0712` | — | ikisi birden | B4'ün mevcut, confound'lu karşılaştırması |

**Tahmin (sayı görülmeden).** Başlatma karşılaştırması **zarfın dışına çıkmayacak** — yani
eğim, öğrencinin başlatmasının değil öğretmenin kalibrasyonunun yönettiği bir büyüklük.
**Yanlışlayıcı:** `|b_scratch2248 − b_pretrained2248|` iki zarfın toplamını aşarsa, yasanın
eğimi başlatmaya duyarlıdır ve §5'teki "yasa öğrenci artefaktı değil" savunması **başlatma
ekseninde de** ayrıca savunulmak zorunda kalır.

**T10a'ya ne olacağı — şimdiden yazılı.** Kapasite karşılaştırması zarfın dışına çıkarsa
T10a kalemi (ii) **SONUÇSUZ**'dan çıkar ve eğim farkı kapasiteye atfedilir. Çıkmazsa (ii)
sonuçsuz kalır — ama artık *confound yüzünden* değil, *gürültü yüzünden*; bu, aynı hükmün
daha dürüst bir gerekçesidir ve öyle yazılır. **"Eğim kapasiteyle değişmiyor" cümlesi hiçbir
sonuçta yazılmayacak** — zarf bir eşdeğerlik testi değildir.

**76× kaldıraca ne olacağı.** G4.2'nin estimand'ı, iki kol da scratch olacak şekilde
**başlatma-eşleştirilmiş** hâliyle yeniden hesaplanacak ve oran **hangi yöne giderse gitsin**
raporlanacak. Mevcut confound'lu oran duyarlılık olarak kalır, silinmez.

| alan | değer |
|---|---|
| **beyan donduruldu** | 2026-08-06 12:04:41 (bu blok + kuyruk dosyası, koşulardan önce) |
| **kuyruk** | `rafdb_a13_scratch_dose_queue.ps1` (üretilmiş, elle yazılmamış) |
| **koşu** | 4 × 400 epoch, ölçülen 2.214 sa/koşu → **~9 sa**, A12'den sonra |
| **sonuçtan önce mi** | ✅ evet — analiz planı B4'ten devralındı, tahmin ve üç sonuç-cümlesi sayı görülmeden yazıldı |
| **sonuç** | *(8 Ağu 2026 hesaplandı; `diagnostics/a13_scratch_dose/a13_verdict.{md,json}`)* **BAŞLATMA TAHMİNİ YANLIŞLANDI — eğim başlatmaya duyarlı.** T10a (ii) sonuçsuz kalıyor, ama artık *confound* yüzünden değil *gürültü* yüzünden. |

**Sonucun ayrıntısı.** Üç eğim, aynı üç sıcaklıkta (T = 1.0, 1.7, 2.2), @swa:

| kol | eğim | zarf | R² |
|---|---|---|---|
| `scratch0712` (0.712 M, scratch) | 0.6547 | ±0.0585 | 0.99996 |
| `pretrained2248` (2.248 M, ön-eğitimli) | 0.7161 | ±0.0219 | 0.99997 |
| **`scratch2248`** (2.248 M, scratch — A13'ün ürettiği) | **0.6488** | **±0.0139** | 0.99882 |

| karşılaştırma | izole ettiği | Δeğim | birleşik zarf | çözülür mü |
|---|---|---|---|---|
| `scratch2248` vs `pretrained2248` | **BAŞLATMA** | **−0.0672** | 0.0358 | ✅ **EVET** |
| `scratch2248` vs `scratch0712` | KAPASİTE | −0.0059 | 0.0724 | hayır |
| `pretrained2248` vs `scratch0712` | ikisi birden (B4'ün confound'lu hâli) | +0.0614 | 0.0804 | hayır |

**Ayrışım, beklenenin tersini gösteriyor.** B4'ün confound'lu karşılaştırması (+0.0614) tek
başına **çözülmüyordu**. Ayrıştırılınca görülüyor ki başlatma bileşeni tek başına (0.0672)
**çözülüyor**, kapasite bileşeni ise sıfıra yakın (−0.0059). Yani B4'ün gördüğü farkın
neredeyse tamamı kapasiteden değil **başlatmadan** geliyor.

**Yanlışlayıcının sonucu — beyanda yazıldığı gibi uygulanır.** `|Δeğim|` iki zarfın toplamını
aştı, dolayısıyla §5'teki *"yasa öğrenci artefaktı değil"* savunması **başlatma ekseninde de
ayrıca savunulmak zorundadır**. Savunmanın dayanağı şu ölçüm: üç kolun üçünde de doz-yanıtı
R² > 0.998 ile duruyor ve eğimler 0.649–0.716 aralığında; başlatma **eğimin katsayısını**
oynatıyor, yasanın varlığını ya da işaretini değil.

**"Eğim kapasiteyle değişmiyor" cümlesi yazılmadı** — beyanda yasaklanmıştı, çünkü zarf bir
eşdeğerlik testi değildir. T10a (ii) sonuçsuz kalıyor; gerekçesi *confound*'dan *gürültü*ye
döndü, ki bu aynı hükmün daha dürüst hâlidir.

**76× kaldıraç, başlatma-eşleştirilmiş** (`paper_tables/g42_init_matched_lever.{md,json}`,
G4.2). Payda (kapasite açıklığı) iki sütunda da aynı; değişen yalnız sıcaklık kolunun
başlatması:

| ckpt | oran — yayımlanan (ön-eğitimli kol) | oran — **başlatma-eşleştirilmiş (scratch kol)** |
|---|---|---|
| @swa (birincil) | 76× | **69×** |
| @best | 79× | 75× |
| @last | 27× | 26× |

Oran **aşağı** gitti, ama yönü ve mertebesi korundu — sıcaklık ekseni kapasite ekseninden
hâlâ iki mertebe geniş. *"Yasa öğretmen tarafında yaşıyor"* cümlesi ayakta; sayısı
başlatma-eşleştirilmiş hâliyle yazılmalı. **Confound'lu oran silinmedi**, kendi sütununda
duruyor (beyanda öyle yazılmıştı).

---

## B. Ön-kaydı OLMAYANLAR — makalede "pre-registered" DENMEYECEK

### B8 · G0 — kontrol öğretmeni grid inceltmesi (2026-08-06) → **inceleme-cevabı, ön-beyanlı DEĞİL**

**Bu koşular ön-beyanlı değildir.** Round-2 hakem raporu (5 Ağu 2026) görülmüşken planlandılar
ve 6 Ağu'da Fatih'in onayıyla başlatıldılar. Makalede "pre-registered" denmeyecek; §4.5
envanterine girmezler.

**Neden koşuluyorlar.** Panel R1-W11: kontrol öğretmeninin (VAE9182) kendi optimumu
T\*_NLL = 0.983 / T\*_ECE = 1.057 aralığında, ama A1'in ön-beyanlı falsifikasyon testinin grid'i
{0.85, 1.00, 1.3406, 1.70, 2.20} — en yakın aralık **0.15**. Yani *"iyi kalibre öğretmen iç
optimum göstermez"* tahmini, **başarısız olabileceği ölçekte sınanamadı**. İki ek nokta
(T = 0.95 ve T = 1.10, 3'er tohum = 6 koşu) onu sınanabilir yapıyor.

**A1'in statüsü değişmiyor.** Orijinal ön-beyanlı test 0.15 grid çözünürlüğünde koşuldu ve
**tuttu**; bu iki nokta onu geçersiz kılmaz, çözünürlüğünü artırır. Çıktıda bu cümle birebir
yer alacak: *"the original pre-declared test was run at grid resolution 0.15 and held; these two
points were added afterwards, in response to review, to test at the scale of the teacher's own
optimum."*

**Tarif.** `rafdb_p1_vae9182_flatcontrol_queue.ps1` ile birebir aynı; yalnız
`--teacher-temperature-scale` ve `--seed` değişiyor. Aynılık koşu argümanlarından doğrulandı
(addan değil): epochs 400, batch 64, α 0.3, τ 6, LS 0.1, mixup 0.1, SWA@200, swa_lr 1e-4,
vich başlık, aynı öğretmen checkpoint'i — dokuz alanın dokuzu referans kolla eşleşti.

**Üç sonucun üçü de yayımlanabilir; hangisi çıkarsa o yazılır:**

| sonuç | nasıl yazılacak |
|---|---|
| 0.95 ve 1.10, T=1'den ayırt edilemez | tahmin, başarısız olabileceği ölçekte sınandı ve tuttu |
| 1.10'da gürültü içinde hafif iyileşme | kendi T\*'ına yakın sığ optimumla uyumlu, üç tohumda çözünmüyor |
| 1.10'da net iyileşme | kontrolün iç optimumu kendi T\*_ECE'sinde — yasayı çürütmez, o incelikte doğrular; çerçeve "düz kontrol"den "optimumu birimden 0.06 uzakta"ya döner |

| alan | değer |
|---|---|
| **artefakt** | `rafdb_g0_control_grid_queue.ps1` |
| **kapsam** | VAE9182 · RAF-DB · T ∈ {0.95, 1.10} × tohum {42, 1, 43} = **6 koşu**, ~14 sa |
| **ön-beyanlı mı** | ❌ **hayır** — hakem raporundan sonra planlandı, bilerek ve açıkça |
| **çıktı** | `paper_tables/control_grid_refinement.md` (beş noktalı tam seri 0.85/0.95/1.00/1.10/1.34) |

### B4 · P3 — kapasite × eğim (2026-07-29) → **tahmin yok, soru + analiz planı var**

`rafdb_p3_capacity_slope_queue.ps1` 2026-07-29 01:28:02'de donduruldu, koşusu P2'den sonra.
İçinde **bilinçli olarak tahmin yok**; donan şey soru ve **analiz planı**: hangi üç sıcaklıkta
fit edileceği, `b_w050`'nin `b_2248` ile **aynı üç sıcaklık üzerinde** karşılaştırılacağı
(5-noktalı fit'e karşı 3-noktalı fit kapasiteyi fit desteğiyle karıştırırdı), ve tek tohum
çiftiyle eğime hata çubuğu **uydurulmayacağı**. Ayrıca scratch/ön-eğitimli confound'u koşudan
önce yazılı: `b_w050` ile `b_2248` iki şeyde birden farklı, ayrıştırmak 2.248 M'de scratch bir
doz-yanıt gerektirir (4 koşu, başlatılmadı).

**Sonuç: P3 exploratory olarak raporlanacak.**

**Koşular bitti** (4/4, `exit 0`, 2026-07-30 08:58:50). Analiz planı harfiyen uygulandı —
`diagnostics/capacity_law_check.py` → `diagnostics/p5_efficiency/capacity_law_check.{json,md}`,
tablo hâli `RESULTS_TABLES.md` T10a.

| kapasite | init | sıcaklıklar | eğim b | R² | en büyük artık | tohum-gürültüsü zarfı |
|---|---|---|---|---|---|---|
| 2.248 M | ön-eğitimli | 1.0 / 1.7 / 2.2 | **0.716** | 0.99997 | 0.00057 | ±0.022 |
| 0.712 M | scratch | 1.0 / 1.7 / 2.2 | **0.655** | 0.99996 | 0.00056 | ±0.058 |

Eğim farkı **−0.061**, iki zarfın toplamı **±0.080** → **fark çözünmüyor.**

Donmuş planın üç şartı da tutuldu:

1. **`b_2248` aynı üç sıcaklıkta yeniden fit edildi** (5-noktalı fit b=0.714 olarak yalnız kayda
   geçti, karşılaştırmada kullanılmadı) — 5-noktaya karşı 3-nokta koymak kapasiteyi fit
   desteğiyle karıştırırdı.
2. **Eğime güven aralığı uydurulmadı.** w050'nin T=1.7 ve T=2.2 hücreleri n=2, yani tek
   serbestlik derecesi. Onun yerine her hücre ortalamasını ölçülmüş bir tohum sd'si kadar eğimi
   en çok oynatan yöne itmekle **en-kötü-durum zarfı** hesaplandı; artefaktta ve tabloda
   "güven aralığı değil" diye etiketli.
3. **Scratch/ön-eğitimli confound'u açıkta.** `b_w050` scratch, `b_2248` ön-eğitimli — iki eğim
   kapasitede *ve* başlatmada farklı. Ayrıştırmak 2.248 M'de scratch bir doz-yanıt gerektirir
   (4 koşu, başlatılmadı).

**Ne söylenebilir:** kalibrasyon aktarım yasası 3.16× daha küçük bir öğrencide de geçerli —
monoton, ve her iki fit'in en büyük artığı (0.00057 / 0.00056) kendi hücrelerinin tohum
sd'lerinin **3.5–15.3 katı altında** (sd aralığı 0.0020–0.0087), yani doğrusallık üç noktaya
oturmaktan değil ilişkinin kendisinden geliyor. Yasa **büyük-öğrenci artefaktı değil.**
*(Not: burada önce "bir büyüklük mertebesi küçük" yazılmıştı; en küçük hücre sd'sine karşı oran
3.5× olduğu için o niceleyici alt sınırda fazla iddialıydı ve ölçülmüş aralıkla değiştirildi.)*

**Ne söylenemez:** "eğim kapasiteyle değişmiyor." Gürültü zarfı −0.061'lik farkı çözmüyor; test
yapılmadı, **sonuçsuz kaldı**. Bir de zaten iki değişken birden hareket ediyor (bkz. 3).

> **P3 bir yan hasarı da açığa çıkardı (kod, kalıcı onarım).** P3'ün koşuları
> `RAFDB_vae9182_frontier_w050_tempscale_T{170,220}_*` adını taşıyor ve ledger onları
> `t_scale ≠ 1.0` olduğu için `dose_response` ailesine koyuyor. `paper_tables.py`'nin T10 hücre
> filtresi yalnız `"frontier" in name` diye baktığından bu dört koşu **`scratch w050` hücresine
> karıştı**: hücre n=3'ten n=7'ye, ECE'si 0.0365'ten **0.1079 ± 0.0737**'ye çıktı ve T10'un
> "kapasite ekseni" açıklığı, karşılaştırılması gereken **sıcaklık eksenini kendi içine yuttu** —
> oran 76×'ten **3×'e** düştü. Hiçbir hata mesajı çıkmadı. Filtre `t_scale == 1.0` şartıyla
> düzeltildi ve hücre başına **tohum tekilliği** kapısı eklendi (`RuntimeError`), çünkü bir
> kapasite hücresinde aynı tohumdan iki koşu bulunması tanım gereği ikinci bir değişkenin
> hareket ettiği anlamına gelir.

### B1 · VICH head izolasyonu → **YOK**

`rafdb_vich_isolation_queue.ps1` (2026-07-22 16:41, koşular 2026-07-24 10:48) **135 satır** ve
içinde tek bir tahmin/beklenti cümlesi yok (`predict|expect|null|hypoth|pre-reg` taraması boş
döndü). `diagnostics/vich_isolation_verdict.py` docstring'i "pre-registered null expectation"
diyor ama o betiğin mtime'ı bugüne ait (bu oturumda düzenlendi) — kanıt değeri sıfır.

**Sonuç: VICH izolasyonu keşifsel (exploratory) olarak raporlanacak.** Sonucun kendisi sağlam
(3/3 tohumda aynı işaret, ΔECE +0.0062 ± 0.0015, VICH linear head'in ECE'sinin %18.6'sını
kaldırıyor) — sadece "önceden söylemiştik" denemez.

### B2 · Gate oracle üst sınırı → **kısmi (sayısal tahmin yok)**

`run_rafdb_gate_signal_followup_queue.ps1` (2026-07-20 01:22, koşu 2026-07-20 08:19) tasarım
gerekçesini donduruyor ("the oracle isolates 'is gating itself useful'... upper-bound") ama
**sayısal bir bar veya yanlışlama koşulu içermiyor**. Tasarım ön-kayıtlı, tahmin değil.
Makalede "pre-registered upper-bound *design*" denebilir, "pre-registered prediction" denemez.

### B3 · Genişlik frontier'ı → **tahmin yok, soru var**

`rafdb_width_frontier_queue.ps1` (2026-07-28 00:40, ilk koşu 05:50) sonuçtan önce donduruldu ✅
ama içeriği bir tahmin değil, bir **soru**: "is the calibration law student-capacity dependent,
or does a 0.7 M student inherit teacher calibration the same way a 2.2 M one does?"
Tahmin yazılmadığı için sonuç ne çıkarsa çıksın "öngördük" denemez. (Karşılığında donan şey daha
değerli: confound'un kendisi — ImageNet ağırlıklarının yalnız width 1.0'da yüklendiği ve bu
yüzden 9 koşu gerektiği, koşular başlamadan belgelendi.)

---

## C. Özet tablo

| # | ön-kayıt | artefakt | donduruldu | ilk koşu | önce mi | sonuç |
|---|---|---|---|---|---|---|
| A1 | B-007 düz-kontrol | `rafdb_p1_vae9182_flatcontrol_queue.ps1` | 24 Tem 18:05:30 | 24 Tem 18:05:50 | ✅ | doğrulandı |
| A2 | B-010 kill-switch | `rafdb_p3_then_miscal_chain.ps1` | 25 Tem 14:35:43 | 25 Tem 23:19:09 | ✅ | NULL (tetiklendi) |
| A3 | B-015 üç tahmin | `ferplus_dose_response_queue.ps1` | 26 Tem 13:27:26 | 26 Tem 13:27:45 | ✅ | CONFIRMED 3/3 |
| A4 | B-017 P1+P2 | `ferplus_tjsd_queue.ps1` | 27 Tem 12:56:29 | 27 Tem 12:56:47 | ✅ | P1 ✗ · P2 ✓ |
| **A7** | **P1 logit_std tohumları** | `rafdb_p1_logit_std_seeds_queue.ps1` | **29 Tem 01:23:40** | **29 Tem 01:24:08** | ✅ **+28 sn** | **CONFIRMED 3/3** |
| **A8** | **P2 gate:oracle + kontrol** | `rafdb_p2_gate_oracle_seeds_queue.ps1` | **29 Tem 01:26:59** | **29 Tem 14:24:13** | ✅ | **P2.1 ✗ · P2.2 ✗ · P2.3 ✓** |
| **B4** | **P3 kapasite × eğim** | `rafdb_p3_capacity_slope_queue.ps1` | **29 Tem 01:28:02** | **30 Tem 01:56:49** | ⚠️ soru, tahmin yok | **keşifsel — eğim farkı çözünmedi** |
| A5 | B-016 iki bant | `diagnostics/bridge_teacher_check.py` | 20 Tem 13:41:12 | 21 Tem 13:36:38 | ✅ | reçete bandı |
| A6 | B-001 Stage1 U'su | `rafdb_p1_temperature_doseresponse_queue.ps1` | 23 Tem 10:34 | 23 Tem 10:35 | ⚠️ kısmen | doğrulandı |
| B1 | VICH izolasyonu | — | — | — | ❌ **yok** | keşifsel |
| B2 | Gate oracle | `run_rafdb_gate_signal_followup_queue.ps1` | 20 Tem 01:22 | 20 Tem 08:19 | ⚠️ tasarım | keşifsel |
| B3 | Genişlik frontier | `rafdb_width_frontier_queue.ps1` | 28 Tem 00:40 | 28 Tem 05:50 | ⚠️ soru | devam ediyor |

**Makaleye giren "pre-registered" ifadesi yalnız A1-A5, A7 ve A8 için kullanılacak. A6 "partially
pre-registered" olarak nitelenecek. B1-B4 keşifsel diye anılacak.**

> **A8 yanlışlanmış bir ön-kayıt, ve öyle kalacak.** İki tahmini düştü; barları sonradan
> gevşetmek yerine hüküm olduğu gibi yazıldı, çünkü ön-kaydın tek değeri tam olarak bu:
> tahmin tutmadığında da aynı kuralla ölçülmesi. Makalede A8, "pre-registered ve yanlışlandı"
> diye anılacak — çerçeveleme de sonuca göre düzeltildi (bkz. A8'deki *"kapalı çünkü zarar
> veriyor"* ayrımı), sonuç çerçeveye göre değil.
