# R2-1 — T* split-half stability (SHA halves)

Producer: `diagnostics/tstar_stability.py` · split and fit imported from `student_ts_baseline` (sha256(basename) hex order, first half A; NLL, continuous, log-bounded [0.05, 10]) · the Eq.8 column is the ECE argmin on the existing grid steps (RAF-DB 0.05, FERPlus 0.02) · no forward pass, cached logits.

| teacher | n (A/B) | T*_A | T*_B | T*_full | **\|T*_A−T*_B\|** | grid step | cross-ECE penalty | argmin-ECE T (A / B / full) | published T* | anchor |
|---|---|---|---|---|---|---|---|---|---|---|
| stage1 | 1534/1534 | 1.3482 | 1.3506 | 1.3494 | **0.0025** | 0.05 | 0.00001 | 1.30 / 1.35 / 1.35 | 1.3494 | OK |
| primary | 1534/1534 | 1.2544 | 1.2680 | 1.2613 | **0.0136** | 0.05 | 0.00142 | 1.25 / 1.25 / 1.25 | 1.2613 | OK |
| vae9182 | 1534/1534 | 0.9878 | 0.9784 | 0.9831 | **0.0094** | 0.05 | 0.00129 | 1.00 / 0.95 / 1.05 | 0.9829 | OK |
| ferplus | 1576/1577 | 0.4929 | 0.5192 | 0.5064 | **0.0263** | 0.02 | 0.00273 | 0.44 / 0.50 / 0.46 | 0.5063 | OK |

**Result, reported as it fell:** in 3/4 teachers |T*_A − T*_B| is below that teacher's own grid step. For FERPlus the difference (0.0263) exceeds the step of its own FINE diagnostic sweep (0.02); but (i) it is ~11% of the dose-response arm spacing (≥0.24), which is the experiments' actual resolution, and (ii) as the cross-ECE penalty column shows, rescaling the full fold with the wrong half's T* costs at most 0.00273 in ECE — about 2.5% of FERPlus's deployed calibration gain (ECE 0.1282→0.0156, ~0.113). The sentence 'below the grid step' can only be written for RAF-DB; the correct sentence covering all four is below.

Suggested sentence for the paper (direction-aware):

> To verify that T* is not an artifact of the evaluation sample, we re-fitted it on two disjoint halves of each evaluation fold (deterministic SHA-sorted split, identical to the student-TS protocol). The two half-fits differ by at most 0.014 for the three RAF-DB teachers (grid step 0.05) and by 0.026 for FERPlus — an order of magnitude below the spacing between experimental arms in every case — and rescaling the full fold with either half's T* changes teacher ECE by less than 3e-03. The choice of fitting sample therefore does not move T* at the resolution the experiments use.

Note on the deployed Stage1 value: the paper's 1.3406 is B3's stratified-random half-A fit (a different splitting rule); the anchor used here is the full-fold 1.3494.

