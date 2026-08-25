# G4.5 — gürültü birimleri: dokuz hücre + hücre-başına eşleştirilmiş-fark sd'si

> **Panel G4.5.** Metnin *"typically 77 / never below 55"* cümlesi denetlenebilir olsun diye dokuz hücrenin tamamı ve üç özet istatistik yan yana basılıyor. **"Typically" bir istatistik değildir** — medyan ve ortalama farklı sayı verir; hangisinin kastedildiği metinde YAZILMALI.

sample sd (n-1, Bessel-corrected), computed over seeds · mekanizma: `logit_std` · payda `denominator_table.control_arms`'tan, eşleştirme `t5_pairing_diff.build(rule="new")`'den **ithal**

## Gürültü birimi tanımı

Bir hücrenin etkisi, o kolun **kendi** kontrolünün **aynı metrikteki** tohum sd'sine bölünür. Raporlanan oran:

```
  (|ΔECE| / σ_ECE)  ÷  (|Δdoğruluk| / σ_acc)
```

İki eksen farklı birimde olduğu için ortak ölçeğe indirmenin başka yolu yok. **σ her checkpoint için ayrı ölçülür** — kontrol kolunun tohum yayılımı @swa ile @best'te aynı değildir.

## Üç özet istatistik — hangisinin "typically" olduğu metinde seçilsin

| istatistik | değer |
|---|---|
| **medyan** | **27.3×** |
| **ortalama** | **51.7×** |
| minimum | **2.6×** |
| maksimum | 213.0× |
| hücre | 9 |

> Medyan ile ortalama arasında 24.3× fark var — bu tam olarak "typically" kelimesinin belirsiz bıraktığı fark. Minimum iddiası (**2.6×**) ise tek bir hücreye dayanıyor ve o hücre aşağıda adıyla görünüyor.

## Aynı hesap, HAVUZ paydasıyla — metnin "77"si buradan geliyor

T5a havuz paydası kullanıyor (üç öğretmenin kontrol sd'lerinin ortalaması), yukarıdaki tablo ise her kolun KENDİ paydasını. İkisi farklı sayı verir; hangisinin kullanıldığı cümlede yazılmalı.

| checkpoint | stage1 | primary | vae9182 | medyan | **ortalama** | min |
|---|---|---|---|---|---|---|
| swa | 47.6× | 32.7× | 139.1× | 47.6× | **73.1×** | 32.7× |
| best | 13.8× | 9.5× | 10.5× | 10.5× | **11.2×** | 9.5× |
| last | 10.3× | 18.9× | 13.6× | 13.6× | **14.3×** | 10.3× |

> **"Typically" = ORTALAMA, ve yalnız @swa.** Havuz paydasıyla @swa ortalaması **73.1×** — metnin *77*'sine en yakın sayı bu. Medyan aynı satırda 47.6×, yani kelime seçimi sayıyı 26× oynatıyor.
> **Ama *"never below 55"* HİÇBİR KONVANSİYONDA TUTMUYOR.** Havuz paydasıyla @swa minimumu **32.7×** (primary), kendi paydasıyla dokuz hücrenin minimumu **2.6×**. Taban iddiası ya kaldırılmalı ya da ölçülen sayıyla değiştirilmeli.

## Dokuz hücre (checkpoint × öğretmen)

| checkpoint | öğretmen | n | ΔECE | σ_ECE | ECE birimi | Δacc (pp) | σ_acc | acc birimi | **oran** |
|---|---|---|---|---|---|---|---|---|---|
| swa | stage1 | 3 | +0.0906 | 0.0012 | 76.6 | -0.228 | 0.3403 | 0.7 | **114.3×** |
| swa | primary | 3 | +0.0859 | 0.0015 | 56.7 | -0.315 | 0.1304 | 2.4 | **23.5×** |
| swa | vae9182 | 3 | +0.1388 | 0.0020 | 69.5 | -0.120 | 0.3664 | 0.3 | **213.0×** |
| best | stage1 | 3 | +0.1252 | 0.0054 | 23.3 | -0.315 | 0.0820 | 3.8 | **6.1×** |
| best | primary | 3 | +0.1191 | 0.0085 | 14.0 | -0.435 | 0.0862 | 5.0 | **2.8×** |
| best | vae9182 | 3 | +0.1573 | 0.0021 | 74.7 | -0.522 | 0.1910 | 2.7 | **27.3×** |
| last | stage1 | 3 | +0.1090 | 0.0081 | 13.4 | -0.522 | 0.0996 | 5.2 | **2.6×** |
| last | primary | 3 | +0.1044 | 0.0031 | 33.9 | -0.272 | 0.2587 | 1.0 | **32.3×** |
| last | vae9182 | 3 | +0.1593 | 0.0011 | 148.6 | -0.576 | 0.1673 | 3.4 | **43.2×** |

> **Oranın büyük olması, doğruluk etkisinin küçük olmasından da gelebilir.** Payda `|Δdoğruluk| / σ_acc`; doğruluk etkisi gürültünün içinde kaldığında bu sayı küçülür ve oran şişer. O yüzden iki bileşen de ayrı sütun olarak basılıyor — oran tek başına okunmamalı.

## Hücre-başına eşleştirilmiş-fark sd'si (tüm mekanizma hücreleri, İKİ EKSEN)

| öğretmen | mekanizma | cw | n@swa · ΔECE sd · Δacc sd | n@best · ΔECE sd · Δacc sd | n@last · ΔECE sd · Δacc sd |
|---|---|---|---|---|---|
| primary | `adaptive_t` | effective_number | 3 · 0.0007 · 0.370 | 3 · 0.0034 · 0.100 | 3 · 0.0040 · 0.433 |
| primary | `ctkd` | effective_number | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 |
| primary | `g2g_kl` | effective_number | 3 · 0.0027 · 0.363 | 3 · 0.0060 · 0.198 | 3 · 0.0022 · 0.222 |
| primary | `gate:mean_logvar` | none | 3 · 0.0092 · 0.855 | 3 · 0.0057 · 0.466 | 3 · 0.0055 · 0.473 |
| primary | `gate:oracle_error` | none | 3 · 0.0053 · 0.722 | 3 · 0.0041 · 0.488 | 3 · 0.0040 · 0.420 |
| primary | `gate:target_logvar` | none | 3 · 0.0030 · 0.443 | 3 · 0.0023 · 0.333 | 3 · 0.0036 · 0.530 |
| primary | `logit_std` | effective_number | 3 · 0.0058 · 0.249 | 3 · 0.0113 · 0.132 | 3 · 0.0068 · 0.271 |
| stage1 | `adaptive_t` | effective_number | 3 · 0.0033 · 0.321 | 3 · 0.0033 · 0.217 | 3 · 0.0050 · 0.147 |
| stage1 | `ctkd` | effective_number | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 |
| stage1 | `g2g_kl` | effective_number | 3 · 0.0004 · 0.378 | 3 · 0.0051 · 0.450 | 3 · 0.0063 · 0.603 |
| stage1 | `gate:mean_logvar` | none | 3 · 0.0010 · 0.118 | 3 · 0.0039 · 0.105 | 3 · 0.0028 · 0.401 |
| stage1 | `gate:oracle_error` | none | 3 · 0.0036 · 0.457 | 3 · 0.0035 · 0.240 | 3 · 0.0016 · 0.285 |
| stage1 | `gate:target_logvar` | none | 3 · 0.0023 · 0.277 | 3 · 0.0021 · 0.229 | 3 · 0.0040 · 0.229 |
| stage1 | `logit_std` | effective_number | 3 · 0.0023 · 0.196 | 3 · 0.0033 · 0.050 | 3 · 0.0106 · 0.370 |
| vae9182 | `adaptive_t` | effective_number | 3 · 0.0047 · 0.572 | 3 · 0.0030 · 0.501 | 3 · 0.0035 · 0.555 |
| vae9182 | `ctkd` | effective_number | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 |
| vae9182 | `g2g_kl` | effective_number | 3 · 0.0043 · 0.408 | 3 · 0.0043 · 0.147 | 3 · 0.0048 · 0.263 |
| vae9182 | `g2g_kl+adaptive_t` | effective_number | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 | 1 · 0.0000 · 0.000 |
| vae9182 | `gate:mean_logvar` | none | 3 · 0.0046 · 0.668 | 3 · 0.0052 · 0.228 | 3 · 0.0064 · 0.419 |
| vae9182 | `gate:oracle_error` | none | 3 · 0.0040 · 0.493 | 3 · 0.0036 · 0.516 | 3 · 0.0065 · 0.363 |
| vae9182 | `logit_std` | effective_number | 3 · 0.0013 · 0.818 | 3 · 0.0096 · 0.314 | 3 · 0.0115 · 0.292 |

n=1 olan hücrelerde sd tanımsızdır ve boş görünür — bu bir eksiklik değil, tek tohumdan yayılım ölçülemez. A12 (gerçek-sinyal gate n=3) bittiğinde `gate:*` satırlarının n'i artacak ve bu tablo yeniden üretilmeli.

---

Üretici: `diagnostics/noise_units.py` · payda: `diagnostics/denominator_table.py::control_arms` (ithal) · eşleştirme: `diagnostics/t5_pairing_diff.py::build` (ithal)

