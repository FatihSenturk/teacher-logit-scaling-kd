# P2 — `gate:oracle_error` at n=3, against a class-weighting-matched control

Producer: `diagnostics/p2_gate_oracle_verdict.py` · @swa primary · sample sd (n-1, Bessel-corrected), computed over seeds

> **Pre-registered.** `rafdb_p2_gate_oracle_seeds_queue.ps1` was frozen 2026-07-29 01:26:59, before the first run (see `PREREGISTRATIONS.md` A8).

## Arms (@swa, selection-independent)

| kol | acc (%) | ECE | n |
|---|---|---|---|
| kontrol (baseline, `class_weight_mode=none`) | 90.146 ± 0.207 | 0.0278 ± 0.0027 | 3 |
| tedavi (`gate:oracle_error`) | 89.917 ± 0.296 | 0.0334 ± 0.0015 | 3 |

## Differences paired within seed (@swa)

| tohum | Δacc (pp) | ΔECE |
|---|---|---|
| 42 | -0.782 | +0.0102 |
| 1 | -0.065 | +0.0038 |
| 43 | +0.163 | +0.0028 |
| **ortalama** | **-0.228 ± 0.493** | **+0.0056 ± 0.0040** |
| signs | `--+` | `+++` |

## Verdict on the pre-registered predictions

| # | prediction | bar (control's seed sd) | measured | ratio | verdict |
|---|---|---|---|---|---|
| P2.1 | \|Δacc\| ≤ the control's sd → NULL | 0.207 pp | 0.228 pp | 1.10× | ❌ FALSIFIED |
| P2.2 | \|ΔECE\| ≤ the control's sd → NULL | 0.0027 | 0.0056 | 2.08× | ❌ FALSIFIED |
| P2.3 | signs inconsistent on at least one axis | — | acc `--+`, ECE `+++` | — | ✅ confirmed |

### Does the verdict depend on the checkpoint choice

| checkpoint | Δacc (pp) | ΔECE | ECE signs | n |
|---|---|---|---|---|
| swa *(birincil)* | -0.228 ± 0.493 | +0.0056 ± 0.0040 | `+++` | 3 |
| best | -0.445 ± 0.516 | +0.0081 ± 0.0036 | `+++` | 3 |
| last | -0.369 ± 0.363 | +0.0052 ± 0.0065 | `++-` | 3 |

## Size of the class-weighting confound (a by-product of P2)

For VAE9182 **both** controls now exist at the same three seeds, so the class-weighting switch can be isolated on its own. The difference below is the **exact size** of the bias carried by the gate rows listed below as 'not moved':

| eksen | `none` − `effective_number` (@swa, n=3) |
|---|---|
| Δacc | +0.196 ± 0.539 pp (signs `++-`) |
| ΔECE | -0.0052 ± 0.0038 (signs `---`) |

### Kirli kontrol neyi gizliyordu

Same treatment, same seeds; the only difference is which control it is differenced against:

| control | Δacc (pp) | ΔECE | ECE signs | reading |
|---|---|---|---|---|
| `effective_number` (used before P2) | -0.033 ± 0.130 | +0.0004 ± 0.0011 | `+-+` | *looks* ECE-neutral |
| `none` (the clean control P2 produced) | -0.228 ± 0.493 | +0.0056 ± 0.0040 | `+++` | degrades calibration consistently |

> **The missing control was masking a real calibration harm almost exactly.** Because class weighting worsens the control's own ECE by 0.0052 , the gate's harm of the same magnitude came out near zero in the difference and the signs became mixed. This is the measured evidence that the A8 repair was not merely a gesture of rigour.

## Re-differencing the six gate rows — how far it got

Gate runs on the 400e/SWA@200 budget: **24**. With a control in their own class-weighting mode: **24**; hâlâ olmayan: **0**.

| teacher | signal | seed | moved onto the clean control |
|---|---|---|---|
| primary | mean_logvar | 1 | ✅ yes |
| primary | mean_logvar | 42 | ✅ yes |
| primary | mean_logvar | 43 | ✅ yes |
| primary | oracle_error | 1 | ✅ yes |
| primary | oracle_error | 42 | ✅ yes |
| primary | oracle_error | 43 | ✅ yes |
| primary | target_logvar | 1 | ✅ yes |
| primary | target_logvar | 42 | ✅ yes |
| primary | target_logvar | 43 | ✅ yes |
| stage1 | mean_logvar | 1 | ✅ yes |
| stage1 | mean_logvar | 42 | ✅ yes |
| stage1 | mean_logvar | 43 | ✅ yes |
| stage1 | oracle_error | 1 | ✅ yes |
| stage1 | oracle_error | 42 | ✅ yes |
| stage1 | oracle_error | 43 | ✅ yes |
| stage1 | target_logvar | 1 | ✅ yes |
| stage1 | target_logvar | 42 | ✅ yes |
| stage1 | target_logvar | 43 | ✅ yes |
| vae9182 | mean_logvar | 1 | ✅ yes |
| vae9182 | mean_logvar | 42 | ✅ yes |
| vae9182 | mean_logvar | 43 | ✅ yes |
| vae9182 | oracle_error | 1 | ✅ yes |
| vae9182 | oracle_error | 42 | ✅ yes |
| vae9182 | oracle_error | 43 | ✅ yes |

> **A8's note that 'all six gate rows can be moved' is fully satisfied.** P4 (6 controls, 30 Jul) landed the missing `class_weight_mode=none` baselines for stage1 and primary, and P5 (6 runs, 31 Jul–1 Aug) the oracle replication: **every gate row is now differenced against the control in its own mode**, with no unpaired rows. P5's verdict is also in `diagnostics/p5_oracle_replication/p5_verdict.md`: the calibration harm **did not resolve** for stage1/primary, so the claim below stays conditional on VAE9182.

> The gate claim does not rest on those four rows: `gate:oracle_error` is an **error-informed diagnostic** — a perfect signal *of the student's own error*, against a **clean** control, at **three seeds**. If even that brings no gain, no weaker **error-derived** signal can. **Scope, stated (11 Aug 2026):** this is not a bound over all signals. A signal that is not derived from the error — teacher variance, input difficulty, human disagreement — is outside it and has to be tested on its own; A12 does exactly that for the learned ones.

