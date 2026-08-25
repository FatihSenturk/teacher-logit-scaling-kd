# Project Status Audit (READ-ONLY) — ⚠️ SUPERSEDED 2026-08-01

> **This file is a dated snapshot (audited 2026-07-22) and is kept as a record, not as current
> state.** Its §12 verdict ("the campaign is not launch-ready") was overtaken: P1–P5 all ran and
> closed. For live state use `diagnostics/status_heartbeat.py` → `repo_export/STATUS.md`; for the
> campaign's standing findings use `diagnostics/claims.md` and `diagnostics/PREREGISTRATIONS.md`.
>
> Specific items below that are now WRONG: the student KD path did gain `--resume`-equivalent
> queue restart via `-StartAt`; run provenance gained `preregistration_block` and a git history
> (first commit 2026-07-11, campaign committed 2026-07-31 — see
> `diagnostics/reports/2026-07-31_git_provenance.md`). The cuDNN nondeterminism finding and the
> gate-normalisation parity check at `kd_common.py:427` still stand.
>
> **Addendum, 2026-08-18 (not a rewrite of the 2026-07-22 body).** §5's line
> "`requirements_27may.txt` EXISTS" is no longer true: that file was deleted on 2026-08-18 and
> replaced by `requirements.txt`, which is now a *producer's output*
> (`diagnostics/requirements_lock.py`) pinning 19 distributions with `==`. The §5 verdict it
> supported — env locking absent — is therefore superseded; the rest of §5 (no git SHA / config
> hash at training time, cuDNN nondeterminism) still stands. Dated records are appended to, not
> edited, in this project.

Audited repo: `poster-var` (git repo, branch `master`).
Method: static inspection only (Read/Grep/git/ls). Every claim cites `file:line`. `UNKNOWN` = not determinable from static inspection.

> Note on the audit's premise: the framing "gating arms: none / entropy / logvar; 3 arms × 3 datasets × 5 seeds = 45 runs" does **not** match the repo. The gate exposes 5 sources (`mean_logvar`/`target_logvar`/`top2_logvar`/`entropy`/`oracle_error`, kd_uncertainty.py:69), runs on disk are single-seed (seed 42), no `entropy`-source gate run exists, and there is no committed 5-seed campaign. Findings below describe the repo as it actually is.

---

## 1. REPO MAP

- **Entry points (training):** `train_rafdb_kd.py` (RAF-DB student KD), `train_affectnetplus_kd.py` (AffectNet+ student KD), `train_ferplus_kd.py` (thin wrapper → `train_affectnetplus_kd`), `main_encoder.py` (POSTER-Var *teacher* training). Modules: `kd_common.py`, `kd_uncertainty.py`, `kd_g2g.py`, `kd_baselines.py`. Student net: `models/mobilenetv2_plus.py`. Teacher net: `trails/posterv2/` (imported, not in root).
- **Config system:** `configs/` holds **53** YAMLs (`ls configs/*.yaml`), all teacher/dataset-architecture specific, loaded by `utils/configs.py::load_yaml` (a flat `setattr` loop, no schema/validation). KD hyperparameters are **not** in YAML — they are argparse flags (e.g. train_rafdb_kd.py:1047-1057).
- **Canonical base.yaml / single-source config:** **MISSING.** No `base.yaml` (`ls base.yaml` → none). There is no single file that defines a full experiment.
- **How one experiment is defined:** a PowerShell launcher assembles a `python -u <script> <flags…>` command and (for teachers) points `--c <config>.yaml` at an architecture YAML. Example: `run_rafdb_component_ablation_3teacher_swa200.ps1`. So an "experiment" = launcher script + CLI flags (+ teacher YAML). No single-source manifest.

## 2. GATE (UGKD)

- **Signal computation** (all in `kd_uncertainty.py`): `mean_logvar` (14-16), `target_logvar` (19-32), `top2_logvar` (35-39), `entropy_from_probabilities` (42-48), `oracle_error` (51-66). Dispatched by `resolve_uncertainty` (72-92); `entropy`/`oracle_error` need no mu/logvar, logvar sources raise if the teacher lacks mu/logvar (kd_uncertainty.py:79-85).
- **Exact normalization:** `UncertaintyNormalizer` (kd_uncertainty.py:95-137). z-score `u_hat = (u − mean)/(std + eps)`, `mode="batch"` (recompute per batch, lines 120-123) or `mode="running"` (EMA momentum 0.99, updated only in `.training`, lines 125-137). Applied at **kd_common.py:427** (`u_hat = self.gate_normalizer(uncertainty)`) to the output of `resolve_uncertainty` (kd_common.py:420-426); the normalizer is constructed once (kd_common.py:204-205).
- **Is normalization identical between entropy and logvar?** **YES.** A single, signal-agnostic normalizer (same instance, same eps/mode) is applied at kd_common.py:427 regardless of which source produced `uncertainty`. There is no per-source normalization branch. (The raw signals differ in scale — entropy in nats vs. logvar ≈ [−4,0] — but both are z-scored by the identical transform, so post-normalization they are on the same scale.)
- **Arm selection:** **CLI flags**, not a config file. `--gate-enable` (train_rafdb_kd.py:1047), `--gate-uncertainty-source {mean_logvar,target_logvar,top2_logvar,entropy,oracle_error}` (train_rafdb_kd.py:1048-1052), plus `--gate-norm/-alpha-lo/-alpha-hi/-k/-tau` (1053-1057). Same flags in train_affectnetplus_kd.py:898-900. Persisted per run via `run_args.json` (`vars(args)` dump).

## 3. TEACHER

- **Loading:** `build_teacher` (train_rafdb_kd.py:94; AffectNet variant train_affectnetplus_kd.py:55) → `load_checkpoint_checked` (kd_common.py:603, default `strict=True`). Run logs emit `"Teacher loaded with strict architecture validation."` → any head/arch mismatch raises immediately.
- **Are VICH mu AND logvar exposed to the student pipeline?** **YES, both.** `extract_mu_logvar` (kd_common.py:573-589) returns `(mu, logvar)` from a VICH dict or a `(logits,mu,logvar)` tuple; both are threaded into the gate (kd_common.py:420-427) and G2G. A plain-logits teacher yields `(None,None)` and consumers raise (kd_uncertainty.py:79-85, kd_g2g.py:60-75).
- **Teacher-output caching:** **EXISTS.** `tools/cache_teacher_outputs.py` dumps per-sample `logits/mu/logvar` to `.npz` + a manifest with `checkpoint_sha256` (line 160) and `"deterministic": True` (line 165), always on the validation transform (lines 68-70). Wired into training via `--teacher-cache` → `load_teacher_cache` (train_rafdb_kd.py:261), `lookup_teacher_cache` (283). Constraint: requires `--no-train-augment` (train_rafdb_kd.py:644-649).

## 4. G2G LOSS

- **Implemented?** **YES**, `kd_g2g.py`: `g2g_kl` (16-36, KL(teacher‖student)), `g2g_w2` (39-48), `g2g_term` (51-57), `validate_g2g_shapes` (60-80, fails loudly on missing/mismatched mu/logvar), `g2g_warmup_factor` (83-92), `clamp_logvar` (12-13). Wired in `DistillationLoss` (kd_common.py; `g2g_enable` kwarg, gate/G2G orthogonal).
- **Student-side Gaussian head present?** **YES.** `VICHHead` (models/mobilenetv2_plus.py:86; `self.mu`=Linear line 109, `self.logvar`=Linear line 110, forward line 125). A VAE-style head with `reparameterize` also exists (models/mobilenetv2_plus.py:68-83).

## 5. REPRODUCIBILITY

- **Seed handling:** student KD calls `set_seed(args.seed)` (train_rafdb_kd.py:627) = `kd_common.py:558-562` → `random`, `numpy`, `torch.manual_seed`, `torch.cuda.manual_seed_all`. **`cudnn.deterministic` / `torch.use_deterministic_algorithms` are NOT set in the student KD path** — so cuDNN nondeterminism is uncovered. Only the **teacher** path sets `cudnn.deterministic = True` (utils/configs.py:23). AffectNet script also seeds `random`/`numpy` (train_affectnetplus_kd.py:444-445).
- **Per-run logging / provenance:** `run_args.json` + `config.json` (`vars(args)` dumps) are written per run. **No git SHA, no config hash, no dataset hash** captured at training time. `hashlib`/`sha256` appear only in tooling — `tools/cache_teacher_outputs.py:160` and `tools/analyze_uncertainty_human.py:233` (checkpoint SHA for their own manifests), and `dataset_utils/affectnet_plus_dataset.py:159` (sha1 cache key, not integrity). → provenance = **PARTIAL**.
- **Env lock files:** `requirements_27may.txt` EXISTS. **No** `conda-lock`/`conda*.yml`/`poetry.lock` (`ls` → none).

## 6. CHECKPOINT / RESUME

- **What is saved (student KD):** `save_checkpoint` (kd_common.py:846-852) persists **only** `{model_state_dict, acc, epoch, +extra}` — **no optimizer state, no scheduler state, no scaler/epoch-RNG**. Files: `last_student.pth`/`last_checkpoint.pth` every epoch (train_rafdb_kd.py:845-846), `best_*` on improvement (866-867), SWA checkpoints (876, 906).
- **Trigger/frequency:** every epoch (last), on val-acc improvement (best).
- **Resume (student KD):** **MISSING.** No `--resume` flag in train_rafdb_kd.py (grep: none) and no optimizer/scheduler in the payload, so a crash restarts from epoch 0. Launchers acknowledge this ("No --resume support -- next attempt restarts from epoch 0", e.g. rafdb_overnight_queue.ps1).
- **Resume (teacher):** **EXISTS.** `main_encoder.py --resume <ckpt>` (main_encoder.py:222) restores full state; teacher checkpoint saves `{model, optimizer, schedule, epoch, scaler}` (main_encoder.py:177-185). Full partial-run recovery for teachers only.

## 7. PRELIMINARY RESULTS (single-seed)

All gate runs are **seed 42**, RAF-DB, under `results/unified_students/` (`run_args.json` + `metrics_best.json`):

| Run | gate source | best acc |
|---|---|---|
| vae9182_gate_noclassweight | `mean_logvar` | 90.09% |
| stage1_gate_noclassweight | `mean_logvar` | 89.57% |
| stage1_gate (200e_noSWA) | `mean_logvar` | 89.02% |
| primary_gate_noclassweight | `mean_logvar` | 89.21% |
| stage1_gate_target_logvar | `target_logvar` | 89.96% |
| primary_gate_target_logvar | `target_logvar` | 89.15% |
| vae9182_gate_oracle_error | `oracle_error` | 89.67% |

- **logvar vs entropy:** only **logvar-source** gate runs exist. **No `entropy`-source gate training run exists anywhere** (`grep '"gate_uncertainty_source": "entropy"' results/.../run_args.json` → none). Entropy is computed only as an offline signal-quality metric (`diagnostics/`), never as a trained gate arm. → the audit's "entropy arm" is **MISSING as a run**.
- Reference baselines (seed 42, same recipe): VAE9182→student 90.06%, Stage1→student 89.67%, Primary→student 89.60% (results/unified_students/*/metrics_best.json).

## 8. DATASETS

- **Expected paths (present):** `data/rafdb_aligned/`, `data/AffectNet+/`, `data/FERPlus_processed/` (+ `data/FERPlus_Created/`) — all exist (`ls data/`).
- **End-to-end wiring:**
  - RAF-DB: **wired**, extensive runs (`results/unified_students/`, train_rafdb_kd.py).
  - AffectNet+8: **wired**, runs under `kd_logs_affectnet8/` (baseline/g2g_kl/logit_std/adaptive_t/ctkd; matches last git commits).
  - FERPlus: teacher + student checkpoints exist (`checkpoints/teacher_ferplus_vich_best.pt`, `checkpoints/ferplus_student_8976_best.pth`), wrapper `train_ferplus_kd.py` — student-run **log location UNKNOWN** (no `training_log.csv` matched under `kd_logs*`/`results` this pass).
  - AffectNet+7: teacher exists (`checkpoints/teacher_affectnetplus7_vich_best.pt`); student runs **UNKNOWN**.
- **Integrity verification:** count-check only, opt-in: `train_affectnetplus_kd.py:513-519` raises on `--expected-train-samples`/`--expected-val-samples` mismatch; RAF-DB only **prints** counts (train_rafdb_kd.py:677). **No SHA/hash-based dataset integrity** anywhere.

## 9. HEALTH

- **Tests (inventory, not run):** `tests/test_baselines.py`, `tests/test_g2g.py`, `tests/test_gate.py`, `tests/test_kd_backward_compat.py` (stdlib `unittest`, fixed `torch.Generator` seeds, e.g. tests/test_g2g.py:19). Coverage: baselines, G2G, gate, backward-compat. **No** dataset/integration or teacher-loading tests.
- **Broken imports:** **UNKNOWN** (not verified without importing; `pytest` is not assumed installed).
- **TODO/FIXME/XXX:** **0** in `*.py` (grep).
- **Git:** branch `master`; last 5 commits are AffectNet+8 ablation resume checkpoints (`902c5b4` adaptive_t 61.63%, `e139a59` logit_std 58.08%, `cb27527` g2g_kl 61.93%, `31cab14`/`95884b8` launcher params). **43 uncommitted** paths: modified `kd_common.py`, `kd_uncertainty.py`, `train_rafdb_kd.py` (+1 ps1); untracked `diagnostics/`, `evaluation_runs/`, new configs (incl. `RAFDB_posterv2_vae_recipe_seed1.yaml`), and ~15 launcher scripts. The Phase-0/A/B/C work (gate sources, temperature-scale flag, G2G, seed replicates) is **uncommitted**.

## 10. TIMING (per-epoch wall-clock, from `training_log.csv::elapsed_sec`)

| Dataset (student KD) | evidence | per-epoch |
|---|---|---|
| RAF-DB | results/unified_students/RAFDB_vae9182_adaptive_t/.../training_log.csv (n=400) | **~36.2 s** |
| AffectNet+8 | kd_logs_affectnet8/affectnet8_adaptive_t_250e/.../training_log.csv (n=250) | **~111.8 s** |
| FERPlus | log not located | **UNKNOWN** |
| Teacher (POSTER-Var) | `main_encoder.py` writes no per-epoch CSV | **UNKNOWN** from committed logs |

RAF-DB student ≈ 36 s/epoch × 400 ep ≈ 4 h solo; AffectNet+8 ≈ 112 s/epoch × 250 ≈ 7.8 h solo (single-run, un-paired).

## 11. GAP TABLE

| Item | Status | Evidence / what is needed |
|---|---|---|
| base.yaml single-source config | **MISSING** | configs/ = 53 arch-only YAMLs; KD hyperparams are argparse (train_rafdb_kd.py:1047-1057). Need one composable base config. |
| one-command launcher | **PARTIAL** | Per-experiment `.ps1` (e.g. run_rafdb_component_ablation_3teacher_swa200.ps1); no single parameterized `run(dataset,arm,seed)` entry. |
| run manifest | **PARTIAL** | `run_args.json`/`config.json` exist; no git SHA / config hash / dataset hash (kd_common has no provenance capture; hashlib only in cache tools). |
| teacher mu/logvar cache | **EXISTS** | tools/cache_teacher_outputs.py (+sha256 manifest 160) wired via --teacher-cache (train_rafdb_kd.py:261,283); caveat: requires --no-train-augment (644-649). |
| gate normalization parity | **EXISTS** | Single normalizer applied to all sources at kd_common.py:427 (UncertaintyNormalizer kd_uncertainty.py:95-137); identical for entropy and logvar. |
| fixed seed list | **MISSING** | `--seed` flag exists; runs are ad-hoc (42, then {1,43,44}); no committed canonical seed list for a 5-seed sweep. |
| checkpoint-resume | **MISSING (student)** / EXISTS (teacher) | student `save_checkpoint` omits optimizer+scheduler (kd_common.py:846-852) and has no `--resume`; teacher has both (main_encoder.py:177-185, 222). |
| results CSV aggregation | **PARTIAL** | tools/build_unified_results_table.py, tools/build_unified_matrix_results.py, tools/eval_rafdb_teacher_student_table.py exist; not a single auto-run pipeline over a seed×arm×dataset grid. |

## 12. VERDICT

The building blocks (gate with parity-normalized signals, G2G with a student Gaussian head, strict teacher load, teacher mu/logvar cache, per-run arg dumps, aggregation tools) are in place and tested; the campaign is **not** launch-ready. Ranked by effort to close: (1) **low** — commit the uncommitted core (kd_uncertainty/kd_common/train_rafdb_kd) and freeze a canonical seed list; (2) **low-med** — a run manifest with git SHA + config/dataset hash, and a single `run(dataset,arm,seed)` launcher + results-grid aggregator; (3) **med** — **student checkpoint-resume** (persist optimizer/scheduler + `--resume`), the single blocker for long unattended multi-seed runs given no student resume today; (4) **med** — add the never-trained `entropy` gate arm and wire AffectNet+7/FERPlus student runs end-to-end (integrity currently count-only, no hashes; cuDNN nondeterminism uncovered in the student path).
