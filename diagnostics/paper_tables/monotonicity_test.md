# G2.2 — What axis is "monotone within all nine seed curves" measured on?

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

Producer: `diagnostics/monotonicity_test.py` · metric `ece_ew_15` (the paper's 15-bin equal-width ECE) · @swa · sample sd (n-1, Bessel-corrected), computed over seeds

The abstract's monotonicity claim never names its axis. This table runs the same nine seed curves on three candidate axes. (b) and (c) differ **only** by whether the two miscalibration branches are pooled, so the pair isolates what pooling does.

| axis | definition | seed curves passing |
|---|---|---|
| (a) T | points ordered by teacher pre-scaling T; monotone in either direction | **0/9** |
| (b) signed gap, within branch | split by sign of teacher signed gap, then ordered by \|gap\| within each branch; student ECE non-decreasing | **9/9** |
| (c) unsigned \|gap\|, pooled | all points ordered by \|gap\|, branches pooled; student ECE non-decreasing | **3/9** |

## RAF-DB stage1

| seed | (a) T axis | (b) within branch | (c) pooled \|gap\| |
|---|---|---|---|
| 42 | ✗ T=0.85→T=1 (-0.0053) | ✓ (2 branch tested) | ✗ |gap|=0.0338→|gap|=0.0427 (-0.0256) |
| 1 | ✗ T=1.7→T=2.2 (-0.0598) | ✓ (2 branch tested) | ✗ |gap|=0.0338→|gap|=0.0427 (-0.0306) |
| 43 | ✗ T=0.85→T=1 (-0.0051) | ✓ (2 branch tested) | ✗ |gap|=0.0338→|gap|=0.0427 (-0.0289) |

Branch composition: over-confident (gap>0): 3 point(s), over-smooth (gap<0): 2 point(s).

## RAF-DB vae9182

| seed | (a) T axis | (b) within branch | (c) pooled \|gap\| |
|---|---|---|---|
| 42 | ✗ T=0.85→T=1 (-0.0094) | ✓ (2 branch tested) | ✓ |
| 1 | ✗ T=0.85→T=1 (-0.0118) | ✓ (2 branch tested) | ✓ |
| 43 | ✗ T=0.85→T=1 (-0.0140) | ✓ (2 branch tested) | ✓ |

Branch composition: over-confident (gap>0): 2 point(s), over-smooth (gap<0): 3 point(s).

## FERPlus

| seed | (a) T axis | (b) within branch | (c) pooled \|gap\| |
|---|---|---|---|
| 42 | ✗ T=0.26→T=0.5063 (-0.0401) | ✓ (1 branch tested) | ✗ |gap|=0.0393→|gap|=0.0649 (-0.0211) |
| 1 | ✗ T=0.26→T=0.5063 (-0.0438) | ✓ (1 branch tested) | ✗ |gap|=0.0393→|gap|=0.0649 (-0.0299) |
| 43 | ✗ T=0.26→T=0.5063 (-0.0368) | ✓ (1 branch tested) | ✗ |gap|=0.0393→|gap|=0.0649 (-0.0220) |

Branch composition: over-confident (gap>0): 1 point(s)  **not testable**, over-smooth (gap<0): 3 point(s).

---

Sources: `paper_tables/robustness_metrics.json` (seed-level student ECE) and `p1_dose_response/two_dataset_overlay.json` (teacher signed gap). No re-measurement: both are existing artifacts.

