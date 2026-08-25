# G3.3 — The Holm family: its members, and when the membership was fixed

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

Producer: `diagnostics/holm_family.py` · numbers read from `paper_tables/inferential_tests.json` (not recomputed) · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · axis: ece

Family size m = **6**. All contrasts are within-seed paired, n = 3, df = 2. Holm step-down: contrasts are ranked by raw p, and the k-th smallest is compared against α/(m−k+1); the adjusted p reported here is the standard monotone transformation of that procedure.

| Holm rank | contrast | ΔECE mean ± sd | t | df | p (raw) | p (Holm) |
|---|---|---|---|---|---|---|
| 1 | vae9182: logit_std vs kontrol | +0.1388 ± 0.0013 | +185.81 | 2 | 2.90e-05 | 0.0002 |
| 2 | stage1: logit_std vs kontrol | +0.0906 ± 0.0023 | +67.41 | 2 | 0.0002 | 0.0011 |
| 3 | stage1: T*(1.3406) vs T=1 | -0.0303 ± 0.0012 | -44.73 | 2 | 0.0005 | 0.0020 |
| 4 | FERPlus: T*_NLL(0.5063) vs T=1 | -0.0598 ± 0.0033 | -31.68 | 2 | 0.0010 | 0.0030 |
| 5 | primary: logit_std vs kontrol | +0.0859 ± 0.0058 | +25.64 | 2 | 0.0015 | 0.0030 |
| 6 | vae9182: gate:oracle_error vs temiz kontrol (P2) | +0.0056 ± 0.0040 | +2.45 | 2 | 0.1339 | 0.1339 |

**5/6** contrasts survive Holm at α = 0.05. With n = 3 and df = 2 the procedure has very little power; this table is reported because §4 promises it, not as a strength claim.

## When was the family membership fixed?

This is the part a reader cannot check from the paper, so it is answered from the repository's own history rather than asserted.

| question | answer |
|---|---|
| defined in | commit `f381704`, 2026-08-01 14:48 |
| revised since? | **no** — the only other commit touching the file (`a0a07c4`, 2026-08-03 13:06) output prose translated to English; contrast definitions untouched |
| pre-registered? | **no** |

**The two facts are separate and are stated separately.**

*Not pre-registered.* The family was assembled on 1 Aug 2026 in response to an earlier panel objection ("§4 promises paired t and a Holm correction; §5 reports neither"). All six contrasts' results were already on disk when the list was written. So this is not a pre-declared family, and the paper will not call it one.

*But not shopped either.* Family membership is the silent degree of freedom here — adjusted p-values depend directly on m, so adding or dropping members after seeing the numbers would move them. That did not happen: the same six rows have stood since the file was created, with no revision. Unlike the previous point, this one is **falsifiable from git** — and it survives the check.

A pre-registered family would have been better. A fixed one is what exists, and the difference between the two is exactly what this block records.

## Contrasts that were requested but cannot be supplied

{'primary_Tstar_vs_T1': 'no temperature-scaled primary arm on disk', 'vae9182_Tstar_vs_T1': 'T*=0.983~1, Eq.8 headroom ~0.002 -- contrast empty'}


Source: `diagnostics/inferential_tests.py` (family definition and all statistics); this file only re-presents them with the Holm ranking made explicit and adds the provenance determination.

