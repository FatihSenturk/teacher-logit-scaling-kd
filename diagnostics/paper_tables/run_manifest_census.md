# Run-manifest census -- which 90?

Producer: `diagnostics/run_manifest_census.py`. The window is **derived from the counted manifests' own timestamps**, not typed in; label and count cannot drift apart.

| field | value |
|---|---|
| population | `results/unified_students/<run>/<stamp>/manifest.json -- HEPSI; bir alt kume degil, bir suzgec degil` |
| window | **17 June--24 July 2026** (`2026-06-17-13-17-49` … `2026-07-24-22-22-33`) |
| manifests | **90** |
| written at launch, code state verified | **26** |
| reconstructed retroactively (`code_state_verified:false`) | **62** |
| unfinished runs (`code_state_verified:null`) | **2** |
| three classes sum to the total | **True** |

### Cross-checks

| check | n |
|---|---|
| manifests carrying `retroactive:true` | 90 |
| unverified **and** flagged retroactive | 62 |
| unfinished **and** without `finished_utc` | 2 |

