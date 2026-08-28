# A12 — gerçek-sinyal gate hücreleri n=3

> **ÖN-BEYANLI.** `PREREGISTRATIONS.md` A12, commit `b71e6ad`, etiket `a12-a13-predeclared` — ölçüt, üç tahmin ve üç cümle-sonucu koşulardan önce donduruldu. Bu betik de ilk sonuç okunmadan commit'lendi.

**HÜKÜM: HİÇBİR HÜCRE ÖLÇÜTÜ KARŞILAMADI — cümle 'başarısız'dan 'n=3'te kurulamadı'ya çevrilir**

## Donmuş kural

n/n tohumda aynı işaret **VE** |ortalama eşleştirilmiş fark| ≥ 2 × o kolun **kendi** `cw=none` kontrolünün **aynı metrikteki** tohum sd'si. İki eksen (ΔECE, Δdoğruluk) ayrı ayrı, her biri kendi paydasıyla. Hüküm `criterion_applied.verdict`'ten, eşleştirme `p5_oracle_replication_verdict`'ten **ithal** — yeniden yazılmadı.

sd konvansiyonu: sample sd (n-1, Bessel-corrected), computed over seeds

**ÇÖZÜNMEDİ ≠ etkisiz.** Bar tek bir kolun tohum gürültüsünün iki katı; altında kalan bir etki *ölçülemedi*, *yok gösterilmedi*.

## Paydalar — sonuçtan önce donduruldu

| öğretmen | n | ECE sd ölçülen | donmuş | ✓ | doğruluk sd ölçülen | donmuş | ✓ |
|---|---|---|---|---|---|---|---|
| stage1 | 3 | 0.00211 | 0.00211 | ✅ | 0.0996 | 0.0996 | ✅ |
| primary | 3 | 0.00333 | 0.00333 | ✅ | 0.3943 | 0.3943 | ✅ |
| vae9182 | 3 | 0.00270 | 0.00270 | ✅ | 0.2070 | 0.2070 | ✅ |

Kontrol kolları A12'den etkilenmiyor (P5 için koşulmuştu), o yüzden payda A12'nin tek bir sonucu görülmeden ölçülebildi. Uyuşmazlık olursa donmuş değer kullanılır ve fark burada görünür.

## Hücreler (@swa birincil)

| öğretmen | sinyal | AUROC | n | ΔECE ort | işaret | oran | hüküm | Δdoğruluk ort (pp) | işaret | oran | hüküm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| stage1 | `mean_logvar` | 0.43 | 3 | -0.0012 | `+--` | 0.55× | ÇÖZÜNMEDİ | -0.10 | `---` | 0.98× | ÇÖZÜNMEDİ |
| stage1 | `target_logvar` | 0.70 | 3 | -0.0041 | `---` | 1.97× | ÇÖZÜNMEDİ | +0.25 | `++-` | 2.51× | ÇÖZÜNMEDİ |
| primary | `mean_logvar` | 0.44 | 3 | -0.0056 | `--+` | 1.67× | ÇÖZÜNMEDİ | +0.20 | `++-` | 0.50× | ÇÖZÜNMEDİ |
| primary | `target_logvar` | 0.84 | 3 | -0.0008 | `+--` | 0.24× | ÇÖZÜNMEDİ | -0.09 | `-+-` | 0.22× | ÇÖZÜNMEDİ |
| vae9182 | `mean_logvar` | 0.17 | 3 | +0.0015 | `+--` | 0.55× | ÇÖZÜNMEDİ | -0.27 | `-++` | 1.31× | ÇÖZÜNMEDİ |

AUROC: o sinyalin o öğretmendeki ölçülmüş ayırt etme gücü (`rafdb_signal_quality_table`). `mean_logvar` için stage1/primary değerleri bu tabloda ayrıca raporlanmıştır; buraya yalnız beyanda tahmine dayanak yapılanlar yazıldı.

## Çıkış kontrolü

| kalem | sayı |
|---|---|
| beklenen yeni koşu | 10 |
| diskte olmayan | 0 |
| birden çok denemesi olan koşu (çökme izi) | 0 |
| elenen yarım deneme (metrics_swa.json yok) | 0 |
| ad→parametre uyuşmazlığı | 0 |

> Yarıda kalan koşu **devam ettirilmez**, temiz yeniden başlar: kesilip devam eden bir koşu optimizer durumu ve veri sırası bakımından temiz koşuyla aynı değildir ve aynı-tarif karşılaştırılabilirliğini bozar. Elenen her deneme kaç epoch'ta öldüğüyle yukarıda görünür — sessizce atılmaz.

## Duyarlılık: best / last

| öğretmen | sinyal | ckpt | ΔECE ort | işaret | oran | hüküm |
|---|---|---|---|---|---|---|
| stage1 | `mean_logvar` | best | +0.0024 | `+++` | 1.15× | ÇÖZÜNMEDİ |
| stage1 | `mean_logvar` | last | +0.0023 | `-++` | 1.10× | ÇÖZÜNMEDİ |
| stage1 | `target_logvar` | best | +0.0004 | `-++` | 0.21× | ÇÖZÜNMEDİ |
| stage1 | `target_logvar` | last | -0.0006 | `+--` | 0.27× | ÇÖZÜNMEDİ |
| primary | `mean_logvar` | best | -0.0075 | `---` | 2.25× | KURULU |
| primary | `mean_logvar` | last | -0.0030 | `+--` | 0.89× | ÇÖZÜNMEDİ |
| primary | `target_logvar` | best | -0.0064 | `---` | 1.91× | ÇÖZÜNMEDİ |
| primary | `target_logvar` | last | -0.0042 | `---` | 1.26× | ÇÖZÜNMEDİ |
| vae9182 | `mean_logvar` | best | +0.0050 | `+-+` | 1.84× | ÇÖZÜNMEDİ |
| vae9182 | `mean_logvar` | last | +0.0016 | `+-+` | 0.58× | ÇÖZÜNMEDİ |

@best 3068 görüntüde argmax val-acc ile seçilir, yani seçim iyimserliği taşır; birincil hüküm @swa'dadır.

---

Üretici: `diagnostics/a12_realsignal_verdict.py` · veri: `diagnostics/selection_audit/selection_audit_unfrozen.csv` · kuyruk: `rafdb_a12_realsignal_gate_queue.ps1` (üretilmiş, elle yazılmamış — üretim raporu `diagnostics/replicate_queue_build.md`)

