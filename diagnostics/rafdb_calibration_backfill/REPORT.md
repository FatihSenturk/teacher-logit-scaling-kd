# RAF-DB calibration backfill — 20 finished student runs

Read-only, CPU-only. No retraining, no config edits. Script:
`diagnostics/rafdb_calibration_backfill.py`. Val set = RAF-DB fold 3 (official
split used by every run in the matrix), 3068 images, loaded once and reused.
Raw outputs: `calibration_table.csv`, `ece_delta_pivot.csv`,
`logits/{run_id}.npz` (20 files), `sanity1_primary_gate_vs_g2g.json`,
`sanity2_epoch_cap/*.png` + `sanity2_epoch_cap_report.json`.

## 1-2. Enumeration + forward pass

20/20 registry entries were finished at run time (18 from the completed
400e_swa200 grid + 2 from the in-progress 200e_noSWA grid: Stage1 baseline
and Stage1 gate, which finished mid-audit). Each run's `best_checkpoint.pth`
was loaded and forwarded once over the full fold-3 set.

## 3. Per-run accuracy sanity + calibration metrics

**Accuracy sanity: 20/20 match the logged value to within 0.05pp** (19/20 are
an *exact* bit-for-bit match; `vae9182_ctkd` differs by 0.033pp — 89.928%
recomputed vs. 89.896% logged — consistent with GPU/AMP vs. CPU/fp32
floating-point noise on a SWA-batchnorm-recalibrated model, not a data or
checkpoint-selection bug). Full table: `calibration_table.csv`.

**Headline calibration finding — logit_std is a calibration disaster, not
just a mild accuracy loss:**

| Teacher | condition | ECE | Δ ECE vs. baseline |
|---|---|---|---|
| Stage1 | baseline | 0.058 | — |
| Stage1 | **logit_std** | **0.184** | **+0.125** |
| Primary | baseline | 0.065 | — |
| Primary | **logit_std** | **0.184** | **+0.119** |
| VAE9182 | baseline | 0.029 | — |
| VAE9182 | **logit_std** | **0.182** | **+0.154** |

`logit_std` triples-to-sextuples ECE in every teacher (Brier/NLL move the
same direction: e.g. VAE9182 NLL 0.342→0.523) while its accuracy loss looked
modest in the earlier ablation table (−0.3 to −0.6pp). Per-sample logit
standardization changes each sample's effective softmax "spread"
independently, which evidently decouples confidence from correctness far
more than it costs top-1 accuracy — this makes `logit_std` look considerably
worse as a KD component once you look past accuracy alone.

Secondary pattern: `g2g_kl` is calibration-neutral-to-positive (Primary
−0.0078, VAE9182 −0.0023, Stage1 +0.0042), `gate` is mildly calibration-negative
in Stage1/VAE9182 (+0.0097/+0.0037) and roughly neutral in Primary (+0.00002).

**Outlier worth flagging:** `primary_adaptive_t` has MCE = 0.76 — far above
every other run (range 0.25-0.38 elsewhere) — a single confidence bin with a
~76pp confidence/accuracy gap, despite unremarkable ECE (0.067). Likely one
sparsely-populated high-confidence bin with poor accuracy; not investigated
further here but a candidate for a follow-up per-bin breakdown if this run's
calibration matters downstream.

Full ECE-delta pivot: `ece_delta_pivot.csv` (200e_noSWA side only has
baseline/gate so far — grid still running).

## 5. Sanity #1 — primary_gate vs. primary_g2g_kl (identical logged accuracy)

Both log **89.21121251629727%** to 11 decimal places, but at different
`best_epoch` (308 vs. 293). Direct prediction comparison over all 3068 test
images:

- **256/3068 predictions differ (8.34%)** — same correct-count, different
  correct samples. **Not the same model, not a bug — a genuine coincidence**
  of aggregate accuracy between two differently-trained checkpoints.
- `g2g_term` was confirmed **active and nonzero throughout training**
  (400 epochs logged: min 8.29, mean 10.26, max 570.49, never zero) —
  rules out "g2g_kl silently degenerated to a no-op and happened to match
  gate's result."

## 6. Sanity #2 — epoch cap (best_epoch ≥ 390)

Four runs qualified (not just the two `adaptive_t` cases the task named —
`primary_adaptive_t` at 391 also crosses the ≥390 threshold):

| run_id | best_epoch | last-50-epoch linear slope | still ascending at cap? |
|---|---|---|---|
| stage1_adaptive_t | 399 | +0.0047/epoch | **yes** |
| vae9182_adaptive_t | 395 | +0.0027/epoch | **yes** |
| vae9182_gate | 398 | +0.0053/epoch | **yes** |
| primary_adaptive_t | 391 | −0.0024/epoch | no (declining) |

3 of 4 runs show a positive linear trend over their last 50 logged epochs —
**the 400-epoch cap plausibly left real accuracy on the table** for
`stage1_adaptive_t`, `vae9182_adaptive_t`, and `vae9182_gate` specifically.
Caveat: val_acc is noisy epoch-to-epoch (last-50 range spans 1.3-2.5pp in all
four runs), so a linear fit over 50 points is a coarse trend signal, not
proof of continued real improvement — but combined with `val_acc_at_best_epoch`
exceeding `val_acc_final_epoch` in all four (the checkpoint selector did pick
a genuine local peak, not just "last epoch"), an epoch-budget extension for
these specific (teacher, condition) pairs is a reasonable, evidence-backed
follow-up if squeezing out the last ~0.2-0.5pp matters. Plots:
`sanity2_epoch_cap/*.png`.
