# G3.5 — Bootstrap confidence intervals

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

Producer: `diagnostics/bootstrap_cis.py` · sample sd (n-1, Bessel-corrected), computed over seeds · B = 2000 · percentile CIs · RNG seed 20260806 · ECE = 15-bin equal-width · T grid 0.5–2.5 step 0.02

Two different resampling units, chosen deliberately:

- **Sample bootstrap** for teacher ECE, T\*, headroom and T\*_JSD — the uncertainty there comes from a finite validation set, so evaluation samples are resampled.
- **Cluster bootstrap** for the pooled ρ — the uncertainty there is that there are only three curves. Series are resampled, not points.

## Teacher-side quantities (sample bootstrap)

| teacher | n | ECE(T=1) | T\*_NLL | T\*_ECE | headroom (Eq. 8) |
|---|---|---|---|---|---|
| stage1 | 3068 | 0.0378 [0.0311, 0.0469] | 1.340 [1.30, 1.40] | 1.320 [1.28, 1.38] | +0.0232 [+0.0151, +0.0305] |
| primary | 3068 | 0.0396 [0.0339, 0.0501] | 1.260 [1.22, 1.30] | 1.240 [1.18, 1.28] | +0.0213 [+0.0154, +0.0280] |
| vae9182 | 3068 | 0.0136 [0.0107, 0.0241] | 0.980 [0.94, 1.02] | 1.060 [0.92, 1.08] | +0.0023 [+0.0000, +0.0080] |
| ferplus | 3153 | 0.1282 [0.1196, 0.1375] | 0.500 [0.50, 0.54] | 0.500 [0.50, 0.54] | +0.1131 [+0.1039, +0.1174] |

Headroom is reported in the Eq. 8 sense (ECE at T=1 minus the grid minimum), which is non-negative by construction. The alternative definition used in earlier text (ECE(T=1) − ECE at T\*_NLL) is in the JSON as `headroom_nllstar`; it can be negative, which is what `headroom_review` flagged.

## Pooled ρ — and why the resampling unit changes the answer

| resampling unit | ρ | 95% CI |
|---|---|---|
| **series (clustered, 3 clusters)** | 0.789 | [0.577, 1.000] |
| points (naive, 14 points) | 0.789 | [0.380, 0.960] |

**The clustered interval is not simply wider — and that is worth stating plainly, because the expected result was that it would be.** Its width is 0.423 against the naive 0.580, and it sits higher. The reason is structural: each series is individually near-monotone in \|gap\|, so resampling whole series preserves that monotonicity (and duplicates it), whereas resampling individual points can break it. Clustering does not add noise here; it removes the one source of noise the naive scheme was manufacturing.

**The real limitation is resolution, not width.** With three clusters there are only ten distinct multisets to draw, so the clustered ρ takes at most a handful of values — 14 distinct values across 2000 replicates. The upper bound sitting exactly at 1.000 is a symptom of that granularity, not a claim that ρ could be 1. Neither interval should be read as a smooth 95% region; what n = 3 teachers buys is a direction, not a calibrated uncertainty.

Sources: cached teacher logits (`teacher_ece_grid/teacher_val_logits_*.pt`, `ferplus_jsd/ferplus_val_logits.pt`), `p1_dose_response/two_dataset_overlay.json` and `paper_tables/robustness_metrics.json`. No forward pass, no GPU.

