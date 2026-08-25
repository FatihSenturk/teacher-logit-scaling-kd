# §5.4 — yedi sınıfın tam tablosu ve "frekansı takip eder" denetimi

> **7 Ağu akşam isteği.** Cümle "sıfırı kesme sıcaklığı sınıf frekansını takip eder" diyor. Bu tablo iddiayı ölçüyor; yeni ölçüm yok, kaynak `perclass` json'u.

**HÜKÜM: EĞİLİM VAR, TEK İNVERSİYONLA**

@swa · 3 tohum · sample sd (n-1, Bessel-corrected), computed over seeds · sinyal: per-class signed confidence gap = mean(top-1 confidence) − accuracy, GERÇEK etikete göre gruplanmış, binleme yok

## Yedi sınıf, frekansa göre azalan

| sınıf | n | native signed gap | sıfırı kesme T | T=2.2'deki gap |
|---|---|---|---|---|
| Happiness | 1185 | +0.0278 ± 0.0021 | **1.457** | -0.1103 ± 0.0030 |
| Neutral | 680 | +0.0615 ± 0.0095 | **1.463** | -0.1262 ± 0.0044 |
| Sadness | 478 | +0.0869 ± 0.0091 | **1.699** | -0.0845 ± 0.0059 |
| Surprise | 329 | +0.0656 ± 0.0126 | **1.622** | -0.0798 ± 0.0114 |
| Anger | 162 | +0.1155 ± 0.0093 | **1.821** | -0.0637 ± 0.0247 |
| Disgust | 160 | +0.2776 ± 0.0123 | **kesmedi** | +0.0629 ± 0.0045 |
| Fear | 74 | +0.3048 ± 0.0087 | **kesmedi** | +0.1655 ± 0.0201 |

Kesmeyen sınıflar: Disgust, Fear — T=2.2'ye kadar **hâlâ aşırı güvenli**. Bunlar "sonsuzda kesiyor" değil, **gözlenen aralıkta kesmedi** demek; sıralamaya sonda ama ayrı etiketle giriyorlar.

## İddianın ölçümü

**Operasyonel tanım (önceden yazıldı):** "frekansı takip eder" = sınıflar n'e göre azalan sıralandığında kesme sıcaklığı monoton **artar**. Her ihlal bir inversiyondur.

- Kesen sınıf sayısı: **5**/7
- **ρ(n, T_cross) = -0.900** — negatif işaret "sık sınıf ERKEN kesiyor" demek, yani iddianın yönü.
- ρ(seyreklik sırası, T_cross) = +0.900 — aynı ilişki, ters eksen.

> **Konvansiyon açıkça yazılmalı.** Bu iki sayı aynı örüntünün iki gösterimi; işareti eksen seçimi belirliyor. Altyazıya girerse hangisinin kullanıldığı yazılsın — işaretsiz bırakılan bir korelasyon belirsizdir.
- Komşu inversiyon: **1**

| daha sık olan | n | kesme T | daha seyrek olan | n | kesme T | fark |
|---|---|---|---|---|---|---|
| **Sadness** | 478 | 1.699 | Surprise | 329 | 1.622 | **+0.078** |

> **Şüpheniz doğrulandı.** Sadness (n=478) Surprise'dan (n=329) **daha sık**, ama sıfırı **0.078 daha geç** kesiyor. Sıralama bu tek noktada bozuluyor — komşu bir yer değiştirme, yani eğilim duruyor ama **tam değil**.

> Önerilen ifade: *"crossing temperature broadly tracks class frequency, with one inversion (sadness crosses later than the less frequent surprise)"*. Niteleyici olmadan cümle veriden fazlasını söylüyor.

## Neden inversiyon şaşırtıcı değil

Kesme sıcaklığı yalnız frekansa değil, sınıfın **native gap'inin büyüklüğüne** de bağlı: büyük gap'i kapatmak daha yüksek T ister. Frekans ile gap arasındaki ilişki gevşek olduğu için sıralamanın tam olması zaten beklenmezdi. Tabloda ikisi yan yana duruyor, okur ilişkiyi kendisi görebilir.

---

Üretici: `diagnostics/perclass_crossing_table.py` · kaynak: `diagnostics/reliability/perclass_calibration.json` (yeni ölçüm yok)

