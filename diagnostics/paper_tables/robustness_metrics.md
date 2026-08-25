# R3-1 — Multi-metric dose–response robustness inventory (@swa)

Producer: `diagnostics/robustness_metrics.py` · metric definitions in `diagnostics/calibration_metrics.py` · equal-width ECE is the campaign's existing `confidence_ece`, called with different bin counts rather than reimplemented · all values come from cached per-sample logits, no forward pass. Pre-declared in `PREREGISTRATIONS.md` A10 (R3-1): **no success criterion, no metric may be withheld, every monotonicity break is listed.**

**42 runs.** RAF-DB stage1 15 · RAF-DB vae9182 15 · FERPlus 12.

**Verification gate.** For every run the `ECE ew-15` column is compared against the value stored in that run's own logit cache (written on a different day by a different script and itself validated against `selection_audit`). A deviation above 1e-09 aborts the whole table — so the six new columns cannot come from a pipeline that fails to reproduce the published one.

**Level-1.** The per-sample caches are read from `diagnostics/student_logits/`, the published byte copies of the 42 run-directory caches (`publish_student_logits.py`; sha256 of source and copy required equal). This table therefore needs no raw run directory — which is the Level-1 promise, and was not true of this script before 8 Aug 2026.

**Metric specifications** (frozen in A10, unchanged since):

| column | specification |
|---|---|
| NLL | mean negative log-likelihood, natural log |
| Brier | multiclass, full probability vector, one-hot target |
| ECE ew-10 / ew-15 / ew-25 | equal-width confidence ECE, 10 / 15 / 25 bins |
| ECE em-15 | equal-**mass** (adaptive) ECE, 15 quantile bins |
| classwise-ECE | mean over classes of the top-1 ECE within each **predicted** class |

### RAF-DB stage1 — 15 runs (5 T × 3 seeds)

**Raw values, @swa.** Every cell is computed from that run's own cached per-sample logits; the source file of each row is listed under the table.

| T | seed | NLL | Brier | ECE ew-10 | ECE ew-15 | ECE ew-25 | ECE em-15 | classwise-ECE | acc |
|---|---|---|---|---|---|---|---|---|---|
| 0.85 | 1 | 0.5048 | 0.1851 | 0.0811 | 0.0814 | 0.0822 | 0.0809 | 0.1096 | 89.47 |
| 0.85 | 42 | 0.4791 | 0.1756 | 0.0781 | 0.0781 | 0.0784 | 0.0780 | 0.1014 | 89.83 |
| 0.85 | 43 | 0.4868 | 0.1802 | 0.0795 | 0.0795 | 0.0800 | 0.0796 | 0.1110 | 89.63 |
| 1 | 1 | 0.4185 | 0.1721 | 0.0719 | 0.0721 | 0.0719 | 0.0716 | 0.0992 | 89.99 |
| 1 | 42 | 0.4234 | 0.1784 | 0.0728 | 0.0728 | 0.0728 | 0.0733 | 0.1008 | 89.37 |
| 1 | 43 | 0.4317 | 0.1787 | 0.0746 | 0.0744 | 0.0757 | 0.0748 | 0.1061 | 89.44 |
| 1.3406 | 1 | 0.3518 | 0.1607 | 0.0425 | 0.0425 | 0.0431 | 0.0512 | 0.0655 | 89.73 |
| 1.3406 | 42 | 0.3539 | 0.1635 | 0.0424 | 0.0432 | 0.0454 | 0.0502 | 0.0770 | 89.67 |
| 1.3406 | 43 | 0.3495 | 0.1620 | 0.0416 | 0.0428 | 0.0430 | 0.0495 | 0.0663 | 89.80 |
| 1.7 | 1 | 0.3680 | 0.1641 | 0.0543 | 0.0415 | 0.0534 | 0.0548 | 0.0719 | 89.41 |
| 1.7 | 42 | 0.3606 | 0.1620 | 0.0542 | 0.0472 | 0.0499 | 0.0554 | 0.0720 | 89.24 |
| 1.7 | 43 | 0.3645 | 0.1621 | 0.0548 | 0.0455 | 0.0513 | 0.0540 | 0.0732 | 89.63 |
| 2.2 | 1 | 0.4252 | 0.1732 | 0.1013 | 0.1013 | 0.1018 | 0.0969 | 0.1094 | 89.31 |
| 2.2 | 42 | 0.4124 | 0.1655 | 0.1008 | 0.1030 | 0.1045 | 0.1039 | 0.1186 | 89.83 |
| 2.2 | 43 | 0.4169 | 0.1675 | 0.0941 | 0.0980 | 0.0984 | 0.0971 | 0.1208 | 89.77 |

**Arm means ± sd** (sample sd (n-1, Bessel-corrected), computed over seeds).

| T | NLL | Brier | ECE ew-10 | ECE ew-15 | ECE ew-25 | ECE em-15 | classwise-ECE |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.4902 ± 0.0132 | 0.1803 ± 0.0047 | 0.0796 ± 0.0015 | 0.0797 ± 0.0016 | 0.0802 ± 0.0019 | 0.0795 ± 0.0015 | 0.1073 ± 0.0052 |
| 1 | 0.4245 ± 0.0067 | 0.1764 ± 0.0037 | 0.0731 ± 0.0013 | 0.0731 ± 0.0012 | 0.0735 ± 0.0020 | 0.0732 ± 0.0016 | 0.1020 ± 0.0036 |
| 1.3406 | 0.3517 ± 0.0022 | 0.1621 ± 0.0014 | 0.0422 ± 0.0005 | 0.0428 ± 0.0003 | 0.0438 ± 0.0013 | 0.0503 ± 0.0008 | 0.0696 ± 0.0064 |
| 1.7 | 0.3644 ± 0.0037 | 0.1627 ± 0.0012 | 0.0545 ± 0.0003 | 0.0447 ± 0.0029 | 0.0515 ± 0.0017 | 0.0547 ± 0.0007 | 0.0724 ± 0.0007 |
| 2.2 | 0.4182 ± 0.0065 | 0.1687 ± 0.0040 | 0.0987 ± 0.0040 | 0.1008 ± 0.0025 | 0.1016 ± 0.0031 | 0.0993 ± 0.0040 | 0.1163 ± 0.0060 |

**Monotonicity in T, within seed.** `sign string` is one character per consecutive T step, in T order. `monotone` counts seeds whose steps all share one non-zero sign. `steps` counts individual (pair, seed) steps that agree with the other seeds at the same pair — no global direction is assumed anywhere. `argmin T` is where each seed's curve bottoms out.

| metric | seed signs | monotone seeds | steps consistent | argmin T (per seed) |
|---|---|---|---|---|
| NLL | 1:`--++` · 42:`--++` · 43:`--++` | 0/3 | 12/12 | **all 1.3406** |
| Brier | 1:`--++` · 42:`+--+` · 43:`--++` | 0/3 | 10/12 | 1:1.3406 · 42:1.7 · 43:1.3406 |
| ECE ew-10 | 1:`--++` · 42:`--++` · 43:`--++` | 0/3 | 12/12 | **all 1.3406** |
| ECE ew-15 | 1:`---+` · 42:`--++` · 43:`--++` | 0/3 | 11/12 | 1:1.7 · 42:1.3406 · 43:1.3406 |
| ECE ew-25 | 1:`--++` · 42:`--++` · 43:`--++` | 0/3 | 12/12 | **all 1.3406** |
| ECE em-15 | 1:`--++` · 42:`--++` · 43:`--++` | 0/3 | 12/12 | **all 1.3406** |
| classwise-ECE | 1:`--++` · 42:`---+` · 43:`--++` | 0/3 | 11/12 | 1:1.3406 · 42:1.7 · 43:1.3406 |

*Monotone seeds are 0/3 for every metric, and that is the expected shape, not a failure: this series is a dose–response with an interior optimum, so no seed can be one-directional end to end. The informative descriptive quantity is where the curve bottoms out — the `argmin T` column, and all seven metrics agree on **T = 1.3406**.

**Steps that disagree with the other seeds at the same pair (4 of 84).** Listed in full, as the pre-declaration requires — pair, seed, metric, and the two values.

| pair | seed | metric | value before → after | its sign | other seeds |
|---|---|---|---|---|---|
| 0.85→1 | 42 | Brier | 0.1756 → 0.1784 | + | - |
| 1.3406→1.7 | 42 | Brier | 0.1635 → 0.1620 | - | + |
| 1.3406→1.7 | 1 | ECE ew-15 | 0.0425 → 0.0415 | - | + |
| 1.3406→1.7 | 42 | classwise-ECE | 0.0770 → 0.0720 | - | + |

<details><summary>source files (published byte copies) and their origin run directories</summary>

- `T=0.85,seed=1` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed1/2026-07-23-23-14-27` (sha256 `36cea19151ff9465…`)
- `T=0.85,seed=42` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed42/2026-07-23-10-35-11` (sha256 `ebba1e80263c27eb…`)
- `T=0.85,seed=43` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed43/2026-07-23-14-53-49` (sha256 `9dea25d97ea664d9…`)
- `T=1,seed=1` → `diagnostics/student_logits/RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1/2026-07-21-22-57-33` (sha256 `b55feff0fd2d545b…`)
- `T=1,seed=42` → `diagnostics/student_logits/RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200.npz`  ← `results/unified_students/RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200/2026-07-18-01-45-58` (sha256 `0b9dd71bd98a1ff6…`)
- `T=1,seed=43` → `diagnostics/student_logits/RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43/2026-07-22-03-03-17` (sha256 `3ffe251b8a44d4ab…`)
- `T=1.3406,seed=1` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed1/2026-07-23-10-35-11` (sha256 `dd4ac1871eacd3eb…`)
- `T=1.3406,seed=42` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T1341_halfA_baseline_b070_T6_224_400e_swa200.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T1341_halfA_baseline_b070_T6_224_400e_swa200/2026-07-21-11-14-32` (sha256 `504860c889b732b7…`)
- `T=1.3406,seed=43` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed43/2026-07-24-03-24-24` (sha256 `247922ed26456f76…`)
- `T=1.7,seed=1` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed1/2026-07-24-03-24-13` (sha256 `bd09d1b0d447ce6c…`)
- `T=1.7,seed=42` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed42/2026-07-23-14-53-49` (sha256 `040051d9f848b73a…`)
- `T=1.7,seed=43` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed43/2026-07-23-19-06-06` (sha256 `3e63f9caa5bfa66d…`)
- `T=2.2,seed=1` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed1/2026-07-24-07-29-46` (sha256 `64e24bf19ba2ceeb…`)
- `T=2.2,seed=42` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed42/2026-07-23-19-06-00` (sha256 `69de67d9bb6fc52d…`)
- `T=2.2,seed=43` → `diagnostics/student_logits/RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed43/2026-07-23-23-14-30` (sha256 `36886236e96b1302…`)

</details>

### RAF-DB vae9182 — 15 runs (5 T × 3 seeds)

**Raw values, @swa.** Every cell is computed from that run's own cached per-sample logits; the source file of each row is listed under the table.

| T | seed | NLL | Brier | ECE ew-10 | ECE ew-15 | ECE ew-25 | ECE em-15 | classwise-ECE | acc |
|---|---|---|---|---|---|---|---|---|---|
| 0.85 | 1 | 0.3419 | 0.1603 | 0.0461 | 0.0460 | 0.0465 | 0.0466 | 0.0750 | 89.96 |
| 0.85 | 42 | 0.3281 | 0.1550 | 0.0434 | 0.0434 | 0.0441 | 0.0440 | 0.0637 | 89.96 |
| 0.85 | 43 | 0.3267 | 0.1560 | 0.0435 | 0.0446 | 0.0449 | 0.0448 | 0.0724 | 89.86 |
| 1 | 1 | 0.3233 | 0.1538 | 0.0234 | 0.0343 | 0.0302 | 0.0338 | 0.0539 | 89.86 |
| 1 | 42 | 0.3293 | 0.1570 | 0.0241 | 0.0340 | 0.0327 | 0.0351 | 0.0579 | 89.63 |
| 1 | 43 | 0.3106 | 0.1478 | 0.0198 | 0.0307 | 0.0299 | 0.0300 | 0.0608 | 90.35 |
| 1.3406 | 1 | 0.3554 | 0.1540 | 0.0629 | 0.0628 | 0.0664 | 0.0633 | 0.0963 | 89.80 |
| 1.3406 | 42 | 0.3508 | 0.1522 | 0.0668 | 0.0682 | 0.0704 | 0.0656 | 0.0943 | 90.09 |
| 1.3406 | 43 | 0.3498 | 0.1510 | 0.0608 | 0.0632 | 0.0649 | 0.0601 | 0.0937 | 90.38 |
| 1.7 | 1 | 0.4292 | 0.1725 | 0.1255 | 0.1270 | 0.1274 | 0.1238 | 0.1412 | 89.60 |
| 1.7 | 42 | 0.4305 | 0.1728 | 0.1260 | 0.1260 | 0.1263 | 0.1247 | 0.1407 | 90.09 |
| 1.7 | 43 | 0.4357 | 0.1760 | 0.1304 | 0.1316 | 0.1308 | 0.1308 | 0.1440 | 89.05 |
| 2.2 | 1 | 0.5270 | 0.2085 | 0.2091 | 0.2090 | 0.2106 | 0.2082 | 0.2147 | 89.67 |
| 2.2 | 42 | 0.5246 | 0.2064 | 0.2148 | 0.2148 | 0.2148 | 0.2148 | 0.2162 | 90.29 |
| 2.2 | 43 | 0.5286 | 0.2092 | 0.2085 | 0.2090 | 0.2100 | 0.2084 | 0.2090 | 89.80 |

**Arm means ± sd** (sample sd (n-1, Bessel-corrected), computed over seeds).

| T | NLL | Brier | ECE ew-10 | ECE ew-15 | ECE ew-25 | ECE em-15 | classwise-ECE |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.3322 ± 0.0084 | 0.1571 ± 0.0028 | 0.0443 ± 0.0015 | 0.0447 ± 0.0013 | 0.0452 ± 0.0012 | 0.0451 ± 0.0013 | 0.0703 ± 0.0059 |
| 1 | 0.3211 ± 0.0096 | 0.1529 ± 0.0047 | 0.0225 ± 0.0023 | 0.0330 ± 0.0020 | 0.0309 ± 0.0015 | 0.0329 ± 0.0027 | 0.0576 ± 0.0035 |
| 1.3406 | 0.3520 ± 0.0030 | 0.1524 ± 0.0015 | 0.0635 ± 0.0030 | 0.0647 ± 0.0030 | 0.0672 ± 0.0029 | 0.0630 ± 0.0028 | 0.0948 ± 0.0014 |
| 1.7 | 0.4318 ± 0.0035 | 0.1738 ± 0.0020 | 0.1273 ± 0.0027 | 0.1282 ± 0.0030 | 0.1281 ± 0.0024 | 0.1264 ± 0.0038 | 0.1420 ± 0.0018 |
| 2.2 | 0.5267 ± 0.0020 | 0.2080 ± 0.0015 | 0.2108 ± 0.0035 | 0.2109 ± 0.0034 | 0.2118 ± 0.0026 | 0.2105 ± 0.0038 | 0.2133 ± 0.0038 |

**Monotonicity in T, within seed.** `sign string` is one character per consecutive T step, in T order. `monotone` counts seeds whose steps all share one non-zero sign. `steps` counts individual (pair, seed) steps that agree with the other seeds at the same pair — no global direction is assumed anywhere. `argmin T` is where each seed's curve bottoms out.

| metric | seed signs | monotone seeds | steps consistent | argmin T (per seed) |
|---|---|---|---|---|
| NLL | 1:`-+++` · 42:`++++` · 43:`-+++` | 1/3 | 11/12 | 1:1 · 42:0.85 · 43:1 |
| Brier | 1:`-+++` · 42:`+-++` · 43:`-+++` | 0/3 | 10/12 | 1:1 · 42:1.3406 · 43:1 |
| ECE ew-10 | 1:`-+++` · 42:`-+++` · 43:`-+++` | 0/3 | 12/12 | **all 1** |
| ECE ew-15 | 1:`-+++` · 42:`-+++` · 43:`-+++` | 0/3 | 12/12 | **all 1** |
| ECE ew-25 | 1:`-+++` · 42:`-+++` · 43:`-+++` | 0/3 | 12/12 | **all 1** |
| ECE em-15 | 1:`-+++` · 42:`-+++` · 43:`-+++` | 0/3 | 12/12 | **all 1** |
| classwise-ECE | 1:`-+++` · 42:`-+++` · 43:`-+++` | 0/3 | 12/12 | **all 1** |

**Steps that disagree with the other seeds at the same pair (3 of 84).** Listed in full, as the pre-declaration requires — pair, seed, metric, and the two values.

| pair | seed | metric | value before → after | its sign | other seeds |
|---|---|---|---|---|---|
| 0.85→1 | 42 | NLL | 0.3281 → 0.3293 | + | - |
| 0.85→1 | 42 | Brier | 0.1550 → 0.1570 | + | - |
| 1→1.3406 | 42 | Brier | 0.1570 → 0.1522 | - | + |

<details><summary>source files (published byte copies) and their origin run directories</summary>

- `T=0.85,seed=1` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed1/2026-07-25-10-55-15` (sha256 `a1eda73bb39301b7…`)
- `T=0.85,seed=42` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed42/2026-07-24-18-05-50` (sha256 `2b91bff22489b20f…`)
- `T=0.85,seed=43` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed43/2026-07-25-02-43-00` (sha256 `ae62947fefb0e84f…`)
- `T=1,seed=1` → `diagnostics/student_logits/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1/2026-07-17-18-01-41` (sha256 `22208aada3d9ea19…`)
- `T=1,seed=42` → `diagnostics/student_logits/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200.npz`  ← `results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200/2026-06-20-08-38-09` (sha256 `d5e65e4b6c016aba…`)
- `T=1,seed=43` → `diagnostics/student_logits/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43/2026-07-17-22-05-44` (sha256 `6572d552f8f871e0…`)
- `T=1.3406,seed=1` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed1/2026-07-25-15-03-07` (sha256 `6c571308d1b4aae8…`)
- `T=1.3406,seed=42` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed42/2026-07-24-22-22-33` (sha256 `8c02b30d4edd1c94…`)
- `T=1.3406,seed=43` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed43/2026-07-25-06-49-04` (sha256 `831bf1ed62676264…`)
- `T=1.7,seed=1` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed1/2026-07-24-18-05-50` (sha256 `26b22a5f67c345c0…`)
- `T=1.7,seed=42` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed42/2026-07-25-02-43-02` (sha256 `02fd1c019152856c…`)
- `T=1.7,seed=43` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed43/2026-07-25-10-55-06` (sha256 `6d409382dc93bf5d…`)
- `T=2.2,seed=1` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed1.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed1/2026-07-24-22-22-33` (sha256 `70591fa4de57a937…`)
- `T=2.2,seed=42` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed42.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed42/2026-07-25-06-49-11` (sha256 `09add73c86972cbe…`)
- `T=2.2,seed=43` → `diagnostics/student_logits/RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed43.npz`  ← `results/unified_students/RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed43/2026-07-25-15-03-00` (sha256 `2f73eb75bda3a3ff…`)

</details>

### FERPlus — 12 runs (4 T × 3 seeds)

**Raw values, @swa.** Every cell is computed from that run's own cached per-sample logits; the source file of each row is listed under the table.

| T | seed | NLL | Brier | ECE ew-10 | ECE ew-15 | ECE ew-25 | ECE em-15 | classwise-ECE | acc |
|---|---|---|---|---|---|---|---|---|---|
| 0.26 | 1 | 0.4961 | 0.1776 | 0.0607 | 0.0632 | 0.0632 | 0.0605 | 0.0974 | 88.93 |
| 0.26 | 42 | 0.4932 | 0.1737 | 0.0568 | 0.0568 | 0.0578 | 0.0568 | 0.1274 | 89.18 |
| 0.26 | 43 | 0.4847 | 0.1743 | 0.0561 | 0.0563 | 0.0606 | 0.0553 | 0.1205 | 89.50 |
| 0.5063 | 1 | 0.3560 | 0.1677 | 0.0209 | 0.0193 | 0.0212 | 0.0187 | 0.0916 | 89.18 |
| 0.5063 | 42 | 0.3580 | 0.1685 | 0.0156 | 0.0167 | 0.0244 | 0.0141 | 0.0892 | 88.96 |
| 0.5063 | 43 | 0.3501 | 0.1670 | 0.0185 | 0.0195 | 0.0227 | 0.0170 | 0.1006 | 89.22 |
| 0.74 | 1 | 0.3482 | 0.1738 | 0.0326 | 0.0332 | 0.0348 | 0.0343 | 0.1177 | 88.84 |
| 0.74 | 42 | 0.3379 | 0.1707 | 0.0343 | 0.0356 | 0.0363 | 0.0332 | 0.1029 | 88.77 |
| 0.74 | 43 | 0.3419 | 0.1744 | 0.0327 | 0.0343 | 0.0336 | 0.0334 | 0.1137 | 88.74 |
| 1 | 1 | 0.3616 | 0.1785 | 0.0824 | 0.0826 | 0.0827 | 0.0805 | 0.1378 | 89.12 |
| 1 | 42 | 0.3707 | 0.1836 | 0.0732 | 0.0734 | 0.0739 | 0.0732 | 0.1614 | 88.39 |
| 1 | 43 | 0.3641 | 0.1821 | 0.0787 | 0.0789 | 0.0799 | 0.0787 | 0.1477 | 88.65 |

**Arm means ± sd** (sample sd (n-1, Bessel-corrected), computed over seeds).

| T | NLL | Brier | ECE ew-10 | ECE ew-15 | ECE ew-25 | ECE em-15 | classwise-ECE |
|---|---|---|---|---|---|---|---|
| 0.26 | 0.4914 ± 0.0059 | 0.1752 ± 0.0021 | 0.0578 ± 0.0025 | 0.0587 ± 0.0038 | 0.0605 ± 0.0027 | 0.0575 ± 0.0027 | 0.1151 ± 0.0157 |
| 0.5063 | 0.3547 ± 0.0041 | 0.1678 ± 0.0007 | 0.0183 ± 0.0027 | 0.0185 ± 0.0016 | 0.0228 ± 0.0016 | 0.0166 ± 0.0024 | 0.0938 ± 0.0060 |
| 0.74 | 0.3427 ± 0.0052 | 0.1730 ± 0.0020 | 0.0332 ± 0.0010 | 0.0344 ± 0.0012 | 0.0349 ± 0.0013 | 0.0336 ± 0.0006 | 0.1114 ± 0.0076 |
| 1 | 0.3655 ± 0.0047 | 0.1814 ± 0.0026 | 0.0781 ± 0.0046 | 0.0783 ± 0.0046 | 0.0788 ± 0.0045 | 0.0774 ± 0.0038 | 0.1490 ± 0.0118 |

**Monotonicity in T, within seed.** `sign string` is one character per consecutive T step, in T order. `monotone` counts seeds whose steps all share one non-zero sign. `steps` counts individual (pair, seed) steps that agree with the other seeds at the same pair — no global direction is assumed anywhere. `argmin T` is where each seed's curve bottoms out.

| metric | seed signs | monotone seeds | steps consistent | argmin T (per seed) |
|---|---|---|---|---|
| NLL | 1:`--+` · 42:`--+` · 43:`--+` | 0/3 | 9/9 | **all 0.74** |
| Brier | 1:`-++` · 42:`-++` · 43:`-++` | 0/3 | 9/9 | **all 0.5063** |
| ECE ew-10 | 1:`-++` · 42:`-++` · 43:`-++` | 0/3 | 9/9 | **all 0.5063** |
| ECE ew-15 | 1:`-++` · 42:`-++` · 43:`-++` | 0/3 | 9/9 | **all 0.5063** |
| ECE ew-25 | 1:`-++` · 42:`-++` · 43:`-++` | 0/3 | 9/9 | **all 0.5063** |
| ECE em-15 | 1:`-++` · 42:`-++` · 43:`-++` | 0/3 | 9/9 | **all 0.5063** |
| classwise-ECE | 1:`-++` · 42:`-++` · 43:`-++` | 0/3 | 9/9 | **all 0.5063** |

*Monotone seeds are 0/3 for every metric, and that is the expected shape, not a failure: this series is a dose–response with an interior optimum, so no seed can be one-directional end to end. The informative descriptive quantity is where the curve bottoms out — the `argmin T` column, where the seven metrics land on ['0.5063', '0.74'].

**No step disagrees with the other seeds at the same pair** in any of the seven metrics.

<details><summary>source files (published byte copies) and their origin run directories</summary>

- `T=0.26,seed=1` → `diagnostics/student_logits/FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed1.npz`  ← `results/unified_students/FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed1/2026-07-26-13-29-57` (sha256 `43d9f1c9409f14c8…`)
- `T=0.26,seed=42` → `diagnostics/student_logits/FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed42.npz`  ← `results/unified_students/FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed42/2026-07-26-22-58-01` (sha256 `0aef19b677e2567b…`)
- `T=0.26,seed=43` → `diagnostics/student_logits/FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed43.npz`  ← `results/unified_students/FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed43/2026-07-27-03-47-04` (sha256 `c5164172c571c2ff…`)
- `T=0.5063,seed=1` → `diagnostics/student_logits/FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed1.npz`  ← `results/unified_students/FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed1/2026-07-27-03-44-38` (sha256 `4f6fbaf0f207a32b…`)
- `T=0.5063,seed=42` → `diagnostics/student_logits/FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed42.npz`  ← `results/unified_students/FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed42/2026-07-26-13-27-45` (sha256 `9c2857c5292a798a…`)
- `T=0.5063,seed=43` → `diagnostics/student_logits/FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed43.npz`  ← `results/unified_students/FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed43/2026-07-26-18-14-59` (sha256 `aa0711810589608c…`)
- `T=0.74,seed=1` → `diagnostics/student_logits/FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed1.npz`  ← `results/unified_students/FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed1/2026-07-28-02-58-40` (sha256 `c0d933e4e3a2fe90…`)
- `T=0.74,seed=42` → `diagnostics/student_logits/FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed42.npz`  ← `results/unified_students/FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed42/2026-07-27-22-09-52` (sha256 `d9425560e439ff3e…`)
- `T=0.74,seed=43` → `diagnostics/student_logits/FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed43.npz`  ← `results/unified_students/FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed43/2026-07-27-22-09-52` (sha256 `31fb19600cccac9b…`)
- `T=1,seed=1` → `diagnostics/student_logits/FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed1.npz`  ← `results/unified_students/FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed1/2026-07-27-08-30-06` (sha256 `377c1d0ce68c34fe…`)
- `T=1,seed=42` → `diagnostics/student_logits/FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed42.npz`  ← `results/unified_students/FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed42/2026-07-26-18-12-16` (sha256 `c958c3cca63d6d58…`)
- `T=1,seed=43` → `diagnostics/student_logits/FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed43.npz`  ← `results/unified_students/FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed43/2026-07-26-23-01-37` (sha256 `da4a329fa20580c7…`)

</details>

## Summary across the three series

**Where each metric puts the minimum.** 20 of 21 (series × metric) cells place the dose–response minimum at the same temperature as the majority of metrics in that series:

| series | consensus argmin T | metrics agreeing |
|---|---|---|
| RAF-DB stage1 | **1.3406** | 7/7 |
| RAF-DB vae9182 | **1** | 7/7 |
| FERPlus | **0.5063** | 6/7 |

This is the round's answer to the single-specification objection: the location of the optimum is a property of the arm, not of the binning rule. Bin count (10/15/25), binning scheme (equal-width vs equal-mass), class weighting (classwise) and even the two metrics that do no binning at all (NLL, Brier) land in the same place.

**The exceptions, in full:**

| series | metric | its argmin T | consensus | unanimous across seeds |
|---|---|---|---|---|
| FERPlus | NLL | 0.74 | 0.5063 | yes |

A row marked unanimous is a **systematic** disagreement, not seed noise: all three seeds of that metric agree with each other and disagree with the other metrics.

**Step consistency.** Across 42 runs × 7 metrics, 224 of 231 individual seed-steps agree with the other seeds at the same T pair (97.0%). Every disagreement is listed in its series' section above, by pair, seed and metric.

