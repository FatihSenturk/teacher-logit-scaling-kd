# Results tables — ready to copy into the paper

Producer: `diagnostics/paper_tables.py` · sd convention: **sample sd (n-1, Bessel-corrected), computed over seeds**

**How to read this.** `@swa` and `@last` are selection-independent; `@best` is chosen by argmax val-acc over the reported set and therefore carries selection optimism (T8 measures it). The primary column in every table is **@swa**.

**One set, several names.** "fold-3 validation split", "the reporting set" and "RAF-DB's official test set" all denote the *same* partition, and `@best` is selected on it: RAF-DB's metadata holds exactly two partitions (fold 2 = `train/`, n=12,271; fold 3 = `test/`, n=3,068) and fold 3's per-class counts reproduce RAF-DB's published test distribution exactly. FERPlus's reporting set is fold 2 (`FER2013Test`, n=3,153). Measured, not asserted: `diagnostics/split_identity.py` -> `paper_tables/split_identity.{md,json}`.

## T1 — Dose-response, RAF-DB / Stage1 teacher

### Stage1 (over-confident teacher, ECE 0.0378)

Signed gap = mean confidence − accuracy, from the teacher's pre-scaled logits on the fold-3 validation split. This arm lies **entirely on the positive** side.

| T | teacher ECE | signed gap | student ECE @swa | student ECE @best | student ECE @last | student acc @swa | n |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.0454 | +0.0431 | 0.0797 ± 0.0016 | 0.0761 ± 0.0006 | 0.0803 ± 0.0059 | 89.65 ± 0.18 | 3 |
| 1 | 0.0378 | +0.0338 | 0.0731 ± 0.0012 | 0.0627 ± 0.0054 | 0.0701 ± 0.0081 | 89.60 ± 0.34 | 3 |
| 1.3406 | 0.0159 | +0.0040 | 0.0428 ± 0.0003 | 0.0338 ± 0.0021 | 0.0365 ± 0.0005 | 89.73 ± 0.07 | 3 |
| 1.7 | 0.0429 | -0.0427 | 0.0447 ± 0.0029 | 0.0559 ± 0.0057 | 0.0572 ± 0.0059 | 89.43 ± 0.20 | 3 |
| 2.2 | 0.1270 | -0.1270 | 0.1008 ± 0.0025 | 0.1178 ± 0.0091 | 0.1189 ± 0.0091 | 89.63 ± 0.28 | 3 |

*Kaynak: `diagnostics/p1_dose_response/two_dataset_overlay.json`*

## T2 — Dose-response, RAF-DB / VAE9182 teacher (flat control)

### VAE9182 (well-calibrated teacher, ECE 0.0136)

B-007's pre-registered flat control: with no miscalibration to correct, T≠1 **should not help**. The signed gap at T=1.0 is +0.0042, the point closest to zero.

| T | teacher ECE | signed gap | student ECE @swa | student ECE @best | student ECE @last | student acc @swa | n |
|---|---|---|---|---|---|---|---|
| 0.85 | 0.0250 | +0.0248 | 0.0447 ± 0.0013 | 0.0355 ± 0.0022 | 0.0358 ± 0.0053 | 89.93 ± 0.06 | 3 |
| 1 | 0.0136 | +0.0042 | 0.0330 ± 0.0020 | 0.0274 ± 0.0021 | 0.0307 ± 0.0011 | 89.95 ± 0.37 | 3 |
| 1.3406 | 0.0627 | -0.0605 | 0.0647 ± 0.0030 | 0.0764 ± 0.0153 | 0.0795 ± 0.0056 | 90.09 ± 0.29 | 3 |
| 1.7 | 0.1454 | -0.1453 | 0.1282 ± 0.0030 | 0.1426 ± 0.0136 | 0.1456 ± 0.0125 | 89.58 ± 0.52 | 3 |
| 2.2 | 0.2622 | -0.2622 | 0.2109 ± 0.0034 | 0.2284 ± 0.0064 | 0.2282 ± 0.0090 | 89.92 ± 0.33 | 3 |

*Kaynak: `diagnostics/p1_dose_response/two_dataset_overlay.json`*

## T3 — Dose-response, FERPlus (under-confident teacher, opposite sign)

### FERPlus (ECE 0.1282 @T=1, signed gap −0.1277)

The **mirror image** of the RAF-DB arms: here the teacher is under-confident, so the correction sharpens rather than softens (T\*<1). The law's direction-independence can only be tested once this arm is included.

| T | teacher ECE | signed gap | student ECE @swa | student ECE @best | student ECE @last | student acc @swa | n |
|---|---|---|---|---|---|---|---|
| 0.26 | 0.0393 | +0.0393 | 0.0587 ± 0.0038 | 0.0568 ± 0.0014 | 0.0591 ± 0.0015 | 89.21 ± 0.29 | 3 |
| 0.5063 | 0.0156 | -0.0117 | 0.0185 ± 0.0016 | 0.0196 ± 0.0020 | 0.0191 ± 0.0061 | 89.12 ± 0.14 | 3 |
| 0.74 | 0.0665 | -0.0649 | 0.0344 ± 0.0012 | 0.0483 ± 0.0083 | 0.0377 ± 0.0007 | 88.78 ± 0.05 | 3 |
| 1 | 0.1282 | -0.1277 | 0.0783 ± 0.0046 | 0.0927 ± 0.0070 | 0.0852 ± 0.0082 | 88.72 ± 0.37 | 3 |

*Kaynak: `diagnostics/p1_dose_response/two_dataset_overlay.json` · `diagnostics/selection_audit/ferplus_selection_audit.csv`*

## T4 — Pooled association, separation test and direction asymmetry

| checkpoint | n points | Spearman(\|signed gap\|, student ECE) | Pearson(\|signed gap\|, student ECE) | Spearman(signed gap, student ECE) |
|---|---|---|---|---|
| **@swa** | 14 | **+0.789** | +0.930 | -0.407 |
| @best | 14 | **+0.895** | +0.970 | -0.560 |
| @last | 14 | **+0.877** | +0.948 | -0.534 |

Why the last column is low: the **signed** axis is NOT monotone on its own — the law operates on |gap|, which means the two branches are each monotone separately. This is also why a single unsigned ECE axis does not suffice.

**Group separation test (FERPlus, B-015).** If the temperature arms' ECE ranges do not overlap at all, the ordering cannot be explained by seed noise.

| checkpoint | Spearman on group means | fully separated | pair | max(lower) | min(upper) | Cohen d |
|---|---|---|---|---|---|---|
| @swa | +1.000 | ✅ | 0.5063<0.26 | 0.0195 | 0.0563 | 13.7 |
| | | | 0.26<1.0 | 0.0632 | 0.0734 | 4.6 |
| @best | +1.000 | ✅ | 0.5063<0.26 | 0.0218 | 0.0556 | 21.4 |
| | | | 0.26<1.0 | 0.0583 | 0.0879 | 7.1 |
| @last | +1.000 | ✅ | 0.5063<0.26 | 0.0235 | 0.0578 | 8.9 |
| | | | 0.26<1.0 | 0.0607 | 0.0765 | 4.5 |

Within seed: **9/9** curves monotone, **9/9** with argmin at T\*=0.5063. Overall verdict: **CONFIRMED**.

> ⚠️ The pooled Spearman is computed **on group means**. Computed at run level it produces ties on the x axis (three runs at the same T); without tie correction the ranking invents an order that does not exist and deflates ρ — which is exactly why the first version of this script reported +0.867 for perfectly separated data.

*Kaynak: `diagnostics/selection_audit/b015_verdict.json`*

**Direction asymmetry @swa.** At equal |signed gap|, how many times more an over-confident teacher costs the student than an under-confident one. Every comparison is made **within the same arm** (seed, dataset and recipe held fixed); the opposite branch is read from that arm's own linear fit, and the `extrapolated` field marks a point outside the fitted range.

| arm | |gap| | ECE (over-confident) | ECE (under-confident, same |gap|) | ratio | extrapolated |
|---|---|---|---|---|---|
| rafdb_stage1 | 0.0040 | 0.0428 | 0.0190 | **2.25×** | yes |
| rafdb_stage1 | 0.0338 | 0.0731 | 0.0388 | **1.88×** | yes |
| rafdb_stage1 | 0.0431 | 0.0797 | 0.0450 | **1.77×** | no |
| rafdb_vae9182 | 0.0042 | 0.0330 | 0.0248 | **1.33×** | yes |
| rafdb_vae9182 | 0.0248 | 0.0447 | 0.0397 | **1.13×** | yes |
| ferplus | 0.0393 | 0.0587 | 0.0287 | **2.04×** | no |

**All comparisons: 1.74 ± 0.43×** (n=6). Those not relying on extrapolation (**these are the ones reported in the paper**): 1.77×, 2.04× → 1.91 ± 0.19× (n=2).

*Kaynak: `diagnostics/p1_dose_response/two_dataset_overlay.json`*

## T5 — Mechanism ablations (paired, within seed)

Every mechanism against **its own matched control**, within the same seed: control = same teacher, 400e/SWA@200, VICH head, α=0.3, unscaled teacher. Negative ΔECE = the mechanism calibrates better.

| teacher | mechanism | class weighting (both arms) | Δacc @swa (pp) | ΔECE @swa | ΔECE @best | ΔECE @last | signs @swa | n |
|---|---|---|---|---|---|---|---|---|
| stage1 | adaptive_t | effective_number | +0.16 ± 0.32 | -0.0011 ± 0.0033 | +0.0029 ± 0.0033 | -0.0046 ± 0.0050 | `++-` | 3 |
| stage1 | ctkd | effective_number | -0.03 *(n=1)* | +0.0058 *(n=1)* | +0.0144 *(n=1)* | +0.0153 *(n=1)* | `+` | 1 |
| stage1 | g2g_kl | effective_number | +0.41 ± 0.38 | -0.0042 ± 0.0004 | -0.0017 ± 0.0051 | -0.0015 ± 0.0063 | `---` | 3 |
| stage1 | gate:mean_logvar | none | -0.10 ± 0.12 | -0.0012 ± 0.0010 | +0.0024 ± 0.0039 | +0.0023 ± 0.0028 | `+--` | 3 |
| stage1 | gate:oracle_error | none | -0.22 ± 0.46 | +0.0015 ± 0.0036 | +0.0040 ± 0.0035 | +0.0021 ± 0.0016 | `-++` | 3 |
| stage1 | gate:target_logvar | none | +0.25 ± 0.28 | -0.0041 ± 0.0023 | +0.0004 ± 0.0021 | -0.0006 ± 0.0040 | `---` | 3 |
| stage1 | logit_std | effective_number | -0.23 ± 0.20 | +0.0906 ± 0.0023 | +0.1252 ± 0.0033 | +0.1090 ± 0.0106 | `+++` | 3 |
| primary | adaptive_t | effective_number | -0.39 ± 0.37 | +0.0023 ± 0.0007 | +0.0047 ± 0.0034 | -0.0043 ± 0.0040 | `+++` | 3 |
| primary | ctkd | effective_number | -0.49 *(n=1)* | +0.0038 *(n=1)* | +0.0048 *(n=1)* | +0.0125 *(n=1)* | `+` | 1 |
| primary | g2g_kl | effective_number | -0.14 ± 0.36 | -0.0016 ± 0.0027 | -0.0043 ± 0.0060 | -0.0111 ± 0.0022 | `+--` | 3 |
| primary | gate:mean_logvar | none | +0.20 ± 0.85 | -0.0056 ± 0.0092 | -0.0075 ± 0.0057 | -0.0030 ± 0.0055 | `--+` | 3 |
| primary | gate:oracle_error | none | -0.01 ± 0.72 | +0.0004 ± 0.0053 | -0.0050 ± 0.0041 | +0.0025 ± 0.0040 | `-++` | 3 |
| primary | gate:target_logvar | none | -0.09 ± 0.44 | -0.0008 ± 0.0030 | -0.0064 ± 0.0023 | -0.0042 ± 0.0036 | `+--` | 3 |
| primary | logit_std | effective_number | -0.32 ± 0.25 | +0.0859 ± 0.0058 | +0.1191 ± 0.0113 | +0.1044 ± 0.0068 | `+++` | 3 |
| vae9182 | adaptive_t | effective_number | +0.28 ± 0.57 | -0.0042 ± 0.0047 | +0.0024 ± 0.0030 | +0.0009 ± 0.0035 | `--+` | 3 |
| vae9182 | ctkd | effective_number | -0.13 *(n=1)* | +0.0038 *(n=1)* | +0.0027 *(n=1)* | +0.0026 *(n=1)* | `+` | 1 |
| vae9182 | g2g_kl | effective_number | +0.16 ± 0.41 | +0.0009 ± 0.0043 | +0.0014 ± 0.0043 | -0.0047 ± 0.0048 | `-++` | 3 |
| vae9182 | g2g_kl+adaptive_t | effective_number | -0.07 *(n=1)* | -0.0018 *(n=1)* | +0.0024 *(n=1)* | +0.0004 *(n=1)* | `-` | 1 |
| vae9182 | gate:mean_logvar | none | -0.27 ± 0.67 | +0.0015 ± 0.0046 | +0.0050 ± 0.0052 | +0.0016 ± 0.0064 | `+--` | 3 |
| vae9182 | gate:oracle_error | none | -0.23 ± 0.49 | +0.0056 ± 0.0040 | +0.0081 ± 0.0036 | +0.0052 ± 0.0065 | `+++` | 3 |
| vae9182 | logit_std | effective_number | -0.12 ± 0.82 | +0.1388 ± 0.0013 | +0.1573 ± 0.0096 | +0.1593 ± 0.0115 | `+++` | 3 |

### T5a — `logit_std`: invisible in accuracy, destructive in calibration

| teacher | Δacc @swa | Δacc @best | Δacc @last | ΔECE @swa | ΔECE @best | ΔECE @last | n |
|---|---|---|---|---|---|---|---|
| primary | -0.32 | -0.43 | -0.27 | **+0.0859** | **+0.1191** | **+0.1044** | 3 |
| stage1 | -0.23 | -0.32 | -0.52 | **+0.0906** | **+0.1252** | **+0.1090** | 3 |
| vae9182 | -0.12 | -0.52 | -0.58 | **+0.1388** | **+0.1573** | **+0.1593** | 3 |

**Same direction in 3/3 teachers and 3/3 checkpoints** (9/9 observations, all ΔECE > 0).

The two axes are in different units, so the comparison is made **in units of their own seed noise**. Denominator: the mean **@swa** seed sd of the three teachers' `effective_number` control arms — acc 0.279 pp, ECE 0.0016; read **at the same checkpoint as the numerator** (see `diagnostics/paper_tables/denominator_table.md`):

| axis | range of the effect | in units of seed sd |
|---|---|---|
| accuracy | -0.58 … -0.12 pp | typically **1.3×** (at most 2.1×) |
| ECE | +0.0859 … +0.1593 | typically **77×** (at least 55×) |

Relative to noise, the calibration damage is typically **58.8 times** the accuracy effect, and **≥27 times** even in the worst comparison. The claim rests on the floor. The mechanism is plain: logit standardisation erases scale by construction, and confidence values live precisely on that scale, while the argmax — and therefore accuracy — is scale-invariant.

> This row is the cleanest instance of the paper's **'accuracy alone misleads'** argument: in an accuracy-based ablation table `logit_std` looks harmless and would most likely have been reported as neutral.

✅ **Pre-registered, confirmed at n=3 seeds** (P1, frozen 2026-07-29 01:23:40, first run 01:24:08 — `rafdb_p1_logit_std_seeds_queue.ps1`; see `diagnostics/PREREGISTRATIONS.md` A7). All three predictions held: ΔECE > 0 in all three teachers · 3/3 same sign in each teacher · the calibration effect exceeds the accuracy effect in noise units (narrowest margin at primary, **23×**; widest at vae9182, 213×). This row is no longer a single-seed observation.

**Sign consistency is this campaign's disqualification rule**: if the three seeds disagree in sign, the effect cannot be separated from seed noise. `selection_robustness` further shows that for some mechanisms the result changes direction with the **choice of checkpoint** — those rows must be reported as null.

*Kaynak: `runs.csv` · `diagnostics/selection_audit/selection_audit_unfrozen.csv` · `diagnostics/selection_audit/selection_robustness.json`*

## T6 — Teacher selection recipe

| teacher | own acc | own ECE | T\* | student acc @best | student ECE @best | n |
|---|---|---|---|---|---|---|
| stage1 | 92.24 | 0.0378 | 1.349 | 89.75 ± 0.08 | 0.0627 | 3 |
| primary | 92.01 | 0.0396 | 1.261 | 89.57 ± 0.09 | 0.0606 | 3 |
| vae9182 | 91.82 | 0.0136 | 0.983 | 90.28 ± 0.19 | 0.0274 | 3 |

- Spearman(teacher **acc**, student acc) = **-0.50** → picking the most accurate teacher is the **wrong** rule.
- Spearman(−teacher **ECE**, student acc) = **+1.00** → picking the best-calibrated teacher is the right rule.
- Does the accuracy rule pick the right teacher: **False** (it picks `stage1`) · ECE rule: **True** (it picks `vae9182`)
- **Cost of the wrong pick: 0.52 pp** of student accuracy (@best; see the per-checkpoint table below — the primary value is @swa).

### T6a — the same question at all three checkpoints

| teacher | student acc @swa | @best | @last |
|---|---|---|---|
| vae9182 | 89.95 ± 0.37 (n=3) | 90.28 ± 0.19 (n=3) | 89.82 ± 0.17 (n=3) |
| stage1 | 89.60 ± 0.34 (n=3) | 89.75 ± 0.08 (n=3) | 88.99 ± 0.10 (n=3) |
| primary | 89.60 ± 0.13 (n=3) | 89.57 ± 0.09 (n=3) | 88.49 ± 0.26 (n=3) |

| checkpoint | ranking by student acc | Spearman(teacher acc, student acc) | Spearman(−teacher ECE, student acc) | cost of the accuracy-pick |
|---|---|---|---|---|
| **@swa** | vae9182 > {stage1 = primary} | -0.866 | +0.866 | **0.35 pp** |
| @best | vae9182 > stage1 > primary | -0.500 | +1.000 | **0.52 pp** |
| @last | vae9182 > stage1 > primary | -0.500 | +1.000 | **0.83 pp** |

- The best teacher is the same at all three checkpoints: **True** (`vae9182`), and **no pairwise comparison reverses** between checkpoints (none).
- **Not a strict total order at @swa:** `stage1` and `primary` land on exactly 89.6023 pp, so the 2nd/3rd places are tied and the phrase "identical ranking" holds for the *winner*, not for the full order.
- The cost of the accuracy-criterion mistake is checkpoint-dependent: **0.35 pp @swa** (primary), 0.52 pp @best, 0.83 pp @last. Quoting one number without its checkpoint is what made the earlier 0.53/0.35 discrepancy look like a contradiction.

> Student columns come from **runs.csv + selection audit, T=1 baseline arm (is_ablation_control, cw=effective_number); columns above are @best**.

*Kaynak: `diagnostics/p4_teacher_selection/p4_teacher_selection.json`*

## T7 — FERPlus human-vote alignment (teacher and student)

**Teacher side** (closed form from the cached logits, zero GPU cost):

| T | role | teacher ECE | signed gap | teacher JSD | teacher entropy |
|---|---|---|---|---|---|
| 0.26 | over-sharpened (sign flipped to OVER-confident) | 0.0393 | +0.0393 | 0.0659 | 0.1161 |
| 0.5063 | T*_NLL / T*_ECE region -- calibrated against HARD labels | 0.0156 | -0.0117 | 0.0490 | 0.2562 |
| 0.74 | T*_JSD -- aligned with the 10-rater HUMAN distribution | 0.0665 | -0.0649 | 0.0440 | 0.4119 |
| 1 | native (under-confident, soft-vote-trained) | 0.1282 | -0.1277 | 0.0492 | 0.6118 |

Human mean entropy (10-rater distribution): **0.4401** nats.

**Student side — TWO AXES, MANDATORY.** Scoring the student on hard-label ECE alone lets T\*_ECE win by construction, so every arm is scored on both axes. The student softmax is taken at T=1 (the deployed output).

**@swa** *(primary)*

| T | teacher ECE | student ECE | student JSD | student entropy | ρ(entropy, human) | n |
|---|---|---|---|---|---|---|
| 0.26 | 0.0393 | 0.0587 ± 0.0038 | 0.0737 ± 0.0007 | 0.1244 | 0.667 | 3 |
| 0.5063 | 0.0156 | 0.0185 ± 0.0016 | 0.0587 ± 0.0005 | 0.2548 | 0.683 | 3 |
| 0.74 | 0.0665 | 0.0344 ± 0.0012 | 0.0536 ± 0.0004 | 0.3840 | 0.702 | 3 |
| 1 | 0.1282 | 0.0783 ± 0.0046 | 0.0551 ± 0.0005 | 0.5465 | 0.704 | 3 |

argmin student ECE: **T=0.5063** · argmin student JSD: **T=0.74**

**@best**

| T | teacher ECE | student ECE | student JSD | student entropy | ρ(entropy, human) | n |
|---|---|---|---|---|---|---|
| 0.26 | 0.0393 | 0.0568 ± 0.0014 | 0.0732 ± 0.0009 | 0.1295 | 0.653 | 3 |
| 0.5063 | 0.0156 | 0.0196 ± 0.0020 | 0.0587 ± 0.0007 | 0.2663 | 0.678 | 3 |
| 0.74 | 0.0665 | 0.0483 ± 0.0083 | 0.0541 ± 0.0005 | 0.4200 | 0.696 | 3 |
| 1 | 0.1282 | 0.0927 ± 0.0070 | 0.0569 ± 0.0003 | 0.5858 | 0.696 | 3 |

argmin student ECE: **T=0.5063** · argmin student JSD: **T=0.74**

**@last**

| T | teacher ECE | student ECE | student JSD | student entropy | ρ(entropy, human) | n |
|---|---|---|---|---|---|---|
| 0.26 | 0.0393 | 0.0591 ± 0.0015 | 0.0739 ± 0.0004 | 0.1296 | 0.661 | 3 |
| 0.5063 | 0.0156 | 0.0191 ± 0.0061 | 0.0591 ± 0.0015 | 0.2663 | 0.679 | 3 |
| 0.74 | 0.0665 | 0.0377 ± 0.0007 | 0.0544 ± 0.0006 | 0.4088 | 0.697 | 3 |
| 1 | 0.1282 | 0.0852 ± 0.0082 | 0.0572 ± 0.0005 | 0.5790 | 0.694 | 3 |

argmin student ECE: **T=0.5063** · argmin student JSD: **T=0.74**

**Trade-off @swa:** distilling at T\*_JSD costs **+0.0159** in hard-label ECE and gains **-0.0051** in human JSD. The two targets are distinct: one has to choose whether to calibrate to argmax labels or to human uncertainty.

**Why JSD and not ρ.** Across the four arms ρ(entropy, human) moves only within 0.667–0.704 (span **0.038**), while student JSD moves over 0.0536–0.0737 (span **0.0201**, typical between-seed sd 0.0005 — i.e. the span is ~40× the noise). Because ρ measures ranking, it is nearly insensitive to teacher temperature: a monotone rescaling preserves the ranking. The criterion that discriminates between arms is **JSD**; ρ is reported only as a consistency check.

*Kaynak: `diagnostics/ferplus_jsd/ferplus_teacher_signed_grid.json` · `diagnostics/ferplus_jsd/ferplus_student_jsd.json` · `diagnostics/ferplus_jsd/ferplus_jsd.json`*

## T8 — Selection audit (how much of 'best' is real, how much is looking)

| dataset | contrast | Δacc (pp) | ΔECE | n runs |
|---|---|---|---|---|
| RAF-DB | best − last | +0.77 ± 0.43 | -0.0029 ± 0.0092 | 131 |
| RAF-DB | best − swa | +0.13 ± 0.26 | -0.0006 ± 0.0118 | 118 |
| FERPlus | best − last | +0.50 ± 0.21 | +0.0041 ± 0.0074 | 12 |
| FERPlus | best − swa | +0.22 ± 0.21 | +0.0069 ± 0.0088 | 12 |

**Pure order-statistic component** (from the training logs, without looking at any checkpoint): the maximum of the last K epochs minus their mean. This is the gain that comes from picking the best of K draws even if the model never improves.

| K | max(last K) − mean(last K), pp | global argmax inside last K | n runs |
|---|---|---|---|
| 50 | +0.645 ± 0.203 | 34% | 131 |
| 100 | +0.764 ± 0.259 | 67% | 131 |

> The per-epoch variant **cannot be computed for ECE**: `training_log.csv` does not record per-epoch ECE and no per-epoch checkpoints are kept (only best/last/swa). The closest calibration-sensitive proxy, the selected epoch's validation NLL, is reported instead.

*Kaynak: `diagnostics/selection_audit/selection_audit.csv` · `diagnostics/selection_audit/ferplus_selection_audit.csv` · `diagnostics/selection_audit/selection_gain.json`*

## T9 — Efficiency

| model | params (M) | GMACs | file (MB) | acc (%) |
|---|---|---|---|---|
| POSTERv2 (VAE head, VAE9182) | 58.334 | 8.483 | 555.02 | 91.82 |
| MobileNetV2Plus + VICH head | 2.248 | 0.329 | 8.83 | 90.28 ± 0.19 |
| **ratio (teacher/student)** | **25.9×** | **25.8×** | **62.9×** | retention **98.32%** |

**Latency** — median ± IQR, broken down by device/batch/dtype. Measured on an idle machine (verified that no queue was running beforehand); warm-up and iteration counts are in the table.

| device | model | batch | dtype | median (ms) | IQR (ms) | per image (ms) | FPS | warm-up/iters |
|---|---|---|---|---|---|---|---|---|
| cuda | student MobileNetV2Plus VICH | 1 | fp32 | 5.41 | 2.59 | 5.413 | 185 | 50/200 |
| cuda | student MobileNetV2Plus VICH | 1 | fp16 | 6.52 | 0.29 | 6.519 | 153 | 50/200 |
| cuda | student MobileNetV2Plus VICH | 32 | fp32 | 9.87 | 0.63 | 0.308 | 3243 | 50/200 |
| cuda | student MobileNetV2Plus VICH | 32 | fp16 | 6.19 | 0.34 | 0.194 | 5166 | 50/200 |
| cuda | teacher POSTERv2 VAE | 1 | fp32 | 10.46 | 0.48 | 10.460 | 96 | 50/200 |
| cuda | teacher POSTERv2 VAE | 1 | fp16 | 13.97 | 0.68 | 13.971 | 72 | 50/200 |
| cuda | teacher POSTERv2 VAE | 32 | fp32 | 38.59 | 0.65 | 1.206 | 829 | 50/200 |
| cuda | teacher POSTERv2 VAE | 32 | fp16 | 24.15 | 0.47 | 0.755 | 1325 | 50/200 |
| cpu | student MobileNetV2Plus VICH | 1 | fp32 | 11.23 | 1.08 | 11.226 | 89 | 5/20 |
| cpu | student MobileNetV2Plus VICH | 32 | fp32 | 161.64 | 10.36 | 5.051 | 198 | 5/20 |
| cpu | teacher POSTERv2 VAE | 1 | fp32 | 44.98 | 1.68 | 44.980 | 22 | 5/20 |
| cpu | teacher POSTERv2 VAE | 32 | fp32 | 716.70 | 13.74 | 22.397 | 45 | 5/20 |

> Environment: NVIDIA GeForce RTX 5070 · torch 2.10.0+cu128 (CUDA 12.8) · Windows-11-10.0.26200-SP0 · measured 2026-07-26T10:20:37Z · cudnn_benchmark=False.

**fp16 — two independent sessions.** Pre-registered rule: this observation enters the paper only if it replicates in an independent second session. The ratio below is fp16/fp32 median latency; **>1 = fp16 is SLOWER**.

| model | batch | session 1 | session 2 | same direction |
|---|---|---|---|---|
| student_MobileNetV2Plus_VICH | 1 | 1.20× | 1.24× | ✅ |
| teacher_POSTERv2_VAE | 1 | 1.34× | 1.20× | ✅ |
| student_MobileNetV2Plus_VICH | 32 | 0.63× | 0.68× | ✅ |
| teacher_POSTERv2_VAE | 32 | 0.63× | 0.69× | ✅ |

> ✅ **REPLICATED — the footnote enters the paper.** At batch=1, fp16 is SLOWER than fp32 in both sessions and for both models; at batch=32 it is faster, as expected. The explanation: at batch=1 the workload is kernel-launch bound rather than compute bound, so there is no arithmetic over which to amortise fp16's cast cost. Practical consequence: **the advice to 'use fp16' is wrong for single-image inference on this hardware.**

*Kaynak: `diagnostics/p5_efficiency/p5_efficiency.json` · `diagnostics/p5_efficiency/latency_benchmark.csv` · `diagnostics/p5_efficiency/latency_benchmark_session2.csv` · `diagnostics/p5_efficiency/latency_benchmark.json`*

## T10 — Student capacity: does the law live on the teacher side or the student side?

The width sweep is **entirely scratch-initialised** (`student_pretrained=False`), so the curve is internally consistent. The campaign's main baseline (pretrained, width 1.0) is at the same width but a different init, so it does **not** sit on the curve; it is given as a separate row and measures the cost of pretraining.

| cell | params (M) | acc @swa | ECE @swa | acc @best | ECE @best | n |
|---|---|---|---|---|---|---|
| scratch w050 | 0.712 | 86.15 ± 0.07 | 0.0365 ± 0.0057 | 86.38 ± 0.15 | 0.0354 ± 0.0017 | 3 |
| scratch w075 | 1.380 | 87.31 ± 0.08 | 0.0388 ± 0.0042 | 87.61 ± 0.20 | 0.0329 ± 0.0049 | 3 |
| scratch w100ns | 2.248 | 88.09 ± 0.15 | 0.0374 ± 0.0030 | 88.33 ± 0.20 | 0.0329 ± 0.0025 | 3 |
| pretrained w100 | 2.248 | 89.95 ± 0.37 | 0.0330 ± 0.0020 | 90.28 ± 0.19 | 0.0274 ± 0.0021 | 3 |

**What each axis buys (same checkpoint, paired):**

| checkpoint | width 3.16× (0.71→2.25 M) | pretraining (width held fixed) |
|---|---|---|
| @swa | +1.94 pp · ΔECE +0.0010 | +1.86 pp · ΔECE -0.0045 |
| @best | +1.96 pp · ΔECE -0.0025 | +1.94 pp · ΔECE -0.0054 |
| @last | +1.98 pp · ΔECE -0.0074 | +2.04 pp · ΔECE -0.0011 |

**The law lives on the teacher side.** Same student, same checkpoint; the only difference is which axis is moved:

| checkpoint | student ECE span — capacity axis (3.16×) | teacher temperature axis (VAE9182, T=1→2.2) | ratio |
|---|---|---|---|
| @swa | 0.00235 | 0.1780 | **76×** |
| @best | 0.00254 | 0.2010 | **79×** |
| @last | 0.00743 | 0.1975 | **27×** |

### T10a — Does the law also hold for the small student (P3, exploratory)

The table above moves **one** axis at a time. This block instead sweeps the teacher axis **at a second capacity** — so it is here that the question 'is the law a large-student artefact?' is answered. Per the pre-registered analysis plan, the two slopes were fitted at **the same three temperatures** (T = 1, 1.7, 2.2 → teacher ECE 0.0136, 0.1454, 0.2622).

| capacity | init | slope b | R² | largest residual | seed-noise envelope |
|---|---|---|---|---|---|
| 2.248 M | pretrained | **0.716** | 0.99997 | 0.00057 | ±0.022 |
| 0.712 M | scratch | **0.655** | 0.99996 | 0.00056 | ±0.058 |

Slope difference **-0.061**, the two envelopes summed **±0.080** → the difference is **not resolvable**.

**Item (i) — established: the law also holds at 0.712 M.** Monotone, and the largest residual of either fit (0.00057 and 0.00056) is ~3× smaller than even the **smallest** seed sd among the cells (0.0020). The linearity therefore comes from the relationship itself, not from a fit having three points to land on. This is a **validity defence** that rules out the 'the law is a large-student artefact' alternative.

**Item (ii) — INCONCLUSIVE: whether the slope varies with capacity could not be measured.** Difference 0.061, noise envelope ±0.080. **Not resolvable ≠ no difference**: this is not a null finding but a test that could not be run. The sentence 'the slope does not change with capacity' **cannot be written** from this data.

> ⚠️ **Item (ii) is exploratory and two-variable; it does not have item (i)'s status.** The result is not pre-registered (the question and analysis plan are: `PREREGISTRATIONS.md` B4). `b_w050` is scratch and `b_2248` is pretrained — the two slopes differ in capacity *and* in initialisation; separating them would require a scratch dose-response at 2.248 M (4 runs, not launched). Two of w050's cells are also n=2. **This subsection stands apart from T10's capacity table**: the table is of established quality, item (ii) is exploratory.

*Kaynak: `diagnostics/selection_audit/selection_audit_unfrozen.csv` · `runs.csv` · `diagnostics/p1_dose_response/two_dataset_overlay.json` · `diagnostics/p5_efficiency/capacity_law_check.json`*

## Appendix — exclusion audit (which run dropped out of which table, and why)

This section is not a claim but a **machine check**: T5's control and treatment pools are built from the runs' own flags, and the rows below count what those filters actually excluded.

| reason for exclusion | n runs | example |
|---|---|---|
| budget 200e/swa- | 13 | `RAFDB_7cls_lightle_vich_from_vae9182_224` |
| budget 500e/swa200 | 9 | `RAFDB_vae9182_adaptive_t_b070_T6_224_500e_swa200_see` |
| α=0.1 | 6 | `RAFDB_stage1_p6alpha_a010_ts100_b070_T6_224_400e_swa` |
| α=0.5 | 6 | `RAFDB_stage1_p6alpha_a050_ts100_b070_T6_224_400e_swa` |
| α=0.7 | 6 | `RAFDB_stage1_p6alpha_a070_ts100_b070_T6_224_400e_swa` |
| α=0.9 | 6 | `RAFDB_stage1_p6alpha_a090_ts100_b070_T6_224_400e_swa` |
| teacher `unknown` not in the three-teacher grid · budget 200e/swa90 | 3 | `RAFDB_ce9241_betaKD_b070_T6_224_amp_classw` |
| head=`linear` | 3 | `RAFDB_vae9182_pluslinear_T6_224_400e_swa200_seed1` |
| teacher `unknown` not in the three-teacher grid | 2 | `RAFDB_bridge_baseline_b070_T6_224_400e_swa200_seed42` |
| budget 200e/swa90 | 2 | `RAFDB_vae9182_betaKD_b070_T6_224_amp_classw` |
| teacher `unknown` not in the three-teacher grid · budget 200e/swa90 · α=0.25 | 1 | `RAFDB_ce9241_betaKD_b075_T6_224_t256_reg005_amp_clas` |

**Legacy α=0.25 runs:** 1 on disk (`RAFDB_ce9241_betaKD_b075_T6_224_t256_reg005_amp_classw`, teacher `unknown`) · **not used** in T1–T7 or T9 (teacher not in the three-teacher grid, budget 200e/swa90, α≠0.3 — excluded by all three filters independently).

> ⚠️ **T8 is the one exception.** The selection-audit table deliberately pools **every** finished RAF-DB run; what it measures is not the effect of a condition but the artefact of argmax-val-acc selection across this whole corpus. The legacy `ce9241` runs **are** included there, and they should be. They appear in no other table.

## T11 — Does the law collapse onto the product T·τ? (P6.1)

Two matched pairs hold T·τ fixed while moving τ and T in opposite directions. If student ECE depended on (T,τ) only through the product, both cells of a pair would land within seed noise of each other. The bar was frozen before the runs at 2×0.0012 = 0.0024 (the seed sd of the control arm's ECE @swa). Full table: `paper_tables/p6_collapse_test.md`.

| pair (T·τ) | τ, T (low-τ cell) | τ, T (high-τ cell) | mean ΔECE | signs | \|mean\|/2×bar | verdict |
|---|---|---|---|---|---|---|
| T·τ = 5.10 | τ=3, T=1.70 | τ=6, T=0.85 | -0.0391 ± 0.0032 | 3/3 same | 16.3× | YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar) |
| T·τ = 10.20 | τ=6, T=1.70 | τ=12, T=0.85 | -0.0324 ± 0.0029 | 3/3 same | 13.5× | YANLIŞLAMA-bacağı sağlandı (3/3 aynı işaret VE |ort| ≥ 2×bar) |

ÇÖKME YANLIŞLANDI — iki çiftte birden 3/3 aynı işaret ve |ort ΔECE| ≥ 2×bar. Beyanın kendi sözleriyle: ayrışmanın kendisi bulgu — sıra bilgisi ile yumuşaklık ayrı kanallar.

The 2 Aug early reading (queue at ~10/42) is reproduced **bit-identically** — all six ΔECE values and both pair verdicts agree.

*Kaynak: `diagnostics/paper_tables/p6_collapse_test.json`*

## T12 — Does the KD weight α modulate the transfer? (P6.2, P6.3)

gap(α) := ECE(T=1) − ECE(T=1.3406), within seed, τ=6 throughout. A larger gap means the pre-scaling intervention moves the student more. Two rules were frozen before the runs: gap(α) is non-increasing in α (P6.2) and gap(0.9) < gap(0.1) strictly (P6.3), each required in 3/3 seeds.

| α | seed 42 | seed 1 | seed 43 | mean |
|---|---|---|---|---|
| 0.1 | +0.0197 | +0.0215 | +0.0262 | **+0.0224** |
| 0.3 | +0.0297 | +0.0296 | +0.0317 | **+0.0303** |
| 0.5 | +0.0344 | +0.0365 | +0.0271 | **+0.0327** |
| 0.7 | -0.0071 | +0.0003 | -0.0007 | **-0.0025** |
| 0.9 | -0.0307 | -0.0397 | -0.0351 | **-0.0352** |

**P6.2 (monotonicity): DOĞRULANMADI** — held in 0/3 seeds. **P6.3 (extremes): DOĞRULANDI** — held in 3/3 seeds.

The α=0.3 row reuses the existing dose-response arms, as the declaration specified; it is not a new run.

*Kaynak: `diagnostics/paper_tables/p6_collapse_test.json`*

## T13 — Multi-metric robustness of the dose–response (R3-1)

Seven metrics on the same 42 runs and the same cached logits. The question is not whether a metric is small but whether the metrics **agree about where the curve bottoms out**; if they do, the result is not an artefact of the 15-bin equal-width ECE specification. `steps` counts individual (T-pair, seed) steps that agree with the other seeds at the same pair. Full table: `paper_tables/robustness_metrics.md`.

| metric | RAF-DB stage1<br>argmin T · steps | RAF-DB vae9182<br>argmin T · steps | FERPlus<br>argmin T · steps |
|---|---|---|---|
| NLL | **1.3406** · 12/12 | 1* · 11/12 | **0.74** · 9/9 |
| Brier | 1.3406* · 10/12 | 1* · 10/12 | **0.5063** · 9/9 |
| ECE ew-10 | **1.3406** · 12/12 | **1** · 12/12 | **0.5063** · 9/9 |
| ECE ew-15 | 1.3406* · 11/12 | **1** · 12/12 | **0.5063** · 9/9 |
| ECE ew-25 | **1.3406** · 12/12 | **1** · 12/12 | **0.5063** · 9/9 |
| ECE em-15 | **1.3406** · 12/12 | **1** · 12/12 | **0.5063** · 9/9 |
| classwise-ECE | 1.3406* · 11/12 | **1** · 12/12 | **0.5063** · 9/9 |

Bold = all three seeds put the minimum at the same T; `*` = modal value, seeds disagree. Across all series and metrics, 224/231 steps agree with the other seeds at the same pair; every disagreement is listed in the full table.

*Kaynak: `diagnostics/paper_tables/robustness_metrics.json`*

## T14 — T\* fitting-criterion sensitivity (R3-2)

The deployed T\* minimises NLL; the reported quantity is ECE. This table prices that mismatch. Full table: `paper_tables/tstar_sensitivity.md`.

| teacher | T\*_NLL | T\*_ECE | \|ΔT\*\| | ΔECE (criterion cost) | ECE removed by TS |
|---|---|---|---|---|---|
| stage1 | 1.3494 | 1.3198 | 0.0296 | +0.00154 | +0.02198 |
| primary | 1.2613 | 1.2441 | 0.0172 | +0.00146 | +0.01985 |
| vae9182 | 0.9831 | 1.0572 | 0.0741 | +0.00432 | -0.00102 |
| ferplus | 0.5064 | 0.4530 | 0.0533 | +0.00846 | +0.11259 |

> The last column is why this table exists: in **vae9182** temperature scaling at the NLL optimum **increases** ECE, and the two criteria disagree about the direction of the correction — so 'the fitting criterion does not matter' cannot be written for every teacher.

*Kaynak: `diagnostics/paper_tables/tstar_sensitivity.json`*

## T15 — FERPlus JSD sensitivity to the vote-count stratum (R3-3)

The human target is built from each row's own vote sum, and that sum is not always 10. This table asks whether the ECE/JSD separation survives conditioning on vote resolution. Full table: `paper_tables/jsd_sensitivity.md`.

| slice | n | T\*_ECE | T\*_NLL | T\*_JSD | separation held |
|---|---|---|---|---|---|
| (a) all rows | 3153 | 0.46 | 0.50 | 0.74 | yes |
| (b) vote sum = 10 | 1977 | 0.42 | 0.46 | 0.74 | yes |
| (c) stratum 6-7 | 28 | 0.74 | 0.70 | 0.88 | yes |
| (c) stratum 8-9 | 1148 | 0.46 | 0.54 | 0.74 | yes |
| (c) stratum 10 | 1977 | 0.42 | 0.46 | 0.74 | yes |

*Kaynak: `diagnostics/paper_tables/jsd_sensitivity.json`*

