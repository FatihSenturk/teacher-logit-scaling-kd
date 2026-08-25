# B7 — FERPlus insan entropisi, abstention kütlesi temsil edilerek

Üretici: `diagnostics/ferplus_abstention_entropy.py` · öğretmen logitleri `ferplus_jsd/ferplus_val_logits.pt` önbelleğinden · oy sütunları `ferplus_jsd/ferplus_val_votes10.csv`

> Makale FERPlus oylarının 10'a tamamlanmamasını *"sebebi belirlenemez"* diye geçiştiriyor. Kanonik `fer2013new.csv` başlığı bunu yalanlıyor: sekiz ifade sütununun yanında **`unknown`** ve **`NF`** var. Eksik oy bir kayıp değil, anotatörün açık *"bilemiyorum" / "yüz değil"* yanıtı.

## Ölçüm

| kalem | değer |
|---|---|
| doğrulama satırı | 3153 |
| **on sütunun toplamı her satırda tam 10** | **evet** |
| abstention kütlesi taşıyan satır | 1176 (%37.3) |
| `unknown` oyu | 1372 |
| `NF` oyu | 48 |

Sekiz sütunun toplamı: **10** oy → 1977 satır, **9** oy → 966 satır, **8** oy → 182 satır, **7** oy → 22 satır, **6** oy → 6 satır. Yani "eksik" görünen oy, on sütunda tam olarak geri geliyor.

## (a) ve (b): iki hedef, iki entropi

| hedef | tanım | ortalama insan entropisi (nat) |
|---|---|---|
| **(a) koşullu (yayımlı)** | sekiz ifadeye yeniden normalize; *"bir ifade seçtiyse hangisi"* | **0.4401** |
| **(b) abstention temsil edilmiş** | on kategori; *"ne yanıt verdi"* | **0.5488** |

Fark **+0.1087 nat** (%+24.7). (a) yayımlanan `per_sample_human_entropy.npy` ile **birebir** yeniden üretildi; en büyük sapma `0.00e+00` (float32 saklama).

## T*_JSD ikisinde de 0.74'te mi kalıyor?

(b)'de öğretmenin dağılımı iki ekstra kategoride **sıfır** olacak şekilde genişletiliyor — model `unknown`/`NF` üretemez, dolayısıyla JSD'nin T'den bağımsız bir **tabanı** var. Soru tabanın büyüklüğü değil, optimumun yeri.

| hedef | T\*_JSD | o T'de ortalama JSD | T=1'de JSD | ölçeklemenin kazancı |
|---|---|---|---|---|
| (a) koşullu-8 | **0.74** | 0.0440 | 0.0492 | +0.0052 (+10.5%) |
| (b) abstention-10 | **0.74** | 0.0588 | 0.0636 | +0.0048 (+7.6%) |

> **T\*_JSD değişmiyor.** Abstention kütlesi temsil edildiğinde optimum aynı sıcaklıkta kalıyor — yani hizalama sonucu, eksik oyların nasıl yorumlandığına **bağlı değil**. Değişen tek şey JSD'nin tabanı, ve o taban T'den bağımsız.

Izgara [0.1, 4.0], adım 0.02 — `ferplus_human_vote_jsd.py`'dekiyle aynı. Optimum sınırda mı: **hayır**.

## Makaleye düşen

*"Eksik oyların sebebi belirlenemez"* cümlesi **gereksiz ve yanlış**: sebep kanonik dosyada yazılı. Doğru cümle, sekiz sütunlu hedefin bir **koşullu** hedef olduğunu söylemek ve abstention kütlesinin ölçülmüş büyüklüğünü (%37.3 satır, entropiye etkisi +0.1087 nat) vermektir.

