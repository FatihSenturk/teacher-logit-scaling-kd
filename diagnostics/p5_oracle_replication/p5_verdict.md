# P5 verdict — does `gate:oracle_error`'s calibration harm replicate?

Producer: `diagnostics/p5_oracle_replication_verdict.py` · @swa primary · sample sd (n-1, Bessel-corrected), computed over seeds

> **Pre-registered.** The decision rule was frozen inside `rafdb_p5_oracle_replication_queue.ps1` at 2026-07-31 14:14:11; the first run started at 14:14:40 (**+29 seconds**). Rule: *3/3 same sign **AND** |ΔECE| ≥ 2 × the ECE seed sd of that arm's own `cw=none` control* → ESTABLISHED; otherwise UNRESOLVED.

## Verdict

| teacher | ΔECE (@swa) | signs | bar | 2×bar | |ΔECE|/bar | verdict |
|---|---|---|---|---|---|---|
| stage1 | **+0.0015** ± 0.0036 | `+-+` | 0.0021 | 0.0042 | 0.74× | **UNRESOLVED** |
| primary | **+0.0004** ± 0.0053 | `+-+` | 0.0033 | 0.0066 | 0.11× | **UNRESOLVED** |

| _reference: vae9182 (P2, the finding being replicated)_ | _+0.0056 ± 0.0040_ | `+++` | — | — | — | _established in P2_ |

## Differences paired within seed (@swa)

| teacher | seed | Δacc (pp) | ΔECE |
|---|---|---|---|
| stage1 | 42 | -0.359 | +0.0039 |
| stage1 | 1 | +0.293 | -0.0026 |
| stage1 | 43 | -0.587 | +0.0033 |
| primary | 42 | -0.522 | +0.0047 |
| primary | 1 | +0.815 | -0.0055 |
| primary | 43 | -0.326 | +0.0020 |

## Kollar (@swa)

| teacher | arm | acc (%) | ECE | n |
|---|---|---|---|---|
| stage1 | kontrol (`cw=none` baseline) | 89.657 ± 0.100 | 0.0745 ± 0.0021 | 3 |
| stage1 | tedavi (`gate:oracle_error`) | 89.439 ± 0.370 | 0.0760 ± 0.0017 | 3 |
| primary | kontrol (`cw=none` baseline) | 89.266 ± 0.394 | 0.0755 ± 0.0033 | 3 |
| primary | tedavi (`gate:oracle_error`) | 89.255 ± 0.375 | 0.0759 ± 0.0024 | 3 |

## Does the verdict depend on the checkpoint choice

| teacher | checkpoint | Δacc (pp) | ΔECE | ECE signs |
|---|---|---|---|---|
| stage1 | swa *(birincil)* | -0.217 ± 0.457 | +0.0015 ± 0.0036 | `+-+` |
| stage1 | best | -0.272 ± 0.240 | +0.0040 ± 0.0035 | `+++` |
| stage1 | last | -0.369 ± 0.285 | +0.0021 ± 0.0016 | `+++` |
| primary | swa *(birincil)* | -0.011 ± 0.722 | +0.0004 ± 0.0053 | `+-+` |
| primary | best | +0.141 ± 0.488 | -0.0050 ± 0.0041 | `---` |
| primary | last | -0.217 ± 0.420 | +0.0025 ± 0.0040 | `+-+` |

## Reading — text fixed in advance

**UNRESOLVED in both teachers.** The mean effects have the same sign as the one measured in VAE9182, but their magnitudes stay below twice that arm's own seed noise — that is, in these two teachers the harm **could not be measured**.

**This is NOT a null finding.** The bar is twice a single arm's seed sd; an effect below it an effect below it is not counted as absent but as unmeasurable. The sentence "the gate does not degrade calibration in stage1 and primary" **cannot be written** from this data.

**D1's closing rationale stays conditional.** In the text: even with perfect information the gate brings no accuracy gain in any teacher (Δacc ≤ 0 in all three); the calibration harm was **established in VAE9182 and unresolved in stage1 and primary**. The no-accuracy-gain leg of the rationale is written unconditionally, the calibration-harm leg conditionally on VAE9182.

> The Δacc axis points the same way in all three teachers: even with perfect information the gate yields no accuracy gain. The gate's closure rests mainly on this row, and P5 strengthened it by adding two more teachers.

*Source: `selection_audit_unfrozen.csv` (the unfrozen superset; the frozen `selection_audit.csv` carries only T8's N=131 and was not used for this verdict) · `runs.csv`*

