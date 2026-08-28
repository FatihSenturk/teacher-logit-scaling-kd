# K5 — RAF-DB student-side TS across the dose arms (leak-free, published logits)

@swa · n=3068 · A=1534/B=1534 · sample sd (n-1, Bessel-corrected), computed over seeds · no training, no run dirs

| arm | teacher ECE | raw student ECE | scaled student ECE | n |
|---|---|---|---|---|
| stage1/0.85 | 0.0454 | 0.0797 ± 0.0016 | 0.0437 ± 0.0012 | 3 |
| stage1/1 | 0.0378 | 0.0731 ± 0.0012 | 0.0411 ± 0.0023 | 3 |
| stage1/1.3406 | 0.0159 | 0.0428 ± 0.0003 | 0.0400 ± 0.0029 | 3 |
| stage1/1.7 | 0.0429 | 0.0447 ± 0.0029 | 0.0478 ± 0.0019 | 3 |
| stage1/2.2 | 0.1270 | 0.1008 ± 0.0025 | 0.0503 ± 0.0038 | 3 |
| vae9182/0.85 | 0.0250 | 0.0447 ± 0.0013 | 0.0305 ± 0.0022 | 3 |
| vae9182/1 | 0.0136 | 0.0330 ± 0.0020 | 0.0339 ± 0.0018 | 3 |
| vae9182/1.3406 | 0.0627 | 0.0647 ± 0.0030 | 0.0403 ± 0.0018 | 3 |
| vae9182/1.7 | 0.1454 | 0.1282 ± 0.0030 | 0.0477 ± 0.0044 | 3 |
| vae9182/2.2 | 0.2622 | 0.2109 ± 0.0034 | 0.0492 ± 0.0045 | 3 |

- **stage1**: raw span 0.0580 -> scaled span 0.0103; collapse 5.6x, spread removed 82.3% (denominator: raw span); scaled ranking 1.3406 < 1 < 0.85 < 1.7 < 2.2; best arm per-seed 2/3.
- **vae9182**: raw span 0.1780 -> scaled span 0.0187; collapse 9.5x, spread removed 89.5% (denominator: raw span); scaled ranking 0.85 < 1 < 1.3406 < 1.7 < 2.2; best arm per-seed 3/3.
