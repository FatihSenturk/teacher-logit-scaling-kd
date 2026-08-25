# G2.1 — Selection-audit contrasts: SD vs SE, with inference

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

Producer: `diagnostics/selection_audit_inference.py` · sample sd (n-1, Bessel-corrected), computed over seeds · paired one-sample t on within-run differences, df = n−1, two-sided

The `±` in `tab_selection_audit` is the **between-run SD**, not the uncertainty of the mean. This table separates them: SE = SD/√n.

## Accuracy contrasts (percentage points)

| dataset | contrast | mean | SD | n | SE | t | df | p (two-sided) | 95% CI |
|---|---|---|---|---|---|---|---|---|---|
| RAF-DB | best − last | +0.766 | 0.431 | 131 | 0.0377 | +20.33 | 130 | 3.33e-42 | [+0.691, +0.840] |
| RAF-DB | best − swa | +0.129 | 0.262 | 118 | 0.0241 | +5.36 | 117 | 4.26e-07 | [+0.081, +0.177] |
| FERPlus | best − last | +0.500 | 0.210 | 12 | 0.0607 | +8.22 | 11 | 5.02e-06 | [+0.366, +0.633] |
| FERPlus | best − swa | +0.225 | 0.210 | 12 | 0.0605 | +3.71 | 11 | 0.0034 | [+0.091, +0.358] |

## ECE contrasts

| dataset | contrast | mean | SD | n | SE | t | df | p (two-sided) | 95% CI |
|---|---|---|---|---|---|---|---|---|---|
| RAF-DB | best − last | -0.0029 | 0.0092 | 131 | 0.00081 | -3.57 | 130 | 0.0005 | [-0.0045, -0.0013] |
| RAF-DB | best − swa | -0.0006 | 0.0118 | 118 | 0.00108 | -0.53 | 117 | 0.5946 | [-0.0027, +0.0016] |
| FERPlus | best − last | +0.0041 | 0.0074 | 12 | 0.00215 | +1.90 | 11 | 0.0839 | [-0.0006, +0.0088] |
| FERPlus | best − swa | +0.0069 | 0.0088 | 12 | 0.00254 | +2.71 | 11 | 0.0202 | [+0.0013, +0.0125] |

## ECE contrast relative to the scale of student ECE

The magnitude of an ECE contrast cannot be read on its own. Three denominators are reported rather than one, because picking a single denominator after seeing the result would be choosing the yardstick to fit the number.

| dataset | contrast | \|mean ΔECE\| | as % of mean ECE @last | as % of median ECE @last | as % of mean ECE @best |
|---|---|---|---|---|---|
| RAF-DB | best − last | 0.0029 | 3.9% (0.0733) | 4.5% (0.0633) | 4.1% (0.0704) |
| RAF-DB | best − swa | 0.0006 | 0.8% (0.0720) | 0.8% (0.0682) | 0.8% (0.0714) |
| FERPlus | best − last | 0.0041 | 8.1% (0.0503) | 8.5% (0.0481) | 7.5% (0.0544) |
| FERPlus | best − swa | 0.0069 | 14.5% (0.0475) | 15.0% (0.0460) | 12.7% (0.0544) |

Source files: `diagnostics/selection_audit/selection_audit.csv` (the frozen N=131 inclusion set the paper quotes) and `diagnostics/selection_audit/ferplus_selection_audit.csv` (N=12). The unfrozen 179-run superset is **not** used here.

