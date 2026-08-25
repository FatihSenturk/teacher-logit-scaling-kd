# 8(b) — The calibration law × student capacity

> ⚠️ **EXPLORATORY — THE RESULT IS NOT PRE-REGISTERED.** No *prediction* about capacity was frozen before these runs. What was frozen is **the question and the analysis plan** (`PREREGISTRATIONS.md` B4, 2026-07-29 01:28:02); this script executes that plan. In the paper this section will be labelled exploratory.

Producer: `diagnostics/capacity_law_check.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds

## How many temperatures exist at each capacity

| capacity | init | teacher-temperature points | slope? |
|---|---|---|---|
| 2.248 M | pretrained | **5** (0.85, 1, 1.3406, 1.7, 2.2) | ✅ |
| 0.712 M | scratch | **3** (1, 1.7, 2.2) | ✅ |
| 1.380 M | scratch | **1** (1) | ❌ |
| 2.248 M | scratch | **1** (1) | ❌ |

P3 (4 runs, finished 2026-07-30 08:58:50) added T=1.7 and T=2.2 at width 0.5, so **a second slope now exists**. 1.380 M still has a single point, so that capacity does not enter this comparison.

## 1. Two slopes, over the same three temperatures

The comparison is made **on the same fit support**: putting a 5-point fit against a 3-point fit would confound capacity with fit support (written in B4 before the runs).

| teacher ECE | T | student ECE @swa — 2.248 M (pretrained) | n | student ECE @swa — 0.712 M (scratch) | n |
|---|---|---|---|---|---|
| 0.0136 | 1 | 0.0330 ± 0.0020 | 3 | 0.0365 ± 0.0057 | 3 |
| 0.1454 | 1.7 | 0.1282 ± 0.0030 | 3 | 0.1236 ± 0.0040 | 2 |
| 0.2622 | 2.2 | 0.2109 ± 0.0034 | 3 | 0.1992 ± 0.0087 | 2 |

| capacity | slope b | intercept | R² | largest residual | seed-noise envelope (±1 sd, NOT a confidence interval) |
|---|---|---|---|---|---|
| 2.248 M (pretrained) | **0.716** | +0.0235 | 0.99997 | 0.00057 | ±0.022 |
| 0.712 M (scratch) | **0.655** | +0.0278 | 0.99996 | 0.00056 | ±0.058 |

> **R² is not an informative statistic on three points**, so the residuals are given as well. What matters is this: the largest residual of either fit (0.00057 ve 0.00056) kendi is **3.5–15.3× below** its own cells' seed sd (sd range 0.0020–0.0087) — so the linearity comes from the relationship itself, not from a fit landing on three points. (Lower bound 3.5×; against the smallest sd, calling it 'an order of magnitude' would be an overstatement, hence the range.) The residual *pattern* is also nearly identical at the two capacities (-0.00027, +0.00057, -0.00030 ve -0.00026, +0.00056, -0.00030), so the slight residual curvature is a structural feature of the teacher-ECE axis, not seed noise.

Slope difference **-0.061** (8.6% shallower), the two envelopes summed **±0.080**.

> **The slope difference is not resolvable.** Seed noise alone can move the slope by ±0.080, while the observed difference is 0.061. So *'the slope changes with capacity'* cannot be said from this data — but what can be said is worth more: **the law also holds for a student 3.16× smaller** (monotone, R²=1.0000), and its slope is not distinguishably different from the large student's. Calibration transfer is not a large-student artefact.

> ⚠️ **Two variables at once.** `b_w050` is scratch and `b_2248` is pretrained — the two slopes differ in capacity *and* in initialisation. Separating them requires a scratch dose-response at 2.248 M (4 runs, **not launched**). This confound was written in B4 before the runs.

> ⚠️ **The envelope is not a confidence interval.** w050's T=1.7 and T=2.2 cells are n=2, i.e. one degree of freedom; producing a t interval from that would be theatre. The envelope is obtained by pushing each cell mean by one measured seed sd in the direction that moves the slope most — i.e. the **upper bound** on how far noise could carry the slope.

5-point fit (for the record only, **not used** in the comparison): b = 0.714, kesme +0.0237, R² = 0.999, n = 5.

## 2. Capacity at a fixed teacher (scratch, same teacher T=1.0)

| capacity | student ECE @swa | student acc @swa | n |
|---|---|---|---|
| 0.712 M | 0.0365 ± 0.0057 | 86.15 ± 0.07 | 3 |
| 1.380 M | 0.0388 ± 0.0042 | 87.31 ± 0.08 | 3 |
| 2.248 M | 0.0374 ± 0.0030 | 88.09 ± 0.15 | 3 |

Capacity span **0.0024**, typical between-seed sd **0.0043** — so the span is **0.5× the noise**. A 3.16× capacity difference does not move student ECE distinguishably from seed noise.

## 3. What can and cannot be said

| iddia | durum |
|---|---|
| Student ECE is flat across a 3.16× capacity range (at a single teacher) | ✅ measured |
| At 2.248 M the law is monotone and near-linear (R²=0.999, 5 points) | ✅ measured |
| **The law also holds at 0.712 M** (monotone, R²=1.0000, 3 points) | ✅ **measured by P3** |
| Does the slope change with capacity | ⚠️ **measured, unresolved** — difference 0.061, noise envelope ±0.080 |
| Does the slope difference come from **capacity** | ❌ not measured (scratch/pretrained confound) |
| Does the law hold at 1.380 M | ❌ not measured (single point) |

## 4. What is missing to close this line

| design | new runs | what it buys |
|---|---|---|
| 2.248 M scratch dose-response (T=1.0/1.7/2.2, 1 seed + existing) | 4 | separates scratch from pretrained — the right to attribute the slope difference to capacity |
| a third seed at T=1.7/2.2 for w050 | 2 | lifts the n=2 cells to n=3, narrows the envelope by ~40% |
| T=1.7/2.2 at 1.380 M (2 seeds) | 4 | a third capacity → a slope-vs-capacity curve |

> These runs were **not launched**. The experiment freeze is in force and the capacity frontier is supplementary; this addition only makes sense with explicit approval.

