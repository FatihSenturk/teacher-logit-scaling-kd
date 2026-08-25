# Claims inventory & naming state (RAF-DB KD calibration study)

Living document, updated as results land — not a historical log (see individual `diagnostics/*.md`
reports and `diagnostics/*/`.csv/json outputs for the underlying evidence trail).

## Closed claims (pre-registered, verdict reached)

### D1 — Uncertainty gate: DEAD as a contribution (verdict: B)
Tested at 3 signal qualities, 3 teachers:
- Default `mean_logvar`: accuracy deltas −0.33 / −0.39 / +0.03pp (Stage1/Primary/VAE9182). All AUROC
  vs. own-error < 0.5 (inverted signal).
- Best real learned signal `target_logvar`: Stage1 AUROC 0.70 → +0.06pp; **Primary AUROC 0.84 (highest
  of any signal tested) → −0.46pp, the single worst gate result** — signal quality and gate outcome
  are not even correlated, let alone causally linked.
- Synthetic perfect "oracle" signal (VAE9182 only): 89.67% vs. 90.06% baseline — **worse than baseline
  even with perfect information.**
- **P2 (2026-07-30) took the oracle arm to n=3 against a class-weighting-MATCHED control and changed
  how this claim must be worded.** @swa, paired within seed: Δacc −0.228 ± 0.493 pp with signs `--+`
  (unresolvable), but **ΔECE +0.0056 ± 0.0040 with signs `+++`** — 2.08× the control's seed sd, all
  three seeds agreeing. The pre-registered "both axes null" prediction was therefore **falsified on the
  calibration axis** (`PREREGISTRATIONS.md` A8; artifact `diagnostics/p2_gate_oracle/p2_verdict.md`).
- **Say "closed because it HURTS calibration", not "closed because it does nothing."** Against the old
  contaminated control the same runs read as ECE-neutral (+0.0004 ± 0.0011, signs `+-+`); the clean
  control revealed the harm, because class weighting was itself degrading the control's ECE by 0.0052
  and cancelling it. Any sentence in the paper of the form "gate is neutral / has no effect" is now
  wrong on the evidence and must be rewritten.
- **BUT the harm is CONDITIONED ON THE WELL-CALIBRATED TEACHER — P4 (2026-07-31) did not replicate it
  elsewhere.** With the missing controls finally on disk for stage1 and primary, the four real-signal
  gate rows read ΔECE +0.0000 / −0.0028 / −0.0027 / +0.0019 (@swa, n=1 each): signs mixed, three of
  four inside their own control's seed sd, and the one exception pointing the *wrong* way. So:
  - **Established:** on VAE9182, `gate:oracle_error` degrades student ECE by +0.0056, 2.08× the
    control's seed sd, 3/3 seeds agreeing, pre-registered (A8).
  - **Not established:** the same on stage1/primary with realisable signals. n=1 cannot refute
    anything, so this is NON-REPLICATION, not refutation.
  - **Confound worth stating:** stage1/primary students sit at ECE 0.0745/0.0755 versus VAE9182's
    0.0278 — 2.7× larger. The same absolute harm is 20% relative there but only 7.5% here, so it
    could be present and invisible against a bigger, noisier base. Separating that needs n=3 on those
    two arms (4 runs, not launched).
  - **Write it conditioned, never generalised:** no "on every teacher", no "consistently".
- **P5 (2026-08-01) ran the replication properly and it did NOT replicate.** P4's four rows were
  real-signal and n=1, which is why they could not settle anything; P5 repeated the *same*
  manipulation (`gate:oracle_error`) on stage1 and primary at n=3 against their own `cw=none`
  controls — 6 runs, 6/6 complete. Frozen rule (declared 2026-07-31 14:14:11, first run +29 s):
  3/3 same sign AND |ΔECE| ≥ 2× the arm's own control ECE seed sd. Result:
  - stage1  ΔECE **+0.0015** ± 0.0036, signs `+-+`, bar 0.0021 → **0.74× bar — ÇÖZÜNMEDİ**
  - primary ΔECE **+0.0004** ± 0.0053, signs `+-+`, bar 0.0033 → **0.11× bar — ÇÖZÜNMEDİ**
  - reference vae9182 (A8/P2): +0.0056, signs `+++`, 2.08× bar — established
  Both arms failed **both** limbs of the AND, and not marginally. The conditioning therefore
  stands on its strongest available evidence rather than on an untested assumption.
  **ÇÖZÜNMEDİ ≠ no effect** — the bar is 2× a single arm's seed noise, so an effect below it was
  *not measured*, not *shown absent*. The sentence "gate does not harm calibration on
  stage1/primary" is still unwritable. Artifact: `diagnostics/p5_oracle_replication/p5_verdict.md`.
- **The accuracy limb, however, is now unconditional and stronger.** With a *perfect* signal the
  gate buys no accuracy on any of the three teachers (Δacc @swa: stage1 −0.22, primary −0.01,
  vae9182 −0.23). This is the limb the closure actually rests on, and P5 added two teachers to it.
  Write D1's closure with two limbs: accuracy-no-gain unconditional, calibration-harm conditioned
  on VAE9182.
- Conclusion: the per-sample alpha-blend mechanism has no headroom on this dataset independent of
  signal quality, and on a well-calibrated teacher it is actively calibration-harmful even with a
  perfect signal. Closed, three layers deep, all pre-registered before results — including the one
  prediction that failed and the follow-up that came out inconveniently.

### Signal-quality / inversion finding (cross-dataset, cross-teacher)
- RAF-DB: `mean_logvar`/`top2_logvar` inversely correlated with own-error in all 3 teachers (AUROC
  0.16-0.44). `target_logvar` redeems itself for VICH teachers only (0.70/0.84) — not for VAE9182
  (0.46). `entropy` universally strong and correctly signed (AUROC ~0.89, all 3 teachers).
- FERPlus (independent cross-check vs. human vote-entropy, not teacher-error): same qualitative
  pattern — `mean_logvar`/`target_logvar`/`top2_logvar` all negatively correlated (Pearson −0.55 to
  −0.68), `entropy` positively and strongly correlated (+0.74). `target_logvar` does NOT redeem itself
  here (unlike RAF-DB's VICH teachers) — so the VICH-redemption of `target_logvar` doesn't generalize
  dataset-to-dataset.

### Teacher-ECE-predicts-student-outcome (n=3, correlational, both channels)
Teacher ECE (real, 15-bin audit over fold-3 val: **VAE9182 0.0136 < Stage1 0.0378 < Primary 0.0396**)
monotonically predicts BOTH student baseline accuracy (VAE9182 90.06% > Stage1 89.67% > Primary
89.60%) AND student baseline ECE (VAE9182 0.0285 < Stage1 0.0581 < Primary 0.0654) — same rank order
in all three channels. **NB:** the Stage1 baseline is 89.67% (best-student, per `calibration_table.csv`),
not 89.90% as an earlier draft stated — so the accuracy-channel middle gap (Stage1 vs Primary) is only
0.07pp (within seed noise; the ECE-channel ordering is the robust one). Metric note: these are
best-student numbers; SWA-student numbers reorder some component deltas (report one metric consistently). Teacher own-accuracy does NOT predict transfer quality (Primary 92.01% own-acc
transfers worse than VAE9182's 91.82%).
> **Correction (2026-07-20):** an earlier draft of this doc listed teacher ECE as 0.029/0.058/0.065.
> Those are the *student* baseline ECE values (0.0285/0.0581/0.0654), mistakenly reused as teacher ECE.
> The real teacher ECE (`diagnostics/teacher_head_compat_audit/full_report.json::task5_full_val_metrics`)
> is 0.0136/0.0378/0.0396. The rank-order finding was and remains correct; only the teacher-side numbers
> were mislabeled. The Phase C bridge decision bands (≈0.015→head, ≈0.038→recipe) were always anchored
> on the *real* teacher values, so they are unaffected.

**Open**: is the VAE9182 ECE advantage head-architecture or a recipe/augmentation confound? See P0 diff
report + Phase C bridge experiment (in progress as of this writing).

### Teacher-ECE gap is (mostly) a scalar-temperature artifact (Phase B1)
Post-hoc temperature scaling (fit T* by NLL over fold-3 val, `diagnostics/teacher_temperature_scaling/
temperature_fit.json`; ECE(T=1) reproduces the audit values to 4 decimals, so T* is trustworthy):
| Teacher | T* | ECE T=1 → T* |
|---|---|---|
| Stage1 (VICH) | 1.349 | 0.0378 → **0.0158** |
| Primary (VICH) | 1.261 | 0.0396 → **0.0197** |
| VAE9182 (VAE) | 0.983 | 0.0136 → 0.0146 |

Both VICH teachers are **systematically over-confident** (T*≈1.3); a single scalar T* drops Stage1's
teacher ECE onto VAE9182's level. VAE9182 is already near its optimal temperature (T*≈1.0 — a scalar
can't improve it). So the teacher-ECE ordering that predicts student transfer is, at the teacher level,
largely "how over-confident is this head by a scalar factor," not a deep distributional difference.
This sharpens the Phase B3 causal test: KD-train Stage1's student with teacher logits pre-divided by
T*=1.349 (teacher ECE → 0.0158 ≈ VAE9182's, no head/recipe change). If the student moves toward
VAE9182's student outcome (90.06%/0.0285), teacher calibration is *causal* and cheaply fixable; if not,
teacher ECE was only correlational.

### Phase B3 RESULT — teacher calibration is CAUSAL, and cheaply fixable (2026-07-21)
Leak-free protocol: T* fit on a held-out half (half-A) of fold-3 val (T*=1.3406), student reported on
half-B (T*-unseen). One flag changed vs. the Stage1 baseline (`--teacher-temperature-scale 1.3406`),
same head/recipe/seed. Result on **half-B**:
| | acc | ECE |
|---|---|---|
| Stage1 baseline (over-confident teacher) | 89.63% | 0.0558 |
| Stage1 + temp-scaled teacher (calibrated) | **90.22%** | **0.0293** |
| Δ (causal) | **+0.59pp** | **−0.0265 (ECE more than halved)** |
| *target: VAE9182's own student* | *90.06%* | *0.0285* |

Temperature-scaling the over-confident Stage1 teacher (a single scalar, no architecture/recipe/seed
change) moves its student **onto the well-calibrated VAE9182 teacher's student outcome on BOTH axes** —
student ECE more than halves (0.0558→0.0293 ≈ VAE9182's 0.0285) and accuracy rises +0.59pp to 90.22 ≈
VAE9182's 90.06. **CL-3 upgrades from correlational to CAUSAL**: teacher calibration causally governs
student transfer, and it is a cheap post-hoc fix. This is the campaign's strongest single result and the
paper's anchor — the thesis is teacher-calibration-first, not clever-KD-component. (Deployable one-liner:
temperature-scale the teacher before distilling.) Full-val numbers agree in direction (+0.26pp/−0.0248);
half-B is the leak-free reported figure. Artifact: `diagnostics/teacher_temperature_scaling/b3_halfb_eval.json`.

### Component summary (400e_swa200 recipe, 3 teachers)
- `g2g_kl`: mixed but mostly positive accuracy (Stage1 +0.19, VAE9182 +0.19, Primary −0.39); calibration
  mildly positive 2/3 (Primary ECE −0.0078, VAE9182 −0.0023, Stage1 +0.0042) — "modest but consistently-
  directioned," not "clearly best."
- `adaptive_t`: single largest accuracy win anywhere in the grid (VAE9182 +0.62pp, 90.68%); teacher-
  conditional (Primary only +0.08pp).
- `logit_std`: calibration disaster in ALL 3 teachers — ECE 3-6x worse than baseline (+0.12 to +0.15
  absolute) despite only modest accuracy loss (−0.3 to −0.6pp). The gap between "looks harmless on
  accuracy" and "wrecks calibration" is the most quotable single number in this study.
- `ctkd`: never beat baseline in the 400e_swa200 recipe (3/3 negative); DID beat baseline in the
  200e_noSWA recipe for Stage1 (+0.30pp, best component there) — recipe-dependent, not a clean win or
  loss.
- Combined `g2g_kl`+`adaptive_t` @ VAE9182: negative at 400 epochs (89.86%, worse than either alone),
  recovered to 90.55% at 500 epochs (between the two solo components) — **epoch-budget artifact, not a
  true negative interaction**; 3 of 4 late-peaking (best_epoch≥390) runs in the original grid were
  still ascending at their 400-epoch cap, so this generalizes as a methodological caveat for the whole
  grid, not just the combined run.

### MCE bin-sensitivity
`primary_adaptive_t`'s MCE=0.76 outlier is a single-sparse-bin (n=1) equal-width-binning artifact,
drops to 0.26 under equal-mass binning (still elevated — real miscalibration in the 0.79-0.94
confidence band, just not 0.76). ECE is robust to binning scheme across all 20 runs (±0.002); MCE is
highly bin-scheme-sensitive. Any paper reporting MCE needs an equal-mass-bins footnote.

## Open / in-progress claims

- **Split naming — one set, four names (measured 2026-08-19).** The set the paper calls "RAF-DB's
  official test set", "the reporting set", "best validation accuracy" and "fold-3 validation split
  (n=3068)" is a **single partition**, and the measurement is now a producer's output, not a claim:
  `diagnostics/split_identity.py` -> `paper_tables/split_identity.{md,json}`. RAF-DB's metadata holds
  exactly **two** partitions (fold 2 = `train/` 12,271; fold 3 = `test/` 3,068) and fold 3's per-class
  counts reproduce RAF-DB's published test distribution **exactly**, so "official test set" is correct
  as to the set and "validation" is correct as to the *use*. FERPlus differs in a way worth stating:
  its metadata holds **three** partitions and the third (PublicTest, 3,199 rows) was put into
  **training**, so there "no separate held-out set" is a property of the *protocol*, not of the
  dataset. Which single name the paper adopts is Fatih's call; the mapping is measured either way.

- **Prose is still outside the audit (recorded 2026-08-19).** `sections/*.tex` carries **821** number
  tokens that the ledger does **not** scan (measured N16). This is a deliberate deferral — the
  controlled reading is in progress and binding a moving target produces rotten bindings — but the
  consequence must be stated plainly: **the most-edited part of the manuscript is the part the audit
  does not see.** Tables, the supplement (S1-S3) and the abstract are covered; body prose is not. The
  scope decision is the first item when the reading closes.

- **Head-architecture vs. recipe-stack attribution of the ECE gap — RESOLVED: RECIPE, not head
  (2026-07-21).** Phase C bridge teacher (VAE head + Primary's exact VICH recipe, `seed=1`) measured on
  fold-3 val: own-acc 92.47%, **ECE(T=1) 0.0391, T* 1.253** — lands squarely in the pre-registered
  RECIPE band (0.038±0.01), nowhere near the HEAD band (0.015). It matches the VICH-recipe teachers
  (Primary 0.0396/T*1.26, Stage1 0.0378/T*1.35) and looks NOTHING like VAE9182 (0.0136/T*0.98).
  **Cleanest cut: bridge vs. Primary share recipe AND seed (both seed 1, RAFDB_RECIPE); only the head
  differs — and their ECE is essentially identical (0.0391 vs 0.0396).** So flipping VICH→VAE head with
  everything else fixed does nothing to calibration → head architecture is ruled out. VAE9182's
  calibration edge was its recipe (QCS augmentation)/seed, NOT its VAE head. The head-type labels are a
  red herring for calibration/transfer. Artifact: `diagnostics/bridge_teacher/bridge_teacher_check.json`.
  (Residual: recipe vs. seed within VAE9182's edge is not separated — Study-2, not EAAI-blocking.)
  *(This item is CLOSED and is kept here only as the pointer to where it was resolved; the entry
  above under "Closed claims" is authoritative. — 2026-08-01)*

**Phase A (seed variance) and Phase B (causal teacher-ECE test) are both CLOSED** and were moved
to the Closed section above on 2026-08-01: Phase B is the temperature-scaling result
(89.63%/0.0558 → 90.22%/0.0293 on half-B), Phase A's replicates are what every n=3 cell in T5
now rests on. They were left listed here after being resolved, which made this section read as
if three things were still open when none were.

Genuinely open, as of 2026-08-01:

- **Naming** — see below; still undecided.
- **P6 (IN FLIGHT, pre-registered `p6-predeclared`)** — τ×T factorial (does student ECE depend on
  (T,τ) only through T·τ?) + α modulation (does the T=1 vs T* gap shrink as the student listens
  less?). 42 runs, launched 2026-08-01 14:23, ≈Aug 2–6. First declaration with the full
  declare → commit → tag → launch chain. Results go to new tables T11/T12, NOT into T1–T8.
- **Real-signal gate cells at n=3** — 10 runs. **DEFERRED (decision 2026-08-01):** the paper goes
  out with the conditioned claim; if referees ask, this becomes a November revision run. Distinct
  from P5, which replicated the *oracle* arm.
- **Scratch dose-response at 2.248 M** — 4 runs. **DEFERRED (decision 2026-08-01):** T10a item
  (ii) is already reported as unresolved, and that wording is honest as-is; re-evaluate after P6
  finishes so the GPU does not sit idle.
- **VAE9182's calibration edge: recipe vs. seed** — not separated. Study-2, not EAAI-blocking.

## Naming

Four candidate names (UGKD, SAGE, GUIDE, GUARD) all assumed the uncertainty gate would be the hero
mechanism — all four are dead now that D1=B. New name should carry the g2g/calibration axis instead
(the surviving useful components + the calibration-conditional-transfer finding), not a gating-hero
framing. **Not yet decided** — revisit once Phase A-C land and the final component ranking is settled.

## Section-5 placement of the capacity result (decided 2026-07-30)

**T10's capacity TABLE moves to immediately after the contrasting-pathology replication (current
5.3), one slot earlier than my own recommendation of "right after 5.4."** The user's reasoning,
adopted: 5's architecture is 1-3 establish the law, 4 onward use or bound it. "Where does the law
live" is not an application — it is a **validity defence** that eliminates the "maybe this is a
student-capacity artifact" alternative, so it belongs with the establishing block.

**Only the table moves.** T10a's slope comparison (b = 0.716 @ 2.248 M vs 0.655 @ 0.712 M) stays
behind as exploratory and must not be adjacent to the table: it rests on n=2 in two cells, carries
the scratch/pre-trained confound, and its uncertainty is a worst-case envelope rather than a
confidence interval. Its verdict is INCONCLUSIVE, not null — "the slope does not change with
capacity" is not a sentence this data supports. Keeping the weak item next to the establishing
table would let it borrow credibility it has not earned. `paper_tables.py` now enforces the split
structurally: T10a states claim (i) (validity defence, stands on residuals 3.5-15x below the
cells' own seed sd) and claim (ii) (inconclusive slope test) as separately labelled items.

## Study split decision (already made)

Keep the current paper (EAAI target) unified around the calibration/signal-quality narrative — teacher
ECE as the real selection criterion, not head-type labels. The EAAI paper's strongest asset is the
head *contrast* (calibration order vs. signal order run in opposite directions, n=3, single mechanism
hypothesis: sampled-CE margin inflation vs. prior-KL homogenization). Splitting VAE-only/VICH-only
would kill that contrast for the EAAI paper and leave VICH with no surviving consumer of its own
distinguishing feature (target_logvar didn't redeem gate; g2g doesn't reward VICH's cleaner signal
either).

A **second paper** ("what makes a good probabilistic teacher head for distillation," architecture-
agnostic, later submission) is scoped separately: matched-pair head experiments, direct test of the
margin-inflation mechanism hypothesis, a "best of both" calibration-regularized VICH design, and
repurposing `target_logvar` for CE-loss label-noise gating instead of KD-loss gating (gating's one
surviving live hypothesis space, since oracle-gate closed off "gate the KD term" entirely). Venue
candidates: The Visual Computer, Neurocomputing. Timing: after EAAI submission.
