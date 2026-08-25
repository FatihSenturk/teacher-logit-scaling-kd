# R3-W1 — Can both FERPlus objectives be met at once? (pre-registration A11)

Producer: `diagnostics/r3w1_joint_optimum.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · reporting set n=3153 (same filter as `ferplus_student_jsd`)

Round-2 review, seat R3 (MAJOR): the dual-axis caption asserts that *no arm occupies the lower-left corner: the two objectives cannot be satisfied at once*. That is an impossibility claim resting on a four-arm grid. The reviewer named a cheap refutation candidate — distil at the human-aligned T=0.74, then cross-fit a student-side temperature to repair ECE. This table runs that candidate, and the same test on all four arms.

**Protocol is R0-1's, unchanged.** The split rule, the TS fit and the two-axis measurement are *imported* from `student_ts_baseline.py`, not reimplemented: image names are sha256'd and sorted by hex, first half A / second half B (A=1576, B=1577); T_s is fitted on one half by NLL minimisation and measured on the other, in both directions; each sample is scored exactly once with the opposite half's T. Only the scope differs — R0-1 applied it to the T=1 arm alone.

## The four arms, before and after student-side TS

| T (teacher pre-scaling) | role | ECE arm | ECE +TS | JSD arm | JSD +TS | T_s (A→B / B→A, seed 42) |
|---|---|---|---|---|---|---|
| 0.26 | over-sharpened | 0.0587 ± 0.0038 | **0.0266 ± 0.0005** | 0.0737 ± 0.0007 | **0.0540 ± 0.0004** | 2.372 / 2.517 |
| 0.5063 | T*_ECE / T*_NLL | 0.0185 ± 0.0016 | **0.0296 ± 0.0016** | 0.0587 ± 0.0005 | **0.0543 ± 0.0002** | 1.289 / 1.350 |
| 0.74 | T*_JSD | 0.0344 ± 0.0012 | **0.0246 ± 0.0041** | 0.0536 ± 0.0004 | **0.0546 ± 0.0002** | 0.882 / 0.908 |
| 1.0 | native | 0.0783 ± 0.0046 | **0.0203 ± 0.0017** | 0.0551 ± 0.0005 | **0.0545 ± 0.0005** | 0.714 / 0.723 |

The corner is defined by the arms' own two best values: **ECE_min = 0.0185** (T=0.5063) and **JSD_min = 0.0536** (T=0.74). A point occupies the corner when it is at or below both, each within one bar (2× the larger of the two seed sds). The definition was frozen in A11 before any number was read.

## Does any point occupy the corner?

| candidate | ECE | vs ECE_min+bar | JSD | vs JSD_min+bar | occupies? |
|---|---|---|---|---|---|
| T=0.26 + student-TS | 0.0266 | 0.0217 (❌ -0.0049) | 0.0540 | 0.0544 (✅ +0.0004) | no |
| T=0.5063 + student-TS | 0.0296 | 0.0218 (❌ -0.0079) | 0.0543 | 0.0543 (✅ +0.0001) | no |
| T=0.74 + student-TS | 0.0246 | 0.0268 (✅ +0.0022) | 0.0546 | 0.0543 (❌ -0.0002) | no |
| T=1.0 + student-TS | 0.0203 | 0.0220 (✅ +0.0017) | 0.0545 | 0.0546 (✅ +0.0001) | **YES** |

### Verdict: ALT YAZI YANLIŞLANDI

1 nokta köşeyi işgal ediyor: T=1.0+TS. Alt yazının 'the two objectives cannot be satisfied at once' cümlesi, post-hoc öğrenci ölçeklemesi içeren tarifler için doğru değil ve yeniden yazılmalı.

#### How wide is the pass?

Not wide. T=1.0+TS sits **+0.0018** from ECE_min (bar 0.0035) and **+0.0009** from JSD_min (bar 0.0010). On both axes it is *above* the best arm's value and clears the test only because it stays inside seed noise. The defensible sentence is therefore **"indistinguishable from both optima within seed noise"**, not "better than both". That is still enough to falsify an impossibility claim — the caption says the two objectives *cannot* be satisfied at once — but it is not a domination result and must not be written as one.

Note also that the reviewer's own candidate (T=0.74+TS) does **not** pass: it clears ECE by +0.0022 but misses JSD by -0.0002. The arm that refutes the caption is the **native T=1 student** — i.e. the cheapest recipe on the board, with no teacher-side intervention at all.

## An unasked-for finding: student-side TS collapses the JSD axis

Before scaling, the four arms span **0.0201** in JSD (0.0536–0.0737). After a single cross-fitted student-side scalar they span **0.0005** (0.0540–0.0546) — a 37× reduction, with all four arms landing on the same value to within seed noise.

The reading is uncomfortable for the teacher-side lever and is reported anyway: on this dataset almost the entire human-alignment difference between pre-scaling arms is a **confidence-scale** effect, and one student-side scalar reproduces it. Whatever the teacher-side intervention does to the student's *representation* — as opposed to its confidence scale — does not show up on the JSD axis once the scale is free. §5.7 already reported the T=1 case of this; extending it to all four arms makes the pattern, not the single comparison, the finding.

**R0-1 reproduction check.** The published T=1 row (raw and student-TS, ECE and JSD, three seeds) is reproduced bit-identically — the shared code path is the same one.

**Scope limit, stated in the declaration.** This check is only possible on FERPlus: RAF-DB has no clean partition on which to fit a student-side temperature (§5.7's own reasoning). The result is FERPlus-specific.

No training and no GPU: the @swa logits are read from `diagnostics/student_logits/`, the published byte copies of the run-directory caches (`publish_student_logits.py`, sha256-verified). The reporting set — labels, vote distributions, file names — is rebuilt from `diagnostics/ferplus_jsd/ferplus_val_logits.pt` and `configs/FERPlus_majority_metadata.csv`, so this table needs no raw run directory.

