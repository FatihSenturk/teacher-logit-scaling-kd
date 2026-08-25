# R3-3 — FERPlus JSD sensitivity to the vote-count stratum

Producer: `diagnostics/jsd_sensitivity.py` · same teacher, same fold, same T grid (0.1–4.0 step 0.02, identical to `ferplus_human_vote_jsd.py`); only the row set changes · each row's vote vector is normalised by **its own** vote sum, exactly as in the published analysis · cached teacher logits, no forward pass. Pre-declared in `PREREGISTRATIONS.md` A10 (R3-3): **no success criterion** — whichever way the ordering falls is what goes in the paper.

Vote-sum distribution over the reporting fold: **6** votes → 6 rows, **7** votes → 22 rows, **8** votes → 182 rows, **9** votes → 966 rows, **10** votes → 1977 rows (total 3153).

| slice | n | T\*_ECE | T\*_NLL | T\*_JSD | **separation** T\*_JSD > both | sub-order ECE<NLL | T\*_JSD − T\*_ECE | JSD @T=1 | JSD @T\*_JSD | JSD gain |
|---|---|---|---|---|---|---|---|---|---|---|
| (a) all rows | 3153 | 0.46 | 0.50 | 0.74 | ✅ **held** | ✅ | +0.28 | 0.0492 | 0.0440 | +0.0052 |
| (b) vote sum = 10 | 1977 | 0.42 | 0.46 | 0.74 | ✅ **held** | ✅ | +0.32 | 0.0379 | 0.0330 | +0.0049 |
| (c) stratum 6-7 | 28 | 0.74 | 0.70 | 0.88 | ✅ **held** | ❌ flipped | +0.14 | 0.1102 | 0.1089 | +0.0014 |
| (c) stratum 8-9 | 1148 | 0.46 | 0.54 | 0.74 | ✅ **held** | ✅ | +0.28 | 0.0671 | 0.0613 | +0.0058 |
| (c) stratum 10 | 1977 | 0.42 | 0.46 | 0.74 | ✅ **held** | ✅ | +0.32 | 0.0379 | 0.0330 | +0.0049 |

**Two different facts, kept apart on purpose.** The pre-declared quantity (A10, R3-3) is the **separation**: does human alignment want less sharpening than *either* hard-label criterion, i.e. T\*_JSD > max(T\*_ECE, T\*_NLL)? That is the paper's claim. Whether T\*_ECE happens to sit below T\*_NLL is an incidental sub-ordering of the published table, not a claim. Collapsing the two into one flag would make a break in the second read as a break in the first.

**Reported as it fell.** The separation **holds in every slice**, including the highest-resolution one (vote sum = 10, n=1977) and each individual stratum down to n=28. It is therefore not an artefact of pooling rows with different vote counts. T\*_JSD is furthermore identical (0.74) in every slice with n ≥ 1000; the strata carrying that value account for 3125 of the fold's 3153 rows (99.1%), and T\*_JSD moves only in the smallest stratum (overall T\*_JSD ∈ {0.74, 0.88}).

The incidental sub-ordering T\*_ECE < T\*_NLL flips in `(c) stratum 6-7` (n=28, 0.9% of the fold). This is reported because the pre-declaration forbids withholding a break, not because a claim rests on it: at that n the two optima are separated by one or two grid steps and the slice's own JSD gain is the smallest of all slices.

Reference slice (a) reproduces the published values: T\*_ECE 0.46, T\*_NLL 0.50, T\*_JSD 0.74, n=3153.

