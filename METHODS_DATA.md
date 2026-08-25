# METHODS / EXPERIMENTS — kaynak veri ve tam spesifikasyon

Yazım için hazırlanmış referans. **Her satır kaynaktan doğrulanmıştır**; iddia edilen her sayının
yanında ya `file:line` ya da üreten artefaktın yolu vardır. Bulgu/karar kaydı ayrı dosyada:
[BULGULAR.md](BULGULAR.md). Koşu tablosu: [runs.csv](runs.csv).

---

# 1. Bölünme ve seçim protokolü — ⚠️ KRİTİK BULGU

## 1.1 Bölünme: iki partisyon, üçüncü YOK

Tek kaynak `data/rafdb_aligned/metadata_rafdb_poster_var.csv` (15339 satır; kolonlar
`path,label,fold`; UTF-8 BOM'lu). Bölme tamamen `fold` kolonundan:

| fold | n | kullanım | kod |
|---|---|---|---|
| 2 | **12271** | train | `--train-folds 2` ([train_rafdb_kd.py:1049](train_rafdb_kd.py#L1049)) |
| 3 | **3068** | val **ve** rapor | `--val-folds 3` ([train_rafdb_kd.py:1050](train_rafdb_kd.py#L1050)) |
| | **15339** | = dataset SHA-256'nın kapsamı | |

Filtreleme: `df = df[df["fold"].isin(folds)]` ([train_rafdb_kd.py:67-73](train_rafdb_kd.py#L67-L73)).
Loader'lar: [train_rafdb_kd.py:228-232](train_rafdb_kd.py#L228-L232).

**Bu RESMÎ RAF-DB bölünmesidir.** Doğrulama: fold-3'ün sınıf-başına sayıları
**329 / 74 / 160 / 1185 / 478 / 162 / 680**, yayımlanmış RAF-DB temel-duygu test kümesinin
birebir dağılımıdır. Buradan etiket eşlemesi de kesinleşiyor:

| label | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| sınıf | Surprise | Fear | Disgust | Happiness | Sadness | Anger | Neutral |
| fold-3 n | 329 | 74 | 160 | 1185 | 478 | 162 | 680 |
| fold-2 n | 1290 | 281 | 717 | 4772 | 1982 | 705 | 2524 |

**Sonuç: ayrı bir doğrulama kümesi yok.** "fold-3 val" dediğimiz şey RAF-DB'nin **resmî test
kümesidir**.

## 1.2 Seçim: `best_epoch` doğrulukla ve AYNI küme üzerinde seçiliyor

```
train_rafdb_kd.py:895-900   if val_acc > best_acc:  best_acc = val_acc; best_epoch = epoch
                            -> best_student.pth / best_checkpoint.pth kaydedilir
train_rafdb_kd.py:960-977   best_checkpoint.pth yeniden yüklenir, AYNI val_loader ile
                            evaluate_detailed -> metrics_best.json
```

- **Seçim ölçütü:** top-1 doğruluk (`val_acc`), başka hiçbir şey (ECE seçime girmiyor).
- **Seçim kümesi:** `val_loader` = fold 3 = resmî test kümesi.
- **Raporlama kümesi:** aynı `val_loader`.

> **⚠️ Seçim ve raporlama aynı görüntülerde. Dolayısıyla bu kampanyada şimdiye kadar raporlanmış
> her "best" doğruluk ve her "best" ECE, epoch seçimi nedeniyle iyimser yönde yanlıdır.**
> Yanlılık doğrudan **doğruluk** üzerinde (seçim ölçütü o), ECE ise kontrolsüz biçimde ona
> biniyor. Kalibrasyon iddiası için "doğrulukla seçilmiş epoch'ta ECE" **yeterli değildir** —
> bu tespit sizin uyarınızla yapıldı ve haklıdır.

## 1.3 Seçimden BAĞIMSIZ iki checkpoint zaten mevcut (yeniden eğitim gerekmiyor)

| checkpoint | dosya | kural | seçimden bağımsız? |
|---|---|---|---|
| best | `best_checkpoint.pth` | argmax val_acc | ✗ **kümeye bakıyor** |
| last | `last_checkpoint.pth` | son epoch (=`--epochs`), sabit kural | ✓ |
| swa | `swa_student.pth` | `[swa_start, epochs]` üzerinden SWA ortalaması, sabit kural | ✓ |

Kaynak: last [train_rafdb_kd.py:877-878](train_rafdb_kd.py#L877-L878) (her epoch yazılır),
SWA [train_rafdb_kd.py:902-908](train_rafdb_kd.py#L902-L908) (`update_bn` train_loader üzerinde
çalıştırıldıktan sonra kaydedilir). SWA `AveragedModel`'den geldiği için state_dict'i `module.`
önekli ve fazladan `n_averaged` buffer'ı taşır.

Bu üç checkpoint'in **tamamı** için seçimden bağımsız metrikler
[`diagnostics/selection_audit_table.py`](diagnostics/selection_audit_table.py) ile ölçülüyor
(çıktı: `diagnostics/selection_audit/selection_audit.csv`). **Makalede kalibrasyon iddiası
SWA ve/veya last üzerinden verilmelidir**; best sayıları ancak "accuracy-selected" etiketiyle
ve seçim-yanlılığı açıkça belirtilerek raporlanabilir.

---

# 2. Metrik tanımları (Methods'a birebir girecek)

Hepsi aynı fold-3 görüntülerinde (n=3068), `eval()` modunda, VICH örneklemesi kapalı, T=1'de.

| Metrik | Tanım | Uygulama |
|---|---|---|
| **ECE** | **15 kutu, EŞİT-GENİŞLİK** [0,1] aralığında (eşit-kütle **değil**); kutulama **top-1 softmax güveni** `max_k p_k` üzerinden; terim `\|acc(kutu) − ortalama_güven(kutu)\|`, ağırlık `\|kutu\|/N`; ilk kutu solda kapalı. Guo et al. (2017) ECE'si. | `diagnostics/teacher_temperature_scaling_fit.py::confidence_ece` |
| **NLL** | ortalama negatif log-olabilirlik, `F.cross_entropy(logits, labels)` | selection_audit_table.py |
| **Brier** | çok-sınıflı: `mean_i Σ_k (p_ik − y_ik)²`, y one-hot; aralık [0,2] | selection_audit_table.py |
| **macro-F1** | 7 sınıfın ağırlıksız F1 ortalaması | selection_audit_table.py |

### 2.1 ECE'nin uygulama ayrıntıları (kaynaktan, birebir)

[`diagnostics/teacher_temperature_scaling_fit.py:73-92`](diagnostics/teacher_temperature_scaling_fit.py#L73-L92):

```python
bins = torch.linspace(0.0, 1.0, n_bins + 1)          # 15 EŞİT-GENİŞLİK kutu
conf, preds = probs.max(dim=1)                        # TOP-1 güven
mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
if cnt == 0: continue                                 # BOŞ kutu atlanır
ece += (cnt / n) * abs(bin_acc - bin_conf)
```

- 15 kutu, **eşit-genişlik** [0,1] — eşit-kütle **değil**
- kutulama **top-1 softmax güveni** `max_k p_k` üzerinden
- **boş kutular atlanır**; ağırlık `cnt/n` olduğundan katkıları zaten sıfır, yani atlama sonucu
  değiştirmez (raporlanabilir bir tercih, gizli bir sapma değil)
- ilk kutu **solda kapalı** (`conf ≥ 0`), diğerleri `(lo, hi]`

**Öğretmen ECE'si** aynı `confidence_ece` ile, ama sıcaklık argümanıyla: ızgaradaki T noktasında
öğretmenin dağılımı `softmax(z/T)` olduğu için öğretmen ECE'si = `confidence_ece(z, y, T)` —
tamamen analitik, önbelleklenmiş logitlerden ([`diagnostics/teacher_ece_grid.py`](diagnostics/teacher_ece_grid.py)).
τ_KD=6 her koşuda sabit olduğu ve koşular arası karşılaştırmalarda sadeleştiği için öğretmen ECE'si
T'de ölçülür, T·τ_KD'de değil.

### 2.2 FERPlus'a özgü ekler

- Sınıf sayısı **8** (macro-F1 8 sınıf üzerinden), val n = **3153**.
- **JSD**: Jensen-Shannon ıraksaması, **nat** biriminde, örnek başına;
  `JSD(p‖q) = ½KL(p‖m) + ½KL(q‖m)`, `m = (p+q)/2`, sınırlı [0, ln 2].
  `p` = 10-oylayıcı dağılımı (**her satır kendi oy toplamına** bölünerek normalize),
  `q` = model softmax'ı. Öğretmen için
  [`diagnostics/ferplus_human_vote_jsd.py`](diagnostics/ferplus_human_vote_jsd.py),
  öğrenci için [`diagnostics/ferplus_student_jsd.py`](diagnostics/ferplus_student_jsd.py)
  (öğrenci softmax'ı **T=1**'de, yani konuşlandırılan çıktısı).
- Öğrenci ECE/NLL/Brier/macro-F1'i
  [`diagnostics/ferplus_selection_audit.py`](diagnostics/ferplus_selection_audit.py) üretir;
  RAF-DB'nin 290 ölçümüyle **birebir aynı** metrik tanımları kullanılır.

> ⚠️ **`kd_common.py` hiçbir kalibrasyon metriği yazmaz.**
> `write_metrics_json` ([kd_common.py:855-877](kd_common.py#L855-L877)) yalnızca accuracy /
> precision / recall / macro_f1 / weighted_f1 / params / flops / size kaydeder;
> `evaluate_detailed` ([:652-680](kd_common.py#L652-L680)) olasılıkları hiç biriktirmediği için
> oradan olasılık-tabanlı metrik **türetilemez**. Dosyanın tamamında `ece`/`nll`/`brier` yok.
> Bu yüzden tüm ECE/NLL/Brier değerleri kaydedilmiş checkpoint'lerden **post-hoc** ölçülmüştür
> (best/last/swa üçü de her koşuda diskte). Reprodüksiyon bölümünde böyle yazılmalı.

### 2.3 Standart sapma konvansiyonu — `KAPANDI` (28 Tem)

**Bağlayıcı konvansiyon:** her hata çubuğu, metindeki her "± x" ve her JSON artefaktındaki her
`*_sd` alanı **örneklem standart sapmasıdır (n−1, Bessel düzeltmeli)**, tohumlar üzerinden.
n her zaman birlikte raporlanır. n=1 hücreleri "± 0.0000" göstermez; sahte bir sıfır hata çubuğu
"mükemmel tekrarlanabilir" diye okunur, oysa tam tersini ifade eder.

Tek tanım: [`diagnostics/stats_convention.py`](diagnostics/stats_convention.py) (`sample_sd`,
`SD_CONVENTION`). Betiklerin hiçbirinde artık `statistics.pstdev` çağrısı yok.

**Neden önemliydi.** Popülasyon sd'si (n bölen) küçük n'de örneklem sd'sini sistematik olarak
küçük gösterir — **n=2'de %29, n=3'te %18, n=5'te %11** — ve yönü daima iyimserdir: her etkiyi
gürültüden olduğundan daha ayrık gösterir.

**Dönüştürülen betikler (8):** `vich_isolation_verdict.py`, `adaptive_t_headroom_table.py`,
`p1_two_teacher_overlay.py`, `selection_robustness.py`, `selection_gain_estimator.py`,
`seed_variance_ece.py`, `selection_audit_table.py`, `ferplus_selection_audit.py`.
Zaten n−1 kullananlar: `b015_verdict.py`, `two_dataset_overlay.py`, `ferplus_student_jsd.py`.

**Betiği düzeltmek yetmedi — türev artefaktlar da yeniden üretilmek zorundaydı.**
`p4_teacher_selection.json` ve `p5_efficiency.json` kendileri sd hesaplamıyor; `seed_variance_
table.json`'dan **kopyalıyorlar**. Üreticileri düzeltildikten sonra bu iki dosya yeniden
üretilmediği için 25 Tem tarihli pstdev değerlerini taşımaya devam ettiler ve T6/T9'un
"öğrenci acc" sütununu **yanlış** (dar) hata çubuğuyla besliyorlardı:

| tablo | hücre | yayınlanan (pstdev) | düzeltilmiş (n−1) |
|---|---|---|---|
| T6 | stage1 öğrenci acc | 89.74 ± 0.06 | 89.74 ± **0.07** |
| T6 | primary öğrenci acc | 89.57 ± 0.07 | 89.57 ± **0.09** |
| T6 | vae9182 öğrenci acc | 90.28 ± 0.16 | 90.28 ± **0.19** |
| T9 | öğrenci acc | 90.28 ± 0.16 | 90.28 ± **0.19** |

Ortalamalar değişmedi; yalnız σ büyüdü (1.2247×, n=3). **Ders:** "üreticiyi düzelttim"
ile "artefakt düzeldi" aynı şey değil. Bu yüzden artık makine kontrolü var — sd raporlayan
her JSON `sd_convention` damgası taşımak zorunda; damgasız dosya = yeniden üretilmemiş dosya.
Şu an **10/11 damgalı**; damgasız tek dosya, üreticisi repoda olmayan süperseded
`p1_dose_response.json` (aşağıda işaretli, hiçbir tabloyu beslemiyor).

**Yön değişikliği: YOK.** Ortalamalar birebir aynı kaldı, sd'ler tam olarak beklenen çarpanla
büyüdü (n=3'te 1.2247×, n=2'de 1.4142×). Kampanyanın taşıyıcı karar ölçütlerinin hiçbiri σ'ya
dayanmadığı için hiçbir karar değişmedi:

| karar | ölçüt | σ'ya bağlı mı | sonuç |
|---|---|---|---|
| B-007 / B-015 | Spearman + grup ayrışması | hayır | değişmedi |
| B-010 kill-switch | işaret tutarlılığı + mutlak ön-kayıtlı bar | hayır | NULL (aynı) |
| Mekanizma ablasyonları | 3 tohumda işaret tutarlılığı | hayır | değişmedi |
| VICH izolasyonu | 3/3 işaret | hayır | değişmedi (+0.0062 ± **0.0015**, eskiden ±0.0012) |

**Tek σ-bağımlı yer** `seed_variance_ece.py`'deki "clears / within-noise" etiketidir
(`abs(d_acc) > baseline_acc_sd`). n=3'te bar **%22.5 yükseldi**, yani "clears" kazanmak
zorlaştı — doğru yön. Bu yüzden altı hücrenin **tamamı** iki konvansiyonla yeniden okundu
(varsayılmadı):

| hücre | d_acc (pp) | eski marj | yeni marj | etiket |
|---|---|---|---|---|
| T-C g2g_kl | +0.022 | 0.14× | 0.11× | within-noise → within-noise |
| T-C adaptive_t | +0.043 | 0.28× | 0.23× | within-noise → within-noise |
| T-C combined_500e | +0.293 | 1.88× | 1.54× | clears → clears |
| T-B g2g_kl | −0.261 | 3.70× | 3.02× | clears → clears |
| **T-A g2g_kl** | **+0.087** | 1.57× | **1.28×** | clears → clears *(sınıra en yakın)* |
| T-A adaptive_t | +0.217 | 3.92× | 3.20× | clears → clears |

Karşılaştırma **aynı veri üzerinde iki sd tanımıyla** yapıldı (n=3, tüm hücreler tam);
"eski" sütunu o veriye popülasyon sd'si uygulanmış hâlidir, tarihsel bir kopya değil.

**Etiket değişimi: 0/6.** Tek dikkat çeken hücre T-A g2g_kl: marjı 1.28×'e indi, yani
+0.087 pp'lik bir farkı "gürültüden ayrık" saymak artık zar zor geçiyor. Makalede bu hücre
için "clears" kelimesi kullanılmayacak; ham fark ve sd birlikte verilecek.

---

# 2A. Damıtma kaybı — tam tanım (denklemin doğrulanmış hâli)

[kd_common.py:440](kd_common.py#L440), aynen:

```python
loss = self.alpha * hard_loss + (1.0 - self.alpha) * soft_loss + aux_beta * aux_kl
```

**`alpha` CE terimine uygulanır.** α = 0.3 → **0.3·CE + 0.7·KD**. Yani makale denklemi:

$$\mathcal{L} = \alpha\,\mathcal{L}_{\mathrm{CE}} + (1-\alpha)\,\tau^2\,\mathrm{KL}\big(p_T^{(\tau)} \,\|\, p_S^{(\tau)}\big) + \beta_{\mathrm{VICH}}\,\mathcal{L}_{\mathrm{KL}}^{\mathrm{aux}}$$

**τ² çarpanı gerçekten uygulanıyor** — [kd_common.py:384-388](kd_common.py#L384-L388):

```python
per_sample_kd = F.kl_div(soft_student, soft_teacher, reduction="none").sum(dim=1)
t_squared = effective_T ** 2
soft_loss = per_sample_kd.mean() * t_squared
```

Methods'a girmesi gereken dört ince ayrıntı:

1. **Çarpan `effective_T²`**, `self.temperature²` değil (:384). Sabit rejimde ikisi aynıdır
   (τ²=36), ama `adaptive_t` açıkken çarpan örnek-başına `T_i²` olur. Gate kolunda açıkça
   `self.temperature ** 2` kullanılır ([:417](kd_common.py#L417)).
2. **KL yönü = KL(öğretmen ‖ öğrenci)**: `F.kl_div(input=öğrenci log-softmax, target=öğretmen
   softmax)` ([:351-356](kd_common.py#L351-L356)) → `Σ_k p_T(log p_T − log p_S)`. Standart KD yönü.
3. **İndirgeme = batchmean**: sınıf üzerinden `.sum(dim=1)`, batch üzerinden `.mean()`.
4. **α aynı zamanda kapıdır**: KD terimi yalnızca `alpha < 1.0` iken hesaplanır
   ([:376](kd_common.py#L376)); α=1.0 damıtmayı tamamen kapatır.

`aux_beta` = `beta_vich` = **1e-4**, öğrenci VICH head'inin kendi KL terimine uygulanır
([:392-394](kd_common.py#L392-L394)).

## 2A.1 `adaptive_t` — ⚠️ yayımlanmış bir yöntem DEĞİL, kendi tasarımımız

[kd_baselines.py:23-38](kd_baselines.py#L23-L38). Docstring "**ATD-style baseline**" ifadesini
kullanır — bu bir **benzetme, atıf değil**. Aynı dosyadaki diğer mekanizmalar gerçek atıf taşır:
`logit_std` → "Sun et al. CVPR 2024" ([:13](kd_baselines.py#L13)),
`ctkd` → "Li et al. AAAI 2023" ([:57](kd_baselines.py#L57)).
**`adaptive_t` için yazar/yıl/denklem numarası yoktur.**

> **Makalede yayımlanmış bir yönteme ATFETMEYİN.** Kendi entropi-koşullu sıcaklığımız olarak
> tanımlanmalı.

Formül — **örnek-başına** (sınıf-başına değil, küresel değil):

$$T_i = \tau\left(1 + \gamma\left(\frac{H_i}{\log C} - \overline{\frac{H}{\log C}}\right)\right),
\qquad T_i \leftarrow \mathrm{clamp}\left(T_i,\; 1.0,\; 2\tau\right)$$

`H_i` öğretmen entropisi ve **T=1'de** hesaplanır ([:32-34](kd_baselines.py#L32-L34); gerekçe
docstring'de: sıcaklığı yeniden şekillendiren entropinin o sıcaklıkta hesaplanması dairesel olurdu).
`C` = sınıf sayısı, `τ` = `--temperature` (=6), `γ` = `--adaptive-t-gamma`.

> **Hakemin soracağı özellik, önceden yazılmalı:** ortalama `h_bar` **batch içinden** alınır
> ([:36](kd_baselines.py#L36)), dolayısıyla `T_i` batch kompozisyonuna bağlıdır — aynı görüntü
> farklı bir batch'te farklı bir T alır. Bu bilinçli bir tasarım tercihi olarak belirtilmelidir.

---

# 3. Öğretmen envanteri — confound kontrolü

Reviewer'ın "kalibrasyon mu, yoksa X mi?" sorusunun cevabı. Üç config birebir okundu.

## 3.1 Tam alan karşılaştırması

| Alan | Stage1 | Primary | VAE9182 |
|---|---|---|---|
| config | `.../2026-07-17-04-41-04/RAFDB_posterv2_vich_klb1e4_200e.yaml` | `configs/RAFDB_posterv2_vich_recipe.yaml` | `.../2026-06-16-23-33-23/RAFDB_teacher_affectnet_recipe.yaml` |
| **head** | VICH | VICH | **VAE** |
| **ce_kld_beta** | **0.0001** | 0.001 | 0.001 |
| **max_epochs / t_max** | **200** | 300 | 300 |
| **transforms_name** | RAFDB_RECIPE | RAFDB_RECIPE | **QCS-rafdb** |
| **seed** | 1 | 1 | **0** |
| train_resize_size | 224 | 224 | 236 *(bu yolda hiç okunmuyor, §3.3)* |
| optimizer | AdamW + SAM | AdamW + SAM | AdamW + SAM |
| rho (SAM) | 0.05 | 0.05 | 0.05 |
| init_lr | 9e-6 | 9e-6 | 9e-6 |
| weight_decay | 1e-4 | 1e-4 | 1e-4 |
| schedule / gamma | ExponentialLR / 0.98 | ExponentialLR / 0.98 | ExponentialLR / 0.98 |
| batch_size | 48 | 48 | 48 |
| loss_name | ce_kld_loss | ce_kld_loss | ce_kld_loss |
| use_amp | False | False | False |
| layer_embedding | True | True | True |
| landmarks | 68 | 68 | 68 |
| pretrained_timm / _local | False / ~ | False / ~ | False / ~ |
| votes_sum | 0 | 0 | 0 |
| folds | [2]/[3] | [2]/[3] | [2]/[3] |
| train/val_size | 224/224 | 224/224 | 224/224 |
| **kendi acc** | 92.24% | 92.01% | 91.82% |
| **kendi ECE** | 0.0378 | 0.0396 | **0.0136** |
| **T\*** | 1.3494 | 1.2613 | 0.9829 |

`votes_sum: 0` → RAF-DB'de oy dağılımı yok, `loss_encoder.py:20` gereği
`labels_em = embeddings[labels]` yoluna düşülüyor (sınıf gömüleri, sert etiket).

### 3.1a Ön-eğitim bir confound DEĞİL — üçünde de aynı ve koşulsuz

Üç config de `pretrained_timm: False`, `pretrained_local: ~` taşır. Ama POSTERv2 omurga
ağırlıklarını bu bayraktan **bağımsız olarak, `__init__` içinde koşulsuz** yükler:

- MobileFaceNet landmark omurgası — [`trails/posterv2/PosterV2_7cls.py:332-336`](trails/posterv2/PosterV2_7cls.py#L332-L336)
  (`mobilefacenet_model_best.pth.tar`)
- IR50 yüz-tanıma omurgası — [`:355-360`](trails/posterv2/PosterV2_7cls.py#L355-L360) (`ir50.pth`)

Dolayısıyla üç öğretmen **aynı ön-eğitilmiş omurgalarla** başlar; ön-eğitim ayırt edici bir
değişken değildir. (`pretrained_timm` bayrağının tam olarak neyi kontrol ettiği ayrı bir kod
yolu — **UNKNOWN**, izlenmedi; üçünde de `False` olduğu için confound analizini etkilemez.)

### 3.1b Head-ile-birlikte gelen ek bayraklar

VICH öğretmenleri `vich_use_sampling: True` ve `vich_init_logvar_bias: 0.0` taşır; VAE9182
config'inde bu anahtarlar **hiç yoktur**. Yani "head farkı" tek bir mimari anahtar değil,
head + örnekleme davranışı paketidir — confound sayımında tek kalem olarak yazılsa da
Methods'ta bu şekilde açılmalıdır.

## 3.2 İkili confound sayımı

| Çift | Farklı alanlar | Sayı |
|---|---|---|
| Stage1 ↔ Primary | `ce_kld_beta` (1e-4 ↔ 1e-3), `max_epochs` (200 ↔ 300) | **2** |
| **Primary ↔ VAE9182** | **head** (VICH↔VAE), **transforms**, **seed** (1↔0) | **3** ← en yakın eşleşen çift |
| Stage1 ↔ VAE9182 | head, transforms, seed, ce_kld_beta, max_epochs | **5** |

**Dürüst ifade:** üç öğretmen yalnızca kalibrasyonda değil, 2–5 alanda birbirinden ayrılıyor.
Bu yüzden **B-001 (öğretmen-ECE → öğrenci sonucu) gözlemsel bir bulgudur ve tek başına
nedensellik taşımaz.** Nedensellik iddiası **B-007**'ye dayanır: orada tek bir öğretmenin
logitleri post-hoc ölçeklenir, yani mimari/reçete/öğretmen-doğruluğu **sabittir** ve yalnızca
kalibrasyon değişir. B-007 hem Stage1 hem VAE9182 için **öğretmen-içi** bir manipülasyondur;
öğretmenler arası olan tek şey headroom *büyüklüklerinin* karşılaştırılmasıdır.

## 3.2a "Head mi, reçete mi?" — köprü öğretmeniyle deneysel olarak kapatıldı (B-016)

Hakemin en olası ilk sorusu Primary ↔ VAE9182 çiftindeki **head** farkıdır. Bunun için tek
değişkenli bir köprü öğretmeni eğitildi: `RAFDB_posterv2_vae_recipe_seed1.yaml`, Primary'nin
config'inin bire bir kopyası, **yalnızca iki satır** çevrilmiş (`vae_head: True`,
`vich_head: False`) — `diff` ile doğrulandı, başka hiçbir alan farklı değil.
Eğitim: `results/teacher_logs/RAFDB/POSTERv2/2026-07-21-13-36-38/`.

Ön-kayıtlı karar kuralı (sonuçtan önce sabitlendi, JSON'da `decision_bands`):
ECE ≈ **0.015** ± 0.01 → head mimarisi; ECE ≈ **0.038** ± 0.01 → reçete/augmentasyon.

| öğretmen | reçete | head | tohum | kendi acc | **ECE(T=1)** | T\* |
|---|---|---|---|---|---|---|
| Primary | RAFDB_RECIPE | VICH | 1 | 92.01% | 0.0396 | 1.261 |
| **Köprü** | **RAFDB_RECIPE** | **VAE** | **1** | **92.47%** | **0.0391** | **1.253** |
| VAE9182 | QCS-rafdb | VAE | 0 | 91.82% | **0.0136** | 0.983 |

**Head'i çevirmek kalibrasyonu düzeltmedi:** köprü 0.0391 (Primary'den Δ = 0.0005),
VAE9182'nin 0.0136'sından 2.9× uzak. T\* de reçeteyi izliyor (1.253 ≈ 1.261, 0.983 değil).
**Karar: VAE9182'nin kalibrasyon üstünlüğünü head mimarisi değil, reçete ve/veya tohum
üretiyor.** Ayrıca köprü dört öğretmenin **en yüksek doğruluğuna** sahip (92.47%) ama
kalibrasyonu Primary seviyesinde kötü — doğruluk/kalibrasyon ayrışmasının bir örneği daha.

**Sınırlar (Methods'a yazılmalı):** köprü VAE9182'den **iki** alanda ayrılır (transforms +
tohum), dolayısıyla sonuç "head **değil**" ve "reçete ve/veya tohum"dur; reçeteyi tohumdan
ayırmaz. n=1 öğretmen, tek tohum (öğretmen eğitimi ~8.4 h). Köprü öğretmeniyle öğrenci
eğitilmedi (`runs.csv`'de 0 satır) — deneyin amacı öğretmen-tarafı ECE ölçümüydü.

Betik: [`diagnostics/bridge_teacher_check.py`](diagnostics/bridge_teacher_check.py) →
`diagnostics/bridge_teacher/bridge_teacher_check.json`

## 3.3 Augmentasyon confound'u — kaynaktan doğrulandı

`transforms_name` string'i `dataset_utils/transforms.py::get_data_transforms` içinde dallanıyor:

**`RAFDB_RECIPE`** → [transforms.py:117-127](dataset_utils/transforms.py#L117-L127) (isim
`rafdb_recipe`'e küçültülüp eşleşiyor):
`Resize(224,224)` → `RandomHorizontalFlip` → `ColorJitter(0.2, 0.2, 0.2)` → `ToTensor` →
`Normalize(ImageNet)` → **`RandomErasing(p=0.5)`**

**`QCS-rafdb`** → **hiçbir isimli dala eşleşmiyor** (satır 117 yalnızca `rafdb-recipe`/`rafdb_recipe`
kabul eder), genel kuyruğa düşüyor [transforms.py:162-167](dataset_utils/transforms.py#L162-L167)
ve augmentasyon `_train_augs("qcs-rafdb")`'dan geliyor — `"qcs" in name` eşleşmesi
[transforms.py:11-18](dataset_utils/transforms.py#L11-L18):
`Resize(224,224)` → `RandomHorizontalFlip` → `RandomApply([ColorJitter(0.3, 0.3, 0.2, hue=0.05)], p=0.5)`
→ `ToTensor` → `Normalize(ImageNet)` — **RandomErasing YOK**

Yani VAE9182 ile iki VICH öğretmeni arasındaki augmentasyon farkı: (a) RandomErasing var/yok,
(b) ColorJitter şiddeti ve olasılığı, (c) hue jitter var/yok. Ayrıca YAML'daki
`train_resize_size: 236` bu yolda **hiç okunmuyor** (yalnızca `train_size`=224 kullanılıyor), yani
config'e bakıp "236'ya resize ediliyor" demek yanlış olur.

**Doğrulama tarafı temiz:** üç öğretmenin de `valid` pipeline'ı birebir aynı
(`Resize(224,224)` → `ToTensor` → `Normalize(ImageNet)`), dolayısıyla ölçümler karşılaştırılabilir.

---

# 4. Tam spesifikasyon

## 4.1 Öğrenci

| | değer |
|---|---|
| mimari | MobileNetV2Plus (`models/mobilenetv2_plus.py`) |
| omurga | MobileNetV2, `width_mult = 1.0` |
| eklentiler | ECA kanal-dikkati (`ECALayer`, :10), GeM havuzlama (`GeM`, :38), hafif LightLE katman-gömüsü (3 katman, :311-327 / forward :373-398) |
| head | **VICH** (`VICHHead`, :86) |
| VICH head yapısı | iki paralel `nn.Linear(in_dim → 7)`: `mu` ve `logvar`. Ağırlıklar `N(0, 0.01²)`; `mu.bias = 0`; `logvar.bias = init_logvar_bias` |
| VICH `init_logvar_bias` | −5.0 (öğrenci varsayılanı) |
| VICH logvar clamp | [−10, 10] |
| VICH örnekleme | eğitimde `--no-vich-sampling` (kapalı); değerlendirmede daima kapalı |
| gömü boyutu | 768 |
| **parametre** | **2.248291 M** |
| **FLOPs @224** | **0.328584384 GMACs** |
| model boyutu | 8.83 MB |
| ImageNet ön-eğitimi | `--student-pretrained` varsayılan **True**; `pretrained/hub/checkpoints/mobilenet_v2-b0353104.pth` |

Karşılaştırma için: linear-head varyantı 2.239324 M (VICH head yerine tek `Linear`), vanilla
torchvision MobileNetV2 2.233 M — yani Plus yığını ~15 K parametre ekliyor.

## 4.2 Öğretmen

| | değer |
|---|---|
| mimari | POSTERv2 (`pyramid_trans_expr2`, `trails/posterv2/`) |
| head | VICH (Stage1, Primary) veya VAE (VAE9182) |
| layer embedding | açık |
| landmarks | 68 |
| **parametre** | 58.345038 M (VICH) / 58.334272 M (VAE) |
| **FLOPs @224** | **8.482723136 GMACs** |
| model boyutu | 555 MB |
| eğitim | bkz. §3.1 (AdamW + SAM ρ=0.05, lr 9e-6, ExponentialLR γ=0.98, wd 1e-4, batch 48, `ce_kld_loss`) |

## 4.3 KD reçetesi — RAF-DB ve FERPlus ayrı

Değerler **gerçek `run_args.json`'lardan** okundu (config varsayılanı değil, fiilen kullanılan).

> **Mekanizma hiperparametreleri burada tekrarlanmaz.** Her mekanizmanın (gate, g2g,
> logit_std, adaptive_t, ctkd) tam bayrak listesi, kol başına koşu sayısı ve formüllerin
> kod referansları tek kaynakta durur: **`diagnostics/paper_tables/mechanism_specs.md`**
> (üretici `diagnostics/mechanism_specs.py`; değerler koşuların kendi `run_args.json`
> dökümlerinden okunur, elle yazılmaz). Buraya kopyalanmamasının sebebi tek-kaynak kuralı:
> iki yerde duran bir hiperparametre, birinde güncellenip ötekinde unutulabilir.

| | **RAF-DB** | **FERPlus** | kaynak |
|---|---|---|---|
| epochs | **400** | **200** | run_args |
| optimizer | AdamW | AdamW | [rafdb:795](train_rafdb_kd.py#L795) / [ferplus:621](train_affectnetplus_kd.py#L621) |
| lr | 3e-4 | 3e-4 | run_args |
| weight_decay | 1e-4 | 1e-4 | run_args |
| momentum | AdamW varsayılan β=(0.9, 0.999), açıkça set edilmiyor | aynı | — |
| scheduler | `CosineAnnealingWarmRestarts(T_0=10, T_mult=2, eta_min=1e-6)` | aynı | [rafdb:808](train_rafdb_kd.py#L808) / [ferplus:632](train_affectnetplus_kd.py#L632) |
| batch_size | 64 | 64 | run_args |
| **SWA** | açık, `swa_start = 200` → **200…400 = 201 epoch ortalanır** | açık, `swa_start = 100` → **100…200 = 101 epoch** | §4.3a |
| `swa_lr` | 1e-4 | 1e-4 | run_args |
| **τ_KD** | **6.0** | **6.0** | run_args |
| **alpha** | **0.3** (→ 0.3·CE + 0.7·KD, §2A) | **0.3** | run_args |
| **label smoothing** | **0.1** | **0.0** — zorlanıyor | [train_ferplus_kd.py:1-19](train_ferplus_kd.py#L1-L19) |
| **denetim** | sert etiket | **`supervision: soft`** (10-oy dağılımı) | run_args |
| mixup | 0.1 | 0.1 | run_args |
| cutmix | **yok** | **yok** | — |
| **sınıf ağırlığı** | `effective_number`, β = 0.9999 | **yok** (bayrak scriptte mevcut değil) | run_args |
| AMP | açık (`GradScaler`) | açık | [rafdb:797](train_rafdb_kd.py#L797) / [ferplus:623](train_affectnetplus_kd.py#L623) |
| **gradient clipping** | **YOK** | **YOK** | `clip_grad*` her iki trainer'da ve `kd_common.py`'de bulunmuyor |
| girdi çözünürlüğü | 224 × 224 | 224 × 224 | run_args |
| beta_vich (aux KL) | 1e-4 | 1e-4 | run_args |
| feature distillation | kapalı (`0.0`) | bayrak yok | run_args |
| EMA | kapalı (`ema_decay` set ama devre dışı) | kapalı | run_args |

### 4.3a SWA'nın gerçek davranışı — LR "sabit SWA-LR" DEĞİL

Epoch döngüsü `range(1, epochs+1)` ([rafdb:827](train_rafdb_kd.py#L827),
[ferplus:652](train_affectnetplus_kd.py#L652)), koşul `epoch >= swa_start`
([rafdb:854](train_rafdb_kd.py#L854), [ferplus:679](train_affectnetplus_kd.py#L679)).

**LR:** SWA başladığı andan itibaren ana scheduler **artık step edilmez** — `if/else`
([rafdb:854-858](train_rafdb_kd.py#L854-L858)) `swa_scheduler.step()` ile `scheduler.step()`
arasında seçim yapar. Cosine warm restarts durur, `SWALR(optimizer, swa_lr=1e-4)` devralır
([rafdb:814](train_rafdb_kd.py#L814)). `SWALR`'ın varsayılanları `anneal_epochs=10`,
`anneal_strategy='cos'` olduğundan gerçek davranış: **10 epoch boyunca cosine ile 1e-4'e iner,
sonra sabit 1e-4.** Methods'ta "sabit SWA-LR" ya da "cosine devam ediyor" yazmak yanlış olur.

**BN istatistikleri yeniden hesaplanıyor:** `update_bn` çağrılıyor
([rafdb:904](train_rafdb_kd.py#L904), [ferplus:752](train_affectnetplus_kd.py#L752)) — **train
loader üzerinden, augmentasyon aktif hâlde** (val üzerinden değil). Bu yapılmasa SWA sayıları
düşük çıkardı; yapıldığı doğrulanmıştır.

## 4.4 Ön-işleme

**Hizalama:** `data/rafdb_aligned/` — RAF-DB'nin hizalanmış (aligned) görüntüleri, 15339 jpg.
Görüntüler `cv2.imread` (BGR) ile okunup `image[:, :, ::-1]` ile RGB'ye çevriliyor
([train_rafdb_kd.py:82-84](train_rafdb_kd.py#L82-L84)).

### 4.4a Augmentasyon — tam liste, her iki veri kümesi

> ### ⚠️ `run_args.json`'daki DÖRT alan EYLEMSİZDİR — Methods'a kopyalanmamalı
> | alan | kayıtlı değer | neden eylemsiz |
> |---|---|---|
> | `random_erasing_p` | FERPlus: **0.5** | QCS yolu bu değeri hiç okumaz ([transforms.py:162-167](dataset_utils/transforms.py#L162-L167)) → FERPlus'ta **RandomErasing yok** |
> | `color_jitter` | her ikisi: 0.2 | RAF-DB `kd` preset'i kullanmaz ([train_rafdb_kd.py:201-208](train_rafdb_kd.py#L201-L208)); FERPlus sabit 0.3/0.3/0.2/hue 0.05 kullanır |
> | `rotation_degrees` | RAF-DB: 12.0 | yalnızca `poster_var_rafdb` preset'i okur; `kd` preset'inde **rotation yok** |
> | `gamma` | RAF-DB: 0.98 | yalnızca `ExponentialLR` dalı okur ([:800](train_rafdb_kd.py#L800)); `cosine_warm_restarts` seçiliyken eylemsiz |

**RAF-DB öğrenci** (`augment_preset: kd`, [train_rafdb_kd.py:201-208](train_rafdb_kd.py#L201-L208)):
`Resize(224,224)` → **`RandAugment(num_ops=2, magnitude=7)`** → `RandomHorizontalFlip` →
`ToTensor` → `Normalize(ImageNet)` → **`RandomErasing(p=0.1)`**
— rotation **yok**, crop **yok**, açık ColorJitter **yok**.

**FERPlus öğrenci** (`transforms_name: QCS-ferplus` → `"qcs" in name` dalı,
[transforms.py:162-167](dataset_utils/transforms.py#L162-L167) + [:11-18](dataset_utils/transforms.py#L11-L18)):
`Resize(224,224)` → `RandomHorizontalFlip` →
**`RandomApply([ColorJitter(0.3, 0.3, 0.2, hue=0.05)], p=0.5)`** → `ToTensor` → `Normalize(ImageNet)`
— **RandomErasing yok, rotation yok, crop yok, RandAugment yok.**

**Doğrulama pipeline'ı** her yerde birebir aynı:
`Resize(224,224)` → `ToTensor` → `Normalize(ImageNet)`
([train_rafdb_kd.py:217-221](train_rafdb_kd.py#L217-L221),
[transforms.py:168-172](dataset_utils/transforms.py#L168-L172)).

**mixup:** her iki veri kümesinde **α = 0.1**; `lam ~ Beta(α, α)`, batch permütasyonu
([kd_common.py:640-648](kd_common.py#L640-L648)). Görüntülerle birlikte **denetimli dağılım VE
öğretmen olasılıkları/logitleri de** karıştırılır
([train_rafdb_kd.py:495-517](train_rafdb_kd.py#L495-L517)). **cutmix yok.**

**Öğretmen ↔ öğrenci karşılaştırması** (hakem soracak):

| | öğretmen pipeline'ı | öğrenci pipeline'ı | aynı mı? |
|---|---|---|---|
| RAF-DB Stage1 / Primary | `RAFDB_RECIPE`: Resize→HFlip→ColorJitter(0.2,0.2,0.2)→Norm→**RandomErasing(p=0.5)** ([transforms.py:117-127](dataset_utils/transforms.py#L117-L127)) | RandAugment(2,7) + RE(0.1) | ❌ **farklı** |
| RAF-DB VAE9182 | `QCS-rafdb`: Resize→HFlip→RandomApply(CJ 0.3/0.3/0.2/hue .05, p=.5), **RE yok** | aynı öğrenci pipeline'ı | ❌ **farklı** |
| FERPlus | `QCS-ferplus` | **birebir aynı** (`QCS-ferplus`) | ✅ **aynı** |

Yani RAF-DB'de öğretmen ve öğrenci farklı augmentasyon görür, FERPlus'ta aynısını görür. Bu
bilinçli bir tasarım tercihi değil, iki ayrı kod yolunun mirasıdır; Methods'ta olduğu gibi
belirtilmelidir.

### 4.4b FERPlus veri kümesi ayrıntıları

**Etiket eşlemesi:** 8 sınıf, `configs/FERPlus_majority_metadata.csv` sütun sırası
`neutral, happiness, surprise, sadness, anger, disgust, fear, contempt`.
Tam başlık (dosyadan): `path,label,fold,neutral,happiness,surprise,sadness,anger,disgust,fear,contempt,source_row`.
Bölme `train_folds [0,1]`, `val_folds [2]` → 25060 / 3199 / **3153**
(config: `configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml:11-12`).

**Oy toplamı — sebep UNKNOWN, iddia edilmemeli.** Oy toplamı dağılımı (31412 satır):

| toplam | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|
| satır | 51 | 280 | 1497 | 7376 | 22208 |

Hiçbir satır 10'u aşmıyor, hiçbiri 6'nın altına düşmüyor. Val fold'da toplanmayan satır oranı
**%37.3**, tüm dosyada %29.3.

> **`unknown` ve `NF` sütunları bu dosyada YOKTUR** ve repoda orijinal FERPlus etiket dosyası
> (`fer2013new.csv` vb.) da bulunamadı. Üst sınırın tam 10 olması, "10 oylayıcıdan bir kısmı
> unknown/NF dedi ve o sütunlar bu türev üretilirken atıldı" senaryosuyla **tutarlıdır**, ama
> **repodaki veriyle kanıtlanamaz.** Methods'ta kesin dille yazılmamalı: "8 duygu sütunu her zaman
> 10'a toplanmıyor; eksik oylar bu türevde mevcut değil" denip neden yalnızca *olası* açıklama
> olarak, FERPlus orijinal şemasına atıfla verilmelidir.

Normalizasyon her yerde ImageNet: mean `(0.485, 0.456, 0.406)`, std `(0.229, 0.224, 0.225)`.

---

# 5. Figür kaynak verisi

| Figür | PNG | Veri (JSON/CSV) | Üretici script |
|---|---|---|---|
| **İKİ VERİ KÜMESİ overlay (ANA FİGÜR ADAYI)** | `diagnostics/p1_dose_response/two_dataset_overlay_swa.png` | `.../two_dataset_overlay.json` | [`diagnostics/two_dataset_overlay.py`](diagnostics/two_dataset_overlay.py) |
| ↳ ek: @best ve @last panelleri | `.../two_dataset_overlay_supp.png` | aynı JSON | aynı script |
| İşaretli miskalibrasyon (RAF-DB, 2 öğretmen) | `.../signed_miscalibration_overlay.png` | `.../signed_miscalibration_overlay.json` | [`diagnostics/p1_signed_miscalibration_overlay.py`](diagnostics/p1_signed_miscalibration_overlay.py) |
| B-015 verdict (FERPlus doz-yanıt) | — | `diagnostics/selection_audit/b015_verdict.json` | [`diagnostics/b015_verdict.py`](diagnostics/b015_verdict.py) |
| FERPlus öğretmen işaretli ızgara | — | `diagnostics/ferplus_jsd/ferplus_teacher_signed_grid.json` | [`diagnostics/ferplus_teacher_signed_grid.py`](diagnostics/ferplus_teacher_signed_grid.py) |
| FERPlus ÖĞRENCİ JSD (insan hizalaması) | — | `diagnostics/ferplus_jsd/ferplus_student_jsd.{csv,json}` | [`diagnostics/ferplus_student_jsd.py`](diagnostics/ferplus_student_jsd.py) |
| FERPlus seçim denetimi | — | `diagnostics/selection_audit/ferplus_selection_audit.csv` | [`diagnostics/ferplus_selection_audit.py`](diagnostics/ferplus_selection_audit.py) |
| Seçim kazancı (saf sıra istatistiği) | — | `diagnostics/selection_audit/selection_gain.json` | [`diagnostics/selection_gain_estimator.py`](diagnostics/selection_gain_estimator.py) |
| Seçim sağlamlığı (checkpoint çaprazı) | — | `diagnostics/selection_audit/selection_robustness.json` | [`diagnostics/selection_robustness.py`](diagnostics/selection_robustness.py) |
| Gecikme ölçümü | — | `diagnostics/p5_efficiency/latency_benchmark.{csv,json}` | [`diagnostics/latency_benchmark.py`](diagnostics/latency_benchmark.py) |
| İki öğretmen overlay (öğretmen-ECE ekseni, önceki sürüm) | `diagnostics/p1_dose_response/two_teacher_overlay.png` | `.../two_teacher_overlay.json` | [`diagnostics/p1_two_teacher_overlay.py`](diagnostics/p1_two_teacher_overlay.py) |
| ~~Stage1 doz-yanıt (tek öğretmen)~~ **SÜPERSEDE** | `diagnostics/p1_dose_response/p1_dose_response.png` | `.../p1_dose_response.json` | scratchpad `p1_figure.py` — **repo'da değil** |
| Öğretmen ECE ızgarası (x ekseni kaynağı) | — | `diagnostics/teacher_ece_grid/teacher_ece_grid.json` + `teacher_val_logits_<t>.pt` | [`diagnostics/teacher_ece_grid.py`](diagnostics/teacher_ece_grid.py) |
| FERPlus JSD | — | `diagnostics/ferplus_jsd/ferplus_jsd.json` + `ferplus_val_logits.pt` | [`diagnostics/ferplus_human_vote_jsd.py`](diagnostics/ferplus_human_vote_jsd.py) |
| VICH izolasyonu | — | `diagnostics/vich_isolation/vich_isolation_verdict.json` | [`diagnostics/vich_isolation_verdict.py`](diagnostics/vich_isolation_verdict.py) |
| adaptive_t × headroom | — | `diagnostics/adaptive_t_headroom/adaptive_t_headroom.json` | [`diagnostics/adaptive_t_headroom_table.py`](diagnostics/adaptive_t_headroom_table.py) |
| Öğretmen seçim reçetesi | — | `diagnostics/p4_teacher_selection/p4_teacher_selection.json` | [`diagnostics/p4_teacher_selection_recipe.py`](diagnostics/p4_teacher_selection_recipe.py) |
| Verimlilik | — | `diagnostics/p5_efficiency/p5_efficiency.json` | [`diagnostics/p5_efficiency_frontier.py`](diagnostics/p5_efficiency_frontier.py) |
| Seçim denetimi | — | `diagnostics/selection_audit/selection_audit.csv` | [`diagnostics/selection_audit_table.py`](diagnostics/selection_audit_table.py) |
| **Kapasite cephesi (T10)** | `diagnostics/p5_efficiency/p5_frontier.png` | `.../p5_frontier.json` | [`diagnostics/p5_frontier_figure.py`](diagnostics/p5_frontier_figure.py) |
| **Mekanizma teşhisi (T5/T5a)** | `diagnostics/paper_tables/mechanism_diagnostic.png` | `.../mechanism_diagnostic.json` | [`diagnostics/mechanism_diagnostic_figure.py`](diagnostics/mechanism_diagnostic_figure.py) |
| **FERPlus çift eksen (T7)** | `diagnostics/ferplus_jsd/ferplus_dual_axis.png` | `.../ferplus_dual_axis.json` | [`diagnostics/ferplus_dual_axis_figure.py`](diagnostics/ferplus_dual_axis_figure.py) |
| **MAKALE FİGÜRLERİ (vektör PDF)** | `paper/figures/*.pdf` (5 adet) | — | [`diagnostics/export_paper_figures.py`](diagnostics/export_paper_figures.py) |
| **Verimlilik frontier'ı (8a)** | `diagnostics/p5_efficiency/efficiency_frontier.png` | `.../efficiency_frontier.{json,md}` | [`diagnostics/efficiency_frontier.py`](diagnostics/efficiency_frontier.py) + `diagnostics/literature_fer_models.csv` |
| **Yasa × kapasite (8b, KEŞİFSEL)** | — | `diagnostics/p5_efficiency/capacity_law_check.{json,md}` | [`diagnostics/capacity_law_check.py`](diagnostics/capacity_law_check.py) |
| **Önbellek zehirlenme denetimi** | — | `diagnostics/calibration_cache_audit.json` | [`diagnostics/calibration_cache_audit.py`](diagnostics/calibration_cache_audit.py) |
| **Terk edilmiş koşu işaretleri** | — | `diagnostics/abandoned_runs.json` + her dizinde `ABANDONED.json` | [`diagnostics/mark_abandoned_runs.py`](diagnostics/mark_abandoned_runs.py) |
| **Gecikme, 2. oturum** | — | `diagnostics/p5_efficiency/latency_benchmark_session2.{csv,json}` | [`diagnostics/latency_benchmark.py`](diagnostics/latency_benchmark.py) `--tag session2` |
| **Makale tabloları T1–T10a** | — | `diagnostics/paper_tables/RESULTS_TABLES.md` | [`diagnostics/paper_tables.py`](diagnostics/paper_tables.py) |
| **P2 hükmü (gate:oracle, ÖN-KAYITLI)** | — | `diagnostics/p2_gate_oracle/p2_verdict.{json,md}` | [`diagnostics/p2_gate_oracle_verdict.py`](diagnostics/p2_gate_oracle_verdict.py) |
| **Özetteki seçim-iyimserliği sayısı** | — | `diagnostics/selection_audit/selection_optimism_headline.json` | [`diagnostics/selection_optimism_headline.py`](diagnostics/selection_optimism_headline.py) |
| **T5 eşleştirme kuralı diff'i (A2)** | — | `diagnostics/paper_tables/t5_pairing_diff.{json,md}` | [`diagnostics/t5_pairing_diff.py`](diagnostics/t5_pairing_diff.py) |
| **5.4 sayı seti (B1–B4)** | — | `diagnostics/paper_tables/section54_numbers.{json,md}` | [`diagnostics/section54_numbers.py`](diagnostics/section54_numbers.py) |
| **Tablo sayıları (yapısal)** | — | `diagnostics/paper_tables/RESULTS_TABLES.json` | [`diagnostics/paper_tables.py`](diagnostics/paper_tables.py) |
| **Tablo diff kapısı** | — | `diagnostics/table_diff_gate/{baseline,last_diff}.*` | [`diagnostics/table_diff_gate.py`](diagnostics/table_diff_gate.py) |
| **Değişen figür teslimi** | `paper/figures/_updated_2026-07-30/*.pdf` | `.../README.md` | — (elle kopyalanacak) |

### 5A.2 İki sessiz havuzlama kusuru ve kalıcı onarımları (2026-07-30)

P2/P3 diske **yeni türde** koşular koydu ve mevcut iki filtre onları yanlış hücrelere aldı.
İkisi de hata mesajı üretmedi — sadece sayıları değiştirdi. Kayda geçiyor, çünkü her ikisinin de
onarımı artık bir `RuntimeError` kapısıyla korunuyor.

**(1) İki yasal kontrol, sözlük sırası hakem.** P2, `class_weight_mode=none` baseline'ını üretti.
`paper_tables.py::is_ablation_control` sınıf-ağırlığına bakmadığı için VAE9182'nin her tohumunda
**iki** yasal kontrol oluştu ve `controls[(teacher, seed)] = key` hangisini tutacağını iterasyon
sırasına bıraktı. Onarım: `class_weight_mode` artık `runs.csv`'de bir sütun **ve** eşleştirme
anahtarının parçası; aynı hücreye ikinci kontrol düşerse `RuntimeError`. Yan etkisi olumlu —
gate satırları böylece kendi sınıf-ağırlığı kipindeki kontrole taşındı (bkz. `PREREGISTRATIONS.md`
A8; 8 gate koşusundan 4'ü taşındı, 4'ü kontrolsüz kaldığı için T5'ten düştü).

**(2) `"frontier" in run_name` sıcaklık taramasını yuttu.** P3'ün koşuları
`RAFDB_vae9182_frontier_w050_tempscale_T{170,220}_*` adını taşıyor. Adında `frontier` geçen her
koşuyu genişlik hücresine koyan **üç** filtre bunları `scratch w050`'ye kattı:

| yer | kirlenmiş hâli | onarım sonrası |
|---|---|---|
| `paper_tables.py` T10 hücreleri | w050: n=7, ECE **0.1079 ± 0.0737** | n=3, ECE 0.0365 ± 0.0057 |
| T10 eksen oranı (@swa) | kapasite açıklığı 0.0704 → oran **3×** | 0.0024 → oran **76×** |
| `efficiency_frontier.py`, `p5_frontier_figure.py` | aynı havuzlama | `t_scale == 1.0` şartı |

T10'un tüm amacı **kapasite eksenini sıcaklık eksenine karşı** ölçmek olduğu için, kirlenme
kapasite açıklığının karşılaştırılacağı ekseni kendi içine yutuyordu ve makalenin "yasa öğretmen
tarafındadır" iddiasını 76×'ten 3×'e indiriyordu. Onarım: üç filtreye de `t_scale == 1.0` şartı,
artı T10 hücrelerine **tohum tekilliği** kapısı (`RuntimeError`) — bir kapasite hücresinde aynı
tohumdan iki koşu bulunması tanım gereği ikinci bir değişkenin hareket ettiği anlamına gelir.

### 5A.3 Sözlüksel filtrelerin süpürülmesi — koşu adı veri yolundan çıkarıldı

`"frontier" in run_name` tekil bir yazım hatası değil, **sınıfsal** bir hataydı: koşu sayısı
arttıkça ad çarpışma yüzeyi büyüyor, 125'te yakalandı, 200'de yakalanmazdı. Bütün analiz/tablo/
figür kodu tarandı ve koşuyu **adından** bir deney hücresine eşleyen her yer anlamsal alana
çevrildi. Ledger'a iki yeni sütun eklendi (`width_mult`, `student_pretrained`) ve
`build_runs_ledger.capacity_tag()` bunlardan tarihsel etiketleri (`w050`/`w075`/`w100ns`/`w100`)
**birebir** üretiyor — 13 kapasite koşusunda 0 sapma, yani figür anahtarları ve makale etiketleri
değişmedi.

| dosya:satır | eski filtre | yeni filtre | etkilenen |
|---|---|---|---|
| `build_runs_ledger.py:71` | `t_scale != 1.0 or "tempscale" in n` | `t_scale != 1.0` | — (ölü kod: `"tempscale"`in yakaladığı her koşuyu `t_scale` zaten yakalıyordu; tarandı, tek karşı örnek yok) |
| `build_runs_ledger.py:80` | `"miscal" in n` | `abs(t_scale − 0.7311) < 1e-9` | aile ataması → T1–T4 |
| `build_runs_ledger.py:82` | `"pluslinear" in n or head=="linear"` | `head == "linear"` | — (ölü kod) |
| `build_runs_ledger.py:88` | `width_mult != 1.0 or "frontier" in n` | `width_mult != 1.0 or not pretrained` | **yük taşıyordu**: `frontier_w100ns` koşularının `width_mult`'ı 1.0; onları T5 kontrol havuzundan uzak tutan tek şey addı |
| `capacity_law_check.py:92,99` | `"_frontier_" in name` + ad ayrıştırma | `student_pretrained == False` + `capacity_tag` | T10a, 8(b) |
| `efficiency_frontier.py:92-99` | `"frontier" in n` + ad ayrıştırma | `cell_of()`: `t_scale` + `pretrained` + `capacity_tag` | 8(a) frontier |
| `p5_frontier_figure.py:69-76` | `"frontier" in n` + ad ayrıştırma | `cell_of()` (aynı) | **`p5_frontier.pdf`** |
| `paper_tables.py:752` | `"frontier" in n` + ad ayrıştırma | ledger satırından `t_scale` + `pretrained` + `capacity_tag` | **T10** |

**Anlamsal alana çevrilemeyen tek filtre**, gerekçesiyle: `build_runs_ledger.py:80`'deki
miscal/dose-response ayrımı. Bir koşunun **hangi ön-kayıtlı bloğa** ait olduğu deneysel niyettir ve
niyeti hiçbir bayrak kaydetmiyor; onun yerine bloğa özgü **manipüle edilen değer** (T=0.7311, doz-yanıt
sweep'inin kullandığı 0.85/1.0/1.3406/1.7/2.2 kümesinde bulunmuyor) vekil olarak kullanılıyor. İleride
başka bir amaçla 0.7311 kullanılırsa ledger'a açık bir `block` alanı gerekir; kodda böyle not düşülü.
Adın kalan kullanımları (state_dict anahtar önekleri, `"_"` ile başlayan JSON meta anahtarları, font
`/Subtype` regex'i, `cell.startswith(teacher)` gibi etiket işlemleri) koşu→hücre eşlemesi yapmıyor,
o yüzden kapsam dışı.

### 5A.4 Tablo diff kapısı — makul ama yanlış bir sayıyı ne yakalar

T10'u kurtaran şey içsel doğrulama değildi: kirli değer (3×) kendi başına tamamen makul
görünüyordu, her hücre içsel tutarlıydı, hiçbir sd tuhaf değildi ve hiçbir istisna atılmadı. Onu
belirleyen tek şey **hatırlanan önceki değerle** karşılaştırmaktı. Kendi kendini doğrulama, makul
bir yanlış cevabı tespit edemez; bunu ancak bir baz sürüm yapabilir. O yüzden baz sürüm artık
kimsenin hafızasında değil, `diagnostics/table_diff_gate.py`'de:

- **Değer**, hücrenin **kendi tohum sd'sinden** fazla kıpırdarsa uyarır (sd'si olmayan türetilmiş
  skalerler için %2 bağıl geri düşüş).
- **n değişirse** koşulsuz uyarır — T10 vakasında `n=3→7` tek başına yeterli sinyaldi.
- Sapma varsa **exit 1**; `--accept "gerekçe"` ile baz ileri taşınır ve gerekçe dosyaya yazılır.

Kapının çalıştığı, tarihsel kirlenme geçici olarak geri enjekte edilerek **doğrulandı**: 4 sapma
bildirdi (`n 3→7` iki hücrede, `capacity_span` 0.0024→0.0704, `ratio` 75.7→2.5) ve exit 1 verdi;
temiz durumda 0 sapma ve exit 0. `paper_tables.py` bu iş için artık markdown'ın
yanında `RESULTS_TABLES.json` da yazıyor — T5/T10 sayıları 30 Temmuz'a kadar **yalnız biçimlenmiş
markdown olarak** vardı, kirlenmenin sessizce geçebilmesinin bir nedeni de buydu.

**Kapsam: 242 hücre.** İlk sürüm yalnız T5/T10/8(b)/P2/özet sayısını izliyordu — yani **iki bilinen
kusurun olduğu yeri**, makalenin çekirdek yasasını değil. Bu yanlış bir yanlılıktı: bir kapı en çok
neyin önemli olduğunu kapsamalı, en son nerede hata çıktığını değil. Doz-yanıt eğrileri (T1–T4,
`two_dataset_overlay.json`) sonradan eklendi: 98 yeni hücre geldi, hiçbiri MOVED/n-CHANGED değil,
yani mevcut sayılar kıpırdamadı.

| kaynak | ne izliyor |
|---|---|
| `p1_dose_response/two_dataset_overlay.json` | T1–T4 doz-yanıt: öğretmen ECE + üç checkpoint'te öğrenci acc/ECE, kol × sıcaklık |
| `paper_tables/RESULTS_TABLES.json` | T5 mekanizma Δ'ları, T10 kapasite hücreleri, T10 eksen açıklıkları/oranı |
| `p5_efficiency/capacity_law_check.json` | iki eğim, R², eğim farkı ve zarf |
| `p2_gate_oracle/p2_verdict.json` | kol ortalamaları + P2.1/P2.2/P2.3 ölçümleri |
| `selection_audit/selection_optimism_headline.json` | özette geçen seçim-iyimserliği sayısı |

> **Süperseded satır hakkında.** `p1_dose_response.json` tek öğretmenli ilk sürümdür; üreticisi
> repoda değil (scratchpad), yani **yeniden üretilemez** ve bu yüzden n−1 damgası da alamaz.
> T1–T9'un hiçbir satırı bu dosyadan beslenmiyor — Stage1 doz-yanıtı artık
> `two_teacher_overlay.json`'dan geliyor. Makalede bu dosyaya atıf yapılmayacak.

**İşaretli miskalibrasyon ekseni:** ECE işaret-kördür (mutlak değer), bu yüzden Stage1 eğrisi
öğretmen-ECE ekseninde zikzak yapıyor — T=0.85 (aşırı-güvenli, ECE 0.0454) ile T=1.70
(aşırı-yumuşak, ECE 0.0429) neredeyse aynı x'e düşüyor hâlde farklı yönlerde patolojiler
(|ΔECE| 0.0025 vs |Δ işaretli açık| 0.0859, **34× ayrışma**). Ana figür bu yüzden
`ortalama güven − doğruluk` eksenini kullanır.

**Ana figürün iki paneli ve raporlanacak istatistikler:**
- **(a) işaretli eksen:** her kol kendi T\*'ında minimumu olan bir V; RAF-DB kolları sıfıra
  **+** tarafından, FERPlus **−** tarafından yaklaşır (öğretmenleri zıt patolojide).
- **(b) sıfırda katlanmış (|işaretli açık|):** 13 nokta (10 RAF-DB + 3 FERPlus),
  **Spearman = +0.907 @swa** (+0.951 @best, +0.929 @last).

> **⚠️ Katlama tam DEĞİL — ve bu raporlanacak bir bulgu, kozmetik bir kusur değil.**
> Panel (b)'deki artık zikzak yön asimetrisidir. Stage1'de T=0.85 (işaretli **+0.0431**) →
> öğrenci ECE **0.0797**, T=1.70 (işaretli **−0.0427**) → **0.0447**: |açık| neredeyse aynı,
> öğrenci ECE'si **1.77×** farklı. Aynı ölçüm FERPlus'ta (|açık| = 0.0393, negatif dal kol-içi
> interpolasyonla) **1.79×** veriyor. İki veri kümesi, iki öğretmen, zıt doğal patolojiler →
> **1.78 ± 0.02**.
>
> **Öğretmen aşırı-güvenliliği, eşit büyüklükteki az-güvenlilikten öğrenci için ~1.8× daha
> zararlı.** Sonuç: |işaretli açık| tek başına öğrenci ECE'sini belirlemez; yasa her iki yönde
> monotondur ama **eğimler farklıdır**. Bu nedenle figür başlığında "direction-independent"
> ifadesi kullanılmamalı — savunulabilir iddia "her iki yönde ve her iki veri kümesinde geçerli".
> Ölçüm: `two_dataset_overlay.py::branch_asymmetry`, çıktı JSON'da
> `pooled_stats.direction_asymmetry_swa` (ekstrapole edilen karşılaştırmalar ayrıca işaretli).

**Checkpoint seçimi:** ana figür **@swa** kullanır, @best değil. `best` checkpoint'i, metriğin
raporlandığı görüntülerde argmax val_acc ile seçilir ([train_rafdb_kd.py:895-900](train_rafdb_kd.py#L895-L900)
→ [:960-977](train_rafdb_kd.py#L960-L977)), yani seçim optimizmi taşır (RAF-DB +0.79 pp doğruluk,
FERPlus +0.46 pp). SWA sabit bir kuraldır ve değerlendirme kümesine bakmaz. @best/@last ek
figürde **raporlanır**, gizlenmez — B-007/B-015 üç checkpoint'te de doğrulanmıştır.

---

# 5A. Reprodüksiyon

| artefakt | üretici | girdi |
|---|---|---|
| `runs.csv` | [`diagnostics/build_runs_ledger.py`](diagnostics/build_runs_ledger.py) | her koşunun kendi `run_args.json` + `metrics_best.json` + `best_checkpoint.pth` ([:3-11](diagnostics/build_runs_ledger.py#L3-L11)); hiçbir alan elle yazılmaz. Öğretmen kimliği `teacher_ckpt` yolundan eşlenir ([:36-50](diagnostics/build_runs_ledger.py#L36-L50)), family/manipulation koşunun bayraklarından ([:53-55](diagnostics/build_runs_ledger.py#L53-L55)). ECE eğitimde kaydedilmediği için post-hoc hesaplanıp `<run_dir>/calibration.json`'a önbelleklenir; `--no-compute-ece` ile atlanan koşular `ece_source="uncached"` alır. |
| `manifest.json` (koşu başına) | [`diagnostics/run_manifest.py`](diagnostics/run_manifest.py) | `poster-var` git deposu **değil** → commit SHA yok; yerine numeriği belirleyen 8 kaynak dosyanın içerik hash'i, `run_args.json`'ın kanonik hash'i, veri kümesi SHA-256 (15339 görüntü + metadata, `5dfed142d4b737d0…`), öğretmen checkpoint hash'i, tohum. Geriye dönük hash'lenen koşular `code_state_verified: false` ile işaretli (28 doğrulanmış / 62 geriye dönük). |
| RAF-DB kuyrukları | `rafdb_p3_then_miscal_chain.ps1` | `-Stream A\|B`, `-StartIndex` ile devam; `train_rafdb_kd.py`'de `--resume` **yok** |
| FERPlus doz-yanıt (9 koşu) | [`ferplus_dose_response_queue.ps1`](ferplus_dose_response_queue.ps1) | aynı desen |
| FERPlus T\*_JSD kolu (3 koşu) | [`ferplus_tjsd_queue.ps1`](ferplus_tjsd_queue.ps1) | aynı desen |
| `<run_dir>/logits_<ckpt>.npz` | [`diagnostics/student_logit_cache.py`](diagnostics/student_logit_cache.py) | Örnek-başına öğrenci logit'i + etiketler, fold-3 val (n=3068). Her yazımda logit'lerden acc ve 15-kutulu ECE **yeniden türetilip** o koşunun `selection_audit.json`'ıyla karşılaştırılır; tolerans dışıysa dosya **yazılmaz** (hard error). Stage1 kolu 5 T × 3 tohum = 15 giriş, hepsi @swa. |
| `paper/figures/reliability_diagram.pdf` | [`diagnostics/reliability_diagram.py`](diagnostics/reliability_diagram.py) | logit önbelleği + `selection_audit.csv` (ECE anotasyonu tabloyla aynı sayı) + `two_dataset_overlay.json` (öğretmen ECE'si) |
| `paper/figures/perclass_calibration.pdf` | [`diagnostics/perclass_calibration.py`](diagnostics/perclass_calibration.py) | logit önbelleği; sınıf-başına **işaretli güven açığı** (kutulama yok), tohumlar arası ortalama ± örnek sd |
| `paper/figures/vote_examples.pdf` | [`diagnostics/vote_examples_figure.py`](diagnostics/vote_examples_figure.py) | `ferplus_val_logits.pt` (önbelleklenmiş öğretmen logit'leri) + `configs/FERPlus_majority_metadata.csv` oy sütunları. Sütunlar **kural ile** seçilir: insan oy entropisinin 10/40/70/95. yüzdeliklerine en yakın örnek, eşitlik en küçük loader index'i ile bozulur; seçilen index'ler, entropiler ve eşitlik sayıları JSON'da. Oylar **satırın kendi toplamına** bölünür (3153 satırın 1176'sı 10'a toplanmıyor). |
| figür denetimi | [`diagnostics/verify_paper_figures.py`](diagnostics/verify_paper_figures.py) | Üretilen PDF'in **kendisini** ölçer: beklenmedik raster XObject yok (`EXPECT_RASTER` ile figür başına beyan edilen sayı hariç), Type 3 yok, gerçekten çizilen en küçük punto ≥ 7 pt, tek sayfa, sayfa genişliği mm |

**Fig. 6'daki tek raster:** dört FER2013 örnek yüzü, **48×48 native** olarak gömülü
(`interpolation="none"`; PDF nesnesinde `/Interpolate` yok → görüntüleyici yumuşatmaz).
Denetleyicide `EXPECT_RASTER = {"vote_examples.pdf": 4}` olarak **tam sayı** beyan edilir —
blanket muafiyet değil, böylece başka bir figüre kazara giren `imshow` yine yakalanır.
Veri kullanımı: FERPlus/FER2013 örnekleri, gönderimde *data availability* beyanında atıflanacak.

### 5A.1 ECE'nin cihaz bağımlı sayısal tabanı (~3e-4)

`selection_audit.json` değerleri **CUDA**'da hesaplandı. Aynı checkpoint CPU'da ileri
beslendiğinde doğruluk altı ondalığa kadar **aynı** çıkıyor ama ECE 3.1e-4 sapıyor
(ör. `RAFDB_stage1_tempscale_T085_…seed1` @swa: CPU 0.0816781 / CUDA 0.0813682, CUDA farkı tam
`0.00e+00`). Sebep checkpoint farkı değil — tahminler özdeş ve CPU tam deterministik
(batch 128 vs 256'da `max|logit farkı| = 0`). Sebep ECE'nin **kutulanmış** bir istatistik olması:
3068 örnekten 2'si 15-kutulu bir kenara 1e-4'ten yakın duruyor ve ~1e-6'lık kayan nokta farkı
onları seyrek kutular arasında taşıyor. Bu taban **RAF-DB tohum sd'sinin 0.07 katı** (0.0043),
hiçbir sonucu değiştirmez; yine de logit önbelleği tablolarla bit-birebir kalsın diye CUDA'da
üretilir.

**Duvar saati (RTX 5070, tek GPU):** FERPlus 200 epoch koşusu **eşli 4.71–4.75 h**, **solo 2.79 h**
→ eşli/solo oranı **1.70×** (RAF-DB'de bağımsız olarak 1.69× ölçüldü; oran veri kümesinden değil
GPU paylaşımından gelir). İki koşuyu eşlemek toplam verimi ~%18 artırır, koşu-başına süreyi ~1.7×
uzatır.

> **Gecikme ölçümü hakkında not:** `latency_benchmark.json` **tek** ölçüm oturumu taşır
> (`measured_utc: 2026-07-26T10:20:37Z`, 12 satır). batch=1'de fp16'nın fp32'den yavaş olması
> hem öğrencide (5.413 → 6.519 ms) hem öğretmende (10.460 → 13.971 ms) görülüyor — iki bağımsız
> mimari, ama **tek oturum**. Bağımsız ikinci bir oturumla tekrarlanmadığı için makalede dipnot
> olarak **verilmemelidir**.

---

# 6. FERPlus insan-oyu JSD — sayı tablosu

Öğretmen: `checkpoints/teacher_ferplus_vich_best.pt` (POSTERv2 + VICH head),
config `configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml`, bölme fold [2], **n = 3153**,
kendi doğruluğu **91.37%**.

## 6.1 Üç ölçüt, aynı öğretmen, aynı bölme

| Ölçüt | Neye karşı | En iyi T | O T'deki değer | T=1'deki değer |
|---|---|---|---|---|
| **ECE** (15 kutu) | sert etiket | **0.46** | **0.0084** | 0.1282 |
| **NLL** | sert etiket | **0.50** | **0.2563** | 0.3399 |
| **JSD** | **10-oylayıcı dağılımı** | **0.74** | **0.0440** | 0.0492 |

Farklar: `|T*_JSD − T*_NLL| = 0.24`, `|T*_JSD − T*_ECE| = 0.28`.
JSD'nin ölçekleme ile iyileşmesi: **−0.0052 (−10.5%)**.

JSD tanımı: Jensen-Shannon ıraksaması, **nat** biriminde, örnek başına;
`JSD(p‖q) = ½KL(p‖m) + ½KL(q‖m)`, `m = (p+q)/2`; sınırlı [0, ln2].

## 6.2 Entropi hizalaması

| | ortalama entropi (nat) |
|---|---|
| **insan (10 rater)** | **0.440** |
| öğretmen @ T=1 | 0.612 *(insandan fazla belirsiz)* |
| öğretmen @ T=0.74 (T\*_JSD) | **0.412** *(insana neredeyse oturuyor)* |

## 6.3 Örnek-başına korelasyon (insan entropisi ↔ öğretmen entropisi)

| | Pearson | Spearman |
|---|---|---|
| @ T=1 | **0.724** | **0.732** |
| @ T=0.74 | 0.711 | **0.734** |

Sıralama korelasyonu sıcaklıktan neredeyse bağımsız (0.732 → 0.734) — öğretmenin *hangi
örneklerde* insanların anlaşamadığını bilmesi, ölçeklemeden etkilenmiyor; ölçekleme yalnızca
belirsizliğin *büyüklüğünü* düzeltiyor.

## 6.4 Yorum (BULGULAR B-008 ile aynı)

1. Üç optimumun **hepsi 1.0'ın altında** → yumuşak-hedefle (`ce_kld_loss` + `votes_sum: 10`)
   eğitilen bu öğretmen hem sert etiketlere hem insan oylarına göre **az-güvenli / aşırı yumuşak**.
   %91.4 doğrulukta ECE(T=1)=0.1282 bunun ölçüsü.

   > **Düzeltme (27 Tem):** bu bölümün önceki sürümünde oy toplamı sapmasının nedeni
   > "FERPlus 'unknown'/'NF' oyları önceden atılmış" diye **kesin dille** yazılmıştı. Bu
   > doğrulanamıyor: `unknown`/`NF` sütunları `configs/FERPlus_majority_metadata.csv`'de
   > **yok** ve repoda orijinal FERPlus etiket dosyası da bulunmuyor. Ayrıntı ve doğru ifade
   > §4.4b'de.
2. **Üç ölçüt çakışmıyor:** sert-etiket kalibrasyonu (0.46–0.50) insan dağılımının gerektirdiğinden
   (0.74) ~%60 daha fazla keskinleştiriyor. "Kalibre etmek = insanlarla hizalamak" **yanlış**;
   ilişkili ama ayrı hedefler. Bu ayrımı yalnızca ham oyu olan FER veri kümeleri gösterebilir.
3. Oy normalizasyonu: veri katmanı sabit `votes_sum`'a bölüyor
   (`dataset_utils/image_dataset.py:63-70`) **ama** iki tüketici de satır-bazlı yeniden normalize
   ediyor (`loss_encoder.py:22-26`, `kd_common.py:485-488`), ve sabit-10 + satır-normalizasyon
   doğrudan satır-normalizasyona **birebir eşit**. Yani **eğitimde hata yok**; etkilenen tek şey
   bu analizin ilk sürümüydü (CSV'yi doğrudan okuyup iki katmanı da atlıyordu), düzeltildi.
