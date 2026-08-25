# G0 — Control-teacher grid refinement (T = 0.95 and 1.10)

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

> The original pre-declared test was run at grid resolution 0.15 and held; these two points were added afterwards, in response to review, to test at the scale of the teacher's own optimum.

Producer: `diagnostics/control_grid_refinement.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · pre-registration status: **not pre-declared** (PREREGISTRATIONS §B8)

## Exit check

| check | result |
|---|---|
| grid points × seeds expected | 5 × 3 = 15 |
| present in the audit | 15 |
| **runs with more than one attempt (crash evidence)** | **1** |
| partial attempts excluded (no `metrics_best.json`) | 1 |
| name → parameter mismatches | 0 |
| keys absent, documented default assumed | 3 |

**Why the multi-attempt line is reported separately.** G0's entire value is that the recipe is byte-for-byte the existing control arm with only T changed. A run that was interrupted and *continued* would not be equivalent to a clean one — optimizer state and data order would differ — so it would break exactly the comparability the experiment depends on. No G0 run was resumed: the campaign's training script has no `--resume`, and the one casualty was restarted from epoch 0 rather than continued.

| excluded attempt | epochs reached | reason |
|---|---|---|
| `RAFDB_vae9182_tempscale_T110_b070_T6_224_400e_swa200_seed42` / 2026-08-06-03-30-23 | 399/400 | no `metrics_best.json` — interrupted, restarted clean |

Runs carrying more than one attempt directory: `RAFDB_vae9182_tempscale_T110_b070_T6_224_400e_swa200_seed42` (2). Each such run's **finished** attempt is the one used; the partial is marked `ABANDONED.json` and is invisible to every table.

**Keys absent, default assumed** (stated rather than silently accepted — the T = 1 arms predate the `--teacher-temperature-scale` flag, so the key is missing from their `run_args.json` rather than set):

- RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200: `teacher_temperature_scale` anahtarı yok → belgelenmiş varsayılan 1 kabul edildi (bayrak bu koşudan sonra eklendi)
- RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1: `teacher_temperature_scale` anahtarı yok → belgelenmiş varsayılan 1 kabul edildi (bayrak bu koşudan sonra eklendi)
- RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43: `teacher_temperature_scale` anahtarı yok → belgelenmiş varsayılan 1 kabul edildi (bayrak bu koşudan sonra eklendi)

## The five-point control series

| T | role | n | student ECE | student acc (pp) |
|---|---|---|---|---|
| 0.85 | pre-declared grid | 3 | 0.0447 ± 0.0013 | 89.93 ± 0.06 |
| 0.95 | **added (G0)** | 3 | 0.0296 ± 0.0027 | 90.07 ± 0.15 |
| 1 | native / pre-declared | 3 | 0.0330 ± 0.0020 | 89.95 ± 0.37 |
| 1.1 | **added (G0)** | 3 | 0.0349 ± 0.0032 | 89.98 ± 0.22 |
| 1.3406 | pre-declared grid | 3 | 0.0647 ± 0.0030 | 90.09 ± 0.29 |

## Paired differences against T = 1, within seed

Criterion (G3.1): |mean ΔECE| ÷ σ_control ≥ 2 **and** all seeds share the sign. σ_control = 0.0020 (vae9182 `effective_number` control arm @swa).

| T | mean ΔECE | signs | ratio | verdict |
|---|---|---|---|---|
| 0.85 | +0.0117 ± 0.0023 | +++ | 5.87× | established |
| 0.95 | -0.0033 ± 0.0042 | --+ | 1.68× | unresolved |
| 1.1 | +0.0020 ± 0.0045 | +-+ | 0.98× | unresolved |
| 1.3406 | +0.0317 ± 0.0029 | +++ | 15.89× | established |

Source: `diagnostics/selection_audit/selection_audit_unfrozen.csv` @swa. The frozen audit (`selection_audit.csv`, N=131) is a different file and is untouched.

