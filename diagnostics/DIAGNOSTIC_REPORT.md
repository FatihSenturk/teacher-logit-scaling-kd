# FER-KD Training Regression — Diagnostic Report

Repo: `poster-var` (verified as the active copy; `clean_core` and
`D:\Veriseti\poster-var` were not used except where explicitly cited as archaeology).
Scope: RAF-DB KD pipeline (`train_rafdb_kd.py`, `kd_common.py`, `kd_uncertainty.py`,
`kd_g2g.py`, `kd_baselines.py`). Read-only investigation; two throwaway scripts were
run under `diagnostics/` (≤2 GPU-minutes total, single val-set forward passes, no
training). A teacher retrain (`configs/RAFDB_posterv2_vich_klb1e4_200e.yaml`, log
`rafdb_teacher_vich_noamp_overnight.log`) was live on the GPU throughout this
investigation and was **not** touched or slowed measurably (see B1 methodology note).

Terminology used below: task's "UGKD" = this repo's **Gate** (`gate_enable`,
`kd_uncertainty.py`); "G2G" = `g2g_enable` (`kd_g2g.py`); "logit standardization" =
`logit_std_enable` (`kd_baselines.py`). **DKD is not implemented anywhere in this
repo** (verified: `grep -rli "DKD" --include=*.py .` → only a false-positive
substring match inside `beta_weighted_kd.py`, no actual DKD code/class/flag exists).
`EVIDENCE_LEDGER.md` and `FINDINGS_LOG.md` do not exist anywhere in the repo
(verified via `find`) — treated as absent/not applicable, not UNKNOWN.

---

## Part A — Run inventory & archaeology

### A1. Run inventory (representative subset; full set is much larger)

| run_id | date | teacher_ckpt | components on | epochs done/target | best val acc | SWA/final acc | best epoch | status |
|---|---|---|---|---|---|---|---|---|
| `results/rafdb_kd_ce9241_mbv2_lightle_vich/2026-05-27-12-17-20` (= `reference_90_74/`) | 2026-05-27 | `teacher_ce9241_best.pt` (92.41%, plain CE head) | none (vanilla KD, LightLE+VICH student) | 200/200 | **90.74%** | — | 191 | finished |
| `results/rafdb_kd_ce9241_mbv2_lightle_vich/2026-06-02-15-18-47` | 2026-06-02 | same as above | none | 197/? | 90.25% | — | 197 | finished |
| `kd_logs_rafdb/rafdb_baseline_250e/2026-07-06-19-41-26` ("old grid") | 2026-07-06 | `teacher_vich9237_best.pt` (92.37%, "untraceable provenance") | none, no LightLE, `use_vich_sampling=True`, `img_size=256`, teacher fed **256px** (native 224 — the pre-fix bug) | 250/250 | 89.83% | n/a (no SWA) | ~250 | finished |
| `kd_logs_rafdb/rafdb_gate_250e/2026-07-06-23-44-06` | 2026-07-06 | same old-grid teacher | Gate | 250/250 | 89.83% | n/a | — | finished |
| `kd_logs_rafdb/rafdb_g2g_kl_250e/2026-07-07-03-46-21` | 2026-07-07 | same | G2G(kl) | 250/250 | 89.57% | n/a | — | finished |
| `kd_logs_rafdb/rafdb_logit_std_250e/2026-07-07-07-47-16` | 2026-07-07 | same | logit_std | 250/250 | 89.73% | n/a | — | finished |
| `kd_logs_rafdb/rafdb_adaptive_t_250e/2026-07-07-12-08-58` | 2026-07-07 | same | adaptive_t | 250/250 | 89.70% | n/a | — | finished |
| `kd_logs_rafdb/rafdb_ctkd_250e/2026-07-07-16-22-55` | 2026-07-07 | same | ctkd | 250/250 | 90.09% | n/a | — | finished |
| `.../rafdb_newrecipe_baseline_lightle_swa_150e/2026-07-16-01-36-02` | 2026-07-16 | `teacher_rafdb_vich_recipe_best.pt` (92.01%) | none, LightLE on, `use_vich_sampling=False`, `img_size=224`, teacher fed **224px (fixed)** | **6/150** | — | — | — | **crashed/restarted** (train.log ends mid-epoch-6, no error captured in tail) |
| `.../rafdb_newrecipe_baseline_lightle_swa_150e/2026-07-16-01-50-24` ("new-recipe baseline") | 2026-07-16 | same | none | 150/150 | **88.75%** | **88.46%** (SWA) | 65 | finished |
| `.../rafdb_newrecipe_gate_lightle_swa_150e/2026-07-16-02-40-49` | 2026-07-16 | same | Gate | 150/150 | 88.62% | 88.72% | 141 | finished |
| `.../rafdb_newrecipe_g2g_kl_lightle_swa_150e/2026-07-16-03-31-37` | 2026-07-16 | same | G2G(kl), weight=0.1 | 150/150 | 89.05% | **89.47%** (best of new-recipe grid) | 143 | finished |
| `.../rafdb_newrecipe_logit_std_lightle_swa_150e/2026-07-16-04-22-13` | 2026-07-16 | same | logit_std | 150/150 | 88.49% | 88.53% | 140 | finished |
| `.../rafdb_newrecipe_adaptive_t_lightle_swa_150e/2026-07-16-05-12-46` | 2026-07-16 | same | adaptive_t | 150/150 | 89.15% | 88.92% | 70 | finished |
| `.../rafdb_newrecipe_ctkd_lightle_swa_150e/2026-07-16-06-03-21` | 2026-07-16 | same | ctkd | 150/150 | 88.62% | 88.59% | 145 | finished |
| `.../rafdb_newrecipe_baseline_lightle_swa_150e_noamp/2026-07-16-11-30-22` | 2026-07-16 | same | none, `use_amp=False` | 150/150 | 89.02% | 88.30% | 65 | finished (AMP-off control) |
| `.../*_112px/*` (baseline/gate/g2g/logit_std/adaptive_t) | 2026-07-16 | same | `img_size=112` | 150/150 each | 86.4–87.5% | 86.8–87.9% | varies | finished; `ctkd_112px` = **0 epochs logged (crashed immediately)** |
| `.../rafdb_ce9241_lightle_swa_150e_baseline/2026-07-16-14-16-01` | 2026-07-16 | `teacher_ce9241_best.pt` (plain CE head, no mu/logvar → Gate/G2G structurally unavailable) | none | 150/150 | 89.15% | **89.54%** | 121 | finished |
| `.../rafdb_ce9241_lightle_swa_150e_ctkd/2026-07-16-15-06-11` | 2026-07-16 | same | ctkd | 150/150 | 89.11% | 89.24% | 126 | finished |
| `kd_logs_rafdb_multiseed/rafdb_baseline_250e_seed43/2026-07-15-01-34-37` | 2026-07-15 | old-grid teacher, seed 43 | none | **35/250** | not evaluated | — | — | **incomplete** (interrupted, likely to free GPU) |
| `kd_logs_rafdb_newrecipe_noerasing/rafdb_newrecipe_baseline_150e_224px/2026-07-15-19-18-04` | 2026-07-15 | `teacher_rafdb_vich_recipe_best.pt` | none, no SWA metrics written | 150/150 | 89.18% | n/a | 66 | finished |
| `kd_logs_rafdb_newrecipe_noerasing/rafdb_newrecipe_baseline_noerasing_250e/*` (x2) | 2026-07-15 | same | none, `random_erasing_p=0` (implied by dir name) | **1 / 3 epochs logged** | — | — | — | **crashed/killed early** (x2 attempts) |
| `results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/` | 2026-07-17 (**today, live**) | n/a — this IS a teacher retrain | `ce_kld_beta` 1e-4 (vs 1e-3 prior), AMP off | in progress (epoch 10/200 at check time, best_acc 90.71%) | n/a | n/a | n/a | **RUNNING — not touched** |

Full per-run CSVs/JSONs live under `kd_logs_rafdb*/**/training_log.csv` +
`metrics_{best,swa,last,ema}.json`; `reports/rafdb_visual_analysis/leaderboard_*.csv`
indexes a large subset (built 2026-06-25, predates the newrecipe grid). **ECE/NLL are
never logged by any run** (`kd_common.py::evaluate_detailed`, lines 651–680, computes
only accuracy/precision/recall/F1/loss/confusion_matrix — no calibration metric). SwanLab
is hard-disabled repo-wide (`train_rafdb_kd.py:616`, confirmed, matches `PHASE0_NOTES.md`).

### A2. Reference points

| Reference | Accuracy | Config / provenance |
|---|---|---|
| (i) Student-only, no-KD baseline | **UNKNOWN — no `disable_kd: true` run found** (`grep -rl '"disable_kd": true' --include=run_args.json .` → zero hits repo-wide). Would need a fresh `--disable-kd` run to establish. |
| (ii) Vanilla-KD baseline (no Phase-0 components) | 90.74% (best, historical, see below) down to 88.75%/88.46% (recent) — see delta table |
| (iii) Best historical run overall | **90.74%** — `reference_90_74/metrics_best.json`, checkpoint `results/rafdb_kd_ce9241_mbv2_lightle_vich/2026-05-27-12-17-20/best_checkpoint.pth`, teacher=`teacher_ce9241_best.pt`, `epochs=200, img_size=256, student_head_type=vich, student_layer_embedding=True(LightLE)`. `ALL_RESULTS_SUMMARY.md` additionally cites a "LE-VAE KD 200e, 91.00%" run as the nominal best — **UNKNOWN, unverified**: no `metrics_best.json` anywhere in this repo instance reports 91.00%±0.05 (checked every `metrics_best.json` in the repo); likely lives only in the historical `D:\Veriseti\poster-var` copy or was computed by a script/table not re-run here. Treat 90.74% as the provenance-backed ceiling for this repo. |
| (iv) Recent failing runs (new-recipe grid, 2026-07-16, `teacher_rafdb_vich_recipe_best.pt`, 224px, LightLE+SWA) | baseline 88.75%/88.46%(SWA), gate 88.62%/88.72%, g2g_kl 89.05%/**89.47%**, logit_std 88.49%/88.53%, adaptive_t 89.15%/88.92%, ctkd 88.62%/88.59% | `kd_logs_rafdb_newrecipe_lightle_swa/*/2026-07-16-*` |

**Delta table** (recent failing run best-acc minus each reference; SWA-final used where the
reference has no SWA):

| Failing run | vs. 90.74% (best historical) | vs. 89.83% (old-grid baseline, same-family closest predecessor) |
|---|---:|---:|
| new-recipe baseline (88.75%) | −1.99 pp | −1.08 pp |
| new-recipe gate (88.62%) | −2.12 pp | −1.21 pp |
| new-recipe g2g_kl (89.05% / 89.47% SWA) | −1.69 / **−1.27** pp | −0.78 / −0.36 pp |
| new-recipe logit_std (88.49%) | −2.25 pp | −1.34 pp |
| new-recipe adaptive_t (89.15%) | −1.59 pp | −0.68 pp |
| new-recipe ctkd (88.62%) | −2.12 pp | −1.21 pp |
| ce9241 baseline, today's diagnostic (89.15% / **89.54%** SWA) | −1.59 / −1.20 pp | −0.68 / −0.29 pp |

### A3. What changed

**Resolved-config diff, old-grid baseline (89.83%, `kd_logs_rafdb/rafdb_baseline_250e/2026-07-06-19-41-26/run_args.json`) vs. new-recipe baseline (88.75%/88.46%, `kd_logs_rafdb_newrecipe_lightle_swa/.../2026-07-16-01-50-24/run_args.json`)**, `diff` of the two JSON dumps:

```
epochs: 250 → 150
img_size: 256 → 224
student_layer_embedding: False → True            (LightLE added)
student_lightweight_layer_embedding: False → True
swa: False → True   (swa_start: 90 → 100)
teacher_ckpt: teacher_vich9237_best.pt (92.37%) → teacher_rafdb_vich_recipe_best.pt (92.01%)
teacher_input_size: 0 (→ effectively 256, upsample bug) → 224 (bug fixed)
use_amp: False → True
use_vich_sampling: True → False   (student VICH head no longer reparameterization-samples at train time)
workers: 0 → 8
```
**Nine simultaneous changes** between the last clean same-family comparator and the
current failing recipe — there is no single-variable "last good run" to diff against;
this is the central methodological problem underlying A2/A3. In particular
**`teacher_input_size` 0→224 (the resolution-bug fix, commit `b8a2e23`, 2026-07-12)
is one of nine confounded changes**, not an isolated fix — the old ("buggy",
256px-fed) grid actually scored *higher* (88–90.09%) than the corrected 224px grid
(88.49–89.47%), so the resolution fix cannot be credited or blamed in isolation from
this diff without a controlled re-run.

**Git history**: repo was `git init`'d 2026-07-11 (`51b05bf Initial commit`); the
old grid (2026-07-06/07) **predates git tracking entirely** — no commit hash exists
for that code state, so a `git log` range between "last good" and "failing" commits
is not meaningful for that comparison. `git log --oneline` for everything since
init:
```
902c5b4 2026-07-14 Resume checkpoint: adaptive_t done (AffectNet+8)
e139a59 2026-07-14 Resume checkpoint: logit_std done
cb27527 2026-07-13 Resume checkpoint: g2g_kl done
31cab14 2026-07-13 Add -StartAt param to AffectNet+8 launcher
95884b8 2026-07-12 Add -SkipBaseline to AffectNet+8 grid launcher
b8a2e23 2026-07-12 Fix RAF-DB new-recipe grid: feed teacher its native 224px, not 256px
8e5db21 2026-07-12 Add verify_machine2_setup.ps1 pre-flight check
b976572 2026-07-11 Split extended ablation into per-machine launchers
51b05bf 2026-07-11 Initial commit
```
**Working tree** (`git status`/`git diff --stat` at investigation start): one tracked
modification, `train_rafdb_kd.py | 2 ++` (2-line addition, not yet reviewed as part of
this diagnostic — content not inspected since ground rules forbid treating this as a
lead without evidence it's used by any of the runs above, all of which predate this
uncommitted change); 13 untracked files, all new configs/launcher scripts for the
in-progress teacher retrain and diagnostics — none touched by this investigation.

### A4. Loss trajectories

Old-grid baseline (`kd_logs_rafdb/rafdb_baseline_250e/2026-07-06-19-41-26/training_log.csv`, 250 epochs) vs. new-recipe baseline (`.../2026-07-16-01-50-24/training_log.csv`, 150 epochs):

| epoch (≈%) | old: train/hard/soft/aux_kl | old val_acc | new: train/hard/soft/aux_kl | new val_acc |
|---|---|---:|---|---:|
| 1 | 1.855 / 1.713 / 1.887 / 30.83 | 76.14% | 2.058 / 1.687 / 2.149 / 14.83 | 76.21% |
| 5 | 1.000 / 1.505 / 0.869 / 35.38 | 84.39% | 1.140 / 1.554 / 1.035 / 15.06 | 85.23% |
| 25% | 0.478 / 1.348 / 0.256 / 35.96 (ep63) | 88.46% | 0.735 / 1.445 / 0.555 / 16.02 (ep38) | 86.67% |
| 50% | 0.458 / 1.338 / 0.233 / 36.03 (ep126) | 89.05% | 0.680 / 1.430 / 0.491 / 15.98 (ep76) | 85.30% |
| final | 0.402 / 1.285 / 0.177 / 36.38 (ep250) | 89.83% | 0.485 / 1.356 / 0.265 / 16.66 (ep150) | 87.68% (last; best was ep65 @ 88.75%) |

No NaN/Inf in any inspected run's `training_log.csv`. No component fails to
decrease. **Aux-KL (student VICH prior term, raw/unweighted) sits ~2.2× higher in the
old grid (~36) than the new recipe (~16)** across training — consistent with
`use_vich_sampling: True→False` changing what drives the student's own logvar (see
B5); this is architecture/config-driven, not a numerical anomaly (aux_kl is weighted
by `beta_vich=1e-4` before being added to the total loss in both cases, so it never
dominates — confirmed in B5). Both runs' hard_loss plateaus around 1.28–1.36 without
collapsing to near-zero, i.e. no overfitting-to-zero-CE-loss pathology in the baseline
comparison (see B5 for a different finding on the `logit_std` run specifically).

### A5. Eval-side check

All accuracy numbers in this report come from `evaluate_detailed()`
(`kd_common.py:651-680`), called on the **same `val_loader`** (RAF-DB fold 3, no
train/val leakage, deterministic `Resize→ToTensor→Normalize` transform, **no crop and
no TTA** — `train_rafdb_kd.py:194-199` for `augment_preset="kd"`, the preset every
run above uses). Checkpoint selection, quoted from `train_rafdb_kd.py`:
- **best**: `best_ckpt_path = save_dir / "best_checkpoint.pth"` loaded and evaluated at
  lines 908–925 — this is the epoch with highest `val_acc` seen during training
  (tracked at lines 843–848, `if val_acc > best_acc: ... save_checkpoint(...best_checkpoint.pth...)`).
- **last**: `last_checkpoint.pth`, evaluated at lines 926–940 (final-epoch weights).
- **SWA**: only if `--swa` was set; `update_bn()` then `validate()` at lines 850–856,
  written to `metrics_swa.json`.
- **EMA**: only if `--ema` was set; none of the runs in this report used `--ema`
  (`ema: false` in every inspected `run_args.json`).

All runs compared in A2/A4 use the **same** `best`/`swa` selection convention and the
**same** val split/transform, so the comparison is apples-to-apples on the eval side —
img_size differs (256 old vs. 224 new), which is itself one of the nine A3 confounds,
not an eval-methodology artifact.

---

## Part B — Pipeline integrity

### B1. Teacher sanity inside the KD pipeline

Ran `diagnostics/b1_b4_teacher_sanity.py`: loads `teacher_rafdb_vich_recipe_best.pt`
(the **current primary teacher** used by every 2026-07-16 new-recipe run) via the
exact `build_teacher`/`build_loaders` functions imported from `train_rafdb_kd.py`,
`img_size=224`, `teacher_input_size=224` (matching `run_args.json` for the new-recipe
grid), fp32, `batch_size=32`, over the full val split (n=3068). No training code was
modified; GPU was shared with the live teacher retrain throughout (95% util observed
before the run) and remained healthy/unaffected (verified by checking
`rafdb_teacher_vich_noamp_overnight.log` progressed normally to epoch 10 afterward).

| Metric | Value |
|---|---:|
| Top-1 accuracy | **92.014%** |
| Mean softmax entropy (nats) | 0.152 |
| Mean max-prob (confidence) | 0.958 |
| Mean top1–top2 margin | 0.930 |
| ECE (15-bin) | 3.96% |

**92.01% matches this teacher's own archived best-epoch accuracy** (`teacher_rafdb_vich_recipe_best.pt`, per session context, trained via `configs/RAFDB_posterv2_vich_recipe.yaml`) to within rounding — **no preprocessing/normalization/class-mapping mismatch in the KD teacher branch**. Confidence/margin/entropy indicate a sharp, well-behaved (if slightly overconfident vs. its own accuracy — ECE 3.96%, not extreme) softmax distribution; not degenerate.

Cross-check against archived data (no new execution): `reports/teacher_distillability/rafdb_vae9182_vs_vae9201.json` (built via `tools/compare_rafdb_teachers.py`, which also imports `build_loaders`/`build_teacher` from `train_rafdb_kd.py`, i.e. the same real pipeline) reports `accuracy_a = 91.8188%` for the **vae9182** family checkpoint (`results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/best.pt`) — matches the nominal "VAE9182 ≈91.82%" figure in the task brief exactly. **Conclusion: teacher sanity is CONFIRMED for both the vae9182 checkpoint (archived) and the current primary `teacher_rafdb_vich_recipe_best.pt` (measured live here); this is not the regression's cause.**

### B2. Class-index mapping

Single source of truth for RAF-DB labels: `data/rafdb_aligned/metadata_rafdb_poster_var.csv` (`path,label,fold`), consumed identically by teacher (`compare_rafdb_teachers.py`/original teacher trainer) and student (`RAFDBDataset` in `train_rafdb_kd.py:66-91`) — both read the same `label` column, so there is **structurally one shared class-index space**, not independently-defined teacher/student orderings to reconcile. Verified mapping (folder-name prefix per label index):

| label idx | class |
|---:|---|
| 0 | Surprise |
| 1 | Fear |
| 2 | Disgust |
| 3 | Happiness |
| 4 | Sadness |
| 5 | Anger |
| 6 | Neutral |

Teacher confusion matrix (from the B1 run, rows=true, cols=pred, order as above):
```
[[301   3   5   4   1   4  11]
 [ 11  50   1   3   6   1   2]
 [  3   1 125   7  10   6   8]
 [  5   1   5 1150  1   2  21]
 [  0   2  10  11 424   1  30]
 [  2   2  11   4   0 137   6]
 [ 11   0   1  11  21   0 636]]
```
Strongly diagonal-dominant, no off-diagonal band — **confirms no class-index
permutation** between teacher output order and dataset labels.

### B3. Teacher input branch (quoted from `train_rafdb_kd.py`)

- **Same augmented view, not a separate clean view**: the teacher forward pass
  (`train_rafdb_kd.py:449-459`) runs on `images` — the *same* batch tensor about to be
  fed to the student — *before* the mixup branch constructs `mixed_images` for the
  student only (`:463-476`). So teacher and student see identical
  rotation/color-jitter/erasing augmentation; only under `--mixup>0` do they diverge
  (teacher sees un-mixed images, its logits/mu/logvar are mixed analytically via
  `mix_targets(...)` at `:482`/`:489` to stay aligned with the student's mixed input —
  correctly implemented, not a bug).
- **Resolution**: `_prepare_teacher_images()` (`:248-258`) only resizes if
  `teacher_input_size > 0` and differs from the current image size; **default
  `--teacher-input-size 0` silently reuses the student's `--img-size`**
  (`train_rafdb_kd.py:963-968`). This is the exact mechanism behind the 256px-vs-224px
  issue in A3/commit `b8a2e23`. All 2026-07-16 new-recipe runs correctly pass
  `--teacher-input-size 224`.
- **Frozen / eval / no grad**: `build_teacher()` (`:94-112`) calls `teacher.eval()`
  and sets `param.requires_grad = False` for every parameter at construction; the
  training loop additionally re-asserts `teacher.eval()` every epoch
  (`train_one_epoch`, `:394-395`) before the student's `.train()`. BatchNorm/dropout
  are therefore in eval mode for the whole run (no separate flag needed — `.eval()`
  covers it). The teacher forward is wrapped in `torch.no_grad()`
  (`:450`).
- **Normalization**: both branches share one `Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])` (ImageNet stats) from the same `build_loaders()` transform pipeline (`:160-245`) — teacher does not get its own separate normalization; it consumes the student-normalized tensor (only resized if needed).
- **AMP**: teacher forward is wrapped in `torch.cuda.amp.autocast(enabled=amp_enabled)` (`:450`), the same `amp_enabled` flag as the student's forward/backward (`:462`) — consistent, not a mismatch.

### B4. σ²/gate health

**Teacher** (from the B1 run, `teacher_rafdb_vich_recipe_best.pt`, val set, `gate_uncertainty_source=mean_logvar` — the default): mean-logvar-over-classes distribution is **not collapsed and not extreme**:

| min | p25 | median | p75 | max |
|---:|---:|---:|---:|---:|
| −3.40 | −1.22 | −0.99 | −0.81 | 0.60 |

Induced UGKD/Gate alpha (default `gate_alpha_lo=0.1, gate_alpha_hi=0.7, gate_k=2.0,
gate_tau=0.0`, batch-normalized as `UncertaintyNormalizer(mode="batch")` would): mean
**0.413**, only **3.3%** of samples within 0.01 of the floor (0.1), **8.3%** above
0.9×hi (0.63) — a healthy, non-degenerate spread, not saturated at either bound. This
independently matches the *training-time* value logged in
`kd_logs_rafdb_newrecipe_lightle_swa/rafdb_newrecipe_gate_lightle_swa_150e/.../training_log.csv`
(epoch 150: `alpha_mean=0.4265, alpha_min=0.1000, alpha_max=0.6985`) — cross-confirmed
by two independent measurements. **Gate signal is alive; Gate's underperformance
(88.62% vs. 88.75% baseline) is not explained by a dead/no-op gate.**

**Student VICH σ** (`diagnostics/b4_student_sigma.py`, new-recipe baseline's
`best_checkpoint.pth`, epoch 65, val set):

| min | p25 | median | p75 | max |
|---:|---:|---:|---:|---:|
| −1.86 | −0.49 | −0.26 | −0.11 | 0.45 |

Not collapsed toward the `init_logvar_bias=-5.0` floor and nowhere near the
`[-10, 10]` clamp — no evidence of a σ→0 blow-up risk in `exp(logvar)`/precision terms
for **this** (non-G2G) run. **Caveat**: `use_vich_sampling=False` in every new-recipe
run (see A3) means `logits = mu` deterministically at train time too (VICHHead
`forward`, `models/mobilenetv2_plus.py:131-136`), so **student logvar receives
gradient only from the tiny `beta_vich=1e-4`-weighted KL term** (and, when enabled,
G2G) — never from the task loss. This is architecturally consistent with "not
collapsed" (nothing pushes it to collapse) but also means the student's own
uncertainty head is largely along for the ride outside G2G runs — see B5. Student σ
was **not** re-checked for a G2G-enabled checkpoint specifically (time-boxed); marked
UNKNOWN — would need one more cheap eval pass on
`rafdb_newrecipe_g2g_kl_lightle_swa_150e`'s `best_checkpoint.pth`.

### B5. Loss-scale + representation audit

Verified the exact weighting formula in `kd_common.py::DistillationLoss.forward`
(`:403-458`) reproduces the logged `train_loss` column arithmetically for two runs:

- **Baseline** (epoch 150): `loss = alpha·hard + (1-alpha)·soft + beta_vich·aux_kl`
  = `0.2×1.3565 + 0.8×0.2646 + 0.0001×16.657` = `0.2713+0.2116+0.0017` = **0.4846**,
  matches logged `train_loss=0.4846` exactly. No dominance issue; aux_kl (raw ~16.7)
  is correctly suppressed to ~0.0017 by `beta_vich`.
- **Gate** (epoch 150): per-sample blend `alpha_i·hard_i + (1-alpha_i)·soft_i` with
  `alpha_mean=0.4265` reproduces logged `train_loss=0.7241` to 3 decimal places once
  the (already-T²-scaled) per-sample soft term is used. Consistent, no anomaly.
- **G2G(kl)** (epoch 150, `g2g_weight=0.1`, `g2g_warmup_epochs=0` → warmup factor
  1.0): base `alpha·hard+(1-alpha)·soft+beta_vich·aux_kl` = `0.2×1.347+0.8×0.298+0.0001×27.68`
  ≈ `0.510`; **G2G contribution `0.1×1.0×8.841 = 0.884`**; total ≈ `1.394`, matches
  logged `train_loss=1.3948`. **The G2G term supplies ~63% of the total loss
  magnitude — larger than hard+soft+aux combined** at the default `g2g_weight=0.1`.
  This is not a >100× runaway, but it is a real dominance: G2G is nominally an
  auxiliary regularizer but is the single largest gradient source in this run. It
  happens to be the *best*-performing new-recipe run (89.47% SWA) despite/because of
  this, so dominance ≠ failure here, but it is a scale imbalance worth deliberate
  tuning rather than accepting as incidental.
- **logit_std** (epoch 150): `hard_loss=0.975` and `aux_kl=4.44` are both **much
  lower** than every other new-recipe run at the same epoch (baseline: hard=1.356,
  aux_kl=16.66; gate: hard=1.261, aux_kl=14.48) — despite `standardize_logits_per_sample`
  (`kd_baselines.py:12-20`) being documented and coded to apply "in the KD term only —
  the supervised term is untouched" (`kd_baselines.py:16-17`). `soft_loss=0.054` is
  also far smaller than baseline's 0.265. Train_acc for this run is the highest of
  the grid (93.8%) while val_acc (88.49%/88.53%) is mid-pack — **consistent with a
  training/generalization-gap signature**, plausibly because standardizing both
  logits to zero-mean/unit-std before dividing by the same fixed `T=6` used
  elsewhere in the grid compresses the KD target distribution much closer to uniform
  than raw-logit softmax(z/6) does, weakening the effective KD regularization signal
  well below what T=6 was tuned for on raw logits. **Representation
  inconsistency flag**: G2G/Gate consume **raw teacher mu/logvar** (never
  standardized), while `logit_std` consumes **standardized logits** — both coexist in
  the codebase as mutually-exclusive per-run flags (never combined in any run in this
  grid), so there is no single run mixing representations, but the *temperature* is
  shared/fixed across all of them (`--temperature 6.0` in every `run_args.json`
  inspected) without being re-tuned per representation. **LIKELY** contributor to
  `logit_std`'s underperformance specifically, not to the other components.
- τ/T²-scaling convention: confirmed at `kd_common.py:383-388` — `soft_loss =
  mean(per_sample_KD) * T²` (or per-sample T² when adaptive-T/CTKD is active,
  `:384-386`), the standard Hinton et al. convention. Gate's own internal KD term
  also applies `T²` at `kd_common.py:417`. Consistent across all components.

### B6. Numerics / environment

- `torch 2.10.0+cu128`, `cudnn 91002`, GPU `NVIDIA GeForce RTX 5070` (checked live via
  `torch.cuda.get_device_name`) — a build recent enough for Blackwell (RTX 50-series)
  support; no evidence of a stale/incompatible build.
- AMP+SAM GradScaler gap (flagged in session context) — verified at
  `main_encoder.py:134`: `scaler = torch.amp.GradScaler(enabled=not
  getattr(args, "use_sam", False))`. This is real, but **it applies only to the
  standalone teacher-pretraining script (`main_encoder.py`), not to
  `train_rafdb_kd.py`** (the KD student trainer, which never uses SAM and
  unconditionally does `scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)` at
  `train_rafdb_kd.py:746`). So this numerical-risk flag is scoped to **teacher
  retraining only** (relevant to the currently-live `configs/RAFDB_posterv2_vich_klb1e4_200e.yaml`
  run, which the session context notes deliberately runs with AMP off for exactly
  this reason) — it does **not** directly explain the *student* KD regression under
  investigation, though a worse/noisier future teacher checkpoint produced under this
  regime could indirectly propagate.
- Grad-norm logs: **UNKNOWN — not implemented**. No gradient-norm logging exists
  anywhere in `kd_common.py`/`train_rafdb_kd.py` (only loss/accuracy/lr/phase0
  diagnostics are logged to `training_log.csv`).
- No explicit `torch.clamp`/NaN-guard around `exp(logvar)` divisions in the live
  training path outside `kd_g2g.py`'s own `clamp_logvar(min=-10,max=10)` (used by
  G2G only) and `VICHHead`'s own `torch.clamp(logvar, logvar_min, logvar_max)`
  (`models/mobilenetv2_plus.py:129`, applied unconditionally to every VICH forward
  pass, teacher and student). No NaN/Inf observed in any inspected
  `training_log.csv` (A4).

### B7. Data sanity

Confirmed from `train.log`: `Dataset loaded: 12271 train, 3068 val.` — matches
`metadata_rafdb_poster_var.csv` fold counts exactly (`fold==2` → 12271 rows,
`fold==3` → 3068 rows, `pandas` cross-check). Per-class distribution (whole metadata
file, both folds combined):

| class | Surprise | Fear | Disgust | Happiness | Sadness | Anger | Neutral | total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| n | 1619 | 355 | 877 | 5957 | 2460 | 867 | 3204 | 15339 |

This is the well-known RAF-DB class imbalance (Happiness dominant, Fear rare) — expected, not a data-loading defect. `train_folds=[2]`/`val_folds=[3]` are consistent across every run inspected in this report (no fold leakage or fold-set drift found).

---

## Part C — Verdict

### C1. Ranked root-cause hypotheses

1. **CONFIRMED — No single-variable regression exists; the "last good" vs. "failing" comparison is nine-way confounded.** Evidence: A3 diff (`epochs, img_size, LightLE on/off, SWA on/off, teacher checkpoint identity, teacher_input_size 0→224, use_amp, use_vich_sampling, workers`) all changed simultaneously between the closest same-family predecessor (89.83%, old grid) and the current recipe (88.75%, new grid). Any single-cause narrative ("it's the resolution fix", "it's the new teacher") is not falsifiable from existing runs.
2. **LIKELY — `use_vich_sampling: True→False` removed a stochastic regularizer from the student's forward pass**, changing what trains the student's own logvar (B4/B5: now only a `1e-4`-weighted KL pulls it, vs. previously also shaping the sampled logits every step) and roughly halving the raw aux-KL magnitude (A4: ~36 old vs. ~16 new). Plausible generalization-regularization loss, untested in isolation.
3. **LIKELY — `logit_std` component is under-tuned for its temperature.** B5: hard/soft/aux losses are all anomalously low relative to the rest of the grid, train_acc highest (93.8%) with mid-pack val_acc — a generalization-gap signature consistent with the shared `T=6` compressing standardized-logit KD targets too close to uniform, weakening the KD signal below what `T=6` was tuned for on raw logits.
4. **LIKELY — G2G(kl) loss dominance (63% of total loss at default `g2g_weight=0.1`) is a real scale imbalance**, though empirically it is *helping* (best new-recipe result, 89.47% SWA) rather than hurting — flagged as needing deliberate weight tuning, not as a bug causing the regression.
5. **SPECULATIVE — Teacher checkpoint identity (`teacher_vich9237_best.pt`, 92.37%, "untraceable provenance" per the repo's own launcher comments) may itself have been a stronger distillation source than the newer, better-documented `teacher_rafdb_vich_recipe_best.pt` (92.01%)**, independent of the resolution-feed bug — both teachers score B1-verified ~92% themselves, but distillability (soft-target quality) is not necessarily monotonic with teacher accuracy. Not directly tested (would need a same-recipe, teacher-only swap run).
6. **RULED OUT — Teacher preprocessing/normalization/class-mapping mismatch** (B1/B2/B3): current primary teacher measured at 92.01% through the literal training pipeline, confusion matrix clean-diagonal, shared normalization/augmentation/AMP/eval-mode confirmed by direct code inspection. This is *not* the cause.
7. **RULED OUT / DOWN-WEIGHTED — AMP as the dominant driver**: session's own AMP-on-vs-off control (89.02% vs 89.15%/88.30% vs 88.46% SWA... within ~0.2–0.3pp) shows AMP is not a major factor for the student KD trainer; the AMP+SAM GradScaler gap in `main_encoder.py:134` is real but scoped to teacher pretraining, not this regression (B6).
8. **RULED OUT — Dead/saturated Gate or collapsed teacher/student σ**: B4 shows healthy, non-degenerate distributions on both sides, cross-confirmed by two independent measurement paths (live val-set eval and training-log epoch-150 stats).

### C2. Single cheapest discriminating experiment between the top two hypotheses (#1's "nine-way confound" vs. #2 "`use_vich_sampling` regression")

Take the existing new-recipe baseline config (`kd_logs_rafdb_newrecipe_lightle_swa/rafdb_newrecipe_baseline_lightle_swa_150e/2026-07-16-01-50-24/run_args.json`) and flip **only** `--vich-sampling` back on (`use_vich_sampling=True`, i.e. drop `--no-vich-sampling` from the launcher), holding every other flag fixed (same teacher, same 224px, same LightLE, same SWA, same AMP, same 150 epochs). One run, ~150 epochs at ~130s/epoch (per this run's own `elapsed_sec` column) ≈ 5.4 GPU-hours — not cheap in wall-clock, but it is the single smallest edit that isolates hypothesis #2 from the rest of A3's nine-way diff, and a short (~30-epoch) truncated version would already show whether the val-acc trajectory re-diverges from the current 85–87% mid-training band toward the old grid's 88%+ mid-training band (A4 table).

### C3. Open questions for the author

1. What produced the "91.00% LE-VAE KD 200e" figure in `ALL_RESULTS_SUMMARY.md`? No matching `metrics_best.json` exists anywhere in this repo copy — is it from `D:\Veriseti\poster-var`, a since-deleted run, or a different eval script/table not re-run here?
2. Is there a deliberate reason `teacher_vich9237_best.pt` ("untraceable provenance") was the teacher for every historical 88–90% run, while the new, better-documented `teacher_rafdb_vich_recipe_best.pt` is now standard — was the switch itself evaluated in a controlled, single-variable way anywhere outside this session's confounded grid?
3. Was `--no-vich-sampling` (student) a deliberate design change for the new recipe, or an incidental default drift? (`use_vich_sampling` is `True` by default in `parse_args()`, `train_rafdb_kd.py:1002-1003`, but every 2026-07-16 run explicitly passes `--no-vich-sampling`.)
4. Is there a `--disable-kd` (student-only, no-KD) baseline anywhere, even historically, to anchor how much of the 88–91% range is actually attributable to distillation at all versus the LightLE+VICH student architecture and augmentation recipe alone? None was found in this repo.
5. For the G2G loss-scale finding (B5, C1#4): was `g2g_weight=0.1` chosen by a sweep, or is it a placeholder default inherited from another dataset/config?

---
*Diagnostic scripts: `diagnostics/b1_b4_teacher_sanity.py`, `diagnostics/b4_student_sigma.py` (outputs: `diagnostics/b1_b4_teacher_sanity_result.json`, `diagnostics/b4_student_sigma_result.json`). No training code, configs, or checkpoints were modified. The live teacher retrain (`results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/`) was left running untouched throughout.*
