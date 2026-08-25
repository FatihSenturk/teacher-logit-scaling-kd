# Teacher head-compatibility audit: Stage1 / Primary (VICH) vs. VAE9182 (VAE)

Read-only diagnostic. No config changed, no training started/resumed/modified.
Script: `diagnostics/teacher_head_compat_audit.py`. Raw outputs: `full_report.json`,
`stage1_logvar_hist.png`, `primary_logvar_hist.png`, `vae9182_logvar_hist.png`.

## 1. Head/final-layer parameter keys and shapes (raw checkpoint, CPU)

| Key | Stage1 (VICH) | Primary (VICH) | VAE9182 (VAE) |
|---|---|---|---|
| `VIT.head.linear.{weight,bias}` | [7,768] / [7] | [7,768] / [7] | [7,768] / [7] |
| `VIT.head_vae.fc_mu.{weight,bias}` | [7,768] / [7] | [7,768] / [7] | [7,768] / [7] |
| `VIT.head_vae.fc_logvar.{weight,bias}` | [7,768] / [7] | [7,768] / [7] | [7,768] / [7] |
| `VIT.head_vae.batchnorm.*` (4 tensors) | present [768]-shaped | present | present |
| `VIT.head_vae.layernorm.{weight,bias}` | [768] / [768] | [768] / [768] | [768] / [768] |
| `VIT.head_vich.fc_mu.{weight,bias}` | **[7,768] / [7]** | **[7,768] / [7]** | **absent** |
| `VIT.head_vich.fc_logvar.{weight,bias}` | **[7,768] / [7]** | **[7,768] / [7]** | **absent** |
| total keys | 765 | 765 | **761** |

**Finding:** `head_vae.*` is present in **all three** checkpoints (unconditional submodule,
`vit_vae_model.py:653`) — in Stage1/Primary these weights are dead/never-trained (forward()
never routes through them when `vich=True`). `head_vich.*` is present **only** in Stage1/Primary
and is **structurally absent** from VAE9182's checkpoint (conditional construction,
`vit_vae_model.py:654`: `VICHClassifier(...) if self.vich else None`). This is the exact
4-key difference (765 − 761 = 4: `head_vich.fc_mu.{weight,bias}`, `head_vich.fc_logvar.{weight,bias}`).

Where `head_vae` and `head_vich` shapes coincide ([7,768]/[7] on both), a name-blind,
shape-only check could not tell them apart — but no code path in this repo does a
shape-only or renamed-key load (see §2).

## 2. Teacher-loading code path

- Single class (`VisionTransformer`/`pyramid_trans_expr2`), not a VAE/VICH branch at the
  loader level — `vae=`/`vich=` are constructor flags selecting between three heads
  (`head`, `head_vae`, `head_vich`) inside one `forward()` (`vit_vae_model.py:787-792`).
- All 5 teacher-checkpoint call sites in the repo (`train_rafdb_kd.py:106`,
  `train_affectnetplus_kd.py:61`, `tools/evaluate_teacher.py:32`,
  `tools/analyze_uncertainty_human.py:198`, `tools/cache_teacher_outputs.py:129`) call
  `load_checkpoint_checked(..., strict=True)`. No `strict=False` usage exists anywhere
  for a teacher checkpoint. PyTorch's own `strict=True` raises `RuntimeError` on any
  missing/unexpected key **before** any forward pass runs.
- Consequence: given §1's key difference, constructing VAE9182 with `vich=True` (or
  Stage1/Primary with `vae=True, vich=False` swapped from their true config) would hard-crash
  at `load_state_dict`, not silently coincide. **Empirically confirmed**: all three teachers
  loaded and evaluated in this audit reproduced their exact known own-accuracy (below),
  which would not happen if the wrong head/weights were in use.

## 3. Exactly which tensors gate/g2g_kl/adaptive_t consume

| Component | Tensor(s) | Shape | Head-type sensitive? |
|---|---|---|---|
| gate (`mean_logvar`/`target_logvar`/`top2_logvar`) | `teacher_logvar` | `[B, C=7]` | No — reduces over class dim regardless of source head |
| g2g_kl / g2g_w2 | `teacher_mu`, `teacher_logvar` vs. student `mu`,`logvar` | `[B, 7]` both sides | No, but `validate_g2g_shapes()` asserts equality every forward |
| adaptive_t | `teacher_logits` only | `[B, 7]` | Doesn't touch mu/logvar at all |

`C == D == 7` for **both** head types — not a coincidence: `vit_vae_model.py:653-654`
constructs `head_vae` and `head_vich` with the identical `out_features=num_classes`.
Neither is a general-purpose VAE with its own latent dimension; both are, by this
codebase's deliberate design, per-class variational heads (`VICHClassifier`'s own
docstring: "predicts mu/logvar directly in class space"). A shape-only check can't and
isn't meant to distinguish them — the real distinguishing facts are architectural
(clamp vs. no clamp, different init, VAE's dead batchnorm/layernorm) from §1.

## 4. Fixed 256-image batch, eval mode, CPU (`data/rafdb_aligned`, fold 3, seed 42)

| Teacher | logvar min | mean | max | std | degenerate? |
|---|---|---|---|---|---|
| Stage1 | -4.95 | -1.89 | 0.43 | 0.93 | none |
| Primary | -4.07 | -1.10 | 0.53 | 0.80 | none |
| VAE9182 | -4.38 | -1.86 | -0.30 | 0.88 | none |

No near-constant, all-zero, or clamp-saturated logvar in any teacher. VAE9182 (no clamp
in its architecture) still lands well inside `[-10,10]` on real data — the missing clamp
is a latent risk, not an observed problem on this batch.

## 5. Full fold-3 val set (3068 images), own top-1 / AUROC(logvar→error) / ECE

| Teacher | own_acc | AUROC(mean_logvar → own error) | ECE (15-bin) |
|---|---|---|---|
| Stage1 | 92.24% | 0.426 | 0.0378 |
| Primary | 92.01% | 0.442 | 0.0396 |
| VAE9182 | 91.82% | **0.169** | 0.0136 |

Own-accuracy matches each teacher's previously-recorded value exactly (92.24/92.01/91.82%),
confirming the right head/weights were exercised in this audit (and, by extension, in the
KD runs that used the identical `build_teacher` path).

**Notable, unprompted finding:** all three AUROCs are **below 0.5** — the gate's
`mean_logvar` signal is *inversely* related to the teacher's own prediction error for
every teacher tested (higher logvar tends to coincide with *correct*, not incorrect,
predictions). This is mild for Stage1/Primary (0.43-0.44, close to chance) but pronounced
for VAE9182 (0.169, strongly inverted). This plausibly explains why `gate` underperformed
baseline for Stage1 (-0.33pp) and Primary (-0.39pp) in the completed ablation, and only
barely beat baseline for VAE9182 (+0.03pp, 90.09% vs. 90.06%) despite VAE9182 having by
far the most useful raw uncertainty signal of the three — not a head-type mismatch, but a
genuine calibration/miscalibration property of `mean_logvar` as an uncertainty proxy on
this dataset, worth flagging as a separate follow-up (e.g. try `target_logvar` or
`top2_logvar` instead, or invert the gate's alpha direction) rather than as evidence
against the VICH-teacher requirement.

## 6. Verdict: **S1 — different head, interface-compatible**

- **Not S0** (naming-only): VAE9182 genuinely lacks `head_vich.*` in its checkpoint
  (§1); it was trained with `vae_head: True, vich_head: False`
  (`RAFDB_teacher_affectnet_recipe.yaml:52-53`) and evaluates through `VaeClassifier`,
  a distinct class from `VICHClassifier` (no logvar clamp, different init, extra
  unused batchnorm/layernorm/dropout parameters carried in the checkpoint).
- **Not S2** (interface mismatch / wrong-space Gaussians): both heads emit
  `(logits, mu, logvar)` 3-tuples with `mu`/`logvar` shaped `[B, num_classes]` by
  deliberate, shared construction (§3), consumed identically by `extract_mu_logvar`
  and by gate/g2g_kl with no reinterpretation needed. `validate_g2g_shapes()` would
  catch any actual shape divergence at every forward call. Loading is `strict=True`
  everywhere, so a real architecture mismatch (e.g. accidentally requesting the wrong
  head for a checkpoint) fails loudly at load time, not silently.
- **S1** stands: VAE9182 is architecturally and statistically a different beast from
  Stage1/Primary (different training objective, no clamp, and — per §5 — a
  qualitatively different, more strongly error-inverted logvar signal), but it exposes
  the exact same tensor interface the KD components were built against, and every
  completed KD run that used it (own_acc reproduced exactly; all 6 ablation conditions
  ran to completion without a single shape/key error) is consistent with that
  interface having worked correctly throughout this session's grid.
