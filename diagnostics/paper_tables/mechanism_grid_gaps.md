# B9 — `tab_mechanisms`'in boş hücreleri: koşulmadı mı, uygulanamaz mı, elendi mi?

Üretici: `diagnostics/mechanism_grid_gaps.py` · eşleştirme `t5_pairing_diff.build(rule="new")`'den **ithal** · sinyal kalitesi `rafdb_signal_quality/signal_quality_table.csv`'den

> Negatif sonuç sayan bir makalede **koşulmamış bir hücre bilgidir**. Boş bir kutuya bakan okuyucu "denendi, çıkmadı" ile "hiç denenmedi"yi ayırt edemez — ve iki durum aynı cümleyi taşımaz.

| ızgara | 8 mekanizma × 3 öğretmen = 24 hücre |
|---|---|
| dolu | 21 |
| **boş** | **3** |

## Boş hücrelerin hükmü

| öğretmen | mekanizma | hüküm | gerekçe (ölçülen) |
|---|---|---|---|
| stage1 | `g2g_kl+adaptive_t` | **koşulmadı** | defterde bu (öğretmen, mekanizma) için hiç koşu yok |
| primary | `g2g_kl+adaptive_t` | **koşulmadı** | defterde bu (öğretmen, mekanizma) için hiç koşu yok |
| vae9182 | `gate:target_logvar` | **elendi** | gate sinyali ön-kayıtlı taramada aleyhte: AUROC 0.4579 (şanstan 0.0421 uzak), yön "higher->less error (confidence-like)" — gate'in istediği yön değil. A12 beş hücresini bu taramadan seçti. |

## Tam ızgara

| mekanizma | stage1 | primary | vae9182 |
|---|---|---|---|
| `adaptive_t` | n=3 | n=3 | n=3 |
| `ctkd` | n=1 | n=1 | n=1 |
| `g2g_kl` | n=3 | n=3 | n=3 |
| `g2g_kl+adaptive_t` | — *koşulmadı* | — *koşulmadı* | n=1 |
| `gate:mean_logvar` | n=3 | n=3 | n=3 |
| `gate:oracle_error` | n=3 | n=3 | n=3 |
| `gate:target_logvar` | n=3 | n=3 | — *elendi* |
| `logit_std` | n=3 | n=3 | n=3 |

## Boş değil ama eksik: bütçe kapısının dışında kalan tohumlar

Bir hücrenin ızgaradaki `n`'i, defterdeki tohum sayısından küçük olabilir — fazla tohumlar T5'in bütçe kapısının (400e / SWA@200) dışında koşulmuştur. Bu hücreler için doğru cümle *"n=1"* değil, ***"bu bütçede n=1, bir üst bütçede n=3"***.

| öğretmen | mekanizma | ızgarada n | defterde tohum | dışarıdaki bütçe | koşular |
|---|---|---|---|---|---|
| vae9182 | `g2g_kl+adaptive_t` | 1 | 3 | 500e/SWA@200 | `RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200`, `RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200_seed1`, `RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200_seed43` |

