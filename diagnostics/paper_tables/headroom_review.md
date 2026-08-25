# R0-3 — Refereeing the headroom numbers

Producer: `diagnostics/headroom_review.py` · sources: `teacher_ece_grid.json`, `ferplus_jsd.json`, `RESULTS_TABLES.json` — no number is typed by hand.

## 1 · VAE9182 "−0.0011": two definitions conflated, not a sign error

| teacher | ECE(T=1) | T*_NLL | ECE@T*_NLL | headroom (NLL-T*) | T argmin-ECE | ECE@argmin | **headroom (Eq.8)** |
|---|---|---|---|---|---|---|---|
| stage1 | 0.0378 | 1.349 | 0.0158 | +0.0220 | 1.35 | 0.0158 | **+0.0220** |
| primary | 0.0396 | 1.261 | 0.0197 | +0.0199 | 1.25 | 0.0190 | **+0.0206** |
| vae9182 | 0.0136 | 0.983 | 0.0146 | -0.0011 | 1.05 | 0.0118 | **+0.0017** |

Where −0.0011 comes from: T* is fitted by minimising **NLL** (0.983), whereas headroom is defined on **ECE**. For VAE9182 the NLL optimum is not the ECE optimum; because ECE@T*_NLL (0.0146) > ECE(T=1) (0.0136), the difference comes out negative. **Under Eq.8's argmin definition the correct value is +0.0017** (argmin T=1.05, grid step 0.05).

**Suggested wording for the text:** "the well-calibrated teacher's headroom is ≈0.002, an order of magnitude smaller than the other two teachers' (0.0220 / 0.0206)" — consistent with Eq.8, no sign problem. Note: for stage1 the two conventions coincide to four decimals (0.0220); for primary they do not (0.0199 vs 0.0206) — whichever convention the text adopts, it must use the same one for ALL THREE teachers; Eq.8 is the recommendation.

## 2 · FERPlus 0.113 vs 0.120: one definition, two grid resolutions

| quantity | T | ECE | value |
|---|---|---|---|
| ECE(T=1) | 1.0 | 0.1282 | — |
| **Eq.8 headroom** — `min` over the swept grid G (4 points) | **0.5063** | 0.0156 | **0.1126 → the paper's "0.113"** |
| finer-resolution refinement (196-point sweep, step 0.02) | 0.46 | 0.0084 | 0.1198 → the paper's "0.120" |

**Binding rule (updated 11 Aug 2026).** Eq.8 is now `min_{T∈G}`, i.e. the definition is tied to the grid that was ACTUALLY SWEPT. So *headroom* carries **0.1126 ≈ 0.113** (T=0.5063), and 0.1198 ≈ 0.120 (T=0.46) is quoted only as what a finer resolution would reach. The arm was run at T=0.5063, so under the new definition the table's "0.1282−0.0156" and the definition's value are THE SAME NUMBER — which is the point of the redefinition: the earlier version needed two names because the definition pointed at a grid nobody had run.

## 3 · The capacity "76×" footnote: rounding dropped the ratio to 74 for the reader

Exact values (@swa): teacher span **0.177981**, capacity span **0.002351** → ratio **75.7 → 76×**. With four-decimal display (0.0024) the reader computed 0.1780/0.0024 = 74.2. Fix: `paper_tables.py` now prints the T10 denominator to five decimals (0.00235); RESULTS_TABLES was regenerated and the JSON values did not change (diff gate green).

