# K1 — FERPlus student-side scaling, ECE axis (derived from r3w1, no new eval)

Source: `r3w1_joint_optimum.json` per_seed · @swa · n=3153 · sample sd (n-1, Bessel-corrected), computed over seeds

| arm (teacher pre-scale T) | raw ECE | scaled ECE | raw JSD | scaled JSD |
|---|---|---|---|---|
| 0.26 | 0.0587 ± 0.0038 | 0.0266 ± 0.0005 | 0.0737 ± 0.0007 | 0.0540 ± 0.0004 |
| 0.5063 | 0.0185 ± 0.0016 | 0.0296 ± 0.0016 | 0.0587 ± 0.0005 | 0.0543 ± 0.0002 |
| 0.74 | 0.0344 ± 0.0012 | 0.0246 ± 0.0041 | 0.0536 ± 0.0004 | 0.0546 ± 0.0002 |
| 1.0 | 0.0783 ± 0.0046 | 0.0203 ± 0.0017 | 0.0551 ± 0.0005 | 0.0545 ± 0.0005 |

- ECE: raw span **0.0598** (0.5063..1.0) -> scaled span **0.0094** (1.0..0.5063); collapse **6.4x**, spread removed **84.3%** (denominator: raw span).
- JSD: raw span 0.0201 -> scaled span 0.00054; collapse **37x** (the printed 37x).
- Scaled ranking by ECE: 1.0 < 0.74 < 0.26 < 0.5063; untreated beats T*_ECE 3/3 seeds, best-of-all 2/3.
