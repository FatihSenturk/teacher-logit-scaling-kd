# G4.1 — yön asimetrisi: estimand, altı karşılaştırma, bootstrap CI

> **Panel G4.1 / DA-5.** *"Mutlak oran"* ile *"optimum üstü fazla zarar"* aynı veriden farklı büyüklükte sayı üretir. Hangi tanımın kullanıldığı cümlede **yazılmalı**; bu tablo ikisini de veriyor.

@swa · sample sd (n-1, Bessel-corrected), computed over seeds · asimetri fonksiyonu `two_dataset_overlay.branch_asymmetry`'den **ithal**

## İki estimand

| # | tanım | formül | altı karşılaştırma ortalaması |
|---|---|---|---|
| **A** | mutlak oran | `ECE_over / ECE_under` | **1.74×** (sd 0.43) |
| **B** | optimum üstü fazla zarar | `(ECE_over − ECE_min) / (ECE_under − ECE_min)` | **7.51×** (sd 8.16) |

> **Tanım seçimi sayıyı 4.3× oynatıyor** — DA-5'in "bir mertebe fark" uyarısı doğrulandı. Sebebi mekanik: (A) iki kola da ortak olan tabanı pay ve paydada birlikte taşır, o yüzden oranı 1'e doğru sıkıştırır; (B) tabanı çıkarınca geriye yalnız müdahalenin kendi zararı kalır.

> **AMA BU BİR TERCİH MESELESİ DEĞİL: (B) bu veride KULLANILAMAZ.** Ölçüldü, iki sebeple:

> 1. **Altı karşılaştırmanın üçünde TANIMSIZ.** (B)'nin paydası `ECE_under − ECE_min`; negatif dala fit edilen değer kolun kendi tabanının altına düştüğünde payda ≤ 0 oluyor ve oran tanımsız kalıyor. Bu tam olarak ekstrapolasyon bölgesinde gerçekleşiyor.
> 2. **Tanımlı olduğu yerde de kararsız.** Payda sıfıra yaklaştığı için bootstrap aralıkları iki mertebe yayılıyor (bir hücrede `[1.05, 543]`). Böyle bir aralık hiçbir iddiayı taşıyamaz.

> **Sonuç: (A) kullanılmalı ve cümlede (A) olduğu YAZILMALI.** Metin şu an (A)'yı kullanıyor ama hangisi olduğunu söylemiyor; eklenmesi gereken tek şey bu. (B)'nin sayıları burada kayda geçiyor ki "denenmedi" denmesin — denendi, veri taşımadı.

## Eşleştirme / interpolasyon prosedürü (metne birebir)

Her karşılaştırma **tek bir kol içinde** yapılır: öğretmen, veri kümesi, tarif ve tohum kümesi sabit tutulur; değişen tek şey enjekte edilen miskalibrasyonun **işaretidir**. Kolun negatif dalına (under-confident noktalar) en küçük kareler doğrusu geçirilir, `ECE = a + b·|gap|`. Her pozitif-gap noktası için aynı `|gap|`'te bu doğrudan bir değer okunur ve oran alınır. `|gap|` negatif dalın gözlenen aralığının dışındaysa nokta **ekstrapole** işaretlenir ve birincil özete girmez.

## Altı karşılaştırmanın tamamı

| kol | \|gap\| | T | ECE over | ECE under (fit) | **A: mutlak** | A %95 CI | **B: fazla zarar** | B %95 CI | ekstrapole |
|---|---|---|---|---|---|---|---|---|---|
| rafdb_stage1 | 0.0040 | 1.3406 | 0.0428 | 0.0190 | **2.25×** | [1.41, 4.53] | **tanımsız** | [0.00, 1.39] | evet |
| rafdb_stage1 | 0.0338 | 1 | 0.0731 | 0.0388 | **1.88×** | [1.55, 2.38] | **tanımsız** | [1.05, 543.47] | evet |
| rafdb_stage1 | 0.0431 | 0.85 | 0.0797 | 0.0450 | **1.77×** | [1.50, 2.13] | 16.84× | [3.78, 154.18] | hayır |
| rafdb_vae9182 | 0.0042 | 1 | 0.0330 | 0.0248 | **1.33×** | [0.89, 2.19] | **tanımsız** | [0.00, 0.00] | evet |
| rafdb_vae9182 | 0.0248 | 0.85 | 0.0447 | 0.0397 | **1.13×** | [0.90, 1.46] | 1.75× | [0.64, 9.74] | evet |
| ferplus | 0.0393 | 0.26 | 0.0587 | 0.0287 | **2.04×** | [1.64, 2.48] | 3.93× | [2.81, 5.30] | hayır |

Bootstrap: 20,000 yineleme, tohum 20260807, %95 yüzdelik aralık.

## Özet — ve iki-karşılaştırma alt kümesi duyarlılık olarak KALIYOR

| küme | n | A: mutlak | B: fazla zarar | hepsi > 1 |
|---|---|---|---|---|
| **altısı** | 6 | **1.74× ± 0.43** | **7.51× ± 8.16** | ✅ |
| ekstrapolasyonsuz (metnin kullandığı) | 2 | 1.91× ± 0.19 | 10.39× ± 9.13 | ✅ |

> **"1.91 ± 0.19" bir güven aralığı değildi** — iki sayının örneklem sd'siydi ve n=2'de bu istatistik neredeyse hiçbir şey söylemez. Yukarıdaki CI'lar hücre-ortalaması belirsizliğini yayıyor ve alt küme yerine **altı karşılaştırmanın tamamı** birincil yapılabilir hâle geliyor; ekstrapolasyona dayanan dördü ayrı işaretli olduğu için okur hangisinin neye dayandığını görüyor.

## Bootstrap'in sınırı — açıkça

Kaynak artefakt (`two_dataset_overlay.json`) hücre başına `mean`/`sd`/`n` taşıyor, **tohum başına değer taşımıyor**. Bu yüzden yapılan şey PARAMETRİK bootstrap: her hücre ortalaması `mean + t(df=n−1)·sd/√n` ile yeniden çekiliyor, negatif dal yeniden fit ediliyor, oran yeniden hesaplanıyor. n=3'te normal yerine t kullanıldı — normal aralığı dar gösterirdi.

**Tohum-düzeyi küme bootstrap'i tercih edilirdi** ve ucuz: `two_dataset_overlay.json`'a nokta başına tohum-başına ECE listesi eklemek yeterli. Yapılmadı, çünkü o artefakt T4'ü besliyor ve bu turda şemasını değiştirmek tablo kapısını gereksiz yere hareket ettirirdi. Öneri olarak kayda geçiyor.

---

Üretici: `diagnostics/asymmetry_estimand.py` · kaynak: `diagnostics/p1_dose_response/two_dataset_overlay.json` · asimetri fonksiyonu `diagnostics/two_dataset_overlay.py::branch_asymmetry` (ithal)

