# Phase 0: Uncertainty-Gated Variational Distillation — ⚠️ ÇALIŞMA KAYDI

> **Bu dosya bir çalışma kaydıdır; güncel iddialar makalededir.** 6 Tem 2026 tarihli;
> beş mekanizmanın (gate, G2G, logit-std, adaptive-T, CTKD) nasıl kurulduğunu ve
> bileştirme kurallarını anlatır. **Doğruluk sayısı taşımaz** (ölçüldü: doksanlık hiçbir
> değer yok), yani makaleyle çelişebilecek bir sonuç iddiası içermiyor.
>
> Buradaki mekanizmaların **sonuçları** sonradan kapandı ve o kapanışlar bu belgede
> değil, `diagnostics/PREREGISTRATIONS.md`'de tarihli beyanlar olarak durur — gate'in
> kapanışı A12'ye kadar uzadı ve son hâli "n=3'te kurulamadı"dır. Makaledeki her sayının
> tek kaynağı `diagnostics/paper_tables/RESULTS_TABLES.md`'dir.

Last update: 2026-07-06

**SwanLab is hard-disabled** in `train_rafdb_kd.py` and `train_affectnetplus_kd.py` (and therefore
`train_ferplus_kd.py`): `main()` forces `args.use_swanlab = False` unconditionally, right after
argument parsing. The `--use-swanlab` CLI flag is still accepted (so existing launcher scripts
that pass it don't break), it just has no effect anymore.

## Scope note: this repo vs. the original task spec

The task spec this phase implements (an external prompt document, not distributed) assumed a repo layout that
doesn't exist here: `specs/datasets.yaml`, `specs/teachers.yaml`, a `tests/` directory,
`experiment_tracking.py`, and root `README.md`/`DANISMAN_PROJE_YAPISI.md`. None of those exist
anywhere in this project. Everything below is adapted to this repo's real conventions instead:
KD hyperparameters are plain argparse flags on `train_rafdb_kd.py`/`train_affectnetplus_kd.py`
(no `specs/` layer), `configs/*.yaml` describe teacher/dataset architecture only, run tracking is
`SwanLabTracker` + `training_log.csv` + `metrics_*.json` (no manifest/hash system), and `tests/`
was created fresh with stdlib `unittest` (no `pytest` installed in this environment; `scipy` is
present transitively via `scikit-learn` and is used directly in Component C rather than
hand-rolling Spearman, per the spec's own "skip only if truly absent" escape hatch). This repo is
also not under git, so there's no commit hash in any manifest.

## What was added

| Component | Files | Config flags (all default off/neutral) |
|---|---|---|
| A. Uncertainty-gated KD (UGKD) | `kd_uncertainty.py`; wired into `kd_common.py::DistillationLoss` | `gate_enable`, `gate_uncertainty_source`, `gate_norm`, `gate_alpha_lo/hi`, `gate_k`, `gate_tau` |
| B. Gaussian-to-Gaussian distillation (G2G) | `kd_g2g.py`; wired into `kd_common.py::DistillationLoss` | `g2g_enable`, `g2g_weight`, `g2g_mode` (`kl`\|`w2`), `g2g_warmup_epochs` |
| C. Human-uncertainty correlation tool | `tools/analyze_uncertainty_human.py` (new) | n/a (standalone tool) |
| D. Baseline KD methods | `kd_baselines.py`; wired into `kd_common.py::DistillationLoss` | `logit_std_enable`; `adaptive_T_enable`, `adaptive_T_gamma`; `ctkd_enable`, `ctkd_t_min/max`, `ctkd_grl_lambda_max` |
| E. Teacher-output caching tool | `tools/cache_teacher_outputs.py` (new); `--teacher-cache`/`--no-train-augment` in both train scripts | n/a (standalone tool + train-script consumption flag) |

New shared helpers in `kd_common.py`: `extract_mu_logvar()` (dict-or-tuple mu/logvar extraction,
mirrors the existing `extract_logits()`), `MinMeanMaxMeter`, `DistillationLoss.supervised_loss_per_sample()`,
`DistillationLoss.set_epoch(epoch, total_epochs)` (drives G2G's warmup and CTKD's GRL ramp).

All 5 components are covered by `tests/test_kd_backward_compat.py`, `tests/test_g2g.py`,
`tests/test_gate.py`, `tests/test_baselines.py` (55 tests total, stdlib `unittest`, run directly:
`python tests/test_x.py`). Both tools were verified end-to-end against real checkpoints/data
(`tools/analyze_uncertainty_human.py` against `checkpoints/ferplus_processed_posterv2_best.pt` +
the FERPlus majority split; `tools/cache_teacher_outputs.py` against
`checkpoints/teacher_vich9237_best.pt` + RAF-DB).

## Integration into train_rafdb_kd.py / train_affectnetplus_kd.py

Both scripts gained an identical set of new flags (see table above, plus `--teacher-cache` /
`--no-train-augment`). `train_ferplus_kd.py` needed no separate changes — it's a thin wrapper
around `train_affectnetplus_kd.py`'s `main()`/`parse_args()`, so it inherits everything.

Key implementation points (see `kd_common.py::DistillationLoss` docstrings/comments for the
authoritative detail):

- `DistillationLoss.forward()` still returns exactly `(loss, hard_loss, soft_loss, aux_kl)` —
  unchanged arity, since both train scripts unpack it positionally. New per-batch diagnostics
  (alpha_i distribution, G2G term, effective-T distribution, CTKD's current T) are exposed as
  `criterion.last_alpha_stats` / `last_g2g_term` / `last_effective_T_stats` / `last_ctkd_T`
  (plain floats or `{"min","mean","max"}` dicts, `None` when not applicable that batch) — both
  train scripts read these after each batch and log epoch-level min/mean/max to
  `training_log.csv` (columns: `alpha_min/mean/max`, `g2g_term`, `effective_T_min/mean/max`,
  `ctkd_T`; blank when the corresponding mechanism is off for that run).
- D1 (logit standardization), D2 (adaptive-T), and D3 (CTKD) all need **raw teacher logits**
  (not the precomputed `teacher_probabilities`) — D1 to standardize before any softmax, D2 for
  its own per-sample temperature, D3 because gradient must flow through a differentiable softmax
  back into the learned temperature. Both train scripts detect this
  (`criterion.logit_std_enable or criterion.adaptive_T_enable or criterion.ctkd_enable`) and pass
  `teacher_logits=` instead of `teacher_probabilities=` accordingly — including under mixup,
  where the raw logits are mixed instead of the softmax probabilities in that case.
- The gate (Component A) always uses the **fixed** `self.temperature` for its own KD blend and
  for its `entropy` uncertainty source, never CTKD's/adaptive-T's effective temperature — per the
  spec ("kapı sadece L_sup/L_KD dengesini değiştirir; T sabit kalır").
- CTKD's learnable `theta` (in `criterion.ctkd`) is added to the optimizer's parameter list in
  both scripts, following the existing precedent in `train_rafdb_kd.py` for the feature-distillation
  projector's parameters.

## Composability / precedence rules

- G2G and logit standardization are fully additive/orthogonal to everything else.
- Gate + adaptive-T: **allowed, prints a warning** (both react to teacher uncertainty, on
  different axes — alpha vs. temperature — spec-mandated warning, not an error).
- Adaptive-T + CTKD: **hard error at `DistillationLoss.__init__`**. Not addressed by the original
  spec, but both fully own "the effective temperature" with no defined combination semantics.
- Gate + class-weighted CE (`--class-weight-mode`): **hard error at construction**. Class-weighted
  `F.cross_entropy(reduction="mean")` normalizes by `sum(weight_i)` across the batch, not
  `mean_i(weight_i * loss_i)`, so it has no exact per-sample decomposition — needed for the gate's
  per-sample alpha blend. Out of Phase 0 scope; none of the smoke configs use class weighting.
- CTKD + `--mixup > 0`: **hard error in both train scripts' `main()`**. Mixup currently mixes
  post-softmax probabilities; CTKD needs raw logits with gradient flowing through a differentiable
  softmax into `theta`, which mixed-then-softmaxed probabilities can't provide.
- `--teacher-cache` + `--mixup > 0`: **hard error**. Mixing cached (pre-computed, path-keyed)
  teacher outputs under mixup has no well-defined semantics; this flag is for
  augmentation-free analysis/smoke runs, where mixup wouldn't be used anyway.
- `--teacher-cache` requires `--no-train-augment`: **hard error otherwise**. The cache is only
  valid for a deterministic transform pipeline; `--no-train-augment` structurally forces the
  train loader onto the same transform as validation (rather than trying to enumerate and zero
  out each augmentation knob individually) before the cache can be trusted.
- Combinations not explicitly covered above (e.g. gate's non-entropy sources + mixup, G2G + mixup)
  are technically allowed but not validated against any acceptance test — the mixup-mixed mu/logvar
  concept is not addressed by the spec, so `train_one_epoch` passes the **unmixed** teacher
  mu/logvar through unchanged in that case.

## `--teacher-cache` scope

`tools/cache_teacher_outputs.py` only supports datasets backed by
`dataset_utils.image_dataset.ImageDataset` (RAF-DB, FER2013/FERPlus, etc. — see
`dataset_utils/builder.py`'s routing); AffectNet+ uses a different dataset/transform pipeline and
raises `NotImplementedError` rather than silently producing a wrong or unlabeled cache. The cache
is keyed by image path (`RAFDBDataset` gained an opt-in `return_path=True` mode for this; the
`dataset_utils.builder`-routed datasets already expose paths in every batch). Per the original
spec, this flag is for augmentation-free analysis/smoke runs only — never the main augmented
training recipe — enforced by the `--no-train-augment` requirement above.

## Phase 0 smoke test (RAF-DB)

`run_phase0_smoke_rafdb.ps1` (repo root) runs 5 short (2-epoch, batch-8) RAF-DB runs — baseline,
+gate, +g2g_kl, +logit_std, +adaptive_T — each producing its own checkpoint/`training_log.csv`/
`metrics_best.json` under `kd_logs_rafdb_phase0_smoke/`. Uses `checkpoints/teacher_vich9237_best.pt`
(`--teacher-vich-head --teacher-vich-init-logvar-bias 0.0`) and `data/rafdb_aligned`, since the
`--teacher-ckpt`/`--aligned-dir` argparse **defaults** in `train_rafdb_kd.py` point at paths that
don't exist on this machine.

```powershell
.\run_phase0_smoke_rafdb.ps1
# or, to force CPU:
.\run_phase0_smoke_rafdb.ps1 -Cpu
```

Equivalent individual commands (student head must be `vich` so the gate/G2G tests below have
mu/logvar to work with):

```
python train_rafdb_kd.py --teacher-ckpt checkpoints/teacher_vich9237_best.pt --teacher-vich-head --teacher-vich-init-logvar-bias 0.0 --aligned-dir data/rafdb_aligned --metadata data/rafdb_aligned/metadata_rafdb_poster_var.csv --student-head-type vich --save-root kd_logs_rafdb_phase0_smoke --epochs 2 --batch-size 8 --name phase0_smoke_baseline
... same, plus --gate-enable --gate-uncertainty-source mean_logvar            --name phase0_smoke_gate
... same, plus --g2g-enable --g2g-weight 0.1 --g2g-mode kl                    --name phase0_smoke_g2g_kl
... same, plus --logit-std-enable                                            --name phase0_smoke_logit_std
... same, plus --adaptive-t-enable                                           --name phase0_smoke_adaptive_t
```

## Running the tests

```
python tests/test_kd_backward_compat.py
python tests/test_g2g.py
python tests/test_gate.py
python tests/test_baselines.py
```

`test_kd_backward_compat.py` is the regression net: with every new flag at its default, it
independently reimplements the pre-Phase-0 loss formula from scratch and checks
`torch.allclose(atol=1e-6)` against `DistillationLoss.forward()`'s actual output — this is what
must stay green through any future change to `kd_common.py`.
