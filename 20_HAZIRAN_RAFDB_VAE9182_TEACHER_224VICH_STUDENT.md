# 20 Haziran RAF-DB 91.82 Teacher -> 224 VICH Student Deney Kaydı

Bu dosya, 20 Haziran 2026 tarihinde RAF-DB üzerinde yürütülen **91.82 civarı VAE/KLD POSTERv2 teacher -> 224 çözünürlük MobileNetV2Plus + LightLE + VICH student** deneyini tek başına belgelemek için hazırlanmıştır. Bu belgeyi okumak için `json`, `csv`, `train.log` veya `.bat` dosyası açmaya gerek yoktur; kritik mimari, reçete, sonuç ve yorum bilgileri doğrudan bu dosyanın içindedir.

## Kısa Özet

| Alan | Değer |
|---|---:|
| Tarih | 20 Haziran 2026 |
| Dataset | RAF-DB |
| Sınıf sayısı | 7 |
| Deney adı | `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200` |
| Durum | Devam ediyor |
| Teacher | POSTERv2, VAE/KLD head aktif |
| Teacher sonucu | Yaklaşık 91.82 RAF-DB |
| Student | MobileNetV2Plus + LightLE + VICH |
| Student resolution | 224 x 224 |
| Teacher input resolution | 224 x 224 |
| Parametre | 2.248291M |
| FLOPs | 0.328584384G |
| Ana bulgu | 224 çözünürlükte **90.0587%** accuracy görüldü |
| En iyi epoch | 139 |
| SWA durumu | En iyi sonuç SWA başlamadan önce geldi |
| SWA başlangıcı | epoch 200 |

En önemli sonuç:

```text
Epoch 139
Validation Accuracy: 90.0586702428865%
Validation Loss: 0.34155995368646674
LR: 1.3778523926237795e-05
```

Bu sonuç **SWA ile gelmedi**. Çünkü bu koşuda `swa_start=200`, en iyi sonuç ise epoch 139'da kaydedildi. Bu nedenle 90+ başarısı, geç SWA stratejisiyle beraber normal scheduler aramasının epoch 90-200 arasında devam edebilmesine bağlı görünmektedir.

## Provenance

Bu bölüm yalnızca izlenebilirlik içindir; deneyin anlaşılması için dış dosya açmak gerekmez.

| Alan | Path |
|---|---|
| Run klasörü | `results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200/2026-06-20-08-38-09` |
| Teacher checkpoint | `results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/best.pt` |
| Best checkpoint | `results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200/2026-06-20-08-38-09/best_checkpoint.pth` |
| Best student weights | `results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200/2026-06-20-08-38-09/best_student.pth` |

## Teacher Bilgileri

| Özellik | Değer |
|---|---:|
| Mimari | POSTERv2 |
| Teacher tipi | VAE/KLD head aktif |
| RAF-DB sonucu | Yaklaşık 91.82 |
| Checkpoint | `results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/best.pt` |
| `teacher_vae_head` | `true` |
| `teacher_vich_head` | `false` |
| `teacher_layer_embedding` | `true` |
| `teacher_votes_sum` | `0` |
| `teacher_input_size` | `224` |
| `teacher_vich_use_sampling` | `true`, fakat VICH teacher head kullanılmadığı için pratikte etkisiz |
| `teacher_vich_logvar_min` | `-10.0` |
| `teacher_vich_logvar_max` | `10.0` |
| `teacher_vich_init_logvar_bias` | `-5.0` |

Bu teacher'ın top-1 accuracy değeri CE 92.41 teacher'dan düşük olsa da, öğrenciye aktardığı soft target dağılımı bu MobileNetV2Plus + VICH student için daha faydalı görünmektedir. 224 öğrenci deneylerinde VAE/KLD teacher, CE 92.41 teacher'a göre daha iyi transfer davranışı vermiştir.

## Student Bilgileri

| Özellik | Değer |
|---|---:|
| Model | MobileNetV2Plus |
| Head | VICH |
| Layer embedding | Açık |
| Lightweight Layer Embedding / LightLE | Açık |
| LightLE tap indeksleri | `(13, 17, 18)` |
| Input resolution | `224` |
| Width multiplier | `1.0` |
| Dropout | `0.5` |
| ImageNet pretrained | Açık |
| VICH sampling | Kapalı (`--no-vich-sampling`) |
| Feature adapter | Yok |
| `student_feature_adapter_dim` | `0` |
| Feature dim | `1280` |
| Toplam parametre | `2,248,291` |
| Trainable parametre | `2,248,291` |
| Parametre milyon | `2.248291M` |
| FLOPs | `0.328584384G` |
| State dict boyutu | `8.7071 MB` |
| Backbone yaklaşık parametre | `2,223,954` |
| VICH head parametre | `17,934` |
| LightLE toplam parametre | `6,403` |
| Level embedding params | `3,840` |
| Fusion norm params | `2,560` |
| Fusion weight params | `3` |
| Heavy square projection | Yok |

VICH head parametre hesabı:

```text
2 * (feature_dim * num_classes + num_classes)
= 2 * (1280 * 7 + 7)
= 17,934
```

LightLE tarafında ağır kare projeksiyon yoktur. Bu nedenle model, 224 çözünürlükte düşük FLOPs ve 2.7M altı parametre hedefini rahat biçimde karşılamaktadır.

## Veri Seti ve Split

| Alan | Değer |
|---|---:|
| Dataset | RAF-DB |
| Sınıf sayısı | 7 |
| Train fold | `2` |
| Validation fold | `3` |
| Train fraction | `1.0` |
| Validation fraction | `1.0` |
| Train örnek sayısı | `12,271` |
| Validation örnek sayısı | `3,068` |
| Metadata | `data/rafdb_aligned/metadata_rafdb_poster_var.csv` |
| Aligned image root | `data/rafdb_aligned` |

## Eğitim Reçetesi

| Hiperparametre | Değer |
|---|---:|
| Epoch | `400` |
| Batch size | `64` |
| Workers | `0` |
| Max train batches | `0`, yani tüm train set |
| Max validation batches | `0`, yani tüm validation set |
| Student image size | `224` |
| Teacher image size | `224` |
| Resize size | `0`, yani doğrudan `img_size=224` |
| Augmentation preset | `kd` |
| RandAugment magnitude | `7` |
| Random erasing p | `0.1` |
| Rotation degrees | `12.0` |
| Color jitter | `0.2` |
| Optimizer | AdamW |
| LR | `0.0003` |
| Weight decay | `0.0001` |
| Scheduler | `cosine_warm_restarts` |
| `scheduler_t0` | `10` |
| `scheduler_t_mult` | `2` |
| `min_lr` | `1e-6` |
| `gamma` | `0.98` |
| AMP | Açık |
| Class weighting | `effective_number` |
| Class weight beta | `0.9999` |
| Balanced sampler | Kapalı |
| Seed | `42` |
| SwanLab | Kapalı |

Class-weighted CE için kullanılan sınıf ağırlıkları:

```text
[0.6712, 2.9315, 1.1740, 0.2141, 0.4518, 1.1933, 0.3642]
```

## KD ve Loss Yapısı

Bu koşuda kullanılan ana kayıp yapısı:

```text
L_total = alpha * L_CE + (1 - alpha) * L_KD + beta_vich * L_VICH_KL
```

| Bileşen | Değer |
|---|---:|
| `alpha` | `0.3` |
| KD ağırlığı | `0.7` |
| Temperature | `6.0` |
| Label smoothing | `0.1` |
| Mixup | `0.1` |
| `beta_vich` | `0.0001` |
| `student_vae_kl_beta` | `0.001`, fakat student VAE head kullanmıyor |
| Feature distillation | Kapalı |
| `feature_distill_weight` | `0.0` |
| `feature_distill_mode` | `mse_cosine`, fakat weight 0 olduğu için etkisiz |

Bu koşudaki damıtma yapısı klasik hard-label CE + temperature KD birleşimidir. Ek olarak student VICH head'in ürettiği logvar/mu yapısından gelen düşük ağırlıklı `VICH_KL` yardımcı kaybı vardır. Feature distillation bu koşuda kapalıdır; bu nedenle 90.0587 sonucu yalnızca logit KD + hard supervision + VICH auxiliary regularization ile elde edilmiştir.

## Önceki 200 Epoch Referansı

Aynı teacher ve aynı 224 VICH student için önceki 200 epoch koşusu:

```text
Run: RAFDB_vae9182_betaKD_b070_T6_224_amp_classw
Epoch: 200
SWA start: 90
```

| Metrik | Değer |
|---|---:|
| Best checkpoint accuracy | `89.63494132985659` |
| Best checkpoint epoch | `65` |
| Best macro-F1 | `84.12177138672502` |
| Best weighted-F1 | `89.54375504945492` |
| SWA accuracy | `89.70013037809647` |
| SWA epoch | `200` |
| SWA macro-F1 | `84.07599778836955` |
| SWA weighted-F1 | `89.6028130536006` |
| Params | `2.248291M` |
| FLOPs | `0.328584384G` |

Önceki 200 epoch koşusunda best checkpoint erken gelmişti: epoch 65. SWA ise epoch 90'da başlıyordu. Bu durum, normal scheduler aramasının epoch 90'dan sonra SWA scheduler'a devredilmesine yol açmış olabilir.

## 400 Epoch Koşusu: Best-So-Far Sonuç

Mevcut 400 epoch koşusunda şu ana kadarki en iyi sonuç:

| Alan | Değer |
|---|---:|
| Best accuracy | `90.0586702428865` |
| Best epoch | `139` |
| Train loss | `0.5435811413421519` |
| Hard loss | `1.4408719620080188` |
| Soft loss | `0.15718866420102076` |
| AuxKL loss | `12.874681543501458` |
| Feature loss | `0.0` |
| Train accuracy | `93.12199493562395` |
| Validation loss | `0.34155995368646674` |
| Validation accuracy | `90.0586702428865` |
| Epoch süresi | `62.54025745391846` saniye |
| LR | `1.3778523926237795e-05` |

Log satırının özetlenmiş hali:

```text
Epoch 139: Train Loss=0.5436, Hard=1.4409, Soft=0.1572, AuxKL=12.8747,
Feat=0.0000, Train Acc=93.12%, Val Loss=0.3416, Val Acc=90.06%
Saved best student (90.06%) at epoch 139
```

Bu sonuç SWA'dan önce gelmiştir:

```text
swa_start = 200
best_epoch = 139
```

Bu nedenle 90+ sonucu, SWA ortalamasından değil, normal model checkpoint'inden gelmektedir.

## Güncel Koşu Durumu

Bu belge hazırlanırken koşu devam ediyordu. Son görülen epoch:

| Alan | Epoch 155 | Epoch 157, en güncel görülen |
|---|---:|---:|
| Train loss | `0.5896155745696928` | `0.5910054402473396` |
| Hard loss | `1.4699872337453532` | `1.4645579580125614` |
| Soft loss | `0.21051640133045188` | `0.2148292969446895` |
| AuxKL loss | `12.579067931704879` | `12.57532735632933` |
| Feature loss | `0.0` | `0.0` |
| Train accuracy | `92.33151330544521` | `92.0625865626341` |
| Validation loss | `0.41374607627052995` | `0.42499260509185094` |
| Validation accuracy | `86.86440682939632` | `87.0599740238513` |
| Epoch süresi | `62.49966835975647` saniye | `67.97901272773743` saniye |
| LR | `0.00029927770900082954` | `0.00029858540106653656` |

Epoch 151 sonrasında validation accuracy belirgin düştü. Bunun nedeni büyük olasılıkla cosine warm restart döngüsünün yeniden yüksek LR bölgesine geçmesidir. Best checkpoint epoch 139'da kaydedildiği için bu düşüş en iyi ağırlıkları kaybettirmemiştir.

## En İyi Epoch Tablosu

| Sıra | Epoch | Val Acc | Val Loss | Train Acc | LR |
|---:|---:|---:|---:|---:|---:|
| 1 | 139 | `90.0586702428865` | `0.34155995368646674` | `93.12199493562395` | `1.3778523926237795e-05` |
| 2 | 141 | `89.83050847457628` | `0.3412658012286314` | `93.61910192405533` | `9.271299611627374e-06` |
| 3 | 134 | `89.79791404992692` | `0.34126302125867375` | `93.35832447570846` | `2.8647450843757897e-05` |
| 4 | 148 | `89.79791395045632` | `0.33999172272707057` | `93.77393854250195` | `4.623999400308054e-07` |
| 5 | 143 | `89.79791395045632` | `0.33856122605648314` | `93.52131037742795` | `5.631714531952924e-06` |
| 6 | 144 | `89.76531942633638` | `0.33994478966453084` | `94.36068778247474` | `4.144511940348516e-06` |
| 7 | 126 | `89.73272500168702` | `0.3530329936797181` | `93.62725121914131` | `6.183221215612904e-05` |
| 8 | 146 | `89.73272490221643` | `0.34002373481200915` | `93.93692443800404` | `1.8467489107293509e-06` |
| 9 | 147 | `89.73272490221643` | `0.34079545705228304` | `94.40143426412203` | `1.0397314567610559e-06` |
| 10 | 133 | `89.70013047756707` | `0.34120058139113435` | `93.8309835962907` | `3.2202460367888255e-05` |

Bu tablo, 90+ sonucunun tekil bir SWA çıktısı olmadığını, scheduler'ın düşük LR bölgesindeki normal checkpoint başarısı olduğunu gösteriyor. Epoch 126-148 bandında birçok değer 89.70 ve üzerindedir; epoch 139 ise 90.0587 ile zirve olmuştur.

## 200 Epoch ve 400 Epoch Reçete Farkı

Ana mimari, teacher, student, KD parametreleri ve augmentasyon aynıdır. Eğitim davranışını değiştiren kritik farklar:

| Alan | 200 epoch koşusu | 400 epoch koşusu |
|---|---:|---:|
| Epoch | `200` | `400` |
| SWA start | `90` | `200` |
| Feature distillation | Yok / eski argümanda yok | `0.0`, yani kapalı |
| Teacher | VAE/KLD 91.82 | VAE/KLD 91.82 |
| Student | 224 VICH + LightLE | 224 VICH + LightLE |
| Alpha | `0.3` | `0.3` |
| Temperature | `6.0` | `6.0` |
| Mixup | `0.1` | `0.1` |
| Label smoothing | `0.1` | `0.1` |
| Class weight | `effective_number` | `effective_number` |

Önemli yorum:

```text
90+ başarısının sebebi sadece "400 epoch" olmayabilir.
Daha güçlü ihtimal: 200 epoch koşusunda SWA epoch 90'da erken devreye girdiği için
normal cosine warm restart araması erken kesildi. 400 epoch koşusunda SWA 200'e
ertelendiği için model epoch 90-200 arasında aramaya devam etti ve epoch 139'da
90.0587 gördü.
```

Bu nedenle ileride daha temiz ve daha kısa bir reçete olarak şu varyant ayrıca denenebilir:

```text
VAE9182 teacher
224 VICH + LightLE student
epochs: 200 veya 250
swa: kapalı veya swa_start: 180/200
diğer hiperparametreler aynı
```

## Neden VAE/KLD Teacher Daha İyi Görünüyor?

CE 92.41 teacher'ın top-1 doğruluğu daha yüksek olsa da, bu student için daha iyi transfer veren teacher VAE/KLD 91.82 oldu. Muhtemel teknik nedenler:

1. VAE/KLD teacher daha yumuşak ve belirsizlik içeren logit dağılımları üretiyor olabilir.
2. Küçük MobileNetV2Plus student, yüksek güvenli CE teacher logits yerine daha bilgi taşıyan soft target dağılımlarından daha iyi öğreniyor olabilir.
3. RAF-DB'de sınıf dengesizliği olduğu için, teacher'ın yalnızca doğru sınıfı baskılaması değil, sınıflar arası ilişkileri taşıması da önemli.
4. VICH student probabilistic head kullandığı için, VAE/KLD teacher'ın belirsizlik davranışı student head karakteriyle daha uyumlu olabilir.
5. CE teacher 92.41 daha iyi teacher olsa bile, "iyi teacher" ile "iyi distillation teacher" aynı şey olmayabilir.

Bu deneyin ana çıkarımı:

```text
Teacher top-1 accuracy tek başına öğrenci başarısını açıklamıyor.
VAE/KLD teacher, 224 VICH student için daha faydalı distillation sinyali sağlıyor.
```

## Yeniden Üretim Komutu

Aşağıdaki komut, bu koşuyu başlatan `.bat` dosyasının tam içeriğidir. Bu blok sayesinde komutu yeniden üretmek için ayrıca `.bat` veya `json` dosyası açmak gerekmez.

```bat
@echo off
cd /d "%~dp0"

python train_rafdb_kd.py ^
  --teacher-ckpt "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt" ^
  --teacher-vae-head ^
  --teacher-layer-embedding ^
  --teacher-input-size 224 ^
  --aligned-dir "data\rafdb_aligned" ^
  --metadata "data\rafdb_aligned\metadata_rafdb_poster_var.csv" ^
  --name RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200 ^
  --save-root "results\unified_students" ^
  --epochs 400 ^
  --batch-size 64 ^
  --workers 0 ^
  --img-size 224 ^
  --resize-size 0 ^
  --augment-preset kd ^
  --student-head-type vich ^
  --student-layer-embedding ^
  --student-lightweight-layer-embedding ^
  --student-layer-embedding-layers 3 ^
  --no-vich-sampling ^
  --alpha 0.3 ^
  --temperature 6 ^
  --label-smoothing 0.1 ^
  --mixup 0.1 ^
  --use-amp ^
  --class-weight-mode effective_number ^
  --class-weight-beta 0.9999 ^
  --scheduler-name cosine_warm_restarts ^
  --min-lr 1e-6 ^
  --gamma 0.98 ^
  --scheduler-t0 10 ^
  --scheduler-t-mult 2 ^
  --swa ^
  --swa-start 200 ^
  --swa-lr 0.0001

pause
```

## Kısa Sonuç

Bu deney, RAF-DB üzerinde 224 çözünürlükte çalışan hafif bir MobileNetV2Plus + LightLE + VICH student için çok değerli bir sonuç verdi:

```text
90.0587% accuracy
2.248291M params
0.328584384G FLOPs
224 x 224 input
```

Bu sonuç, 256 çözünürlüklü modellerden daha düşük hesaplama maliyetiyle 90 barajını geçebilen bir öğrenci adayı sunduğu için özellikle edge/VR kullanım senaryosu açısından güçlüdür.

Bu koşuda kritik iyileştirici faktör büyük olasılıkla:

```text
VAE/KLD teacher + 224 VICH student + SWA'nın geç başlatılması
```

400 epoch koşusu tamamlandığında SWA ve final checkpoint sonuçları ayrıca aynı dosyaya eklenebilir; ancak şu anki best checkpoint değeri zaten 90+ barajını geçmiştir.
