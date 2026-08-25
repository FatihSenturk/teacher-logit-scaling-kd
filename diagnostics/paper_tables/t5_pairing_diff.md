# A2 — Cell-level diff of the T5/T5a pairing-rule change

Producer: `diagnostics/t5_pairing_diff.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds

Old rule `(teacher, seed)`, new rule `(teacher, seed, class_weight_mode)`. The treatment filter is byte-identical in both, so the difference below comes **from the control pairing alone**.

**7 cells unchanged**, **14 cells changed.**

## Controls the old rule silently discarded

On each row below the old rule saw two legal controls under the same key and **kept whichever came later** (the winner depended on `runs.csv` row order):

| key (teacher, seed) | kept | discarded |
|---|---|---|
| primary, 1 | `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed1` | `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1` |
| primary, 43 | `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` | `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43` |
| stage1, 1 | `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed1` | `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1` |
| stage1, 43 | `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` | `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43` |
| vae9182, 42 | `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200` | `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed42` |
| vae9182, 1 | `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1` | `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed1` |
| vae9182, 43 | `RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43` | `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| primary, 42 | `RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200` | `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed42` |
| stage1, 42 | `RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200` | `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed42` |

## Cells that changed (@swa)

| cell | Δacc old | Δacc new | diff | ΔECE old | ΔECE new | diff | n old→new | control used (new) |
|---|---|---|---|---|---|---|---|---|
| primary/adaptive_t | -0.16 | -0.39 | -0.228 | -0.0014 | +0.0023 | +0.0037 | 3→3 | `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1`, `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43`, `RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200` |
| primary/g2g_kl | +0.09 | -0.14 | -0.228 | -0.0053 | -0.0016 | +0.0037 | 3→3 | `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1`, `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43`, `RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200` |
| primary/gate:mean_logvar | +0.09 | +0.20 | +0.109 | -0.0045 | -0.0056 | -0.0011 | 3→3 | `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| primary/gate:oracle_error | -0.12 | -0.01 | +0.109 | +0.0015 | +0.0004 | -0.0011 | 3→3 | `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| primary/gate:target_logvar | -0.20 | -0.09 | +0.109 | +0.0003 | -0.0008 | -0.0011 | 3→3 | `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_primary_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| primary/logit_std | -0.09 | -0.32 | -0.228 | +0.0822 | +0.0859 | +0.0037 | 3→3 | `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1`, `RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43`, `RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200` |
| stage1/adaptive_t | +0.20 | +0.16 | -0.033 | -0.0026 | -0.0011 | +0.0015 | 3→3 | `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1`, `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43`, `RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200` |
| stage1/g2g_kl | +0.45 | +0.41 | -0.033 | -0.0057 | -0.0042 | +0.0015 | 3→3 | `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1`, `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43`, `RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200` |
| stage1/gate:mean_logvar | -0.01 | -0.10 | -0.087 | -0.0013 | -0.0012 | +0.0001 | 3→3 | `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| stage1/gate:oracle_error | -0.13 | -0.22 | -0.087 | +0.0014 | +0.0015 | +0.0001 | 3→3 | `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| stage1/gate:target_logvar | +0.34 | +0.25 | -0.087 | -0.0043 | -0.0041 | +0.0001 | 3→3 | `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_stage1_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| stage1/logit_std | -0.20 | -0.23 | -0.033 | +0.0891 | +0.0906 | +0.0015 | 3→3 | `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1`, `RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43`, `RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200` |
| vae9182/gate:mean_logvar | -0.08 | -0.27 | -0.196 | -0.0037 | +0.0015 | +0.0052 | 3→3 | `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |
| vae9182/gate:oracle_error | -0.03 | -0.23 | -0.196 | +0.0004 | +0.0056 | +0.0052 | 3→3 | `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed1`, `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed42`, `RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200_seed43` |

## Cells that did not change

`primary/ctkd`, `stage1/ctkd`, `vae9182/adaptive_t`, `vae9182/ctkd`, `vae9182/g2g_kl`, `vae9182/g2g_kl+adaptive_t`, `vae9182/logit_std`.

> All of these are `class_weight_mode=effective_number` treatments; the old rule kept the control appearing **last** in `runs.csv` order, and that happened to be the `effective_number` baseline (`baseline_noclassweight` sorts before `betaKD` alphabetically), so the result came out the same. **That was a coincidence, not a guarantee** — a change in run name would have changed the winner; the rule is now semantic.

## The numbers 5.4 quotes — re-anchored

`vae9182/logit_std` @swa, eski kural: Δacc **-0.12 ± 0.82** pp, ΔECE **+0.1388 ± 0.0013** (n=3)  
same cell, new rule: Δacc **-0.12 ± 0.82** pp, ΔECE **+0.1388 ± 0.0013** (n=3)

**The two denominators in the text are not the same statistic.** On the accuracy side 5.4 says "its control's seed spread (0.82 pp)", but 0.82 pp is **not the control's spread; it is the sd of the paired Δacc**. Candidate denominators:

| denominator | value | Δacc as a multiple | ΔECE as a multiple |
|---|---|---|---|
| paired Δacc sd (the 0.82 in the text) | 0.8183 | 0.1× | — |
| paired ΔECE sd | 0.0013 | — | 107.3× |
| kontrol kolunun kendi acc tohum sd'si (`effective_number`) | 0.3664 | 0.3× | — |
| kontrol kolunun kendi ECE tohum sd'si (`effective_number`) | 0.0020 | — | 69.5× |
| kontrol kolunun kendi ECE tohum sd'si (`none`) | 0.0027 | — | 51.4× |

> **The correct sentence for the text:** the accuracy change (-0.12 pp) is smaller than its own paired sd (0.82 pp) — statistically invisible; the calibration change (+0.1388) is this many times its own paired sd: (0.0013) **107 **. If the control's own ECE seed sd is preferred instead, the ratio becomes 69×. **74× does not come out under any denominator** — that number must be updated.

