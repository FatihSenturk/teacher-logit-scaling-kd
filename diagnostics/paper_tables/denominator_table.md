# Denominator table — every ratio in 5.4 on one convention

Producer: `diagnostics/denominator_table.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds

**Adopted convention: the seed sd of the treatment's OWN CONTROL ARM**, per teacher, in **the same class-weighting mode the treatment ran in**. Rationale: (a) it is a property of the control, not of the contrast — it does not shrink when a mechanism turns out to be reproducible; (b) it is the same auxiliary quantity the pre-registered P2/P5 decision rules use; (c) it is **defined even on n=1 rows** — half of T5's gate rows are n=1 and a paired sd does not exist there at all; (d) it is per teacher, so a teacher whose students are inherently noisy is not judged against someone else's noise floor.

## Control arms (the denominators)

| teacher | class weighting | acc mean ± **sd** | ECE mean ± **sd** | n | seeds |
|---|---|---|---|---|---|
| primary | `effective_number` | 89.602 ± **0.130** | 0.0707 ± **0.0015** | 3 | [1, 42, 43] |
| primary | `none` | 89.266 ± **0.394** | 0.0755 ± **0.0033** | 3 | [1, 42, 43] |
| stage1 | `effective_number` | 89.602 ± **0.340** | 0.0731 ± **0.0012** | 3 | [1, 42, 43] |
| stage1 | `none` | 89.657 ± **0.100** | 0.0745 ± **0.0021** | 3 | [1, 42, 43] |
| vae9182 | `effective_number` | 89.950 ± **0.366** | 0.0330 ± **0.0020** | 3 | [1, 42, 43] |
| vae9182 | `none` | 90.146 ± **0.207** | 0.0278 ± **0.0027** | 3 | [1, 42, 43] |

> Gate rows take the `none` arm as denominator and every other mechanism takes the `effective_number` arm — because each treatment is differenced against the control in its own mode (`METHODS_DATA.md` §5A.2).

## Every T5 row, in units of its own control arm's sd (@swa)

| teacher | mechanism | cw | Δacc | acc sd | **Δacc / sd** | ΔECE | ECE sd | **ΔECE / sd** | n |
|---|---|---|---|---|---|---|---|---|---|
| primary | adaptive_t | `effective_number` | -0.391 | 0.130 | **3.00×** | +0.0023 | 0.0015 | **1.5×** | 3 |
| primary | ctkd | `effective_number` | -0.489 | 0.130 | **3.75×** | +0.0038 | 0.0015 | **2.5×** | 1 |
| primary | g2g_kl | `effective_number` | -0.141 | 0.130 | **1.08×** | -0.0016 | 0.0015 | **1.1×** | 3 |
| primary | gate:mean_logvar | `none` | +0.196 | 0.394 | **0.50×** | -0.0056 | 0.0033 | **1.7×** | 3 |
| primary | gate:oracle_error | `none` | -0.011 | 0.394 | **0.03×** | +0.0004 | 0.0033 | **0.1×** | 3 |
| primary | gate:target_logvar | `none` | -0.087 | 0.394 | **0.22×** | -0.0008 | 0.0033 | **0.2×** | 3 |
| primary | logit_std | `effective_number` | -0.315 | 0.130 | **2.42×** | +0.0859 | 0.0015 | **56.7×** | 3 |
| stage1 | adaptive_t | `effective_number` | +0.163 | 0.340 | **0.48×** | -0.0011 | 0.0012 | **0.9×** | 3 |
| stage1 | ctkd | `effective_number` | -0.033 | 0.340 | **0.10×** | +0.0058 | 0.0012 | **4.9×** | 1 |
| stage1 | g2g_kl | `effective_number` | +0.413 | 0.340 | **1.21×** | -0.0042 | 0.0012 | **3.6×** | 3 |
| stage1 | gate:mean_logvar | `none` | -0.098 | 0.100 | **0.98×** | -0.0012 | 0.0021 | **0.6×** | 3 |
| stage1 | gate:oracle_error | `none` | -0.217 | 0.100 | **2.18×** | +0.0015 | 0.0021 | **0.7×** | 3 |
| stage1 | gate:target_logvar | `none` | +0.250 | 0.100 | **2.51×** | -0.0041 | 0.0021 | **2.0×** | 3 |
| stage1 | logit_std | `effective_number` | -0.228 | 0.340 | **0.67×** | +0.0906 | 0.0012 | **76.6×** | 3 |
| vae9182 | adaptive_t | `effective_number` | +0.282 | 0.366 | **0.77×** | -0.0042 | 0.0020 | **2.1×** | 3 |
| vae9182 | ctkd | `effective_number` | -0.130 | 0.366 | **0.36×** | +0.0038 | 0.0020 | **1.9×** | 1 |
| vae9182 | g2g_kl | `effective_number` | +0.163 | 0.366 | **0.44×** | +0.0009 | 0.0020 | **0.5×** | 3 |
| vae9182 | g2g_kl+adaptive_t | `effective_number` | -0.065 | 0.366 | **0.18×** | -0.0018 | 0.0020 | **0.9×** | 1 |
| vae9182 | gate:mean_logvar | `none` | -0.272 | 0.207 | **1.31×** | +0.0015 | 0.0027 | **0.5×** | 3 |
| vae9182 | gate:oracle_error | `none` | -0.228 | 0.207 | **1.10×** | +0.0056 | 0.0027 | **2.1×** | 3 |
| vae9182 | logit_std | `effective_number` | -0.120 | 0.366 | **0.33×** | +0.1388 | 0.0020 | **69.5×** | 3 |

## Reconciliation with the pooled denominator T5a currently uses

T5a currently uses the **mean** seed sd of the three teachers' `effective_number` baseline cells (acc **0.279** pp, ECE **0.0016**). The two conventions separate on the `logit_std` rows as follows:

| teacher | ΔECE | pooled denominator | ratio | own arm's denominator | ratio |
|---|---|---|---|---|---|
| stage1 | +0.0906 | 0.0016 | 58× | 0.0012 | **77×** |
| primary | +0.0859 | 0.0016 | 55× | 0.0015 | **57×** |
| vae9182 | +0.1388 | 0.0016 | 89× | 0.0020 | **69×** |

> **Which one the text uses.** The pooled denominator is appropriate for T5a's *across-teachers* claim ("in all three teachers the calibration effect exceeds the accuracy effect in noise units"), because that needs one common scale. **Any sentence about a single cell** must use that cell's own arm's denominator. Which denominator is in use has to be stated in the sentence — 5.4 as it currently stands does not state it, and that is exactly why "74×" does not hold under any convention.

> **Number withdrawn:** "its control's seed spread (0.82 pp)". 0.818 pp is the **paired Δacc sd** of `vae9182/logit_std`; the same cell's control arm's own accuracy seed sd is **0.366 pp**. The number was right, its label was wrong.

