# R2-4/5 — Trend analysis inside the order-statistic window

Producer: `diagnostics/order_stat_trend.py` · frozen audit set (N=131 runs, those with a long enough log are in the table) · sample sd (n-1, Bessel-corrected), computed over seeds · window = last K epochs, OLS detrend.

| K | n | raw a2 (max−mean) | §5.6 value | OLS drift (over the window) | **detrended a2** |
|---|---|---|---|---|---|
| 50 | 131 | +0.645 ± 0.203 | +0.6445 | +0.146 ± 0.515 pp | **+0.640 ± 0.218** |
| 100 | 131 | +0.764 ± 0.259 | +0.7640 | -0.015 ± 0.435 pp | **+0.728 ± 0.238** |

K=50→100 growth: raw +18.5% · detrended +13.7% (the purely mechanical growth of an iid Gaussian maximum is ≈ +8–9%).

