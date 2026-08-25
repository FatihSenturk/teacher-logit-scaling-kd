# R2-3 — Mechanism specification appendix (machine-generated)

Producer: `diagnostics/mechanism_specs.py` · values read from the runs' own `run_args.json` dumps (no number is typed by hand) · formulas carry code references (file:line in every cell) · scope: the RAF-DB arms in runs.csv.

## gate  (n=25 runs)

α_i = α_lo + (α_hi−α_lo)·sigmoid(k·(û_i − τ_g)); û_i = z-score(u_i) (gate_norm=batch: batch mean/std, eps 1e-6; running: EMA momentum 0.99, frozen at eval). Blend: loss_i = α_i·CE_i + (1−α_i)·KD_i — α_i is the HARD-label weight. Sources: mean/target/top2_logvar, entropy, oracle_error. ORACLE DIRECTION: if the teacher's top-1 is wrong then u_i=1 → û_i high → α_i→α_hi → on that sample the TEACHER's WEIGHT (1−α_i) is MINIMISED (a sample the teacher gets wrong is listened to less). [kd_uncertainty.py:51-66,140-146; kd_common.py:406-438]

| parameter | value(s) [n runs] |
|---|---|
| `gate_uncertainty_source` | `mean_logvar` [10] · `oracle_error` [9] · `target_logvar` [6] |
| `gate_norm` | `batch` [25] |
| `gate_alpha_lo` | `0.1` [25] |
| `gate_alpha_hi` | `0.7` [25] |
| `gate_k` | `2` [25] |
| `gate_tau` | `0` [25] |

## adaptive_t  (n=19 runs)

Per sample T_i = τ·(1 + γ·(H̃_i − mean(H̃))), H̃_i = H_i/log C, with H_i computed at T=1 (so the definition is not circular); clamp [1.0, 2τ]. [kd_baselines.py:23-38]

| parameter | value(s) [n runs] |
|---|---|
| `adaptive_t_gamma` | `0.5` [19] |

## g2g  (n=14 runs)

Additional term: loss += w·ramp(epoch)·mean_i KL(N(μ_t,σ_t²) ‖ N(μ_s,σ_s²)); CLASS-SPACE diagonal Gaussians (the head's 7/8-dimensional μ, logvar output — not an intermediate layer), summed over classes independently; logvar clamped to ±10; KL direction teacher‖student; STATELESS (no EMA or running statistics — the batch/running question does not arise). Where w applies: additively to the total loss, AFTER the α blend. [kd_g2g.py:16-36; kd_common.py:453]

| parameter | value(s) [n runs] |
|---|---|
| `g2g_weight` | `0.1` [14] |
| `g2g_mode` | `kl` [14] |
| `g2g_warmup_epochs` | `0` [14] |

## logit_std  (n=10 runs)

ẑ = (z − mean_c z)/(std_c z + ε), ε=1e-6, std unbiased=False, taken per sample over the CLASS axis (dim=1); in the KD term ONLY, BEFORE the division by T, on both the teacher and the student side (Sun et al. CVPR 2024). The supervision term is untouched. [kd_baselines.py:12-20]

No tunable hyperparameter (ε=1e-6 is fixed in the code).

## ctkd  (n=4 runs)

A single GLOBAL learnable temperature: T = t_min + (t_max−t_min)·sigmoid(GRL(θ,λ)); θ initialised at 0 (so T starts mid-range), λ cosine-ramped 0→λ_max over epochs; the GRL flips the gradient by −λ in the backward pass (the direction that makes KD harder = the curriculum). θ is added to the main optimiser → the 'adversarial lr' is the run's own lr (in the table), AdamW, no separate optimiser. A single-scalar simplification of Li et al. AAAI 2023 (no per-sample MLP). [kd_baselines.py:41-92]

| parameter | value(s) [n runs] |
|---|---|
| `ctkd_t_min` | `1` [4] |
| `ctkd_t_max` | `8` [4] |
| `ctkd_grl_lambda_max` | `1` [4] |
| `lr` | `0.0003` [4] |

## Common check (all mechanism runs)

| key | value(s) → in which mechanisms |
|---|---|
| `temperature` | `6` (adaptive_t, ctkd, g2g, gate, logit_std) |
| `alpha` | `0.3` (adaptive_t, ctkd, g2g, gate, logit_std) |
| `teacher_temperature_scale` | `0.7311` (adaptive_t) · `1` (adaptive_t, g2g, gate, logit_std) · `None` (adaptive_t, ctkd, g2g, gate, logit_std) |

τ=6 and α=0.3 are expected throughout, as is `teacher_temperature_scale` 1.0 — the only known exception is the T0=0.7311 arms of the B-010 deliberate-miscalibration pilot (visible on the adaptive_t row; intentional, see BULGULAR B-010). If the table shows any other variation, that row must be carried into the appendix as an exception.

