# Bölme kimliği — hangi ad, hangi bölme, kaç örnek

Üretici: `diagnostics/split_identity.py` · ölçüm, beyan değil. Bu tablo bir adın DOĞRU olup olmadığını söyler; hangi adın kullanılacağı makale tarafının kararıdır.

> **Level-1 / lisans.** RAF-DB meta CSV'si görüntü adı taşır ve yayımlanamaz; varsayılan yol yayımlanmış SAYIM dosyasını okur (`diagnostics/split_identity/rafdb_fold_class_counts.json`, yalnız fold × etiket sayıları). CSV'yi okumak açık bir eylemdir: `--from-data`.

## Tek denklem

| veri kümesi | eğitim fold | raporlanan fold | raporlanan bölüm | n (eğitim) | n (raporlanan) | meta'da bölüm sayısı | ayrı held-out | seçim = raporlama |
|---|---|---|---|---|---|---|---|---|
| RAF-DB | [2] | [3] | `test` | 12271 | **3068** | 2 | yok | EVET |
| FERPlus | [0, 1] | [2] | `FER2013Test` | 28259 | **3153** | 3 | VAR | EVET |

## RAF-DB — raporlanan fold gerçekten resmî test bölümü mü?

Raporlanan fold (3) **3068** satır taşıyor ve satırların yol öneki dağılımı: `{'test': 3068}`. Tek önek: **evet** — yani fold 3 tam olarak `test/` bölümüdür, karışım değil.

Sınıf dağılımı, RAF-DB'nin yayımlanmış test dağılımıyla karşılaştırıldı:

| sınıf | ölçülen | yayımlanmış |
|---|---|---|
| Surprise | 329 | 329 |
| Fear | 74 | 74 |
| Disgust | 160 | 160 |
| Happiness | 1185 | 1185 |
| Sadness | 478 | 478 |
| Anger | 162 | 162 |
| Neutral | 680 | 680 |

**Birebir eşleşme: EVET.** Meta dosyasında yalnız 2 bölüm var (fold 2: 12271, fold 3: 3068), yani RAF-DB tarafında ayrı bir held-out bölme **yoktur**; resmî test bölümü hem epoch-başı doğrulama hem raporlama için kullanılır.

## FERPlus — ayrı bir held-out VARDI ve eğitime verildi

Meta dosyasında **3** bölüm var: fold 0 = 25060 (`FER2013Train`) · fold 1 = 3199 (`FER2013Valid`) · fold 2 = 3153 (`FER2013Test`).

Eğitim `train_folds: [0, 1]` (28259 satır), raporlama `val_folds: [2]` (**3153** satır). Yani FERPlus'ın üçüncü bölmesi (PublicTest) **eğitime** katılmıştır; RAF-DB'de olmayan bir seçenek burada vardı ve harcandı. Bu bir kusur beyanı değil, bir yordam olgusudur — ama "ayrı held-out yok" cümlesi FERPlus için veri kümesinin değil **yordamın** sonucudur.

Eğitim betiğinin sert beyanı: `expected_train_samples=28259` · `expected_val_samples=3153`. Ölçümle uyum: **EVET**.

Çoğunluk süzgecinin düşürdüğü satırlar (ham FERPlus → çoğunluk meta):

| fold | ham | çoğunluk | düşen |
|---|---|---|---|
| 0 | 28559 | 25060 | 3499 |
| 1 | 3579 | 3199 | 380 |
| 2 | 3573 | 3153 | 420 |

