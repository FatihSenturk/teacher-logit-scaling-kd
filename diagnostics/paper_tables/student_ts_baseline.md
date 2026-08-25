# R0-1 — FERPlus student-side TS comparison arm (no training)

Producer: `diagnostics/student_ts_baseline.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds · reporting set n=3153 (same filter as `ferplus_student_jsd`)

**Leak-free protocol.** The TS temperature was not fitted on the reporting set: image names were sha256'd and sorted by hex, first half A / second half B (A=1576, B=1577); T_s was fitted on one half by NLL minimisation (Guo et al. 2017) and measured on the other, in both directions; the combined row scores every sample exactly once, with the opposite half's T. The fitted T_s values are in the table.

| seed | ECE raw | ECE student-TS | ECE T\*-arm | JSD raw | JSD student-TS | JSD T\*-arm | T_s (A→B / B→A) |
|---|---|---|---|---|---|---|---|
| 42 | 0.0734 | 0.0215 | 0.0167 | 0.0555 | 0.0549 | 0.0592 | 0.714 / 0.723 |
| 1 | 0.0826 | 0.0210 | 0.0193 | 0.0546 | 0.0540 | 0.0585 | 0.690 / 0.709 |
| 43 | 0.0789 | 0.0183 | 0.0195 | 0.0552 | 0.0547 | 0.0584 | 0.676 / 0.708 |
| **mean ± sd** | **0.0783 ± 0.0046** | **0.0203 ± 0.0017** | **0.0185 ± 0.0016** | **0.0551 ± 0.0005** | **0.0545 ± 0.0005** | **0.0587 ± 0.0005** | — |

## Reading

- **On the ECE axis, student-side TS works**: raw 0.0783 → TS 0.0203 (T\*-arm 0.0185). On ECE, TS and the T\*-arm do not separate beyond seed noise (difference +0.0018, bar 0.0035). The fitted T_s ∈ [0.676, 0.723] — all < 1: an under-confident student is being sharpened, i.e. the teacher's pathology has passed to the student and TS corrects in the same direction.
- **JSD axis**: raw 0.0551 → TS 0.0545; T\*-arm 0.0587. **student-TS's JSD is BETTER than the T\*-arm's** (0.0545 vs 0.0587): TS fixes ECE while preserving the better human alignment of the T=1 arm, whereas the T\*-teacher arm paid for its ECE gain out of JSD (the student-side trace of the teacher-side trade-off). On this axis the sentence "student-side TS cannot touch the representation" works IN FAVOUR of TS, not against it — the Block-3 reframing should use that direction.

> The numbers are reported whichever way they fell; the sentences were written direction-aware and selected by the measurement.

