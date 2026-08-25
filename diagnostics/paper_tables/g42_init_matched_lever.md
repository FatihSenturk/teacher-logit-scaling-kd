# G4.2 — kaldıraç oranı, başlatma eşleştirilmiş

> **Ön-beyanlı sonuç.** `PREREGISTRATIONS.md` A13 (commit `b71e6ad`, etiket `a12-a13-predeclared`): *"oran hangi yöne giderse gitsin raporlanacak; mevcut confound'lu oran duyarlılık olarak kalır, silinmez."*

**SONUÇ: @swa: 76× -> 69× (AŞAĞI, 7.0 birim)**

## Sorun neydi

Yayımlanan oran iki açıklığın bölümü — sıcaklık ekseni ÷ kapasite ekseni — ama iki kol aynı başlatmadan gelmiyordu: **kapasite kolu scratch, sıcaklık kolu ön-eğitimli** (panel R1-W7). A13'ün dört koşusu sıcaklık kolunun scratch hâlini üretti; aşağıdaki ikinci sütun onunla hesaplandı. Payda (kapasite açıklığı) iki sütunda da **aynı**, yani fark yalnız sıcaklık kolunun başlatmasından geliyor.

| ckpt | kapasite açıklığı (ortak payda) | sıcaklık açıklığı — ön-eğitimli | oran (yayımlanan) | sıcaklık açıklığı — **scratch** | oran (**başlatma-eşleştirilmiş**) |
|---|---|---|---|---|---|
| @swa | 0.00235 | 0.1780 | 76× | 0.1615 | **69×** |
| @best | 0.00254 | 0.2010 | 79× | 0.1900 | **75×** |
| @last | 0.00743 | 0.1975 | 27× | 0.1959 | **26×** |

@swa birincil (A13'ün birincil kontrol noktasıyla aynı); best/last duyarlılık.

Paylaşılan sıcaklık desteği: T=1, T=1.7, T=2.2 — yayımlanan açıklık da tam bu üç nokta üzerinde ölçülmüştü (varsayılmadı, `RESULTS_TABLES.json`'dan okunup doğrulandı).

sd konvansiyonu: sample sd (n-1, Bessel-corrected), computed over seeds

## Ne değişti, ne değişmedi

**Değişen:** oranın büyüklüğü. **Değişmeyen:** yönü ve mertebesi — sıcaklık ekseni kapasite ekseninden hâlâ iki mertebe geniş. Yani *"yasa öğretmen tarafında yaşıyor"* cümlesi ayakta, ama sayısı başlatma-eşleştirilmiş hâliyle yazılmalı.

> **Confound'lu oran silinmedi.** Yukarıdaki tabloda kendi sütununda duruyor; hangi sayının hangi karşılaştırmadan geldiği okunabilir olmalı.

---

Üretici: `diagnostics/g42_init_matched_lever.py` · veri: `selection_audit_unfrozen.csv` (donmuş dosya okunmadı) + `paper_tables/RESULTS_TABLES.json` · kol: A13'ün 2.248 M scratch doz-yanıtı

