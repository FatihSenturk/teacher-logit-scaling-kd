# G4.4 — verim: öğrenci/öğretmen doğruluk oranı

> **Panel G4.4.** Makalenin verim cümlesi `best` checkpoint'inden geliyordu. `best`, raporlanan 3068 görüntüde argmax val-acc ile seçiliyor — seçim ve raporlama aynı görüntüler, dolayısıyla sayı seçim iyimserliği taşıyor. Birincil sayı **@swa**'ya geçiyor; @best parantezde kalıyor, silinmiyor.

**BİRİNCİL: 89.95 / 91.82 = %97.96** (@best: %98.32)

Kol: `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200` (+`_seed1`, +`_seed43`) · sample sd (n-1, Bessel-corrected), computed over seeds

## Üç checkpoint

| checkpoint | n | öğrenci doğruluk | oran | açık (pp) |
|---|---|---|---|---|
| `swa` **(birincil)** | 3 | 89.950 ± 0.366 | **%97.96** | 1.87 |
| `best` | 3 | 90.276 ± 0.191 | **%98.32** | 1.54 |
| `last` | 3 | 89.820 ± 0.167 | **%97.82** | 2.00 |

Öğretmen: POSTERv2 (VAE head, VAE9182), 91.82%.

## Seçim iyimserliği, bu kolda ölçülmüş

- `best` − `swa` = **+0.326 pp** → oranı %+0.35 puan şişiriyor
- `best` − `last` = **+0.456 pp**

Yani iki sayı arasındaki fark küçük ama **tek yönlü**: `best` her zaman kayırır, çünkü tanımı gereği maksimumu seçer. Bir kalibrasyon makalesinde verim iddiasının gözetlemeyen bir kurala dayanması, farkın büyüklüğünden bağımsız olarak doğru olandır.

## Sıkıştırma (yapısal, deterministik — checkpoint'ten bağımsız)

| eksen | öğretmen | öğrenci | oran |
|---|---|---|---|
| parametre | 58.334 M | 2.248 M | **25.9×** |
| FLOPs | 8.4827 G | 0.3286 G | **25.8×** |
| boyut | 555.0 MB | 8.83 MB | **62.9×** |

Bu üç oran ölçüm değil sayım; checkpoint seçiminden etkilenmezler ve olduğu gibi kalırlar. Yapı sayıları `p5_efficiency_frontier`'dan **ithal** edildi.

## Tohum bazında

| koşu | @swa | @best | @last |
|---|---|---|---|
| `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200` | 89.635 | 90.059 | 89.863 |
| `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1` | 89.863 | 90.352 | 89.961 |
| `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43` | 90.352 | 90.417 | 89.635 |

---

Üretici: `diagnostics/efficiency_retention.py` · veri: `diagnostics/selection_audit/selection_audit_unfrozen.csv` · yapı sayıları: `diagnostics/p5_efficiency_frontier.py` (ithal)

