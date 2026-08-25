# N11 — FERPlus headroom: which grid, which number

> **Review-responsive, not pre-declared (15 Aug 2026).** Written to settle a contradiction between two already-published artifacts; no prediction was frozen beforehand.

Producer: `diagnostics/headroom_grid_audit.py` · sources: cached teacher logits (`ferplus_jsd/ferplus_val_logits.pt`, `teacher_ece_grid/teacher_val_logits_*.pt`), `ferplus_jsd.json`, `ferplus_teacher_signed_grid.json` · ECE = 15-bin equal-width · B = 2000 · percentile CIs · RNG seed 20260806 · no forward pass, no GPU.

The two numbers use **the same formula, the same 3153 samples, the same binning and the same cached logits**. The only thing that differs is the grid G that `min_{T∈G}` runs over — and G is part of the estimand, not an implementation detail.

## 1 · The same quantity on three grids

| grid | definition | argmin T | ECE@argmin | headroom | 95% CI | argmin on a grid bound? |
|---|---|---|---|---|---|---|
| `run` — actually-run arms (`ferplus_teacher_signed_grid`) | [0.26, 1], non-uniform, 4 points | 0.5063 | 0.0156 | **0.1126** | [0.1018, 0.1165] | no (interior) |
| `boot` — `bootstrap_cis.T_GRID` | [0.5, 2.5], step 0.02, 101 points | 0.5 | 0.0151 | **0.1131** | [0.1039, 0.1174] | **yes — lower** |
| `fine` — `ferplus_jsd.sweep` | [0.1, 4], step 0.02, 196 points | 0.46 | 0.0084 | **0.1198** | [0.1069, 0.1269] | no (interior) |

ECE(T=1) is common to all three: 0.1282.

**Why 0.1131's interval excludes 0.1198, and why that is not a paradox.** The refinement's optimum sits at T = 0.46, which is *below* the bootstrap grid's floor of 0.5. A minimum taken over a subset can only be larger, so `headroom(boot) ≤ headroom(fine)` holds by construction — 0.1131 ≤ 0.1198. The interval [0.1039, 0.1174] is a percentile interval for the *truncated* estimand and contains its own point estimate; it was never an interval for 0.1198. No bias correction, no BCa, no normal approximation is involved — see `ci_type` in the JSON.

**The truncation is visible in the data, not only in the code.** On the bootstrap grid the FERPlus argmin lands on the grid's lower bound in 78.5% of the 2000 replicates (point estimate: on the bound). On the run grid it is interior in 100.0% and on the refinement grid the optimum is interior as well.

## 2 · Which grid truncates, and for whom

| teacher | argmin T on `bootstrap_cis.T_GRID` | truncated? |
|---|---|---|
| stage1 | 1.32 | no |
| primary | 1.24 | no |
| vae9182 | 1.06 | no |
| ferplus | 0.50 | **yes — sits on the 0.50 floor** |

**Headroom is not the only casualty.** The same floor truncates the published FERPlus **T\*_ECE**: the continuous argmin is 0.45305 (`tstar_sensitivity`, bounded Brent) and the 196-point grid puts it at 0.46, both below the 0.5 floor, so `bootstrap_cis` can only report 0.50 [0.50, 0.54] — an interval whose lower end is the floor itself. Anywhere the paper quotes that interval it is quoting a censored quantity, not an estimate of where the optimum is.

This is why the RAF-DB rows of the two artifacts agree in direction and the FERPlus row does not: the RAF-DB optima are interior to the bootstrap grid, so a denser step moves them slightly and nothing more. FERPlus is the only teacher whose optimum is outside that grid altogether.

**Correction to the 14 Aug audit (`number_audit_round3`, item 9).** That item answered "is the Appendix-B interval boundary-constrained?" with **no**, having checked the RAF-DB fine sweep and the 196-point FERPlus sweep. It did not check `bootstrap_cis.T_GRID`, which is the grid the Appendix-B *interval* actually comes from and whose lower bound is exactly the 0.50 the panel asked about. On that grid the FERPlus optimum does sit on the bound. The panel's question was right and yesterday's answer was wrong; the 14 Aug record stands as written and is corrected here.

## 3 · Cross-check against the published artifacts

| quantity | published | re-measured here | |Δ| |
|---|---|---|---|
| headroom_review.eq8 (0.1198) | 0.119824 | 0.119824 | 1.07e-08 |
| headroom_review.deployed (0.1126) | 0.112605 | 0.112605 | 2.21e-08 |
| bootstrap_cis.headroom_eq8 (0.1131) | 0.113113 | 0.113113 | 0.00e+00 |
| bootstrap_cis.ci_lo | 0.103907 | 0.103907 | 0.00e+00 |
| bootstrap_cis.ci_hi | 0.117432 | 0.117432 | 0.00e+00 |
| ferplus_jsd.ece_T1 | 0.128233 | 0.128233 | 1.55e-08 |

Largest deviation 2.21e-08 (tolerance 1e-06); the residual is the float32 cache versus float64 recomputation, not a difference of method. **This script introduces no fourth definition** — it re-measures the two published ones and adds the interval the run grid never had.

## 4 · What the paper should carry

Under the binding rule adopted on 11 Aug 2026 — Eq. 8 is `min_{T∈G}` with G the grid **actually swept** — the primary number is **0.1126 [0.1018, 0.1165]** at T = 0.5063, the temperature the deployed arm was run at (verified: the run grid's ECE argmin is that same temperature). The other two are refinements over grids no arm was run on:

- **0.1198** ("0.120") — a genuine finer-resolution minimum at T = 0.46; quotable only as *what a denser sweep would reach*, never under the same name as the headline.
- **0.1131** ("0.1131") — neither of the above. It is the minimum of a grid that stops before the optimum, so it is an artifact of the bootstrap script's own T range. It should not appear in the paper at all; if the supplement wants an interval for the headline, it is the `run` row above.

Note on the near-coincidence: the headline 0.1126 and the truncated 0.1131 agree to three decimals (0.0005 apart) because both grids' minima land near T ≈ 0.5. They are still two different estimands, and "0.113" currently names both — which is exactly how the contradiction survived unnoticed.

