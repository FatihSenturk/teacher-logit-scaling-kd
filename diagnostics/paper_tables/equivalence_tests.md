# G3.4 — Equivalence (TOST): auditing the "indistinguishable" claims

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

Producer: `diagnostics/equivalence_tests.py` · sample sd (n-1, Bessel-corrected), computed over seeds · α = 0.05 · two one-sided tests, paired, df = n−1

A large p-value is **not** evidence of equivalence; it only says a difference could not be demonstrated. At n = 3 that distinction is decisive, because power is low enough that almost nothing can be demonstrated. TOST asks the right question: is the difference demonstrably **inside** a margin declared in advance?

**Margin, declared before reading any result:** δ = 2 × the seed sd of the comparison's own control/reference arm — deliberately the *same* number as the campaign's `established effect` threshold (G3.1), so that "a real effect" and "a negligible difference" are measured against one ruler rather than two.

| test | mean diff | 90% CI | δ | p (TOST) | outcome |
|---|---|---|---|---|---|
| primary/gate:oracle_error | -0.011 | [-1.228, +1.206] | ±0.789 | 0.1015 | inconclusive |
| stage1/gate:oracle_error | -0.217 | [-0.987, +0.553] | ±0.199 | 0.5243 | inconclusive |
| vae9182/gate:oracle_error | -0.228 | [-1.060, +0.603] | ±0.414 | 0.2905 | inconclusive |
| FERPlus ECE: student-TS − T*-arm | +0.0018 | [-0.0034, +0.0069] | ±0.0032 | 0.2535 | inconclusive |
| FERPlus JSD: student-TS − T*-arm | -0.0041 | [-0.0049, -0.0034] | ±0.0009 | 0.9967 | **difference beyond margin** |

**0** equivalence established · **1** difference beyond the margin · **4** inconclusive (of 5).

### One row is not underpowered — it is a difference

A failed TOST has two very different causes, and collapsing them would be the error this table exists to prevent. Where the 90% CI straddles ±δ the data are simply uninformative. But for **FERPlus JSD: student-TS − T*-arm** the interval lies **entirely outside** the margin, on one side: that is a demonstrated difference larger than δ, not an absence of evidence. It should be reported as a difference, with its direction.

### What this means for the wording

For every **inconclusive** test the defensible sentence is **"no evidence for a difference"**, not "statistically indistinguishable" and not "equivalent". The 90% CIs above show why: they extend beyond ±δ, so a difference as large as the margin cannot be excluded by these data.

This is a power statement, not a claim that the arms differ. With n = 3 and df = 2, TOST is close to unable to certify equivalence at any margin a reader would find interesting; the honest report is the interval, not a verdict.

Sources: `paper_tables/criterion_applied.json` (oracle cells and their control-arm sds) and `paper_tables/student_ts_baseline.json` (§5.7 per-seed values). Nothing is recomputed from checkpoints here.

