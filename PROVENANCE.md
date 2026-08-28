# Provenance

> **Note, 25 August 2026 — this archive supersedes an earlier one.** The work recorded
> here was first published as `FatihSenturk/calibration-law-fer` and archived on Zenodo in
> three versions between 15 and 23 August 2026 (`10.5281/zenodo.21947605`, `…22017329`,
> `…22067981`). On 25 August 2026 the depositor withdrew all three of those records; each
> now returns HTTP 410 and serves a tombstone page that retains the citation. Because no
> version of that series survives, its concept DOI (`10.5281/zenodo.21947604`) reaches a
> tombstone as well. This repository re-publishes the same work as one clean archive.
>
> **What is the same.** Every producer, every measured value, every dated pre-declaration
> record. `diagnostics/table_diff_gate.py` compares 1658 cells against the accepted
> baseline and reports no deviation on this tree — the same baseline the earlier archive
> carried.
>
> **What is different.** The internal Turkish working reports under
> `diagnostics/reports/` are not published here. What that directory does carry is the
> seven machine-generated gate outputs, plus `2026-07-31_git_provenance.md` and
> `2026-08-02_p6_1_early_reading.md`, because a dated pre-declaration record and a
> producer respectively name them. The live-status mechanism that copied artefacts to the
> author's private cloud folder (`diagnostics/status_heartbeat.py`,
> `diagnostics/status_queue.txt`) is not published either; section 3 below says it should
> not be, and in the earlier archive it was.
>
> **Note, 27 August 2026.** `v1.0.1-submission` was re-cut on 27 August 2026 while no
> Zenodo record for it yet existed; a version tag is final only once its archive is
> published, and `v1.0.0-submission` has not moved since its record was minted.
>
> **Note, 28 August 2026.** `v1.0.1-submission` was re-cut once more, for the same
> reason and under the same rule: its archive had still not been published. What the
> re-cut adds is a student-side scaling round: two producers,
> `diagnostics/ferplus_scaled_ece_axis.py` and `diagnostics/rafdb_student_ts_dose.py`,
> with their tables under `diagnostics/paper_tables/`. Neither runs a model or reads a
> run directory. The first derives an ECE-axis summary from the already-published
> `r3w1_joint_optimum.json`; the second reads the already-published student logit
> copies under `diagnostics/student_logits/`. `diagnostics/rafdb_student_ts_dose.py`
> was committed, together with its decision to publish whatever it returned, **before**
> it was run; the working repository carries the two commits in that order. In the same
> round the baseline of `diagnostics/table_diff_gate.py` grew from 1656 to 1658 cells,
> with the reason recorded in the baseline file itself; no cell changed and none
> vanished.
>
> One of the two can be re-run from this archive and one cannot, and it is worth saying
> which. `diagnostics/ferplus_scaled_ece_axis.py` reads only
> `diagnostics/paper_tables/r3w1_joint_optimum.json`, which is published here, so it
> reproduces from the archive alone. `diagnostics/rafdb_student_ts_dose.py` reads the
> published student logit copies **and** the RAF-DB fold-3 file list, which it needs in
> order to hash file names into the two halves. That list is a derivative of a licensed
> dataset and is not redistributed here, so the producer will stop on a missing
> `data/rafdb_aligned/metadata_rafdb_poster_var.csv` rather than produce numbers. Its
> output table is published in full, and the protocol it uses is the same imported
> `sha_split` / `fit_ts` pair that `diagnostics/student_ts_baseline.py` applies to
> FERPlus, whose metadata **is** published under `configs/`; that FERPlus path is
> therefore runnable end to end and exercises the identical code.
>
> **One thing to know while reading the paper.** The manuscript under review still prints
> the earlier repository's URL and its concept DOI, and neither resolves any more: that
> repository was made private on 26 August 2026, and the concept DOI reaches a tombstone
> because all three of its versions were withdrawn. This archive is what those two lines
> are corrected to at revision.

This repository has a **new, single-commit history**. The work it records was
carried out in a private working repository between 2026-07-11 and 2026-08-03
(25 commits). That repository is not published: it also contains an unrelated
earlier project, abandoned experimental arms, machine-specific paths and large
binary artefacts. This file preserves the part of its history that carries
evidential weight — the timestamps of the pre-declaration chain — so that the
records in `diagnostics/PREREGISTRATIONS.md` can be checked against something
external to the file that asserts them.

## Why timestamps matter here

The campaign's discipline was **declare → commit → tag → launch**: a prediction
and its decision rule were written down, committed, and tagged *before* the runs
that would test them started, so that no rule could be adjusted after seeing a
result. `diagnostics/PREREGISTRATIONS.md` contains those declarations with their
dates. The tags below are the independent corroboration: a tag object's date is
fixed when the tag is created, and the commit it points at fixes the file
contents at that moment.

Anyone verifying this has to take on trust that the tag dates below are reported
faithfully, since the original repository is not public. That is a real limit
and it is stated rather than papered over. What the published files *do* support
without trust is internal consistency: every declaration names the launcher
script that implements it, every launcher is in this repository, and every
verdict script applies the declared rule to the ledger in `runs.csv`.

## Tags in the working repository

| tag | commit | tagged (local time, +03:00) | what it fixes |
|---|---|---|---|
| `audit-frozen-131` | `9b2d31c5c11d051eae8d2b7714c975a608fe5c33` | 2026-07-31 19:41:40 | Selection audit inclusion set frozen at N=131, cutoff `2026-07-31-06-00-00`. The set quoted in the abstract. |
| `p5-predeclared` | `9b2d31c5c11d051eae8d2b7714c975a608fe5c33` | 2026-07-31 19:41:40 | P5 `oracle_error` replication: decision rule declared **before** the results. |
| `p5-verdict` | `0e615f26897e31765ffcb289ab9bce5c139e257f` | 2026-08-01 04:29:34 | P5 verdict recorded: 0/2 established, both arms undetermined. Applied verbatim from the declaration tagged above, which predates runs 2–6 finishing. |
| `p6-predeclared` | `3d9dbee948e479b1ab8cb4c76fca0fae4d633517` | 2026-08-01 14:23:31 | P6 declaration frozen before launch: τ×T factorial (P6.1 collapse rule, bar 0.0012 frozen) and α modulation (P6.2 monotonicity, P6.3 extremes). Runs started only after this tag existed. |

Commit dates of the tagged commits: `9b2d31c` 2026-07-31 17:04:24, `0e615f2`
2026-08-01 04:29:23, `3d9dbee` 2026-08-01 14:23:31.

## Snapshot this repository was built from

| field | value |
|---|---|
| source commit | `d5ba10ca7500` |
| commit date | 2026-08-03 11:07:27 +03:00 |
| produced by | `tools/build_repro_export.py` (included here; the ALLOW/DENY lists in it are the content declaration) |
| method | `git archive <commit>` — the snapshot comes from the commit, never from a possibly-dirty working tree |

## What was changed between the snapshot and this repository

Nothing that affects a reported number. One pruning pass, two mechanical passes,
and one later addition (§4):

1. **Material not tied to the paper was removed** — 111 files, 4.3 MB, roughly
   half the snapshot's size: the AffectNet / AffectNet+ line of work, the
   pre-campaign FERPlus arms with their two superseded label files, five
   earlier-project configs, and the Phase-0 / "unified" era launchers and
   reporting tools. None is referenced by `RESULTS_TABLES.md`, `claims.md`,
   `PREREGISTRATIONS.md`, `METHODS_DATA.md` or `runs.csv`, and none is imported
   by anything that is. Two knock-on edits followed: `dataset_utils/builder.py`
   lost its (now unreachable) AffectNet branch, and three pre-campaign FERPlus
   launchers left pointing at removed configs went with them.

   Note the deliberate asymmetry: `tools/build_repro_export.py` still names a
   few removed files in its ALLOW list, and the Turkish laboratory records still
   discuss some of the removed work. Both are left as they were — the first is
   published *as the tool that produced the snapshot*, and the second is a
   historical log. Editing either to match the pruned tree would misrepresent
   what it is.


2. **Absolute paths made relative.** Every script rooted at the author's working
   directory now resolves its root as `Path(__file__).resolve().parents[1]`, and
   the `run_dir` column of `runs.csv` and of the selection-audit CSVs is now
   repository-relative with forward slashes. Stale default paths in argparse and
   in a few launchers (pointing at machines that no longer exist, and always
   overridden at call time) were replaced with relative placeholders.
   *Exception, deliberate:* four commented-out lines in `trails/posterv2/ir50.py`
   still carry the upstream author's own paths. That file is third-party and is
   kept verbatim.
3. **Author-local infrastructure removed.** The export band that copied
   artefacts to the author's private cloud folder (`diagnostics/export_to_drive.py`,
   `diagnostics/status_heartbeat.py`, `diagnostics/status_queue.txt`) is not
   published: it produces no table, figure or claim, and carried a private path
   and the submission timetable. The three scripts that called it guard the
   import, so their behaviour here is unchanged.

4. **The R3 robustness round was added on 4 Aug 2026**, after the snapshot. It
   answers three computable gaps raised by an external review and is
   pre-registered in `diagnostics/PREREGISTRATIONS.md` A10 — declared, committed
   and tagged (`r3-predeclared`, `0b8ef2f`, 2026-08-04 00:59:56) before any
   metric was computed. Four producers
   (`calibration_metrics.py`, `robustness_metrics.py`, `tstar_sensitivity.py`,
   `jsd_sensitivity.py`), one cache builder
   (`ferplus_student_logit_cache.py`), their tables, and T13/T14/T15 in
   `RESULTS_TABLES.md`. It adds columns; it changes no previously reported
   number, and `diagnostics/table_diff_gate.py` was extended to cover the new
   cells and re-baselined with that check recorded (278 → 432 cells, all
   APPEARED, zero MOVED). The producers are published; the per-run logit caches
   they read are not, for the same reason as every other `*.npz` below.

Also excluded by the snapshot's own DENY list: datasets, model checkpoints,
`results/` run directories, raw logs, the manuscript sources, the cached teacher
logits (`*.npz`) and JSD intermediates (`*.npy`), and figure binaries — every
figure is regenerated by `diagnostics/export_paper_figures.py` and gated by
`diagnostics/verify_paper_figures.py`.
