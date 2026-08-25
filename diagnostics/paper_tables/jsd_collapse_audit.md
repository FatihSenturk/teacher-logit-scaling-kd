# N12 — The JSD collapse: 37× or 40×? One numerator, two denominators

> **Review-responsive, not pre-declared (17 Aug 2026).** Written to settle a contradiction between an internal audit and an external review; no prediction was frozen beforehand.

Producer: `diagnostics/jsd_collapse_audit.py` · sources: published @swa student logits (`diagnostics/student_logits/`), `ferplus_jsd/ferplus_val_logits.pt`, `configs/FERPlus_majority_metadata.csv` · reporting set n=3153 · @swa · seeds (42, 1, 43) · sample sd (n-1, Bessel-corrected), computed over seeds · no forward pass, no GPU.

The paper prints two ratios whose **numerator is the same number** and whose denominators both round to `0.0005` at four decimals. They are not the same denominator, and the two ratios are not the same quantity. Both sentences sit in the same subsection (`sections/05_results_discussion.tex`, `\label{sec:res_human}`): the *noise* ratio in the subsection body and the *collapse* ratio in its `\paragraph{What post-hoc student scaling can and cannot do}`.

## 1 · The two ratios

| ratio | definition | numerator | denominator | value | printed as |
|---|---|---|---|---|---|
| `R_collapse` | span of the four **raw** arms ÷ span of the four arms **after one cross-fitted student-side scalar** | 0.020083 | 0.000539 | **37.23** | **37×** |
| `R_noise` | span of the four **raw** arms ÷ **typical seed sd** (mean over arms) | 0.020083 | 0.000504 | **39.81** | **40×** |

The numerator is the same in both rows: the raw JSD span between arm T=0.26 (0.073681) and arm T=0.74 (0.053598).

### Where each field lives

| quantity | artifact | field |
|---|---|---|
| numerator | `paper_tables/r3w1_joint_optimum.json` | `arms.0.26.jsd_arm[0]` − `arms.0.74.jsd_arm[0]` |
| numerator (same value, second artifact) | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa.0.26.jsd[0]` − `by_checkpoint.swa.0.74.jsd[0]` |
| `R_collapse` denominator | `paper_tables/r3w1_joint_optimum.json` | `arms.0.74.jsd_ts[0]` − `arms.0.26.jsd_ts[0]` |
| `R_noise` denominator | `ferplus_jsd/ferplus_student_jsd.json` | mean of `by_checkpoint.swa.*.jsd[1]` over the four arms |

## 2 · The four arms, raw and after student-side TS

| T (teacher pre-scaling) | role | JSD raw | JSD +TS | ECE raw | ECE +TS |
|---|---|---|---|---|---|
| 0.26 | over-sharpened | 0.073681 ± 0.000733 | **0.054045 ± 0.000399** | 0.0587 ± 0.0038 | 0.0266 ± 0.0005 |
| 0.5063 | T*_ECE / T*_NLL | 0.058690 ± 0.000462 | **0.054274 ± 0.000209** | 0.0185 ± 0.0016 | 0.0296 ± 0.0016 |
| 0.74 | T*_JSD | 0.053598 ± 0.000373 | **0.054584 ± 0.000249** | 0.0344 ± 0.0012 | 0.0246 ± 0.0041 |
| 1.0 | native | 0.055107 ± 0.000450 | **0.054545 ± 0.000506** | 0.0783 ± 0.0046 | 0.0203 ± 0.0017 |

## 3 · Where "40" comes from — two routes, both belonging to `R_noise`

**Route 1 — dividing the printed values.** The paper prints the numerator as `0.0201` and the denominator as `0.0005`. Divide those and you get **40.20**, which rounds to 40. Divide the ledger values and you get **37.23**. Four-decimal rounding on a denominator of order 5e-4 moves the ratio by 3.0 — this is the same failure mode as the "13–14 times smaller" case (`number_audit_round3` item 2), where both sides divided rounded table cells.

**Route 2 — the other ratio is genuinely ≈40.** To make `R_collapse` equal exactly 40 the denominator would have to be **0.000502**. The mean seed sd is **0.000504** — 0.47% away. The post-TS span is **0.000539** — 6.91% away. So "40" is not a rounding of the collapse ratio; it is the *noise* ratio, correct in its own sentence and wrong in this one. Both denominators print as `0.0005` and `0.0005` (identical at 4 dp), which is how one sentence's number could migrate into the other's without either author noticing.

**All five seed-sd conventions** (the choice `number_audit_round3` item 7 flagged as unresolved):

| convention | typical seed sd | `R_noise` |
|---|---|---|
| mean sd | 0.000504 | 39.81 |
| median sd | 0.000456 | 44.05 |
| largest sd | 0.000733 | 27.39 |
| smallest sd | 0.000373 | 53.87 |
| pooled sd | 0.000523 | 38.43 |

`R_noise` is between 27.4 and 53.9 depending on which reduction of the four arms' seed sds is called "typical"; the mean-sd reading (39.81) is the one the published "roughly forty" matches. The convention must be named in the text — the sd convention itself (sample sd over seeds) is campaign-wide and fixed, but *which* reduction across arms is "typical" is a free choice and currently unstated.

## 4 · Honesty note: the collapse ratio's denominator is itself at noise level

After scaling, the four arms span 0.000539, while one bar — R3-W1's own definition, 2× the largest post-TS seed sd — is 0.001012. The span is **inside** one bar, i.e. the four post-TS arms are not separable from each other at three seeds. That is exactly what the sentence claims ("onto a common value"), but it also means `R_collapse` is a ratio to a quantity that is itself indistinguishable from zero.

The consequence is visible if the ratio is formed inside each seed instead of from the seed means: 20.9 / 35.4 / 16.9, i.e. 24.4 ± 9.8 — all three below 37.2. The direction is expected and is not a defect of either estimator: a span is a max minus a min, so it is biased upward by noise, and averaging three seeds per arm first removes some of that noise from the denominator while the between-arm signal it is measuring is already ~0. The published estimand (spans of seed means) is the right one to report and is what both ratios use throughout this table; the point is that **the multiplier carries no more than two significant figures of information**. The defensible claim is *the axis collapses to within seed noise* — for which 37 versus 40 changes nothing scientifically, and everything about whether a reader who divides the printed numbers gets the paper's own value.

## 5 · Cross-check against the published artifacts

All 35 checks below re-derive the published values from the published logits through the *imported* R0-1/R3-W1 code path, not by reading them back:

| quantity | published | re-measured here | |Δ| |
|---|---|---|---|
| r3w1.arms[0.26].jsd_arm mean | 0.07368071 | 0.07368071 | 0.0e+00 |
| r3w1.arms[0.26].jsd_arm sd | 0.00073317 | 0.00073317 | 0.0e+00 |
| r3w1.arms[0.26].jsd_ts mean | 0.05404463 | 0.05404463 | 0.0e+00 |
| r3w1.arms[0.26].jsd_ts sd | 0.00039916 | 0.00039916 | 0.0e+00 |
| r3w1.arms[0.26].ece_arm mean | 0.05874081 | 0.05874081 | 0.0e+00 |
| r3w1.arms[0.26].ece_ts mean | 0.02659055 | 0.02659055 | 0.0e+00 |
| ferplus_student_jsd.swa[0.26].jsd mean | 0.07368071 | 0.07368071 | 0.0e+00 |
| ferplus_student_jsd.swa[0.26].jsd sd | 0.00073317 | 0.00073317 | 0.0e+00 |
| r3w1.arms[0.5063].jsd_arm mean | 0.05869022 | 0.05869022 | 0.0e+00 |
| r3w1.arms[0.5063].jsd_arm sd | 0.00046157 | 0.00046157 | 0.0e+00 |
| r3w1.arms[0.5063].jsd_ts mean | 0.05427386 | 0.05427386 | 0.0e+00 |
| r3w1.arms[0.5063].jsd_ts sd | 0.00020913 | 0.00020913 | 0.0e+00 |
| r3w1.arms[0.5063].ece_arm mean | 0.01849860 | 0.01849860 | 0.0e+00 |
| r3w1.arms[0.5063].ece_ts mean | 0.02964618 | 0.02964618 | 0.0e+00 |
| ferplus_student_jsd.swa[0.5063].jsd mean | 0.05869022 | 0.05869022 | 0.0e+00 |
| ferplus_student_jsd.swa[0.5063].jsd sd | 0.00046157 | 0.00046157 | 0.0e+00 |
| r3w1.arms[0.74].jsd_arm mean | 0.05359789 | 0.05359789 | 0.0e+00 |
| r3w1.arms[0.74].jsd_arm sd | 0.00037277 | 0.00037277 | 0.0e+00 |
| r3w1.arms[0.74].jsd_ts mean | 0.05458399 | 0.05458399 | 0.0e+00 |
| r3w1.arms[0.74].jsd_ts sd | 0.00024939 | 0.00024939 | 0.0e+00 |
| r3w1.arms[0.74].ece_arm mean | 0.03436323 | 0.03436323 | 0.0e+00 |
| r3w1.arms[0.74].ece_ts mean | 0.02455943 | 0.02455943 | 0.0e+00 |
| ferplus_student_jsd.swa[0.74].jsd mean | 0.05359789 | 0.05359789 | 0.0e+00 |
| ferplus_student_jsd.swa[0.74].jsd sd | 0.00037277 | 0.00037277 | 0.0e+00 |
| r3w1.arms[1.0].jsd_arm mean | 0.05510710 | 0.05510710 | 0.0e+00 |
| r3w1.arms[1.0].jsd_arm sd | 0.00045023 | 0.00045023 | 0.0e+00 |
| r3w1.arms[1.0].jsd_ts mean | 0.05454466 | 0.05454466 | 0.0e+00 |
| r3w1.arms[1.0].jsd_ts sd | 0.00050605 | 0.00050605 | 0.0e+00 |
| r3w1.arms[1.0].ece_arm mean | 0.07830038 | 0.07830038 | 0.0e+00 |
| r3w1.arms[1.0].ece_ts mean | 0.02026965 | 0.02026965 | 0.0e+00 |
| ferplus_student_jsd.swa[1.0].jsd mean | 0.05510710 | 0.05510710 | 0.0e+00 |
| ferplus_student_jsd.swa[1.0].jsd sd | 0.00045023 | 0.00045023 | 0.0e+00 |
| number_audit_round3 item7 span | 0.02008283 | 0.02008283 | 0.0e+00 |
| number_audit_round3 item7 ratio(mean sd) | 39.81261945 | 39.81261945 | 0.0e+00 |
| number_audit_round3 item7 mean sd | 0.00050443 | 0.00050443 | 0.0e+00 |

Largest deviation 0.0e+00 (tolerance 1e-12). Both authorities' inputs are reproduced exactly: R3-W1's four arms (raw and post-TS, JSD and ECE) and `number_audit_round3` item 7's span and mean-sd ratio. **This script adds no third definition** — the cross-fit block and the arm list are imported from `r3w1_joint_optimum`, the split/fit/measure functions from `student_ts_baseline`.

## 6 · Correction to the 14 Aug audit (`number_audit_round3`, item 7)

Item 7 asked which of the paper's two numbers was right and answered "~40× correct, 37× not reproducible". Its measurement is arithmetically sound but it only ever tried **seed-sd denominators** — five of them, listed above — and never the post-TS span. It read `ferplus_jsd/ferplus_student_jsd.json`, which contains the raw arms and their seed sds and nothing about student-side scaling; the post-TS arms live in a different artifact, `paper_tables/r3w1_joint_optimum.json`, which item 7 did not open. 37× is not unreproducible: its producer `r3w1_joint_optimum.py` prints it directly from `spread_arm / spread_ts` and the value is 37.23. The external review's reading is the correct one for the post-hoc-scaling paragraph's sentence, and item 7's is the correct one for the subsection body's.

The 14 Aug record stands as written — it is a dated declaration — and is corrected here, under today's date. The dangerous half of that verdict was not the arithmetic but the instruction it implied: "37 is not reproducible" invites editing 37 into 40, which turns a correct sentence into an incorrect one. That the edit happened is on the record in the audit itself — item 7's `published` field, written on 14 Aug, reads `37× ve ~40× (aynı 0.0005)`, so the collapse sentence carried 37× then and carries 40× now.

## 7 · What the paper should carry

1. **The "collapse onto a common value" sentence: `37×`**, not 40×. Numerator and denominator are both *spans across arms* — before and after scaling — so the name "collapse" belongs here and nowhere else. Its producer already prints 37× in `paper_tables/r3w1_joint_optimum.md`; the paper and the artifact disagree only because the paper's copy was changed.
2. **The "times the noise" sentence: `40×` stands**, but name the denominator and quote it to five decimals — "a typical seed spread of 0.00050 (the mean of the four arms' seed sds), roughly forty times the noise" — so the two sentences stop sharing the string `0.0005`. Naming it is not cosmetic: the reduction is a free choice and the ratio runs 27–54 across the five readings above. If a pooled estimator is preferred, it is 0.00052 → 38.4×, which the same prose still covers. The word "collapse" must not appear in this sentence, and "noise" must not appear in the other.
3. **Neither number may be re-derived from printed values.** 0.0201/0.0005 = 40.20 is how 40 was produced for the wrong sentence; the ledger value is 37.23. Same rule, same failure mode as item 2's "13–14 times smaller".

