# 8(a) — Efficiency frontier

Producer: `diagnostics/efficiency_frontier.py` · @swa · sample sd (n-1, Bessel-corrected), computed over seeds

| nokta | params (M) | GMACs | acc (%) | ECE | n | kaynak |
|---|---|---|---|---|---|---|
| scratch w050 | 0.712 | 0.112 | 86.15 ± 0.07 | 0.0365 ± 0.0057 | 3 | this work |
| scratch w075 | 1.380 | 0.233 | 87.31 ± 0.08 | 0.0388 ± 0.0042 | 3 | this work |
| scratch w100ns | 2.248 | 0.329 | 88.09 ± 0.15 | 0.0374 ± 0.0030 | 3 | this work |
| pretrained w100 | 2.248 | 0.329 | 89.95 ± 0.37 | 0.0330 ± 0.0020 | 3 | this work |
| POSTERv2 (teacher) | 58.334 | 8.483 | 91.82 | 0.0136 | 1 | this work (teacher) |

**Literature rows: 0**  — `diagnostics/literature_fer_models.csv` is empty; the figure was drawn from our points only.
