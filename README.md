# teacher-logit-scaling-kd

Code, run manifests and pre-declaration records for

> **Teacher-Side Logit Scaling Governs Student Calibration in Knowledge
> Distillation: Dose-Response Evidence from Facial Expression Recognition**
> Muhammed Fatih Şentürk, Gülsüm Zeynep Gürkaş Aydın
> Department of Computer Engineering, Istanbul University-Cerrahpaşa
> *Under review at Neurocomputing.*

The paper's claim is that a teacher's **calibration**, not its accuracy, governs
what a distilled student inherits. This repository holds what is needed to check
that claim from the recorded evidence: the ledger of every finished run, the
frozen selection audit, the analysis scripts that turn them into the paper's
tables, and the pre-declarations that fixed each decision rule before its runs
were launched.

**Not included:** datasets, model checkpoints, `results/` run directories, raw
training logs, and the manuscript sources. See [Data](#data) and
[PROVENANCE.md](PROVENANCE.md).

**Which version this is.** The current tag is `v1.0.1-submission`. Cite a tag, not
the branch: the branch moves and the tag does not.

| tag | date | what it adds |
|---|---|---|
| `v1.0.0-submission` | 2026-08-26 | the archive as submitted alongside the manuscript |
| `v1.0.1-submission` | 2026-08-28 | `evidence/` (dated commit-and-tag export + authoring-machine mtime manifest, promised by the manuscript's S11); the figure producers moved to the SWA checkpoint (paper Fig. 2 / S2); the pre-registration block map correction dated 2026-08-27; and the student-side scaling round of 2026-08-28 &mdash; two derived producers (`diagnostics/ferplus_scaled_ece_axis.py`, `diagnostics/rafdb_student_ts_dose.py`) with their tables, both computed from already-published artifacts rather than from any new evaluation |

**This archive supersedes an earlier one.** The same work was first published as
`FatihSenturk/calibration-law-fer` and archived on Zenodo in three versions between
15 and 23 August 2026. All three of those records were withdrawn by the depositor on
25 August 2026 and now serve tombstone pages, and that repository was made private on
26 August 2026. This repository re-publishes the work as one clean archive: the same
producers, the same measured values, the same pre-declarations. `PROVENANCE.md` states
exactly what is the same and what is not. Note that the manuscript under review still
prints the earlier repository's URL and DOI; neither resolves any more, and both are
corrected at revision.

The DOI to cite is the **concept DOI** for this archive — `10.5281/zenodo.22111203` —
which always resolves to the newest archived version. To pin one exact tree instead,
use that version's own DOI from its Zenodo record: `v1.0.0-submission` is
`10.5281/zenodo.22111204`; `v1.0.1-submission`'s version DOI is shown on its record
(it is minted at publication and is deliberately not guessed here).

Citation metadata is machine-readable: [`CITATION.cff`](CITATION.cff) (the paper
is the preferred citation; the archive is listed under `identifiers`) and
[`.zenodo.json`](.zenodo.json), which is what the archive record is built from.

---

## What can be reproduced, and at what cost

| level | what you get | what you need |
|---|---|---|
| **1. Tables and numbers** | every table and quoted number in the paper | this repository + Python. **No GPU, no dataset, no checkpoint.** |
| **2. Figures** | the paper's figure PDFs, regenerated and gated | as above, plus `PyMuPDF` |
| **3. Re-running an experiment** | a new run of any arm | a GPU, the datasets, and a teacher checkpoint (available on request) |

Level 1 works because the evidence is committed, not just the code: `runs.csv`
carries one row per finished run with every field derived from that run's own
artefacts, and `diagnostics/selection_audit/` carries the frozen N=131 audit set
quoted in the abstract.

### Level 1 — regenerate the tables

```
python -m venv .venv && .venv\Scripts\activate     # Windows
python -m venv .venv && source .venv/bin/activate  # macOS / Linux
pip install -r requirements-level1.txt

python diagnostics/paper_tables.py                 # -> diagnostics/paper_tables/RESULTS_TABLES.{md,json}
python diagnostics/table_diff_gate.py              # verifies the result cell-by-cell vs. the accepted baseline
```

`requirements-level1.txt` is what these two commands need — 14 distributions,
no CUDA. `requirements.txt` is the full measured environment (19) and pulls the
CUDA build of PyTorch; you need it only for Level 3. `paper_tables.py` also
writes `paper/tables/tab_app_paired_sd.tex`, the one table the manuscript takes
verbatim; the manuscript is not distributed here, so that file has nothing to be
read by and the directory it creates can be deleted.

`table_diff_gate.py` is the check that matters: it compares the freshly
generated tables against the committed baseline and reports any drifted cell. A
clean run means the tables in the paper and the tables this code produces are
the same tables.

### Tracing a single number back to its source

`runs.csv` is the **run ledger** — one row per finished run. It is not the same
thing as the **number ledger**, which is the layer added after the first
submission and answers a narrower question: for every number printed in the
paper, which artifact field is it, and does it still match?

| file | what it holds |
|---|---|
| `diagnostics/paper_tables/number_ledger.md` | every printed number, its artifact, its field path and the rounding declared for it |
| `diagnostics/paper_tables/derived_registry.json` | quantities the paper computes from other fields, with the formula |
| `diagnostics/check_numbers.py` | the auditor: re-resolves every binding against the artifacts and exits non-zero on any mismatch or unregistered number |
| `diagnostics/reports/producer_freshness.md` | which script produces which artifact (machine-checked; the prose is Turkish) |

The auditor needs the manuscript source to re-read the printed side, and that
source is not distributed with this repository (see **Not included**, above). What you can do
here without it: open `number_ledger.md`, find the number, and follow its
artifact path into `diagnostics/`. Every artifact it names is present in this
repository — that is itself checked, and a binding whose source were missing
would fail the gate.

### Level 2 — regenerate the figures

```
pip install PyMuPDF==1.27.1                        # Level 2 only; not in requirements-level1.txt

python diagnostics/export_paper_figures.py         # -> paper/figures/*.pdf (directory created if absent)
python diagnostics/verify_paper_figures.py         # hard gate: vector-only, TrueType, >= 7 pt, single page
```

The extra install is named because leaving it out is a real failure and not a
theoretical one: `verify_paper_figures.py:39` imports `fitz`, and a reader who
installed only the Level-1 file gets `ModuleNotFoundError: No module named 'fitz'`
on that second line. The pin is the one in `requirements.txt`, which is generated.
`export_paper_figures.py` itself needs nothing beyond Level 1.

Figure binaries are deliberately **not** committed — they are outputs, and the
gate above is what guarantees they are correct.

---

## Output → producing script

Everything below is Level 1 (CPU, no data) unless the row says **Level 3**. Five rows
say it because they reach into `results/`, `checkpoints/` or `data/`, none of which is
distributed here; they are listed so their output can be traced to a producer, not so
that it can be regenerated. An earlier version of this line implied the marking was
complete when those five carried no marker.
`D` = `diagnostics/`.

### Main tables

| output | script |
|---|---|
| `D/paper_tables/RESULTS_TABLES.{md,json}` (T1–T15) | `D/paper_tables.py` |
| `D/table_diff_gate/last_diff.md` (the cell-by-cell gate) | `D/table_diff_gate.py` |
| `D/paper_tables/t5_pairing_diff.*` (T5 pairing) | `D/t5_pairing_diff.py` |
| `D/paper_tables/denominator_table.*` (denominator conventions, seed-sd bars) | `D/denominator_table.py` |
| `D/paper_tables/section54_numbers.*` (§5.4) | `D/section54_numbers.py` |
| `runs.csv` (the run ledger itself) | `D/build_runs_ledger.py` — **needs the run directories** |

### Statistics and calibration analysis

| output | script |
|---|---|
| `D/paper_tables/inferential_tests.*` (§5.1 paired *t*, *d_z*, Holm) | `D/inferential_tests.py` |
| `D/paper_tables/headroom_review.*` (Eq. 8 headroom, three teachers) | `D/headroom_review.py` |
| `D/paper_tables/student_ts_baseline.*` (§5.6, post-hoc student scaling) | `D/student_ts_baseline.py` |
| `D/paper_tables/tstar_stability.*` (T\* split-half stability) | `D/tstar_stability.py` |
| `D/teacher_temperature_scaling/` (teacher T\* fits) | `D/teacher_temperature_scaling_fit.py` — **needs teacher checkpoints** |
| `D/seed_variance/` (seed-variance bars) | `D/seed_variance_ece.py`  **Level 3** — reads `results/unified_students`, which is not distributed. |
| `D/rafdb_calibration_backfill/` (ECE/MCE backfill, bin sensitivity) | `D/rafdb_calibration_backfill.py`  **Level 3** — reads `results/unified_students`, which is not distributed. |
| — the sd convention used throughout (sample sd, *n*−1) | `D/stats_convention.py` |

### Selection audit (§4 m6)

| output | script |
|---|---|
| `D/selection_audit/selection_audit.csv` (frozen, N=131) | `D/selection_audit_table.py` — **Level 3**, reads `results/unified_students`; cutoff frozen inside; **raises if the set drifts** |
| `D/selection_audit/selection_gain.json` (order-statistic estimate) | `D/selection_gain_estimator.py` |
| `D/paper_tables/order_stat_trend.*` (last-*K* window, detrended) | `D/order_stat_trend.py` |
| `D/selection_audit/selection_robustness.json` | `D/selection_robustness.py` |
| `D/selection_audit/selection_optimism_headline.json` | `D/selection_optimism_headline.py` |
| `D/selection_audit/ferplus_selection_audit.csv` (replication) | `D/ferplus_selection_audit.py` |

### Pre-declared verdicts

| output | script |
|---|---|
| `D/p2_gate_oracle/p2_verdict.{json,md}` (B2 oracle-gate diagnosis) | `D/p2_gate_oracle_verdict.py` |
| `D/p5_oracle_replication/` (P5 replication verdict) | `D/p5_oracle_replication_verdict.py` |
| `D/vich_isolation/vich_isolation_verdict.json` (B1 head isolation) | `D/vich_isolation_verdict.py`  **Level 3** — reads `results/unified_students`, which is not distributed. |
| `D/adaptive_t_headroom/` (adaptive-T headroom) | `D/adaptive_t_headroom_table.py` |
| `D/a13_scratch_dose/a13_verdict.{json,md}` (A13 scratch dose-response) | `D/a13_scratch_dose_verdict.py` |
| `D/teacher_head_compat_audit/VERDICT.md` (teacher-head compatibility) | `D/teacher_head_compat_audit.py`  **Level 3** — reads `results/ + checkpoints/`, which is not distributed. |

### Mechanisms, efficiency, FERPlus

| output | script |
|---|---|
| `D/paper_tables/mechanism_specs.*` (appendix spec table, machine-generated from each run's own `run_args.json`) | `D/mechanism_specs.py` |
| `D/paper_tables/mechanism_diagnostic.json` | `D/mechanism_diagnostic_figure.py` |
| `D/p5_efficiency/latency_benchmark.{csv,json}` | `D/latency_benchmark.py` — **needs checkpoints + a device** |
| `D/p5_efficiency/` (efficiency frontier, capacity law) | `D/efficiency_frontier.py`, `D/capacity_law_check.py`, `D/p5_efficiency_frontier.py` |
| `D/c4_efficiency_table/` | `D/c4_efficiency_table.py` |
| `D/ferplus_jsd/` (human-vote JSD, teacher/student grids) | `D/ferplus_human_vote_jsd.py`, `D/ferplus_student_jsd.py`, `D/ferplus_teacher_signed_grid.py` |
| `D/teacher_ece_grid/` | `D/teacher_ece_grid.py` — **needs teacher checkpoints** |

### Figures

| output | script |
|---|---|
| `paper/figures/*.pdf` (all figures, journal styling) | `D/export_paper_figures.py` |
| the figure gate (vector / fonts / type size / no in-figure title) | `D/verify_paper_figures.py` |
| individual producers | `D/reliability_diagram.py`, `D/perclass_calibration.py`, `D/vote_examples_figure.py`, `D/selection_distribution_figure.py`, `D/p1_two_teacher_overlay.py`, `D/p1_signed_miscalibration_overlay.py`, `D/two_dataset_overlay.py`, `D/p5_frontier_figure.py`, `D/ferplus_dual_axis_figure.py`, `D/graphical_abstract.py` |

### Training (Level 3 — GPU + data + checkpoints)

| what | entry point |
|---|---|
| teacher training | `main_encoder.py --c <config in configs/>` |
| RAF-DB distillation | `train_rafdb_kd.py` |
| AffectNet+ / FERPlus distillation | `train_affectnetplus_kd.py`, `train_ferplus_kd.py` |
| the exact command line of every published run | the `*.ps1` queue at the repository root named by the matching block in `diagnostics/PREREGISTRATIONS.md` |

**What Level 3 costs.** The run ledger records **199 finished student runs** across
six families — baseline 49, mechanism_ablation 66, dose_response 68, width_frontier 9,
miscal_causal 4, vich_isolation 3 — totalling **76,700 epochs**. Both numbers come from
`runs.csv`, which `diagnostics/build_runs_ledger.py` derives from each run's own
`run_args.json` and `metrics_best.json`; the same 199 runs are the ones whose per-epoch
curves sit in `diagnostics/epoch_curves.npz`.

Wall-clock cost is **not** measurable from anything published here, and an earlier
version of this paragraph claimed otherwise: it reported "172 finished student runs =
575 GPU-hours" under the heading *measured*. The count was stale and `runs.csv` has no
duration column, so neither the GPU-hours nor the per-run mean can be re-derived from
this repository. As an order of magnitude recorded at the time and **not** reproducible
here: a solo 400-epoch run took roughly 2 h on one RTX 5070, and runs executed
two-at-a-time cost about 1.8× that each. Teacher trainings are not in the ledger at all,
so this repository supports no count of them. Reproducing a *single* arm is cheap;
reproducing the campaign is not.

**What is deliberately not published, and why.**

| not here | why | on request |
|---|---|---|
| run directories under `results/` (checkpoints, per-epoch logs, confusion matrices) | size — hundreds of GB | yes |
| teacher checkpoints | size | yes |
| the per-run raw outputs under `results/` | size | yes |
| the datasets (RAF-DB, FERPlus) | licensed by their owners, not ours to redistribute | obtain from the original providers |

The cached model outputs under `diagnostics/` **are** included (5.3 MB in total): they let
you re-derive the joint-optimum, robustness, selection-gain and FERPlus-JSD tables without
any run directory. They are model outputs computed on the validation split, plus the minimum needed to
line a row up with the thing it predicts. Stated exactly, because the short version
("no dataset content is republished") was here first and is not true: **no image is
republished, and no FERPlus vote distribution is republished**, but every cache does
carry the ground-truth **label vector** for the split it was computed on, and one of
them also carries the FERPlus **file names**. What that is and why is in the table
below. A label column without the images is not the dataset and cannot be used as one,
but it is annotation, and calling it "not dataset content" was wrong.

Three groups make up that total.

| group | size | what it is |
|---|---|---|
| `diagnostics/ferplus_jsd/`, `diagnostics/teacher_ece_grid/` | 554 KB | four teacher/validation logit caches, here from the start |
| `diagnostics/student_logits/` | 3.4 MB | 42 student logit caches, added 8 Aug 2026 |
| `diagnostics/epoch_curves.npz` | 1.2 MB | per-epoch validation accuracy and loss — 199 runs, 76,700 epochs, added 9 Aug 2026 |

Opened and listed rather than described from memory — every array in every cache:

| cache | arrays |
|---|---|
| `teacher_ece_grid/teacher_val_logits_{stage1,primary,vae9182}.pt` | `logits`, `labels` |
| `ferplus_jsd/ferplus_val_logits.pt` | `logits`, `labels`, `indices`, **`paths`** |
| `student_logits/*.npz` (42 files) | `logits`, `labels`, `meta` |
| `epoch_curves.npz` | 597 arrays = 199 runs × (`epoch`, `val_acc`, `val_loss`) |

The logit matrices have 3068 rows for RAF-DB and 3153 for FERPlus. **No image and no
FERPlus vote distribution appears in any of them** — a scan of every array name across
all 43 `.npz` and 4 `.pt` files returns nothing matching vote, distribution or
annotation.

The exception worth naming is `paths` in `ferplus_val_logits.pt`: 3153 FERPlus image
**file names** (`fer0032220.png`, …). It is there because four producers —
`ferplus_abstention_entropy.py`, `ferplus_human_vote_jsd.py`,
`ferplus_teacher_signed_grid.py` and `jsd_sensitivity.py` — align a cached row with a
row of the human-vote file by name, and would silently mis-pair rows without it. File
names are not pixels and not votes, but they are FERPlus identifiers, so they are
declared here rather than left for a reader to discover by opening the file.

The **42 student caches** were added for one reason: without them,
`diagnostics/robustness_metrics.py` (the seven-metric dose–response inventory) and
`diagnostics/r3w1_joint_optimum.py` (the FERPlus joint-optimum test) read
`results/unified_students/`, so those two tables could **not** be reproduced here. They are
**byte copies**
of the caches written inside each run directory, not repackaged: the collector
(`diagnostics/publish_student_logits.py`) hashes source and copy separately and stops
unless the two sha256 digests are equal. `diagnostics/student_logits/MANIFEST.json` records
for each file which run directory it came from, its sha256, and the accuracy and ECE stored
in its own metadata — so the copy's provenance is checkable, not asserted.

One consequence of insisting on byte copies is stated rather than hidden: each `.npz` still
carries, inside its own `meta` field, the **absolute path of the run directory it was
written in** on the machine that trained it. It was not scrubbed, because scrubbing means
repacking, and repacking would void the sha256 identity that makes the copy provable in the
first place. `MANIFEST.json` publishes the same provenance in repository-relative form
(`results/unified_students/<run>/<timestamp>`), so nothing here depends on reading the
embedded string. Every one of the 42 shares the same root, `…\poster-var\results`: a local
directory layout and nothing else, with no user name and no credential in it.

`epoch_curves.npz` was written by `diagnostics/publish_epoch_curves.py` and is **not** a byte
copy — it is a repack, because the source is ten-column CSV and only three columns are used.
That is why its arrays are `float64` rather than `float32`, and the reason is worth stating
because it is not obvious: the training logs record `val_acc` at full double precision, and
rounding to `float32` makes distinct epoch accuracies compare equal. `argmax` then picks an
earlier epoch, and `argmax_in_last_K` moved by 1.5–2 points before the dtype was fixed. With
`float64` both consumers reproduce their previously published numbers exactly. A repack is
only safe once you have checked that it is.

**So please do not shrink this file.** `float32` halves it to 761 KB and the two tables it
feeds stop reproducing — that was measured, not feared.

This is the honest consequence: **a reader who clones this repository and runs the
analysis scripts gets Level 1 and Level 2, not Level 3.** Level 1 works precisely
because the evidence that the tables read — `runs.csv`, the frozen audit set, the
cached `paper_tables/` artefacts — is committed here rather than being regenerated
from the raw runs. Scripts that do reach into `results/`, `checkpoints/` or `data/` are included for
inspection and will not run end-to-end without those directories. They are marked
**Level 3** in the table above — `selection_audit_table.py:59`,
`seed_variance_ece.py:65`, `rafdb_calibration_backfill.py:41`,
`vich_isolation_verdict.py:53` and `teacher_head_compat_audit.py:35` are the lines that
make each of them Level 3.

---

## Pre-declaration records

`diagnostics/PREREGISTRATIONS.md` is the campaign's central discipline, and the
reason several results in the paper are reported as null rather than quietly
dropped. The rule was **declare → commit → tag → launch**: before a queue of
runs started, its prediction *and* its decision rule were written down,
committed, and tagged. Nothing in the rule could then be adjusted after seeing a
result — and where a rule turned out to be looser than its declaration, it was
tightened rather than relaxed (the A2 kill-switch is the worked example).

Read it together with:

- `diagnostics/preregistration_blocks.csv` — a **human-authored declaration** of
  experimental intent, not something inferred from the data. Its header says so.
- `diagnostics/claims.md` — the paper's claim inventory and what backs each one.
- `PROVENANCE.md` — the tag hashes and dates from the working repository. This
  repository has a fresh single-commit history, so the timestamps that carry
  evidential weight are recorded there. It also states plainly what that record
  can and cannot prove.

Dates inside `PREREGISTRATIONS.md` are the declaration dates; where a
declaration precedes its runs, the corresponding tag in `PROVENANCE.md` is the
corroboration.

One document it cites is **not** here, and naming it is better than letting a reader
find the gap: lines 518 and 532 attribute a scope decision to `paper_review.md`, an
external review that was never part of this repository and is not distributed. The rule
that every cited artifact must be present in this repository is enforced for the number
ledger — the layer that binds printed numbers to fields — and that rule is what the
`v1.0.1`/`v1.0.2` tags added. It does not extend to documents cited in prose inside the
pre-declaration record, which is a dated file and is not edited after the fact.

### A note on language

This campaign was conducted in Turkish, and its records were written in Turkish.
Everything a reader needs in order to follow the evidence is in English:

- **`diagnostics/PREREGISTRATIONS.md` is Turkish and was not translated.** Of
  its 850 non-empty lines, 719 (85%) carry Turkish. An earlier version of this
  section said it had been translated for release; that was wrong. It is included
  verbatim on purpose — it is the record of *when* each prediction was fixed, and
  a rewritten declaration is a weaker declaration. What carries the evidence in it
  is language-independent: dates, artefact paths, line numbers, thresholds and
  measured values, which is what the corroboration in `PROVENANCE.md` is built on.
- **The two documents a reader follows first are English.**
  `diagnostics/paper_tables/RESULTS_TABLES.md` (4 of 318 non-empty lines carry
  Turkish) and `diagnostics/claims.md` (3 of 221) read as English apart from the
  verdict words their producers print: `DOĞRULANDI` (confirmed), `YANLIŞLANDI`
  (falsified), `ÇÖZÜNMEDİ` (not resolved — the effect was below the declared bar,
  which is not the same as "no effect"). Of the 43 generated tables under
  `diagnostics/paper_tables/`, 21 carry some Turkish in their headers and notes;
  no column name or number depends on it. These files are produced by the scripts
  listed above, so their language lives in the producers rather than in a
  hand-edited copy: regenerating them reproduces exactly this.

Left in Turkish on purpose: `BULGULAR.md`, `METHODS_DATA.md`,
`diagnostics/DIAGNOSTIC_REPORT.md` and the two dated files kept under
`diagnostics/reports/` are original laboratory records, included verbatim rather
than rewritten, because their value is precisely that they were not written for an
audience. The rest of that directory — the campaign's internal round reports — is
not published here; `PROVENANCE.md` says which files were kept and why. Many source comments
are Turkish for the same reason.

---

## Environment

Everything here was run on **Python 3.13.10**, **PyTorch 2.10.0 (CUDA 12.8)**,
Windows 11, on a single NVIDIA RTX 5070 with an AMD Ryzen 9 7950X. Versions are
pinned in `requirements.txt`.

There are two pin files and the difference is measured, not curated.
`requirements.txt` records the environment the campaign actually ran in: every
top-level import in the repository, mapped to the installed distribution.
`requirements-level1.txt` is narrower, and its definition is the **transitive
import closure of the two Level-1 commands** — start at `paper_tables.py` and
`table_diff_gate.py`, and every time an import resolves to a file in this
repository, descend into it. That closure is 18 local files and 14 distributions;
what falls away relative to the full environment is `PyMuPDF`, `PyYAML`,
`seaborn`, `torchmetrics` and `wandb`.

The definition is worth stating that precisely because the obvious shorter one is
wrong, and was wrong here first. "The distributions imported by `diagnostics/*.py`"
looks equivalent and is not: it stops after one hop, and `paper_tables.py` reaches
`cv2`, `tqdm`, `timm` and `thop` on the *second* hop, through
`calibration_metrics.py` → `teacher_temperature_scaling_fit.py` →
`train_rafdb_kd.py`. Those are repository files, so a one-hop scan classifies them
as local and never looks inside. An environment built from that shorter list
installs cleanly and then fails at `paper_tables.py:410` with
`ModuleNotFoundError: No module named 'cv2'`.

`torch` is **not** dropped — it is in the closure, and 31 scripts under
`diagnostics/` import it directly. What Level 1 does not need is CUDA, so the
local version label is stripped there (`torch==2.10.0` rather than
`torch==2.10.0+cu128`) and the CPU wheel index is named.

That label is also why an earlier version of this repository could not be
installed from its own instructions: `torch==2.10.0+cu128` is not on PyPI, so
`pip install -r requirements.txt` ended in "No matching distribution". Both files
now carry the `--extra-index-url` line that makes the pin resolvable, and the URL
is derived from the label rather than typed in.

Two entries in `requirements.txt` will look odd, and both are deliberate. `numpy==2.4.0rc1`
is a release *candidate* — that is what the analysis actually ran on, and the file
records the measured environment rather than a tidier one. And both
`opencv-python` and `opencv-contrib-python` are pinned, because the import name
`cv2` resolves to either: a clean install needs both to reproduce what was here.
Both are in the Level-1 subset too, for the reason given above.

Run scripts from the repository root — each resolves its own paths relative to
its own location. Scripts that read run artefacts expect them under `results/`,
which is not distributed; those are marked above.

---

## Data

**No dataset is redistributed here.** The paper uses two, each obtained from its
maintainers under their own terms:

- **RAF-DB** — <http://www.whdeng.cn/raf/model1.html> (request form, academic use)
- **FERPlus** — <https://github.com/microsoft/FERPlus> (labels; the images come
  from the FER2013 Kaggle release)

AffectNet is **not** needed; the arms that used it were removed before
publication (see [Scope](#scope)). One filename still points the wrong way:
`configs/RAFDB_teacher_affectnet_recipe.yaml` trains a **RAF-DB** teacher — it
only borrows AffectNet's augmentation recipe (`transforms_name: QCS-rafdb`) and
starts from no AffectNet weights (`pretrained_local: ~`).

`configs/FERPlus_majority_metadata.csv` is the derived label file for the strict
majority split used in the paper — a hard label is kept only when one emotion
holds **more than 50%** of the cleaned votes, which makes ties structurally
impossible. It is built from the public FER+ vote file by
`tools/build_ferplus_majority_metadata.py` and contains no image data.

Model checkpoints are excluded for size and are available on request from the
corresponding author.

**Where the config files expect your copy.** Because the datasets are licensed to
their owners and are not ours to redistribute, no config in `configs/` can point at
a real directory in this repository. Every dataset path is therefore written as the
placeholder `<DATASET_ROOT>` — **the directory holding your own copies of the image
sets** — for example `train_root: <DATASET_ROOT>/AffectNet+` and
`metadata: <DATASET_ROOT>/FERPlus_processed_metadata.csv`. A second placeholder,
`<CHECKPOINT_ROOT>`, marks **the directory holding locally pre-trained backbone
weights**, and appears only in the `pretrained_local:` field, e.g.
`pretrained_local: <CHECKPOINT_ROOT>/best.pt`. The two are separate because they are
separate things: a checkpoint root is not a dataset root, and on most machines they do
not live under the same parent. **Replace both with the paths to your own copies before
running anything at Level 3.** Configs whose data path is already repo-relative
(`train_root: data/rafdb_aligned`) are left as they are — nothing to substitute there,
you just place your copy under `data/`. The placeholder is
deliberate rather than a relative path that happens to resolve: a config that
silently points at an empty `data/` directory fails later and less clearly than one
that states outright that a path is required. Level 1 (regenerating every table and
number in the paper) needs none of this — it reads only the artefacts committed here.

---

## Scope

Every file here should be able to produce a table, a figure or a declared claim
in the paper. That is the intent, and the analysis layer meets it. Two sentences
that used to stand here claimed more, and correcting them matters more than the
tidiness they claimed.

**The pruning announced in `PROVENANCE.md` §1 was never applied to this
repository.** Both documents stated that 111 files — 4.3 MB, "about half the
original size" — tied to no paper number had been removed: the AffectNet /
AffectNet+ line of work, the pre-campaign FERPlus arms with their two superseded
label files, five earlier-project configs, and the Phase-0 / "unified" era
launchers and reporting tools. None of it was removed. Every category is in the
tag you are reading, and was already in the first archived version. Measured in this
tree: 9 paths matching `affectnet`, 19 `run_phase0_*.ps1`, 5 of 5 named configs,
2 of 2 superseded label files — 41 tracked files, 4,308,776 bytes. The size in
that sentence was right; the verb was not.

**Carrying it out as written would have broken the FERPlus chain.**
`train_affectnetplus_kd.py` is not AffectNet work. It is the FERPlus student
trainer, under a name inherited from the code it was forked from:
`METHODS_DATA.md` cites it by line number six times (optimiser, scheduler, AMP,
the SWA window), eight scripts under `diagnostics/` name it, and
`ferplus_dose_response_queue.ps1` launches it. The same holds for
`configs/RAFDB_teacher_affectnet_recipe.yaml`, which `METHODS_DATA.md` gives as
the teacher config of one of the three arms.

What survives is the part a reader can act on: none of the surrounding material
carries a number the paper prints. `AffectNet` appears **0** times in
`diagnostics/paper_tables/RESULTS_TABLES.md`, `diagnostics/claims.md`,
`diagnostics/PREREGISTRATIONS.md` and `runs.csv` (199 rows). Where it does appear
— `METHODS_DATA.md`, `STATUS.md`, `BULGULAR.md` — it is either that trainer under
its old name, or a Turkish laboratory record of work that did not enter the paper.

So read this repository as the campaign, not as a curated subset of it. Configs
and launchers that produced nothing the paper uses are still here. That is worse
for tidiness and better for the question this repository exists to answer, which
is not "is this clean?" but "can I get from a printed number to the thing that
produced it?" See [PROVENANCE.md](PROVENANCE.md).

---

## Licence

MIT — see [LICENSE](LICENSE). The teacher backbone under `trails/` and the
optimiser under `trials/` are derived from third-party projects and remain under
their own terms; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
