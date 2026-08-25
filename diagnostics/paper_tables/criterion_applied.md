# G3.1 + G3.2 — The 2×-control-sd criterion, written down and applied to every cell

> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts.

Producer: `diagnostics/criterion_applied.py` · sample sd (n-1, Bessel-corrected), computed over seeds · denominators imported from `denominator_table.control_arms()`

## G3.1 — The criterion, stated

| component | definition |
|---|---|
| numerator | \|mean paired difference\| — mechanism minus **its own matched control**, within seed |
| denominator | the seed sd of **that teacher's own control arm**, same metric, same checkpoint |
| sign condition | all n seeds share the sign |
| threshold | ratio ≥ **2** *and* the sign condition → `established`; otherwise `unresolved` |

The denominator is the **control arm's** seed sd, not the paired difference's own sd. Both are reported below for every cell, because the choice changes verdicts and the reader is entitled to see by how much.

## Every three-seed cell of Table 3, @swa, ECE axis

Applied mechanically — no cell is omitted for failing.

| cell | mean ΔECE | signs | σ_control | ratio | verdict | σ_paired | ratio | verdict |
|---|---|---|---|---|---|---|---|---|
| `primary/adaptive_t` | +0.0023 | +++ | 0.0015 | **1.52×** | unresolved | 0.0007 | 3.22× | established |
| `primary/g2g_kl` | -0.0016 | +-- | 0.0015 | **1.06×** | unresolved | 0.0027 | 0.59× | unresolved |
| `primary/gate:mean_logvar` | -0.0056 | --+ | 0.0033 | **1.67×** | unresolved | 0.0092 | 0.60× | unresolved |
| `primary/gate:oracle_error` | +0.0004 | -++ | 0.0033 | **0.11×** | unresolved | 0.0053 | 0.07× | unresolved |
| `primary/gate:target_logvar` | -0.0008 | +-- | 0.0033 | **0.23×** | unresolved | 0.0030 | 0.26× | unresolved |
| `primary/logit_std` | +0.0859 | +++ | 0.0015 | **56.68×** | established | 0.0058 | 14.80× | established |
| `stage1/adaptive_t` | -0.0011 | ++- | 0.0012 | **0.93×** | unresolved | 0.0033 | 0.33× | unresolved |
| `stage1/g2g_kl` | -0.0042 | --- | 0.0012 | **3.57×** | established | 0.0004 | 11.92× | established |
| `stage1/gate:mean_logvar` | -0.0012 | +-- | 0.0021 | **0.55×** | unresolved | 0.0010 | 1.14× | unresolved |
| `stage1/gate:oracle_error` | +0.0015 | -++ | 0.0021 | **0.73×** | unresolved | 0.0036 | 0.43× | unresolved |
| `stage1/gate:target_logvar` | -0.0041 | --- | 0.0021 | **1.97×** | unresolved | 0.0023 | 1.82× | unresolved |
| `stage1/logit_std` | +0.0906 | +++ | 0.0012 | **76.62×** | established | 0.0023 | 38.92× | established |
| `vae9182/adaptive_t` | -0.0042 | --+ | 0.0020 | **2.10×** | unresolved | 0.0047 | 0.90× | unresolved |
| `vae9182/g2g_kl` | +0.0009 | -++ | 0.0020 | **0.47×** | unresolved | 0.0043 | 0.22× | unresolved |
| `vae9182/gate:mean_logvar` | +0.0015 | +-- | 0.0027 | **0.55×** | unresolved | 0.0046 | 0.32× | unresolved |
| `vae9182/gate:oracle_error` | +0.0056 | +++ | 0.0027 | **2.08×** | established | 0.0040 | 1.41× | unresolved |
| `vae9182/logit_std` | +0.1388 | +++ | 0.0020 | **69.49×** | established | 0.0013 | 107.28× | established |

**5/17** cells are `established` under the control-sd denominator; **5/17** under the paired-difference denominator. The verdict changes for **2** cell(s): `primary/adaptive_t`, `vae9182/gate:oracle_error`.

## The same cells, accuracy axis (@swa)

| cell | mean Δacc (pp) | signs | σ_control | ratio | verdict |
|---|---|---|---|---|---|
| `primary/adaptive_t` | -0.391 | --+ | 0.130 | 3.00× | unresolved |
| `primary/g2g_kl` | -0.141 | -++ | 0.130 | 1.08× | unresolved |
| `primary/gate:mean_logvar` | +0.196 | ++- | 0.394 | 0.50× | unresolved |
| `primary/gate:oracle_error` | -0.011 | +-- | 0.394 | 0.03× | unresolved |
| `primary/gate:target_logvar` | -0.087 | -+- | 0.394 | 0.22× | unresolved |
| `primary/logit_std` | -0.315 | --- | 0.130 | 2.42× | established |
| `stage1/adaptive_t` | +0.163 | +-+ | 0.340 | 0.48× | unresolved |
| `stage1/g2g_kl` | +0.413 | +++ | 0.340 | 1.21× | unresolved |
| `stage1/gate:mean_logvar` | -0.098 | -+- | 0.100 | 0.98× | unresolved |
| `stage1/gate:oracle_error` | -0.217 | +-- | 0.100 | 2.18× | unresolved |
| `stage1/gate:target_logvar` | +0.250 | ++- | 0.100 | 2.51× | unresolved |
| `stage1/logit_std` | -0.228 | --- | 0.340 | 0.67× | unresolved |
| `vae9182/adaptive_t` | +0.282 | ++- | 0.366 | 0.77× | unresolved |
| `vae9182/g2g_kl` | +0.163 | ++- | 0.366 | 0.44× | unresolved |
| `vae9182/gate:mean_logvar` | -0.272 | -++ | 0.207 | 1.31× | unresolved |
| `vae9182/gate:oracle_error` | -0.228 | --+ | 0.207 | 1.10× | unresolved |
| `vae9182/logit_std` | -0.120 | -+- | 0.366 | 0.33× | unresolved |

## G3.2 — What false-positive rate does this criterion carry?

Simulation under a seed-noise null: the mechanism has **no** effect, so the within-seed paired differences are zero-mean noise. Their seed sd is `k ×` the control's seed sd. The criterion is scale-free in σ_control, so σ_control = 1 without loss of generality. 200,000 replicates per k, n = 3 seeds, RNG seed 20260806.

| k = σ_paired / σ_control | per-cell false-positive rate |
|---|---|
| 0.50 | 0.0000 |
| 1.00 | 0.0005 |
| 1.41 | 0.0130 |
| 2.00 | 0.0660 |
| 3.00 | 0.1522 |

The **observed** k across the 17 three-seed ECE cells has median **1.70** (range 0.30–3.83). At that k the per-cell false-positive rate is **0.0350**, and over the 17 cells of Table 3 the family-wise rate — the chance that *at least one* cell fires by chance — is **0.454** (1 − (1 − 0.0350)^17, independence assumed).

### G3.3 — the family is **22**, not 17 (B5, 14 Aug 2026)

The criterion is applied on the ECE axis to the 17 three-seed cells, **and on the accuracy axis to the 5 learned-signal gate cells** (`gate:mean_logvar`, `gate:target_logvar`; `oracle_error` is synthetic, not a learned signal, so it is not in this family). Counting only the ECE axis understates the family by 5 tests.

| family | n | family-wise rate |
|---|---|---|
| ECE axis only (as published) | 17 | 0.454 |
| **ECE + learned-signal accuracy cells** | **22** | **0.543** |
| same 22 cells, each at its **own** k | 22 | 0.740 |

At the median per-cell rate the 22-test value is 1 − (1 − 0.0350)^22 = **0.543**. Using each cell's own k instead of the median gives **0.740** — the median understates it, because the rate is convex in k and a handful of high-k cells carry most of the risk.

#### Sensitivity across the observed spread ratio

k = σ_paired/σ_control over the 22 cells: **0.30 … 3.83** (median 1.70). The per-cell rate is not flat over that range — it moves by more than two orders of magnitude:

| k | per-cell rate | which cell |
|---|---|---|
| 0.30 | 0.0000 | `stage1/g2g_kl` (ECE) |
| 1.70 | 0.0359 | `vae9182/gate:mean_logvar` (ECE) |
| 3.83 | 0.1916 | `primary/logit_std` (ECE) |

> The lowest-k cell fires by chance essentially never (0.0000); the highest-k cell fires **0.192** of the time. A single family-wise number therefore hides a very uneven distribution of risk across the table.

#### The independence assumption, measured

> **One sentence:** cells that share a control arm have mean pairwise correlation **+0.393** across their three seeds (n = 18 pairs) against **-0.077** for cells that do not (n = 213 pairs), and re-simulating the 22-cell family with that shared component inside each control group gives a family-wise rate of **0.732** instead of the **0.740** the independence product reports — so the published figure is an upper bound, and the measured size of the gap is 0.008.

The correlation is not an artefact of small n alone: it is what the design **implies**. Every cell in a group is differenced against the *same three control runs*, so the control's seed noise enters every difference in that group with the same sign. Sharing the seed set (42/1/43) on the treatment side adds a second, smaller channel.

### G3.4 — the same five numbers, computed exactly (20 Aug 2026)

The independence arm of this section needs no Monte Carlo. With n = 3 and a threshold on |mean| plus a common-sign condition, the per-cell rate reduces to a single one-dimensional integral (derivation in the `fpr_exact` docstring), evaluated here by Gauss–Legendre quadrature to ~1e-15. That matters because the published values came from a 200,000-replicate simulation whose standard error on the per-cell rate is 4.1e-4 — and the family-wise rate is ~10.4× as sensitive, so its **third decimal was Monte-Carlo noise**. Fixing that digit by brute force would need ~1.3e8 replicates per cell.

| quantity | published (MC) | exact | difference |
|---|---|---|---|
| per-cell rate at the median k | 0.0350 | **0.035155** | +0.000180 |
| family-wise, 22 cells at the median k | 0.543 | **0.544941** | +0.001870 |
| family-wise, 22 cells at each cell's own k | 0.740 | **0.741038** | +0.000948 |

Quadrature convergence: halving the node count (400 → 200) moves the per-cell rate by 5.55e-16.

The dependent arm keeps its simulation — sharing a control arm inside a group has no closed form here — but at 20,000,000 replicates (seed 20260820) its standard error is 9.9e-05, so its third decimal is real. Against the **exact** independence product the gap is **0.0086** (0.7410 − 0.7324); the earlier pairing of two noisy estimates put it at 0.0077.

> The sign of the conclusion is unchanged: the independence product is an upper bound and the shared component moves the family-wise rate down by under a hundredth. What changes is which digits may be printed.

Sources: `paper_tables.mechanism_table()` (cells) and `denominator_table.control_arms()` (denominators), both imported rather than reimplemented.

