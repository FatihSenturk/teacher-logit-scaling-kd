# P0: RAF-DB teacher recipe diff — is the ECE gap head-architecture or recipe-stack?

Read-only analysis. No training run for this report itself (the bridge experiment that resolves the
open question here is tracked separately, Phase C).

## 1. Field-by-field diff (3 teacher training configs, full YAML reads)

| Field | Stage1 (VICH, 92.24%) | Primary (VICH, 92.01%) | VAE9182 (VAE, 91.82%) |
|---|---|---|---|
| Config path | `results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/RAFDB_posterv2_vich_klb1e4_200e.yaml` | `configs/RAFDB_posterv2_vich_recipe.yaml` | `results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/RAFDB_teacher_affectnet_recipe.yaml` |
| `vich_head` / `vae_head` | True / False | True / False | False / True |
| `transforms_name` | **RAFDB_RECIPE** | **RAFDB_RECIPE** | **QCS-rafdb** |
| `train_resize_size` | 224 | 224 | 236 (never read — see §2) |
| `ce_kld_beta` | **0.0001** | 0.001 | 0.001 |
| `max_epochs` / `t_max` | **200** | 300 | 300 |
| `seed` | 1 | 1 | **0** |
| `vich_init_logvar_bias` | 0.0 (override, default is −5.0) | 0.0 (override) | *(n/a, vich_head=False)* |
| train_folds / val_folds | [2] / [3] | [2] / [3] | [2] / [3] |
| batch_size | 48 | 48 | 48 |
| schedule_name / gamma | ExponentialLR / 0.98 | ExponentialLR / 0.98 | ExponentialLR / 0.98 |
| use_sam / rho | True / 0.05 | True / 0.05 | True / 0.05 |
| optimizer / init_lr / weight_decay | AdamW / 9e-6 / 1e-4 | AdamW / 9e-6 / 1e-4 | AdamW / 9e-6 / 1e-4 |
| layer_embedding | True | True | True |

**Primary and VAE9182 share `ce_kld_beta=0.001` and `max_epochs=300` — the closest matched pair.**
Stage1 differs on both of those fields as well as head type, making it the noisier comparison.

## 2. The confound: `transforms_name` is not just a label, it changes what actually trains

`dataset_utils/transforms.py` dispatches on `transforms_name`. Only two exact strings hit the named
`rafdb-recipe`/`rafdb_recipe` branch (lines 117-136):

```python
Resize((resize_size, resize_size)) -> RandomHorizontalFlip() -> ColorJitter(0.2, 0.2, 0.2)
-> ToTensor() -> Normalize(...) -> RandomErasing(p=0.5)
```

`QCS-rafdb` does not match this (or any other named branch) and falls through to the generic tail
(lines 162-167), which calls `_train_augs("qcs-rafdb")` (lines 8-18). Since `"qcs" in name`:

```python
RandomHorizontalFlip() -> RandomApply([ColorJitter(0.3, 0.3, 0.2, hue=0.05)], p=0.5)
```

**No `RandomErasing` at all**, and the fallback tail never reads `train_resize_size` — only
`train_size`/`val_size` (224). So VAE9182's YAML-specified `train_resize_size: 236` was silently
dead the entire time it was trained.

This was verified against the actual `transforms.py` **snapshotted into VAE9182's own run directory
at training time** (`results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/transforms.py`), which
predates a later addition of the `rafdb-recipe` branch — confirming this is what genuinely ran, not
an artifact of the current file having since changed.

**Net effect:** VICH teachers trained with a fixed, deterministic RandomErasing(p=0.5) regularizer
and mild fixed ColorJitter; VAE9182 trained with a stronger, probabilistic ColorJitter and **no
RandomErasing**, and effectively a plain 224-resize with no resize-then-implied-crop behavior the
YAML's `236` suggested. This is a real, structural augmentation-pipeline difference, independent of
head architecture.

## 3. Confound table

| Factor | Stage1 vs. VAE9182 | Primary vs. VAE9182 |
|---|---|---|
| Head architecture | differs | differs |
| Augmentation pipeline | differs | differs |
| Seed | differs (1 vs 0) | differs (1 vs 0) |
| `ce_kld_beta` | differs (1e-4 vs 1e-3) | **same (1e-3)** |
| `max_epochs` | differs (200 vs 300) | **same (300)** |

**Primary vs. VAE9182 is the closest matched pair** (only head + augmentation + seed differ, not
KD-beta or epoch budget) — this is the pair the Phase C bridge experiment targets.

## 4. Why this matters

This session found that **teacher ECE (not teacher own-accuracy) predicts both student baseline
accuracy and student ECE, monotonically, across all 3 teachers** (teacher ECE, 15-bin audit:
VAE9182 0.0136 < Stage1 0.0378 < Primary 0.0396; student baseline accuracy 90.06% > 89.90% > 89.60%;
student baseline ECE 0.0285 < 0.0581 < 0.0654 — same rank order in all three channels). *(The teacher
ECE values here are from `teacher_head_compat_audit/full_report.json`; note the student baseline ECE
values 0.0285/0.0581/0.0654 are a numerically distinct, separately-computed set — do not conflate the
two.)* VAE9182 is the best-calibrated and best-transferring teacher despite having the *lowest*
own-accuracy. But given §2-3, that ECE advantage cannot yet be attributed to head
architecture alone — it could equally be the augmentation-pipeline difference (RandomErasing
regularization is a well-known calibration-relevant knob) or the seed.

**Resolution: Phase C** trains one new teacher — VAE head, otherwise Primary's exact recipe
(`RAFDB_RECIPE` transform, `ce_kld_beta=0.001`, `max_epochs=300`, `seed=1`) — changing only the head
architecture. Pre-registered decision rule: resulting ECE ≈0.015 → attribute the original gap to head
architecture; ≈0.038 → attribute it to the recipe/augmentation-stack confound instead.
