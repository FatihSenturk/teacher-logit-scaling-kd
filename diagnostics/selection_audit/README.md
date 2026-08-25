# Selection audit — the inclusion set is FROZEN (31 Jul 2026)

## What was frozen

**N = 131 runs**, cutoff `2026-07-31-06-00-00` (each run's own launch timestamp).
Code: [`diagnostics/selection_audit_table.py`](../selection_audit_table.py) → `AUDIT_CUTOFF`,
`AUDIT_FROZEN_N`. No run launched after the cutoff enters the audit; **P5's six runs will not**,
and neither will anything after them.

The script raises a `RuntimeError` if the frozen set does not come to 131 — so that a deleted run
directory, or a cutoff that stops separating campaigns, cannot silently produce a table at a
different N. `--ignore-cutoff` exists for inspecting new runs; the number quoted in the paper is
always the frozen one.

## Why it was frozen

The audit is a property of the **selection procedure**, not of an **experiment**, so it grew every
time the campaign added a phase: 116 → 125 → 131. Each growth required a correction in the abstract
and bought no scientific gain in return — the estimate stayed within **0.015 pp**, moving only
across 0.781 → 0.769 → 0.766 pp.

## Why the cutoff is not midnight on 30 July

The freeze was decided as "N = 131, cutoff 30 July"; those two are **not consistent**. P4's
sequential queue ran past midnight and its sixth control is stamped `2026-07-31-02-06-02`. A
literal 30 July cutoff yields **130** and drops one of the very six controls the freeze exists to
include. 31 July 06:00 falls after P4's last launch (02:06) and before P5's first (12:2x), so it
separates the two campaigns exactly and produces the intended N = 131.

The same subtlety governs the boundaries of the stability series: P1's six `logit_std` runs started
between 29 July 01:24 and 09:47, so a "midnight on 29 July" boundary would cut P1 in half and
report 110 instead of 116. Boundaries are therefore placed at the **gaps between campaigns**, not
at calendar midnights.

## Stability — the line for the text

| inclusion set | n | Δacc (best − last) |
|---|---|---|
| before P2 (the set the paper's current text quotes) | 116 | +0.781 ± 0.447 pp |
| after P2+P3 | 125 | +0.769 ± 0.438 pp |
| **after P4 — FROZEN, the number to quote** | **131** | **+0.766 ± 0.431 pp** |

**The span across the three sets is 0.015 pp.** That statement is stronger than any single N:

> *the estimate is insensitive to the inclusion set (n = 116 / 125 / 131 → +0.781 / +0.769 /
> +0.766 pp, span 0.015 pp)*

Producer: [`diagnostics/selection_optimism_headline.py`](../selection_optimism_headline.py) →
`stability_across_inclusion_sets` in `selection_optimism_headline.json`.

## Which comparison

The quoted number is **best − last**. `best − swa` answers a different question (the SWA average
has already flattened the late epochs, so it is a harder reference) and the two must not be
conflated:

| comparison | n | Δacc | ΔECE |
|---|---|---|---|
| best − last | 131 | +0.766 ± 0.431 pp | −0.0029 ± 0.0092 |
| best − swa | 118 | +0.129 ± 0.262 pp | −0.0006 ± 0.0118 |

In both cases ΔECE has an sd several times its mean, i.e. it is **null** — one cannot say
"selection also inflates calibration"; the inflation is on the accuracy axis (the selection
criterion), with calibration merely dragged along beside it.

## Scope

The audit is structurally closed to RAF-DB: it measures on the fold-3 validation split (n=3068) and
filters each run by the `dataset` field in its own `metrics_best.json` rather than guessing from
the name. The phrase "116/131 RAF-DB runs" is therefore exact; no run from another dataset can
enter.
