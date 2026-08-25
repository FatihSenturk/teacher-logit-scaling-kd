# R0-2 — Inferential tests: paired t + Holm

Producer: `diagnostics/inferential_tests.py` · @swa · ECE axis · sample sd (n-1, Bessel-corrected), computed over seeds · Holm family = the six rows of this table

> **n=3, df=2 — a known limitation.** This table is not a claim about power; it is the report of the procedure declared in §4. The campaign's actual decision instrument is pre-registered sign consistency plus 2×sd bars; the p values here sit alongside them, not in their place.

| # | contrast | ΔECE mean ± sd | per seed | t | df | p (raw) | p (Holm) |
|---|---|---|---|---|---|---|---|
| 1 | stage1: T*(1.3406) vs T=1 | -0.0303 ± 0.0012 | -0.0297 / -0.0296 / -0.0317 | -44.73 | 2 | 0.0005 | **0.0020** |
| 2 | stage1: logit_std vs kontrol | +0.0906 ± 0.0023 | +0.0881 / +0.0927 / +0.0910 | +67.41 | 2 | 0.0002 | **0.0011** |
| 3 | primary: logit_std vs kontrol | +0.0859 ± 0.0058 | +0.0802 / +0.0857 / +0.0918 | +25.64 | 2 | 0.0015 | **0.0030** |
| 4 | vae9182: logit_std vs kontrol | +0.1388 ± 0.0013 | +0.1381 / +0.1403 / +0.1380 | +185.81 | 2 | 0.0000 | **0.0002** |
| 5 | vae9182: gate:oracle_error vs temiz kontrol (P2) | +0.0056 ± 0.0040 | +0.0102 / +0.0038 / +0.0028 | +2.45 | 2 | 0.1339 | **0.1339** |
| 6 | FERPlus: T*_NLL(0.5063) vs T=1 | -0.0598 ± 0.0033 | -0.0568 / -0.0633 / -0.0594 | -31.68 | 2 | 0.0010 | **0.0030** |

**The two contrasts that were requested but cannot be supplied, with reasons:**
- *primary: T\* vs T=1* — primary has no temperature-scaled arm on disk; the dose-response campaign ran stage1+vae9182. The contrast is not measurable (it would require runs, ~7 h × 3).
- *vae9182: T\* vs T=1* — T\*=0.983 ≈ 1 and Eq.8 headroom ≈ 0.002 (`headroom_review`): the contrast is defined but empty — there is no miscalibration to scale away. The row was not opened because a 'no difference' conclusion does not follow from it; the teacher is already calibrated.

## Context for d = 13.7 (FERPlus calibrated-vs-native)

| quantity | value |
|---|---|
| paired d_z = \|mean Δ\| / sd(Δ) | **18.3** |
| pooled-sd Cohen d | **17.4** |
| T\*-arm seed range | [0.0167, 0.0195] |
| native-arm seed range | [0.0734, 0.0826] |
| do the ranges overlap | **NO** |

Basis for the wording in the abstract: between the two arms' seed ranges there is no intersection — "no overlap across seeds" can be written. At n=3 the point value of d is unstable (its sd denominator is estimated on two degrees of freedom); in the text, give d together with the range separation rather than on its own.

