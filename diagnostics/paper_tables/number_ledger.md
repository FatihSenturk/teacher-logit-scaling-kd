# N13 — Number provenance ledger

> **Review-responsive, not pre-declared (17 Aug 2026).** The ledger records the value-to-FIELD binding, not the value: a stale number exists somewhere too, so existence proves nothing.

Producer: `diagnostics/number_ledger.py` · scanner: `diagnostics/paper_number_scan.py` · auditor: `diagnostics/check_numbers.py`

### Token accounting — this column adds up

| in-scope numeric token | count |
|---|---|
| bound to an artifact field | 1199 |
| derived, occupying an in-scope token | 71 |
| declared not-a-measurement | 499 |
| **unregistered** | **0** |
| **= numeric tokens in scope** | **1769** |

The four categories are disjoint (bound ∩ exempt is checked to be empty) and the column sums to the total. Two kinds of declaration are **not** in that table because they occupy no in-scope token — they are anchored to sentences the scanner deliberately does not read:

| declaration anchored outside the scanned scope | count |
|---|---|
| derived quantity on a prose anchor | 4 |
| prose field binding (`pv`) | 3 |

The registry therefore holds **75** derived quantities in total: 71 on in-scope tokens + 4 on prose anchors. Adding *declaration* counts to *token* counts is what made an earlier version of this table appear not to sum.

| other | count |
|---|---|
| printed-vs-field mismatch | 0 |
| confirmation records (second source) | 3 (0 failing) |
| layout tokens dropped by the scanner | 362 |
| sign patterns bound (non-numeric, see below) | 24 of 24 |

## Scope (declared)

**In:** `paper/tables/*.tex`, `abstract`, `supplementary S8-S11`, `individually anchored prose sentences (declared one by one)`  
**Out:** sections/*.tex prose, except the individually anchored sentences (revision window) · supplementary S1-S3 (today's headroom verdict not applied yet)  
**Not a measurement:** `algorithm_name_digits`, `architecture_dim`, `benchmark_protocol`, `citation`, `column_header`, `criterion_constant`, `dataset_name_digits`, `date`, `doi`, `dtype_name`, `enumerator`, `equation_constant`, `hardware_name`, `hyperparameter`, `method_name_digits`, `metric_name_digits`, `name_digits`, `notation_digits`, `null_value`, `population_count`, `preregistration_provenance`, `rounding_caveat`, `sample_size`, `scientific_notation`, `sign_count`, `stated_bound`, `table_reference`, `teacher_name_digits`

## Unregistered numbers

None — every in-scope number is bound, derived or declared.

## Mismatches

None.

## Sign patterns (data claims that carry no digit)

`tab_mechanisms` prints the per-seed sign string next to each cell (`[++-]`) and the discussion refers to those strings by name. They are **not numeric tokens** — the scanner's number extractor cannot see them — but they are copies of artifact fields, so a corrupted sign string would have passed every gate silently. Since 22 Aug 2026 each one is bound and checked. Empty LaTeX groups (`-{}-`, inserted to defeat an en-dash ligature in the printed PDF) are normalised away before comparison: the printed characters, not the source bytes, are what the claim is about.

| printed | field | value | where |
|---|---|---|---|
| `++-` | `T5_mechanisms["stage1/adaptive_t"].swa.d_ece_signs` | `++-` | paper/tables/tab_mechanisms.tex:33 |
| `+++` | `T5_mechanisms["primary/adaptive_t"].swa.d_ece_signs` | `+++` | paper/tables/tab_mechanisms.tex:33 |
| `--+` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_ece_signs` | `--+` | paper/tables/tab_mechanisms.tex:33 |
| `---` | `T5_mechanisms["stage1/g2g_kl"].swa.d_ece_signs` | `---` | paper/tables/tab_mechanisms.tex:42 |
| `+--` | `T5_mechanisms["primary/g2g_kl"].swa.d_ece_signs` | `+--` | paper/tables/tab_mechanisms.tex:42 |
| `-++` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_ece_signs` | `-++` | paper/tables/tab_mechanisms.tex:42 |
| `+--` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_ece_signs` | `+--` | paper/tables/tab_mechanisms.tex:50 |
| `--+` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_ece_signs` | `--+` | paper/tables/tab_mechanisms.tex:50 |
| `+--` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_ece_signs` | `+--` | paper/tables/tab_mechanisms.tex:50 |
| `---` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_ece_signs` | `---` | paper/tables/tab_mechanisms.tex:54 |
| `+--` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_ece_signs` | `+--` | paper/tables/tab_mechanisms.tex:54 |
| `-++` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_ece_signs` | `-++` | paper/tables/tab_mechanisms.tex:58 |
| `-++` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_ece_signs` | `-++` | paper/tables/tab_mechanisms.tex:58 |
| `+++` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_ece_signs` | `+++` | paper/tables/tab_mechanisms.tex:58 |
| `+++` | `T5_mechanisms["stage1/logit_std"].swa.d_ece_signs` | `+++` | paper/tables/tab_mechanisms.tex:62 |
| `+++` | `T5_mechanisms["primary/logit_std"].swa.d_ece_signs` | `+++` | paper/tables/tab_mechanisms.tex:62 |
| `+++` | `T5_mechanisms["vae9182/logit_std"].swa.d_ece_signs` | `+++` | paper/tables/tab_mechanisms.tex:62 |
| `-++` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_ece_signs + T5_mechanisms["primary/gate:oracle_error"].swa.d_ece_signs` | `-++` / `-++` | paper/sections/05_results_discussion.tex:438 |
| `+--` | `T5_mechanisms["primary/g2g_kl"].swa.d_ece_signs` | `+--` | paper/sections/05_results_discussion.tex:468 |
| `-++` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_ece_signs` | `-++` | paper/sections/05_results_discussion.tex:468 |
| `---` | `T5_mechanisms["stage1/g2g_kl"].swa.d_ece_signs` | `---` | paper/sections/05_results_discussion.tex:468 |
| `++-` | `T5_mechanisms["stage1/adaptive_t"].swa.d_ece_signs` | `++-` | paper/sections/05_results_discussion.tex:476 |
| `--+` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_ece_signs` | `--+` | paper/sections/05_results_discussion.tex:483 |
| `++-` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_acc_signs` | `++-` | paper/sections/05_results_discussion.tex:550 |

## Confirmation records (same quantity, second source)

Some quantities are computed twice by independent implementations. They are **deliberately not merged**: agreement between two computations is a cross-check, and merging destroys it. One source is declared canonical and bound; the other is recorded here and audited. The tolerance is not hand-written — it is `0.5 x 10^-d`, where `d` is the **tightest rounding the paper uses for that quantity**, so the gate tightens automatically if a table starts printing more digits. A second, sharper gate is structural: both sources must round to the same value at *every* rounding declared for that field.

| quantity | canonical | confirming | \|diff\| | tolerance | roundings | ok |
|---|---|---|---|---|---|---|
| T*_NLL (stage1, tam fold) | `results.stage1.T_star_nll` = 1.3493829 | `stage1.T_star` = 1.3493927 | 9.87e-06 | 5.0e-05 | 2dp, 3dp, 4dp | yes |
| T*_NLL (primary, tam fold) | `results.primary.T_star_nll` = 1.2613452 | `primary.T_star` = 1.2613412 | 4.05e-06 | 5.0e-04 | 3dp | yes |
| T*_NLL (vae9182, tam fold) | `results.vae9182.T_star_nll` = 0.9830837 | `vae9182.T_star` = 0.9829375 | 1.46e-04 | 5.0e-04 | 2dp, 3dp | yes |

Relays — artifacts that **copy** the confirming value rather than computing it. A drifted relay would produce a silently false confirmation.

| quantity | relay | value | exact copy |
|---|---|---|---|
| T*_NLL (stage1, tam fold) | `p4_teacher_selection/p4_teacher_selection.json` → `recipe_step3_ranking.rows[teacher=stage1].T_star` | 1.3493927 | yes |
| T*_NLL (stage1, tam fold) | `paper_tables/tstar_provenance.json` → `full_fold_fits.stage1` | 1.3493927 | yes |
| T*_NLL (primary, tam fold) | `p4_teacher_selection/p4_teacher_selection.json` → `recipe_step3_ranking.rows[teacher=primary].T_star` | 1.2613412 | yes |
| T*_NLL (primary, tam fold) | `paper_tables/tstar_provenance.json` → `full_fold_fits.primary` | 1.2613412 | yes |
| T*_NLL (vae9182, tam fold) | `p4_teacher_selection/p4_teacher_selection.json` → `recipe_step3_ranking.rows[teacher=vae9182].T_star` | 0.9829375 | yes |
| T*_NLL (vae9182, tam fold) | `paper_tables/tstar_provenance.json` → `full_fold_fits.vae9182` | 0.9829375 | yes |

## Derived quantities

| id | printed | formula | recomputed | ok |
|---|---|---|---|---|
| `jsd_collapse` | 37 | ratio | 37.2342 | yes |
| `jsd_noise_ratio` | 40 | ratio | 39.8126 | yes |
| `capacity_vs_teacher_lever` | 76 | ratio | 75.7089 | yes |
| `selection_cost_best` | 0.52 | diff | 0.521515 | yes |
| `selection_cost_swa` | 0.35 | diff | 0.347674 | yes |
| `selection_cost_last` | 0.83 | diff | 0.825727 | yes |
| `human_trade_ece` | +0.0159 | diff | 0.0158646 | yes |
| `human_trade_jsd` | -0.0051 | diff | -0.00509233 | yes |
| `collapse_ratio_5_10` | 16.3 | ratio | 16.3044 | yes |
| `collapse_ratio_10_20` | 13.5 | ratio | 13.5023 | yes |
| `selection_cost_best_caption` | 0.52 | diff | 0.521515 | yes |
| `ece_reduction_min` | 41 | pct_drop | 41.4635 | yes |
| `ece_reduction_max` | 76 | pct_drop | 76.3748 | yes |
| `accuracy_band_widest_arm` | 0.51 | diff | 0.510646 | yes |
| `robust_agreeing_steps` | 224 | diff | 224 | yes |
| `robust_agreement_pct` | 97.0 | pct_of | 96.9697 | yes |
| `jsd_smallest_stratum_pct` | 0.9 | pct_of | 0.888043 | yes |
| `tstar_criterion_cost_min_supp` | 13 | ratio | 13.307 | yes |
| `tstar_criterion_cost_max_supp` | 14 | ratio | 14.3155 | yes |
| `tstar_criterion_cost_min` | 13 | ratio | 13.307 | yes |
| `tstar_criterion_cost_max` | 14 | ratio | 14.3155 | yes |
| `intro.acc_band_stage1` | 0.30 | diff | 0.304214 | yes |
| `intro.acc_band_vae9182` | 0.51 | diff | 0.510646 | yes |
| `intro.acc_decline_ferplus` | 0.49 | diff | 0.486313 | yes |
| `methodology.votes_below_ten_val` | 37.3 | pct_of | 37.2978 | yes |
| `methodology.abstention_mass_val` | 37.3 | pct_of | 37.2978 | yes |
| `results.jsd_gap_student_ts` | 0.0041 | diff | 0.00414556 | yes |
| `results.ferplus_ece_share_low` | 13 | pct_of | 12.6601 | yes |
| `results.ferplus_ece_share_high` | 15 | pct_of | 14.974 | yes |
| `results.tstar_gap_pct` | 63 | pct_excess | 63.3386 | yes |
| `meth.argmin_cells_agreeing` | 20 | sum | 20 | yes |
| `meth.argmin_cells_total` | 21 | sum | 21 | yes |
| `meth.tstar_criterion_cost_min` | 13 | ratio | 13.307 | yes |
| `meth.tstar_criterion_cost_max` | 14 | ratio | 14.3155 | yes |
| `meth.acc_band_stage1` | 0.30 | diff | 0.304214 | yes |
| `meth.acc_band_vae9182` | 0.51 | diff | 0.510646 | yes |
| `meth.acc_trend_ferplus` | 0.49 | diff | 0.486313 | yes |
| `res.jsd_slice_coverage_pct` | 99.1 | pct_of | 99.112 | yes |
| `res.tradeoff_ece_cost` | +0.0159 | diff | 0.0158646 | yes |
| `res.tradeoff_jsd_gain` | -0.0051 | diff | -0.00509233 | yes |
| `res.sharpened_target_acc_gain` | +0.40 | diff | 0.401738 | yes |
| `res.ferplus_control_mde` | 0.74 | sum | 0.740646 | yes |
| `res.corner_jsd_shortfall` | 0.0002 | diff | 0.00024057 | yes |
| `res.detrend_shift_max` | 0.04 | diff | 0.0359174 | yes |
| `res.rafdb_ece_effect_pct` | 4 | pct_drop | 3.92608 | yes |
| `res.fp16_b1_ratio_lo` | 1.20 | ratio | 1.20419 | yes |
| `res.fp16_b1_ratio_hi` | 1.34 | ratio | 1.33565 | yes |
| `res.fp16_b32_ratio_lo` | 0.63 | ratio | 0.625834 | yes |
| `res.fp16_b32_ratio_hi` | 0.69 | ratio | 0.691174 | yes |
| `s5.ece_reduction_rafdb` | 41 | pct_drop | 41.4635 | yes |
| `s5.full_swing` | 2.4 | ratio | 2.3543 | yes |
| `s5.acc_band_stage1` | 0.30 | diff | 0.304214 | yes |
| `s5.acc_paired_gain` | +0.13 | diff | 0.130376 | yes |
| `s5.ctrl_deterioration` | 6.4 | ratio | 6.40037 | yes |
| `s5.acc_band_vae9182` | 0.51 | diff | 0.510646 | yes |
| `s5.ece_reduction_ferplus` | 76 | pct_drop | 76.3748 | yes |
| `s5.collapse_ratio_510` | 16.3 | ratio | 16.3044 | yes |
| `s5.collapse_ratio_1020` | 13.5 | ratio | 13.5023 | yes |
| `s5.acc_band_ferplus` | 0.49 | diff | 0.486313 | yes |
| `s5.capacity_acc_span` | +1.94 | diff | 1.94481 | yes |
| `s5.teacher_acc_span` | 0.42 | diff | 0.423729 | yes |
| `s5.teacher_ece_factor` | 2.9 | ratio | 2.91989 | yes |
| `s5.sel_cost_swa` | 0.35 | diff | 0.347674 | yes |
| `s5.sel_cost_last` | 0.83 | diff | 0.825727 | yes |
| `s5.baseline_ece_overconf` | 0.075 | mean | 0.0749972 | yes |
| `res.argmin_cells_agreeing_0` | 20 | sum | 20 | yes |
| `s5.r2_floor` | 0.998 | min | 0.998818 | yes |
| `s5.baseline_ece_ratio` | 2.7 | ratio_of_mean | 2.70102 | yes |
| `s5.composite_T_stage1` | 8.04 | product | 8.0436 | yes |
| `s5.composite_T_vae9182` | 6.0 | product | 6 | yes |
| `s5.composite_T_ferplus` | 3.04 | product | 3.0378 | yes |
| `s4.prereg_lead_min` | 18 | min | 18 | yes |
| `figp.snr_floor` | 10.5 | min | 10.5557 | yes |
| `s57.tost_margin` | 0.0034 | sum | 0.00347997 | yes |
| `capacity_vs_teacher_lever_caption` | 76 | ratio | 75.7089 | yes |

## Bindings

| id | printed | artifact | path | rounding |
|---|---|---|---|---|
| `tab_dose_response.rafdb_stage1.T0.85.teacher_ece` | 0.0454 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_stage1.T0.85.signed_gap` | +0.0431 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].signed_gap` | 4dp |
| `tab_dose_response.rafdb_stage1.T0.85.ece_swa_mean` | 0.0797 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T0.85.ece_swa_sd` | 0.0016 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T0.85.ece_last_mean` | 0.0803 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T0.85.ece_last_sd` | 0.0059 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T0.85.acc_swa_mean` | 89.65 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_stage1.T0.85.acc_swa_sd` | 0.18 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[0].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_stage1.T1.00.teacher_ece` | 0.0378 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.00.signed_gap` | +0.0338 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].signed_gap` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.00.ece_swa_mean` | 0.0731 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.00.ece_swa_sd` | 0.0012 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.00.ece_last_mean` | 0.0701 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.00.ece_last_sd` | 0.0081 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.00.acc_swa_mean` | 89.60 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_stage1.T1.00.acc_swa_sd` | 0.34 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_stage1.T1.34.teacher_ece` | 0.0159 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.34.signed_gap` | +0.0040 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].signed_gap` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.34.ece_swa_mean` | 0.0428 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.34.ece_swa_sd` | 0.0003 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.34.ece_last_mean` | 0.0365 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.34.ece_last_sd` | 0.0005 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.34.acc_swa_mean` | 89.73 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_stage1.T1.34.acc_swa_sd` | 0.07 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_stage1.T1.70.teacher_ece` | 0.0429 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.70.signed_gap` | -0.0427 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].signed_gap` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.70.ece_swa_mean` | 0.0447 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.70.ece_swa_sd` | 0.0029 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.70.ece_last_mean` | 0.0572 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.70.ece_last_sd` | 0.0059 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T1.70.acc_swa_mean` | 89.43 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_stage1.T1.70.acc_swa_sd` | 0.20 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_stage1.T2.20.teacher_ece` | 0.1270 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_stage1.T2.20.signed_gap` | -0.1270 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].signed_gap` | 4dp |
| `tab_dose_response.rafdb_stage1.T2.20.ece_swa_mean` | 0.1008 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T2.20.ece_swa_sd` | 0.0025 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T2.20.ece_last_mean` | 0.1189 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_stage1.T2.20.ece_last_sd` | 0.0091 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_stage1.T2.20.acc_swa_mean` | 89.63 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_stage1.T2.20.acc_swa_sd` | 0.28 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_vae9182.T0.85.teacher_ece` | 0.0250 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_vae9182.T0.85.signed_gap` | +0.0248 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].signed_gap` | 4dp |
| `tab_dose_response.rafdb_vae9182.T0.85.ece_swa_mean` | 0.0447 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T0.85.ece_swa_sd` | 0.0013 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T0.85.ece_last_mean` | 0.0358 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T0.85.ece_last_sd` | 0.0053 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T0.85.acc_swa_mean` | 89.93 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_vae9182.T0.85.acc_swa_sd` | 0.06 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_vae9182.T1.00.teacher_ece` | 0.0136 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.00.signed_gap` | +0.0042 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].signed_gap` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.00.ece_swa_mean` | 0.0330 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.00.ece_swa_sd` | 0.0020 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.00.ece_last_mean` | 0.0307 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.00.ece_last_sd` | 0.0011 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.00.acc_swa_mean` | 89.95 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_vae9182.T1.00.acc_swa_sd` | 0.37 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_vae9182.T1.34.teacher_ece` | 0.0627 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.34.signed_gap` | -0.0605 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].signed_gap` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.34.ece_swa_mean` | 0.0647 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.34.ece_swa_sd` | 0.0030 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.34.ece_last_mean` | 0.0795 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.34.ece_last_sd` | 0.0056 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.34.acc_swa_mean` | 90.09 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_vae9182.T1.34.acc_swa_sd` | 0.29 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_vae9182.T1.70.teacher_ece` | 0.1454 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.70.signed_gap` | -0.1453 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].signed_gap` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.70.ece_swa_mean` | 0.1282 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.70.ece_swa_sd` | 0.0030 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.70.ece_last_mean` | 0.1456 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.70.ece_last_sd` | 0.0125 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T1.70.acc_swa_mean` | 89.58 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_vae9182.T1.70.acc_swa_sd` | 0.52 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_vae9182.T2.20.teacher_ece` | 0.2622 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_vae9182.T2.20.signed_gap` | -0.2622 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].signed_gap` | 4dp |
| `tab_dose_response.rafdb_vae9182.T2.20.ece_swa_mean` | 0.2109 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T2.20.ece_swa_sd` | 0.0034 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T2.20.ece_last_mean` | 0.2282 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.rafdb_vae9182.T2.20.ece_last_sd` | 0.0090 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.rafdb_vae9182.T2.20.acc_swa_mean` | 89.92 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.rafdb_vae9182.T2.20.acc_swa_sd` | 0.33 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.ferplus.T0.26.teacher_ece` | 0.0393 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].teacher_ece` | 4dp |
| `tab_dose_response.ferplus.T0.26.signed_gap` | +0.0393 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].signed_gap` | 4dp |
| `tab_dose_response.ferplus.T0.26.ece_swa_mean` | 0.0587 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T0.26.ece_swa_sd` | 0.0038 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T0.26.ece_last_mean` | 0.0591 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T0.26.ece_last_sd` | 0.0015 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T0.26.acc_swa_mean` | 89.21 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.ferplus.T0.26.acc_swa_sd` | 0.29 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[0].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.ferplus.T0.51.teacher_ece` | 0.0156 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].teacher_ece` | 4dp |
| `tab_dose_response.ferplus.T0.51.signed_gap` | -0.0117 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].signed_gap` | 4dp |
| `tab_dose_response.ferplus.T0.51.ece_swa_mean` | 0.0185 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T0.51.ece_swa_sd` | 0.0016 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T0.51.ece_last_mean` | 0.0191 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T0.51.ece_last_sd` | 0.0061 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T0.51.acc_swa_mean` | 89.12 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.ferplus.T0.51.acc_swa_sd` | 0.14 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.ferplus.T0.74.teacher_ece` | 0.0665 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].teacher_ece` | 4dp |
| `tab_dose_response.ferplus.T0.74.signed_gap` | -0.0649 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].signed_gap` | 4dp |
| `tab_dose_response.ferplus.T0.74.ece_swa_mean` | 0.0344 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T0.74.ece_swa_sd` | 0.0012 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T0.74.ece_last_mean` | 0.0377 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T0.74.ece_last_sd` | 0.0007 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T0.74.acc_swa_mean` | 88.78 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.ferplus.T0.74.acc_swa_sd` | 0.05 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[2].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.ferplus.T1.00.teacher_ece` | 0.1282 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].teacher_ece` | 4dp |
| `tab_dose_response.ferplus.T1.00.signed_gap` | -0.1277 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].signed_gap` | 4dp |
| `tab_dose_response.ferplus.T1.00.ece_swa_mean` | 0.0783 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T1.00.ece_swa_sd` | 0.0046 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T1.00.ece_last_mean` | 0.0852 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.last.ece_mean` | 4dp |
| `tab_dose_response.ferplus.T1.00.ece_last_sd` | 0.0082 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.last.ece_sd` | 4dp |
| `tab_dose_response.ferplus.T1.00.acc_swa_mean` | 88.72 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.acc_mean` | 2dp |
| `tab_dose_response.ferplus.T1.00.acc_swa_sd` | 0.37 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.acc_sd` | 2dp |
| `tab_dose_response.rafdb_stage1.header.teacher_ece_T1` | 0.0378 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].teacher_ece` | 4dp |
| `tab_dose_response.rafdb_vae9182.header.teacher_ece_T1` | 0.0136 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].teacher_ece` | 4dp |
| `tab_dose_response.stage1.header.T_star_fit` | 1.35 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 2dp |
| `tab_dose_response.vae9182.header.T_star_fit` | 0.98 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 2dp |
| `tab_dose_response.ferplus.header.T_star_fit` | 0.51 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 2dp |
| `tab_dose_response.ferplus.header.teacher_ece_T1` | 0.1282 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].teacher_ece` | 4dp |
| `tab_dose_response.caption.stage1_half_fold_fit` | 1.3406 | `paper_tables/tstar_provenance.json` | `half_fold_fits.stage1` | 4dp |
| `tab_dose_response.caption.stage1_full_fold_fit` | 1.3494 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 4dp |
| `tab_dose_response.caption.vae9182_fit` | 0.98 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 2dp |
| `app_seeds.rafdb_stage1.T0.85.teacher_ece` | 0.0454 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].teacher_ece` | 4dp |
| `app_seeds.rafdb_stage1.T0.85.signed_gap` | +0.0431 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].signed_gap` | 4dp |
| `app_seeds.rafdb_stage1.T0.85.seed1` | 0.0814 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T0.85.seed42` | 0.0781 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T0.85.seed43` | 0.0795 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T0.85.mean` | 0.0797 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].ece_mean` | 4dp |
| `app_seeds.rafdb_stage1.T0.85.sd` | 0.0016 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[0].ece_sd` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.teacher_ece` | 0.0378 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].teacher_ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.signed_gap` | +0.0338 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].signed_gap` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.seed1` | 0.0721 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.seed42` | 0.0728 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.seed43` | 0.0744 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.mean` | 0.0731 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].ece_mean` | 4dp |
| `app_seeds.rafdb_stage1.T1.00.sd` | 0.0012 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[1].ece_sd` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.teacher_ece` | 0.0159 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].teacher_ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.signed_gap` | +0.0040 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].signed_gap` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.seed1` | 0.0425 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.seed42` | 0.0432 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.seed43` | 0.0428 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.mean` | 0.0428 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].ece_mean` | 4dp |
| `app_seeds.rafdb_stage1.T1.3406.sd` | 0.0003 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[2].ece_sd` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.teacher_ece` | 0.0429 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].teacher_ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.signed_gap` | -0.0427 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].signed_gap` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.seed1` | 0.0415 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.seed42` | 0.0472 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.seed43` | 0.0455 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.mean` | 0.0447 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].ece_mean` | 4dp |
| `app_seeds.rafdb_stage1.T1.70.sd` | 0.0029 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[3].ece_sd` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.teacher_ece` | 0.1270 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].teacher_ece` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.signed_gap` | -0.1270 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].signed_gap` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.seed1` | 0.1013 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.seed42` | 0.1030 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.seed43` | 0.0980 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.mean` | 0.1008 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].ece_mean` | 4dp |
| `app_seeds.rafdb_stage1.T2.20.sd` | 0.0025 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_stage1.points[4].ece_sd` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.teacher_ece` | 0.0250 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].teacher_ece` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.signed_gap` | +0.0248 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].signed_gap` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.seed1` | 0.0460 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.seed42` | 0.0434 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.seed43` | 0.0446 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.mean` | 0.0447 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].ece_mean` | 4dp |
| `app_seeds.rafdb_vae9182.T0.85.sd` | 0.0013 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[0].ece_sd` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.teacher_ece` | 0.0136 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].teacher_ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.signed_gap` | +0.0042 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].signed_gap` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.seed1` | 0.0343 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.seed42` | 0.0340 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.seed43` | 0.0307 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.mean` | 0.0330 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].ece_mean` | 4dp |
| `app_seeds.rafdb_vae9182.T1.00.sd` | 0.0020 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[1].ece_sd` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.teacher_ece` | 0.0627 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].teacher_ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.signed_gap` | -0.0605 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].signed_gap` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.seed1` | 0.0628 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.seed42` | 0.0682 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.seed43` | 0.0632 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.mean` | 0.0647 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].ece_mean` | 4dp |
| `app_seeds.rafdb_vae9182.T1.3406.sd` | 0.0030 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[2].ece_sd` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.teacher_ece` | 0.1454 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].teacher_ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.signed_gap` | -0.1453 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].signed_gap` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.seed1` | 0.1270 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.seed42` | 0.1260 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.seed43` | 0.1316 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.mean` | 0.1282 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].ece_mean` | 4dp |
| `app_seeds.rafdb_vae9182.T1.70.sd` | 0.0030 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[3].ece_sd` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.teacher_ece` | 0.2622 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].teacher_ece` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.signed_gap` | -0.2622 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].signed_gap` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.seed1` | 0.2090 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].per_seed["1"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.seed42` | 0.2148 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].per_seed["42"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.seed43` | 0.2090 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].per_seed["43"].ece` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.mean` | 0.2109 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].ece_mean` | 4dp |
| `app_seeds.rafdb_vae9182.T2.20.sd` | 0.0034 | `paper_tables/dose_response_per_seed.json` | `series.rafdb_vae9182.points[4].ece_sd` | 4dp |
| `app_seeds.ferplus.T0.26.teacher_ece` | 0.0393 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].teacher_ece` | 4dp |
| `app_seeds.ferplus.T0.26.signed_gap` | +0.0393 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].signed_gap` | 4dp |
| `app_seeds.ferplus.T0.26.seed1` | 0.0632 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].per_seed["1"].ece` | 4dp |
| `app_seeds.ferplus.T0.26.seed42` | 0.0568 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].per_seed["42"].ece` | 4dp |
| `app_seeds.ferplus.T0.26.seed43` | 0.0563 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].per_seed["43"].ece` | 4dp |
| `app_seeds.ferplus.T0.26.mean` | 0.0587 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].ece_mean` | 4dp |
| `app_seeds.ferplus.T0.26.sd` | 0.0038 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[0].ece_sd` | 4dp |
| `app_seeds.ferplus.T0.5063.teacher_ece` | 0.0156 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].teacher_ece` | 4dp |
| `app_seeds.ferplus.T0.5063.signed_gap` | -0.0117 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].signed_gap` | 4dp |
| `app_seeds.ferplus.T0.5063.seed1` | 0.0193 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].per_seed["1"].ece` | 4dp |
| `app_seeds.ferplus.T0.5063.seed42` | 0.0167 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].per_seed["42"].ece` | 4dp |
| `app_seeds.ferplus.T0.5063.seed43` | 0.0195 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].per_seed["43"].ece` | 4dp |
| `app_seeds.ferplus.T0.5063.mean` | 0.0185 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].ece_mean` | 4dp |
| `app_seeds.ferplus.T0.5063.sd` | 0.0016 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[1].ece_sd` | 4dp |
| `app_seeds.ferplus.T0.74.teacher_ece` | 0.0665 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].teacher_ece` | 4dp |
| `app_seeds.ferplus.T0.74.signed_gap` | -0.0649 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].signed_gap` | 4dp |
| `app_seeds.ferplus.T0.74.seed1` | 0.0332 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].per_seed["1"].ece` | 4dp |
| `app_seeds.ferplus.T0.74.seed42` | 0.0356 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].per_seed["42"].ece` | 4dp |
| `app_seeds.ferplus.T0.74.seed43` | 0.0343 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].per_seed["43"].ece` | 4dp |
| `app_seeds.ferplus.T0.74.mean` | 0.0344 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].ece_mean` | 4dp |
| `app_seeds.ferplus.T0.74.sd` | 0.0012 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[2].ece_sd` | 4dp |
| `app_seeds.ferplus.T1.00.teacher_ece` | 0.1282 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].teacher_ece` | 4dp |
| `app_seeds.ferplus.T1.00.signed_gap` | -0.1277 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].signed_gap` | 4dp |
| `app_seeds.ferplus.T1.00.seed1` | 0.0826 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].per_seed["1"].ece` | 4dp |
| `app_seeds.ferplus.T1.00.seed42` | 0.0734 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].per_seed["42"].ece` | 4dp |
| `app_seeds.ferplus.T1.00.seed43` | 0.0789 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].per_seed["43"].ece` | 4dp |
| `app_seeds.ferplus.T1.00.mean` | 0.0783 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].ece_mean` | 4dp |
| `app_seeds.ferplus.T1.00.sd` | 0.0046 | `paper_tables/dose_response_per_seed.json` | `series.ferplus.points[3].ece_sd` | 4dp |
| `app_sd.swa.stage1.effective_number.ece_control_level` | 0.0731 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.swa.stage1.effective_number.ece_control_sd` | 0.0012 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.swa.stage1.effective_number.acc_control_level` | 89.602 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.swa.stage1.effective_number.acc_control_sd` | 0.340 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.swa.stage1.effective_number.ece_mde_2sd` | 0.0024 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.swa.stage1.effective_number.ece_mde_pct_of_level` | 3.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.swa.stage1.effective_number.acc_mde_2sd` | 0.681 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.swa.stage1.effective_number.acc_mde_pct_of_level` | 0.8 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.swa.stage1.none.ece_control_level` | 0.0745 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.swa.stage1.none.ece_control_sd` | 0.0021 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.swa.stage1.none.acc_control_level` | 89.657 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.swa.stage1.none.acc_control_sd` | 0.100 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.swa.stage1.none.ece_mde_2sd` | 0.0042 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.swa.stage1.none.ece_mde_pct_of_level` | 5.7 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.swa.stage1.none.acc_mde_2sd` | 0.199 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.swa.stage1.none.acc_mde_pct_of_level` | 0.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.swa.primary.effective_number.ece_control_level` | 0.0707 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.swa.primary.effective_number.ece_control_sd` | 0.0015 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.swa.primary.effective_number.acc_control_level` | 89.602 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.swa.primary.effective_number.acc_control_sd` | 0.130 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.swa.primary.effective_number.ece_mde_2sd` | 0.0030 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.swa.primary.effective_number.ece_mde_pct_of_level` | 4.3 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.swa.primary.effective_number.acc_mde_2sd` | 0.261 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.swa.primary.effective_number.acc_mde_pct_of_level` | 0.3 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.swa.primary.none.ece_control_level` | 0.0755 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.swa.primary.none.ece_control_sd` | 0.0033 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.swa.primary.none.acc_control_level` | 89.266 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.swa.primary.none.acc_control_sd` | 0.394 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.swa.primary.none.ece_mde_2sd` | 0.0067 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.swa.primary.none.ece_mde_pct_of_level` | 8.8 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.swa.primary.none.acc_mde_2sd` | 0.789 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.swa.primary.none.acc_mde_pct_of_level` | 0.9 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.swa.vae9182.effective_number.ece_control_level` | 0.0330 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.swa.vae9182.effective_number.ece_control_sd` | 0.0020 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.swa.vae9182.effective_number.acc_control_level` | 89.950 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.swa.vae9182.effective_number.acc_control_sd` | 0.366 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.swa.vae9182.effective_number.ece_mde_2sd` | 0.0040 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.swa.vae9182.effective_number.ece_mde_pct_of_level` | 12.1 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.swa.vae9182.effective_number.acc_mde_2sd` | 0.733 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.swa.vae9182.effective_number.acc_mde_pct_of_level` | 0.8 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.swa.vae9182.none.ece_control_level` | 0.0278 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.swa.vae9182.none.ece_control_sd` | 0.0027 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.swa.vae9182.none.acc_control_level` | 90.146 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.swa.vae9182.none.acc_control_sd` | 0.207 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.swa.vae9182.none.ece_mde_2sd` | 0.0054 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.swa.vae9182.none.ece_mde_pct_of_level` | 19.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.swa.vae9182.none.acc_mde_2sd` | 0.414 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.swa.vae9182.none.acc_mde_pct_of_level` | 0.5 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.best.stage1.effective_number.ece_control_level` | 0.0627 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.best.stage1.effective_number.ece_control_sd` | 0.0054 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.best.stage1.effective_number.acc_control_level` | 89.754 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.best.stage1.effective_number.acc_control_sd` | 0.082 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.best.stage1.effective_number.ece_mde_2sd` | 0.0108 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.best.stage1.effective_number.ece_mde_pct_of_level` | 17.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.best.stage1.effective_number.acc_mde_2sd` | 0.164 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.best.stage1.effective_number.acc_mde_pct_of_level` | 0.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.best.stage1.none.ece_control_level` | 0.0651 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.best.stage1.none.ece_control_sd` | 0.0037 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.best.stage1.none.acc_control_level` | 89.820 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.best.stage1.none.acc_control_sd` | 0.075 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.best.stage1.none.ece_mde_2sd` | 0.0074 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.best.stage1.none.ece_mde_pct_of_level` | 11.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.best.stage1.none.acc_mde_2sd` | 0.151 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.best.stage1.none.acc_mde_pct_of_level` | 0.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=stage1][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.best.primary.effective_number.ece_control_level` | 0.0606 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.best.primary.effective_number.ece_control_sd` | 0.0085 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.best.primary.effective_number.acc_control_level` | 89.570 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.best.primary.effective_number.acc_control_sd` | 0.086 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.best.primary.effective_number.ece_mde_2sd` | 0.0170 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.best.primary.effective_number.ece_mde_pct_of_level` | 28.0 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.best.primary.effective_number.acc_mde_2sd` | 0.172 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.best.primary.effective_number.acc_mde_pct_of_level` | 0.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.best.primary.none.ece_control_level` | 0.0707 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.best.primary.none.ece_control_sd` | 0.0048 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.best.primary.none.acc_control_level` | 89.070 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.best.primary.none.acc_control_sd` | 0.191 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.best.primary.none.ece_mde_2sd` | 0.0097 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.best.primary.none.ece_mde_pct_of_level` | 13.7 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.best.primary.none.acc_mde_2sd` | 0.382 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.best.primary.none.acc_mde_pct_of_level` | 0.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=primary][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.best.vae9182.effective_number.ece_control_level` | 0.0274 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.best.vae9182.effective_number.ece_control_sd` | 0.0021 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.best.vae9182.effective_number.acc_control_level` | 90.276 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.best.vae9182.effective_number.acc_control_sd` | 0.191 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.best.vae9182.effective_number.ece_mde_2sd` | 0.0042 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.best.vae9182.effective_number.ece_mde_pct_of_level` | 15.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.best.vae9182.effective_number.acc_mde_2sd` | 0.382 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.best.vae9182.effective_number.acc_mde_pct_of_level` | 0.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.best.vae9182.none.ece_control_level` | 0.0225 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.best.vae9182.none.ece_control_sd` | 0.0012 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.best.vae9182.none.acc_control_level` | 90.385 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.best.vae9182.none.acc_control_sd` | 0.267 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.best.vae9182.none.ece_mde_2sd` | 0.0024 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.best.vae9182.none.ece_mde_pct_of_level` | 10.8 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.best.vae9182.none.acc_mde_2sd` | 0.534 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.best.vae9182.none.acc_mde_pct_of_level` | 0.6 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=best][teacher=vae9182][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.last.stage1.effective_number.ece_control_level` | 0.0701 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.last.stage1.effective_number.ece_control_sd` | 0.0081 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.last.stage1.effective_number.acc_control_level` | 88.994 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.last.stage1.effective_number.acc_control_sd` | 0.100 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.last.stage1.effective_number.ece_mde_2sd` | 0.0163 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.last.stage1.effective_number.ece_mde_pct_of_level` | 23.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.last.stage1.effective_number.acc_mde_2sd` | 0.199 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.last.stage1.effective_number.acc_mde_pct_of_level` | 0.2 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.last.stage1.none.ece_control_level` | 0.0691 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.last.stage1.none.ece_control_sd` | 0.0052 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.last.stage1.none.acc_control_level` | 89.124 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.last.stage1.none.acc_control_sd` | 0.191 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.last.stage1.none.ece_mde_2sd` | 0.0103 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.last.stage1.none.ece_mde_pct_of_level` | 15.0 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.last.stage1.none.acc_mde_2sd` | 0.382 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.last.stage1.none.acc_mde_pct_of_level` | 0.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=stage1][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.last.primary.effective_number.ece_control_level` | 0.0701 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.last.primary.effective_number.ece_control_sd` | 0.0031 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.last.primary.effective_number.acc_control_level` | 88.494 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.last.primary.effective_number.acc_control_sd` | 0.259 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.last.primary.effective_number.ece_mde_2sd` | 0.0062 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.last.primary.effective_number.ece_mde_pct_of_level` | 8.8 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.last.primary.effective_number.acc_mde_2sd` | 0.517 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.last.primary.effective_number.acc_mde_pct_of_level` | 0.6 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.last.primary.none.ece_control_level` | 0.0737 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.last.primary.none.ece_control_sd` | 0.0048 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.last.primary.none.acc_control_level` | 88.353 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.last.primary.none.acc_control_sd` | 0.303 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.last.primary.none.ece_mde_2sd` | 0.0095 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.last.primary.none.ece_mde_pct_of_level` | 12.9 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.last.primary.none.acc_mde_2sd` | 0.606 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.last.primary.none.acc_mde_pct_of_level` | 0.7 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=primary][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.last.vae9182.effective_number.ece_control_level` | 0.0307 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_level` | 4dp |
| `app_sd.last.vae9182.effective_number.ece_control_sd` | 0.0011 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `app_sd.last.vae9182.effective_number.acc_control_level` | 89.820 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=acc].control_level` | 3dp |
| `app_sd.last.vae9182.effective_number.acc_control_sd` | 0.167 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=acc].control_sd` | 3dp |
| `app_mde.last.vae9182.effective_number.ece_mde_2sd` | 0.0021 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `app_mde.last.vae9182.effective_number.ece_mde_pct_of_level` | 7.0 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.last.vae9182.effective_number.acc_mde_2sd` | 0.335 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=acc].mde_2sd` | 3dp |
| `app_mde.last.vae9182.effective_number.acc_mde_pct_of_level` | 0.4 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=effective_number][axis=acc].mde_pct_of_level` | 1dp |
| `app_sd.last.vae9182.none.ece_control_level` | 0.0297 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=ece].control_level` | 4dp |
| `app_sd.last.vae9182.none.ece_control_sd` | 0.0039 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `app_sd.last.vae9182.none.acc_control_level` | 89.602 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=acc].control_level` | 3dp |
| `app_sd.last.vae9182.none.acc_control_sd` | 0.267 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=acc].control_sd` | 3dp |
| `app_mde.last.vae9182.none.ece_mde_2sd` | 0.0079 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=ece].mde_2sd` | 4dp |
| `app_mde.last.vae9182.none.ece_mde_pct_of_level` | 26.5 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=ece].mde_pct_of_level` | 1dp |
| `app_mde.last.vae9182.none.acc_mde_2sd` | 0.534 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=acc].mde_2sd` | 3dp |
| `app_mde.last.vae9182.none.acc_mde_pct_of_level` | 0.6 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=last][teacher=vae9182][class_weight_mode=none][axis=acc].mde_pct_of_level` | 1dp |
| `tab_mechanisms.stage1.adaptive_t.d_acc` | +0.16 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.adaptive_t.d_ece` | -0.0011 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.adaptive_t.d_acc` | -0.39 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.adaptive_t.d_ece` | +0.0023 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.adaptive_t.d_acc` | +0.28 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.adaptive_t.d_ece` | -0.0042 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.stage1.ctkd.d_acc` | -0.03 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/ctkd"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.ctkd.d_ece` | +0.0058 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/ctkd"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.ctkd.d_acc` | -0.49 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/ctkd"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.ctkd.d_ece` | +0.0038 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/ctkd"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.ctkd.d_acc` | -0.13 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/ctkd"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.ctkd.d_ece` | +0.0038 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/ctkd"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.stage1.g2g_kl.d_acc` | +0.41 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.g2g_kl.d_ece` | -0.0042 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.g2g_kl.d_acc` | -0.14 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/g2g_kl"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.g2g_kl.d_ece` | -0.0016 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/g2g_kl"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.g2g_kl.d_acc` | +0.16 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.g2g_kl.d_ece` | +0.0009 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.stage1.gate:mean_logvar.d_acc` | -0.10 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.gate:mean_logvar.d_ece` | -0.0012 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.gate:mean_logvar.d_acc` | +0.20 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.gate:mean_logvar.d_ece` | -0.0056 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.gate:mean_logvar.d_acc` | -0.27 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.gate:mean_logvar.d_ece` | +0.0015 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.stage1.gate:target_logvar.d_acc` | +0.25 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.gate:target_logvar.d_ece` | -0.0041 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.gate:target_logvar.d_acc` | -0.09 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.gate:target_logvar.d_ece` | -0.0008 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.stage1.gate:oracle_error.d_acc` | -0.22 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.gate:oracle_error.d_ece` | +0.0015 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.gate:oracle_error.d_acc` | -0.01 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.gate:oracle_error.d_ece` | +0.0004 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.gate:oracle_error.d_acc` | -0.23 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.gate:oracle_error.d_ece` | +0.0056 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.stage1.logit_std.d_acc` | -0.23 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.stage1.logit_std.d_ece` | +0.0906 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.primary.logit_std.d_acc` | -0.32 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.primary.logit_std.d_ece` | +0.0859 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.logit_std.d_acc` | -0.12 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.logit_std.d_ece` | +0.1388 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_mechanisms.vae9182.g2g_kl+adaptive_t.d_acc` | -0.07 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl+adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_mechanisms.vae9182.g2g_kl+adaptive_t.d_ece` | -0.0018 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl+adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_logitstd.caption.narrowest_swa` | 23 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|primary"].ratio` | int |
| `tab_logitstd.caption.median` | 27 | `paper_tables/noise_units.json` | `summary.median` | int |
| `tab_logitstd.caption.mean` | 52 | `paper_tables/noise_units.json` | `summary.mean` | int |
| `tab_logitstd.caption.floor` | 2.6 | `paper_tables/noise_units.json` | `summary.min` | 1dp |
| `tab_logitstd.primary.swa.d_acc` | -0.32 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_logitstd.primary.swa.d_ece` | +0.0859 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_logitstd.primary.best.d_acc` | -0.43 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].best.d_acc_mean` | 2dp |
| `tab_logitstd.primary.best.d_ece` | +0.1191 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].best.d_ece_mean` | 4dp |
| `tab_logitstd.primary.last.d_acc` | -0.27 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].last.d_acc_mean` | 2dp |
| `tab_logitstd.primary.last.d_ece` | +0.1044 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].last.d_ece_mean` | 4dp |
| `tab_logitstd.stage1.swa.d_acc` | -0.23 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_logitstd.stage1.swa.d_ece` | +0.0906 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_logitstd.stage1.best.d_acc` | -0.32 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].best.d_acc_mean` | 2dp |
| `tab_logitstd.stage1.best.d_ece` | +0.1252 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].best.d_ece_mean` | 4dp |
| `tab_logitstd.stage1.last.d_acc` | -0.52 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].last.d_acc_mean` | 2dp |
| `tab_logitstd.stage1.last.d_ece` | +0.1090 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].last.d_ece_mean` | 4dp |
| `tab_logitstd.vae9182.swa.d_acc` | -0.12 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_logitstd.vae9182.swa.d_ece` | +0.1388 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_logitstd.vae9182.best.d_acc` | -0.52 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].best.d_acc_mean` | 2dp |
| `tab_logitstd.vae9182.best.d_ece` | +0.1573 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].best.d_ece_mean` | 4dp |
| `tab_logitstd.vae9182.last.d_acc` | -0.58 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].last.d_acc_mean` | 2dp |
| `tab_logitstd.vae9182.last.d_ece` | +0.1593 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].last.d_ece_mean` | 4dp |
| `tab_mechanisms.foot.stage1.effective_number.0` | 0.0012 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.vae9182.effective_number.1` | 0.0020 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.stage1.effective_number.3` | 0.0012 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.primary.effective_number.4` | 0.0015 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.vae9182.effective_number.6` | 0.0020 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=effective_number][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.stage1.none.7` | 0.0021 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.primary.none.8` | 0.0033 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.stage1.none.10` | 0.0021 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.primary.none.11` | 0.0033 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=primary][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `tab_mechanisms.foot.vae9182.none.13` | 0.0027 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=vae9182][class_weight_mode=none][axis=ece].control_sd` | 4dp |
| `tab_selection.stage1.teacher_acc` | 92.24 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].teacher_acc` | 2dp |
| `tab_selection.stage1.teacher_ece` | 0.0378 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].teacher_ece` | 4dp |
| `tab_selection.stage1.T_star` | 1.349 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 3dp |
| `tab_selection.stage1.student_acc_mean` | 89.75 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.acc_mean` | 2dp |
| `tab_selection.stage1.student_acc_sd` | 0.08 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.acc_sd` | 2dp |
| `tab_selection.stage1.student_ece` | 0.0627 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.ece_mean` | 4dp |
| `tab_selection.primary.teacher_acc` | 92.01 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].teacher_acc` | 2dp |
| `tab_selection.primary.teacher_ece` | 0.0396 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].teacher_ece` | 4dp |
| `tab_selection.primary.T_star` | 1.261 | `paper_tables/tstar_sensitivity.json` | `results.primary.T_star_nll` | 3dp |
| `tab_selection.primary.student_acc_mean` | 89.57 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].student_by_ckpt.best.acc_mean` | 2dp |
| `tab_selection.primary.student_acc_sd` | 0.09 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].student_by_ckpt.best.acc_sd` | 2dp |
| `tab_selection.primary.student_ece` | 0.0606 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].student_by_ckpt.best.ece_mean` | 4dp |
| `tab_selection.vae9182.teacher_acc` | 91.82 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].teacher_acc` | 2dp |
| `tab_selection.vae9182.teacher_ece` | 0.0136 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].teacher_ece` | 4dp |
| `tab_selection.vae9182.T_star` | 0.983 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 3dp |
| `tab_selection.vae9182.student_acc_mean` | 90.28 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.acc_mean` | 2dp |
| `tab_selection.vae9182.student_acc_sd` | 0.19 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.acc_sd` | 2dp |
| `tab_selection.vae9182.student_ece` | 0.0274 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.ece_mean` | 4dp |
| `tab_selection.swa_tie` | 89.60 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.swa.acc_mean` | 2dp |
| `tab_selection.rho_teacherACC_studentACC` | -0.50 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.spearman_teacherACC_vs_studentACC` | 2dp |
| `tab_selection.rho_negTeacherECE_studentACC` | +1.00 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.spearman_negTeacherECE_vs_studentACC` | 2dp |
| `tab_selection.best_winner_exact` | 90.2760 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].student_by_ckpt.best.acc_mean` | 4dp |
| `tab_selection.best_acc_rule_exact` | 89.7545 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].student_by_ckpt.best.acc_mean` | 4dp |
| `tab_holm.rank1.mean` | +0.1388 | `paper_tables/inferential_tests.json` | `results[3].mean` | 4dp |
| `tab_holm.rank1.sd` | 0.0013 | `paper_tables/inferential_tests.json` | `results[3].sd` | 4dp |
| `tab_holm.rank1.t` | 185.8 | `paper_tables/inferential_tests.json` | `results[3].t` | 1dp |
| `tab_holm.rank1.p_holm` | 0.0002 | `paper_tables/inferential_tests.json` | `results[3].p_holm` | 4dp |
| `tab_holm.rank2.mean` | +0.0906 | `paper_tables/inferential_tests.json` | `results[1].mean` | 4dp |
| `tab_holm.rank2.sd` | 0.0023 | `paper_tables/inferential_tests.json` | `results[1].sd` | 4dp |
| `tab_holm.rank2.t` | 67.4 | `paper_tables/inferential_tests.json` | `results[1].t` | 1dp |
| `tab_holm.rank2.p_holm` | 0.0011 | `paper_tables/inferential_tests.json` | `results[1].p_holm` | 4dp |
| `tab_holm.rank3.mean` | -0.0303 | `paper_tables/inferential_tests.json` | `results[0].mean` | 4dp |
| `tab_holm.rank3.sd` | 0.0012 | `paper_tables/inferential_tests.json` | `results[0].sd` | 4dp |
| `tab_holm.rank3.t` | -44.7 | `paper_tables/inferential_tests.json` | `results[0].t` | 1dp |
| `tab_holm.rank3.p_holm` | 0.0020 | `paper_tables/inferential_tests.json` | `results[0].p_holm` | 4dp |
| `tab_holm.rank4.mean` | -0.0598 | `paper_tables/inferential_tests.json` | `results[5].mean` | 4dp |
| `tab_holm.rank4.sd` | 0.0033 | `paper_tables/inferential_tests.json` | `results[5].sd` | 4dp |
| `tab_holm.rank4.t` | -31.7 | `paper_tables/inferential_tests.json` | `results[5].t` | 1dp |
| `tab_holm.rank4.p_holm` | 0.0030 | `paper_tables/inferential_tests.json` | `results[5].p_holm` | 4dp |
| `tab_holm.rank5.mean` | +0.0859 | `paper_tables/inferential_tests.json` | `results[2].mean` | 4dp |
| `tab_holm.rank5.sd` | 0.0058 | `paper_tables/inferential_tests.json` | `results[2].sd` | 4dp |
| `tab_holm.rank5.t` | 25.6 | `paper_tables/inferential_tests.json` | `results[2].t` | 1dp |
| `tab_holm.rank5.p_holm` | 0.0030 | `paper_tables/inferential_tests.json` | `results[2].p_holm` | 4dp |
| `tab_holm.rank6.mean` | +0.0056 | `paper_tables/inferential_tests.json` | `results[4].mean` | 4dp |
| `tab_holm.rank6.sd` | 0.0040 | `paper_tables/inferential_tests.json` | `results[4].sd` | 4dp |
| `tab_holm.rank6.t` | 2.5 | `paper_tables/inferential_tests.json` | `results[4].t` | 1dp |
| `tab_holm.rank6.p_holm` | 0.1339 | `paper_tables/inferential_tests.json` | `results[4].p_holm` | 4dp |
| `tab_human.T0.26.teacher_ece` | 0.0393 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].teacher_ece` | 4dp |
| `tab_human.T0.26.student_ece_mean` | 0.0587 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].ece[0]` | 4dp |
| `tab_human.T0.26.student_ece_sd` | 0.0038 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].ece[1]` | 4dp |
| `tab_human.T0.26.jsd_mean` | 0.0737 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].jsd[0]` | 4dp |
| `tab_human.T0.26.jsd_sd` | 0.0007 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].jsd[1]` | 4dp |
| `tab_human.T0.26.entropy` | 0.124 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].entropy` | 3dp |
| `tab_human.T0.5063.teacher_ece` | 0.0156 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].teacher_ece` | 4dp |
| `tab_human.T0.5063.student_ece_mean` | 0.0185 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].ece[0]` | 4dp |
| `tab_human.T0.5063.student_ece_sd` | 0.0016 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].ece[1]` | 4dp |
| `tab_human.T0.5063.jsd_mean` | 0.0587 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].jsd[0]` | 4dp |
| `tab_human.T0.5063.jsd_sd` | 0.0005 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].jsd[1]` | 4dp |
| `tab_human.T0.5063.entropy` | 0.255 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].entropy` | 3dp |
| `tab_human.T0.74.teacher_ece` | 0.0665 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].teacher_ece` | 4dp |
| `tab_human.T0.74.student_ece_mean` | 0.0344 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].ece[0]` | 4dp |
| `tab_human.T0.74.student_ece_sd` | 0.0012 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].ece[1]` | 4dp |
| `tab_human.T0.74.jsd_mean` | 0.0536 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].jsd[0]` | 4dp |
| `tab_human.T0.74.jsd_sd` | 0.0004 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].jsd[1]` | 4dp |
| `tab_human.T0.74.entropy` | 0.384 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].entropy` | 3dp |
| `tab_human.T1.0.teacher_ece` | 0.1282 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].teacher_ece` | 4dp |
| `tab_human.T1.0.student_ece_mean` | 0.0783 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].ece[0]` | 4dp |
| `tab_human.T1.0.student_ece_sd` | 0.0046 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].ece[1]` | 4dp |
| `tab_human.T1.0.jsd_mean` | 0.0551 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].jsd[0]` | 4dp |
| `tab_human.T1.0.jsd_sd` | 0.0005 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].jsd[1]` | 4dp |
| `tab_human.T1.0.entropy` | 0.547 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].entropy` | 3dp |
| `tab_human.human_entropy` | 0.440 | `ferplus_jsd/ferplus_student_jsd.json` | `human_mean_entropy` | 3dp |
| `tab_pooled.swa.spearman_unsigned` | +0.789 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.spearman_abs_signed_gap` | 3dp |
| `tab_pooled.swa.pearson_unsigned` | +0.930 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.pearson_abs_signed_gap` | 3dp |
| `tab_pooled.swa.spearman_signed` | -0.407 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.spearman_signed_gap` | 3dp |
| `tab_pooled.best.spearman_unsigned` | +0.895 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.best.spearman_abs_signed_gap` | 3dp |
| `tab_pooled.best.pearson_unsigned` | +0.970 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.best.pearson_abs_signed_gap` | 3dp |
| `tab_pooled.best.spearman_signed` | -0.560 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.best.spearman_signed_gap` | 3dp |
| `tab_pooled.last.spearman_unsigned` | +0.877 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.last.spearman_abs_signed_gap` | 3dp |
| `tab_pooled.last.pearson_unsigned` | +0.948 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.last.pearson_abs_signed_gap` | 3dp |
| `tab_pooled.last.spearman_signed` | -0.534 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.last.spearman_signed_gap` | 3dp |
| `tab_capacity.scratch w050.acc_mean` | 86.15 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w050"].acc_mean` | 2dp |
| `tab_capacity.scratch w050.acc_sd` | 0.07 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w050"].acc_sd` | 2dp |
| `tab_capacity.scratch w050.ece_mean` | 0.0365 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w050"].ece_mean` | 4dp |
| `tab_capacity.scratch w050.ece_sd` | 0.0057 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w050"].ece_sd` | 4dp |
| `tab_capacity.scratch w075.acc_mean` | 87.31 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w075"].acc_mean` | 2dp |
| `tab_capacity.scratch w075.acc_sd` | 0.08 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w075"].acc_sd` | 2dp |
| `tab_capacity.scratch w075.ece_mean` | 0.0388 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w075"].ece_mean` | 4dp |
| `tab_capacity.scratch w075.ece_sd` | 0.0042 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w075"].ece_sd` | 4dp |
| `tab_capacity.scratch w100ns.acc_mean` | 88.09 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w100ns"].acc_mean` | 2dp |
| `tab_capacity.scratch w100ns.acc_sd` | 0.15 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w100ns"].acc_sd` | 2dp |
| `tab_capacity.scratch w100ns.ece_mean` | 0.0374 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w100ns"].ece_mean` | 4dp |
| `tab_capacity.scratch w100ns.ece_sd` | 0.0030 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["scratch w100ns"].ece_sd` | 4dp |
| `tab_capacity.pretrained w100.acc_mean` | 89.95 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["pretrained w100"].acc_mean` | 2dp |
| `tab_capacity.pretrained w100.acc_sd` | 0.37 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["pretrained w100"].acc_sd` | 2dp |
| `tab_capacity.pretrained w100.ece_mean` | 0.0330 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["pretrained w100"].ece_mean` | 4dp |
| `tab_capacity.pretrained w100.ece_sd` | 0.0020 | `paper_tables/RESULTS_TABLES.json` | `T10_capacity_cells.swa["pretrained w100"].ece_sd` | 4dp |
| `tab_capacity.capacity_span` | 0.00235 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.swa.capacity_span` | 5dp |
| `tab_capacity.teacher_span` | 0.1780 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.swa.teacher_span` | 4dp |
| `tab_collapse.T·τ = 5.10.mean` | -0.0391 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 5.10"].mean` | 4dp |
| `tab_collapse.T·τ = 5.10.sd` | 0.0032 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 5.10"].sd` | 4dp |
| `tab_collapse.T·τ = 10.20.mean` | -0.0324 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 10.20"].mean` | 4dp |
| `tab_collapse.T·τ = 10.20.sd` | 0.0029 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 10.20"].sd` | 4dp |
| `tab_collapse.alpha0.1.seed42` | +0.0197 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.1"].by_seed["42"]` | 4dp |
| `tab_collapse.alpha0.1.seed1` | +0.0215 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.1"].by_seed["1"]` | 4dp |
| `tab_collapse.alpha0.1.seed43` | +0.0262 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.1"].by_seed["43"]` | 4dp |
| `tab_collapse.alpha0.1.mean` | +0.0224 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.1"].mean` | 4dp |
| `tab_collapse.alpha0.3.seed42` | +0.0297 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.3"].by_seed["42"]` | 4dp |
| `tab_collapse.alpha0.3.seed1` | +0.0296 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.3"].by_seed["1"]` | 4dp |
| `tab_collapse.alpha0.3.seed43` | +0.0317 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.3"].by_seed["43"]` | 4dp |
| `tab_collapse.alpha0.3.mean` | +0.0303 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.3"].mean` | 4dp |
| `tab_collapse.alpha0.5.seed42` | +0.0344 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.5"].by_seed["42"]` | 4dp |
| `tab_collapse.alpha0.5.seed1` | +0.0365 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.5"].by_seed["1"]` | 4dp |
| `tab_collapse.alpha0.5.seed43` | +0.0271 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.5"].by_seed["43"]` | 4dp |
| `tab_collapse.alpha0.5.mean` | +0.0327 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.5"].mean` | 4dp |
| `tab_collapse.alpha0.7.seed42` | -0.0071 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.7"].by_seed["42"]` | 4dp |
| `tab_collapse.alpha0.7.seed1` | +0.0003 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.7"].by_seed["1"]` | 4dp |
| `tab_collapse.alpha0.7.seed43` | -0.0007 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.7"].by_seed["43"]` | 4dp |
| `tab_collapse.alpha0.7.mean` | -0.0025 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.7"].mean` | 4dp |
| `tab_collapse.alpha0.9.seed42` | -0.0307 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.9"].by_seed["42"]` | 4dp |
| `tab_collapse.alpha0.9.seed1` | -0.0397 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.9"].by_seed["1"]` | 4dp |
| `tab_collapse.alpha0.9.seed43` | -0.0351 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.9"].by_seed["43"]` | 4dp |
| `tab_collapse.alpha0.9.mean` | -0.0352 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.9"].mean` | 4dp |
| `tab_collapse.threshold_2bar` | 0.0024 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][teacher=stage1][class_weight_mode=effective_number][axis=ece].mde_2sd` | 4dp |
| `tab_efficiency.teacher.params_m` | 58.334 | `paper_tables/efficiency_retention.json` | `teacher.params_m` | 3dp |
| `tab_efficiency.teacher.gmacs` | 8.483 | `paper_tables/efficiency_retention.json` | `teacher.flops_g` | 3dp |
| `tab_efficiency.teacher.size_mb` | 555.0 | `paper_tables/efficiency_retention.json` | `teacher.size_mb` | 1dp |
| `tab_efficiency.teacher.acc` | 91.82 | `paper_tables/efficiency_retention.json` | `teacher.acc` | 2dp |
| `tab_efficiency.student.params_m` | 2.248 | `paper_tables/efficiency_retention.json` | `student.params_m` | 3dp |
| `tab_efficiency.student.gmacs` | 0.329 | `paper_tables/efficiency_retention.json` | `student.flops_g` | 3dp |
| `tab_efficiency.student.size_mb` | 8.8 | `paper_tables/efficiency_retention.json` | `student.size_mb` | 1dp |
| `tab_efficiency.student.acc_mean` | 89.95 | `paper_tables/efficiency_retention.json` | `by_checkpoint.swa.acc_mean` | 2dp |
| `tab_efficiency.student.acc_sd` | 0.37 | `paper_tables/efficiency_retention.json` | `by_checkpoint.swa.acc_sd` | 2dp |
| `tab_efficiency.ratio.params` | 25.9 | `paper_tables/efficiency_retention.json` | `compression.params_ratio` | 1dp |
| `tab_efficiency.ratio.flops` | 25.8 | `paper_tables/efficiency_retention.json` | `compression.flops_ratio` | 1dp |
| `tab_efficiency.ratio.size` | 62.9 | `paper_tables/efficiency_retention.json` | `compression.size_ratio` | 1dp |
| `tab_efficiency.ratio.retention` | 98.0 | `paper_tables/efficiency_retention.json` | `headline.retention_pct_swa` | 1dp |
| `tab_efficiency.latency.cuda_b1` | 1.93 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cuda][batch=1][dtype=fp32].speedup` | 2dp |
| `tab_efficiency.latency.cuda_b32` | 3.91 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cuda][batch=32][dtype=fp32].speedup` | 2dp |
| `tab_efficiency.latency.cpu_b1` | 4.01 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cpu][batch=1][dtype=fp32].speedup` | 2dp |
| `tab_efficiency.latency.cpu_b32` | 4.43 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cpu][batch=32][dtype=fp32].speedup` | 2dp |
| `tab_efficiency.caption.flops_ratio` | 25.8 | `paper_tables/efficiency_retention.json` | `compression.flops_ratio` | 1dp |
| `tab_efficiency.caption.speedup_min` | 1.9 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cuda][batch=1][dtype=fp32].speedup` | 1dp |
| `tab_efficiency.caption.speedup_max` | 4.4 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cpu][batch=32][dtype=fp32].speedup` | 1dp |
| `tab_selection_audit.rafdb_best_last.d_acc_mean` | +0.77 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.mean` | 2dp |
| `tab_selection_audit.rafdb_best_last.d_acc_sd` | 0.43 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.sd` | 2dp |
| `tab_selection_audit.rafdb_best_last.d_ece_mean` | -0.0029 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_ece.mean` | 4dp |
| `tab_selection_audit.rafdb_best_last.d_ece_sd` | 0.0092 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_ece.sd` | 4dp |
| `tab_selection_audit.rafdb_best_last.n` | 131 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.n` | int |
| `tab_selection_audit.rafdb_best_swa.d_acc_mean` | +0.13 | `selection_audit/selection_gain.json` | `audit_deltas.c_best_minus_swa.d_acc.mean` | 2dp |
| `tab_selection_audit.rafdb_best_swa.d_acc_sd` | 0.26 | `selection_audit/selection_gain.json` | `audit_deltas.c_best_minus_swa.d_acc.sd` | 2dp |
| `tab_selection_audit.rafdb_best_swa.d_ece_mean` | -0.0006 | `selection_audit/selection_gain.json` | `audit_deltas.c_best_minus_swa.d_ece.mean` | 4dp |
| `tab_selection_audit.rafdb_best_swa.d_ece_sd` | 0.0118 | `selection_audit/selection_gain.json` | `audit_deltas.c_best_minus_swa.d_ece.sd` | 4dp |
| `tab_selection_audit.rafdb_best_swa.n` | 118 | `selection_audit/selection_gain.json` | `audit_deltas.c_best_minus_swa.n` | int |
| `tab_selection_audit.ferplus_best_last.d_acc_mean` | +0.50 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].acc_pp.mean` | 2dp |
| `tab_selection_audit.ferplus_best_last.d_acc_sd` | 0.21 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].acc_pp.sd` | 2dp |
| `tab_selection_audit.ferplus_best_last.d_ece_mean` | +0.0041 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.mean` | 4dp |
| `tab_selection_audit.ferplus_best_last.d_ece_sd` | 0.0074 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.sd` | 4dp |
| `tab_selection_audit.ferplus_best_last.n` | 12 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].acc_pp.n` | int |
| `tab_selection_audit.ferplus_best_swa.d_acc_mean` | +0.22 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.mean` | 2dp |
| `tab_selection_audit.ferplus_best_swa.d_acc_sd` | 0.21 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.sd` | 2dp |
| `tab_selection_audit.ferplus_best_swa.d_ece_mean` | +0.0069 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.mean` | 4dp |
| `tab_selection_audit.ferplus_best_swa.d_ece_sd` | 0.0088 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.sd` | 4dp |
| `tab_selection_audit.ferplus_best_swa.n` | 12 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.n` | int |
| `tab_selection_audit.order_stat.K50.mean` | +0.645 | `paper_tables/order_stat_trend.json` | `results["50"].a2_raw.mean` | 3dp |
| `tab_selection_audit.order_stat.K50.sd` | 0.203 | `paper_tables/order_stat_trend.json` | `results["50"].a2_raw.sd` | 3dp |
| `tab_selection_audit.order_stat.K50.n` | 131 | `paper_tables/order_stat_trend.json` | `results["50"].n_runs` | int |
| `tab_selection_audit.order_stat.K100.mean` | +0.764 | `paper_tables/order_stat_trend.json` | `results["100"].a2_raw.mean` | 3dp |
| `tab_selection_audit.order_stat.K100.sd` | 0.259 | `paper_tables/order_stat_trend.json` | `results["100"].a2_raw.sd` | 3dp |
| `tab_selection_audit.order_stat.K100.n` | 131 | `paper_tables/order_stat_trend.json` | `results["100"].n_runs` | int |
| `app_mde.cap.swa_min` | 0.0024 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_min` | 4dp |
| `app_mde.cap.swa_max` | 0.0067 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_max` | 4dp |
| `app_mde.cap.swa_pct_min` | 3.2 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_pct_min` | 1dp |
| `app_mde.cap.swa_pct_max` | 19.4 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_pct_max` | 1dp |
| `app_predecl.A2.lead_h` | 8 | `paper_tables/prereg_lead_audit.json` | `items.A2.lead_hours` | int_floor |
| `app_predecl.A8.lead_h` | 12 | `paper_tables/prereg_lead_audit.json` | `items.A8.lead_hours` | int_floor |
| `app_predecl.A9.lead_s` | 108 | `paper_tables/prereg_lead_audit.json` | `items.A9.lead_seconds` | int_floor |
| `abstract.pooled_rho` | 0.79 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.spearman_abs_signed_gap` | 2dp |
| `abstract.audit_n_runs` | 131 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.n` | int |
| `abstract.selection_inflation` | 0.77 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.mean` | 2dp |
| `abstract.asymmetry_min` | 1.8 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.min` | 1dp |
| `abstract.asymmetry_max` | 2.0 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.max` | 1dp |
| `abstract.logitstd_noise_median` | 27 | `paper_tables/noise_units.json` | `summary.median` | int |
| `app_tstar.stage1.T_star_nll` | 1.349 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 3dp |
| `app_tstar.stage1.T_star_ece` | 1.320 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_ece` | 3dp |
| `app_tstar.stage1.d_ece` | +0.0015 | `paper_tables/tstar_sensitivity.json` | `results.stage1.d_ece` | 4dp |
| `app_tstar.stage1.ece_removed_by_ts` | +0.0220 | `paper_tables/tstar_sensitivity.json` | `results.stage1.ece_removed_by_ts` | 4dp |
| `app_tstar.primary.T_star_nll` | 1.261 | `paper_tables/tstar_sensitivity.json` | `results.primary.T_star_nll` | 3dp |
| `app_tstar.primary.T_star_ece` | 1.244 | `paper_tables/tstar_sensitivity.json` | `results.primary.T_star_ece` | 3dp |
| `app_tstar.primary.d_ece` | +0.0015 | `paper_tables/tstar_sensitivity.json` | `results.primary.d_ece` | 4dp |
| `app_tstar.primary.ece_removed_by_ts` | +0.0199 | `paper_tables/tstar_sensitivity.json` | `results.primary.ece_removed_by_ts` | 4dp |
| `app_tstar.vae9182.T_star_nll` | 0.983 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 3dp |
| `app_tstar.vae9182.T_star_ece` | 1.057 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_ece` | 3dp |
| `app_tstar.vae9182.d_ece` | +0.0043 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.d_ece` | 4dp |
| `app_tstar.vae9182.ece_removed_by_ts` | -0.0010 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.ece_removed_by_ts` | 4dp |
| `app_tstar.ferplus.T_star_nll` | 0.506 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 3dp |
| `app_tstar.ferplus.T_star_ece` | 0.453 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_ece` | 3dp |
| `app_tstar.ferplus.d_ece` | +0.0085 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.d_ece` | 4dp |
| `app_tstar.ferplus.ece_removed_by_ts` | +0.1126 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.ece_removed_by_ts` | 4dp |
| `app_tstar.caption.half_fold` | 1.3406 | `paper_tables/tstar_provenance.json` | `half_fold_fits.stage1` | 4dp |
| `app_tstar.caption.full_fold` | 1.3494 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 4dp |
| `app_tstar.caption.dense_step` | 0.005 | `paper_tables/tstar_sensitivity.json` | `dense_grid.step` | 3dp |
| `app_tstar.caption.dense_ece` | 0.0142 | `paper_tables/tstar_sensitivity.json` | `results.stage1.dense_grid_ece` | 4dp |
| `app_tstar.caption.dense_T` | 1.335 | `paper_tables/tstar_sensitivity.json` | `results.stage1.dense_grid_T` | 3dp |
| `app_jsd.(a) all rows.n` | 3153 | `paper_tables/jsd_sensitivity.json` | `results["(a) all rows"].n` | int |
| `app_jsd.(a) all rows.T_ece` | 0.46 | `paper_tables/jsd_sensitivity.json` | `results["(a) all rows"].T_ece` | 2dp |
| `app_jsd.(a) all rows.T_nll` | 0.50 | `paper_tables/jsd_sensitivity.json` | `results["(a) all rows"].T_nll` | 2dp |
| `app_jsd.(a) all rows.T_jsd` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(a) all rows"].T_jsd` | 2dp |
| `app_jsd.(b) vote sum = 10.n` | 1977 | `paper_tables/jsd_sensitivity.json` | `results["(b) vote sum = 10"].n` | int |
| `app_jsd.(b) vote sum = 10.T_ece` | 0.42 | `paper_tables/jsd_sensitivity.json` | `results["(b) vote sum = 10"].T_ece` | 2dp |
| `app_jsd.(b) vote sum = 10.T_nll` | 0.46 | `paper_tables/jsd_sensitivity.json` | `results["(b) vote sum = 10"].T_nll` | 2dp |
| `app_jsd.(b) vote sum = 10.T_jsd` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(b) vote sum = 10"].T_jsd` | 2dp |
| `app_jsd.(c) stratum 6-7.n` | 28 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 6-7"].n` | int |
| `app_jsd.(c) stratum 6-7.T_ece` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 6-7"].T_ece` | 2dp |
| `app_jsd.(c) stratum 6-7.T_nll` | 0.70 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 6-7"].T_nll` | 2dp |
| `app_jsd.(c) stratum 6-7.T_jsd` | 0.88 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 6-7"].T_jsd` | 2dp |
| `app_jsd.(c) stratum 8-9.n` | 1148 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 8-9"].n` | int |
| `app_jsd.(c) stratum 8-9.T_ece` | 0.46 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 8-9"].T_ece` | 2dp |
| `app_jsd.(c) stratum 8-9.T_nll` | 0.54 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 8-9"].T_nll` | 2dp |
| `app_jsd.(c) stratum 8-9.T_jsd` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 8-9"].T_jsd` | 2dp |
| `app_jsd.(c) stratum 10.n` | 1977 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 10"].n` | int |
| `app_jsd.(c) stratum 10.T_ece` | 0.42 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 10"].T_ece` | 2dp |
| `app_jsd.(c) stratum 10.T_nll` | 0.46 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 10"].T_nll` | 2dp |
| `app_jsd.(c) stratum 10.T_jsd` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 10"].T_jsd` | 2dp |
| `app_argmin.RAF-DB stage1.consensus_T` | 1.34 | `paper_tables/robustness_metrics.json` | `series["RAF-DB stage1"]._consensus_T` | 2dp |
| `app_argmin.RAF-DB stage1.metrics_agreeing` | 7 | `paper_tables/robustness_metrics.json` | `series["RAF-DB stage1"]._consensus_metrics_agreeing` | int |
| `app_argmin.RAF-DB stage1.n_metrics` | 7 | `paper_tables/robustness_metrics.json` | `series["RAF-DB stage1"]._n_metrics` | int |
| `app_argmin.RAF-DB vae9182.consensus_T` | 1.00 | `paper_tables/robustness_metrics.json` | `series["RAF-DB vae9182"]._consensus_T` | 2dp |
| `app_argmin.RAF-DB vae9182.metrics_agreeing` | 7 | `paper_tables/robustness_metrics.json` | `series["RAF-DB vae9182"]._consensus_metrics_agreeing` | int |
| `app_argmin.RAF-DB vae9182.n_metrics` | 7 | `paper_tables/robustness_metrics.json` | `series["RAF-DB vae9182"]._n_metrics` | int |
| `app_argmin.FERPlus.consensus_T` | 0.51 | `paper_tables/robustness_metrics.json` | `series["FERPlus"]._consensus_T` | 2dp |
| `app_argmin.FERPlus.metrics_agreeing` | 6 | `paper_tables/robustness_metrics.json` | `series["FERPlus"]._consensus_metrics_agreeing` | int |
| `app_argmin.FERPlus.n_metrics` | 7 | `paper_tables/robustness_metrics.json` | `series["FERPlus"]._n_metrics` | int |
| `app_argmin.FERPlus.nll_exception_modal` | 0.74 | `paper_tables/robustness_metrics.json` | `series["FERPlus"].metrics.nll.argmin_T_modal` | 2dp |
| `robust.ferplus_nll_argmin_all_seeds` | 0.74 | `paper_tables/robustness_metrics.json` | `series["FERPlus"].metrics.nll.argmin_T_all_seeds` | 2dp |
| `robust.total_runs` | 42 | `paper_tables/robustness_metrics.json` | `total_runs` | int |
| `robust.total_runs_2` | 42 | `paper_tables/robustness_metrics.json` | `total_runs` | int |
| `robust.total_steps` | 231 | `paper_tables/robustness_metrics.json` | `total_steps` | int |
| `robust.max_criterion_cost` | 0.0085 | `paper_tables/tstar_sensitivity.json` | `max_d_ece` | 4dp |
| `robust.control_T_nll` | 0.98 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 2dp |
| `robust.control_T_ece` | 1.06 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_ece` | 2dp |
| `robust.bootstrap_B` | 2000 | `paper_tables/bootstrap_cis.json` | `B` | int |
| `robust.headroom.stage1.point.headroom_eq8` | +0.0232 | `paper_tables/bootstrap_cis.json` | `results.stage1.point.headroom_eq8` | 4dp |
| `robust.headroom.stage1.ci95.headroom_eq8[0]` | +0.0151 | `paper_tables/bootstrap_cis.json` | `results.stage1.ci95.headroom_eq8[0]` | 4dp |
| `robust.headroom.stage1.ci95.headroom_eq8[1]` | +0.0305 | `paper_tables/bootstrap_cis.json` | `results.stage1.ci95.headroom_eq8[1]` | 4dp |
| `robust.headroom.primary.point.headroom_eq8` | +0.0213 | `paper_tables/bootstrap_cis.json` | `results.primary.point.headroom_eq8` | 4dp |
| `robust.headroom.primary.ci95.headroom_eq8[0]` | +0.0154 | `paper_tables/bootstrap_cis.json` | `results.primary.ci95.headroom_eq8[0]` | 4dp |
| `robust.headroom.primary.ci95.headroom_eq8[1]` | +0.0280 | `paper_tables/bootstrap_cis.json` | `results.primary.ci95.headroom_eq8[1]` | 4dp |
| `robust.headroom.vae9182.point.headroom_eq8` | +0.0023 | `paper_tables/bootstrap_cis.json` | `results.vae9182.point.headroom_eq8` | 4dp |
| `robust.headroom.vae9182.ci95.headroom_eq8[0]` | +0.0000 | `paper_tables/bootstrap_cis.json` | `results.vae9182.ci95.headroom_eq8[0]` | 4dp |
| `robust.headroom.vae9182.ci95.headroom_eq8[1]` | +0.0080 | `paper_tables/bootstrap_cis.json` | `results.vae9182.ci95.headroom_eq8[1]` | 4dp |
| `robust.headroom.ferplus.point` | +0.1126 | `paper_tables/headroom_grid_audit.json` | `grids.run.headroom` | 4dp |
| `robust.headroom.ferplus.ci_lo` | +0.1018 | `paper_tables/headroom_grid_audit.json` | `grids.run.ci95[0]` | 4dp |
| `robust.headroom.ferplus.ci_hi` | +0.1165 | `paper_tables/headroom_grid_audit.json` | `grids.run.ci95[1]` | 4dp |
| `robust.dense_grid.lo` | 0.50 | `paper_tables/headroom_grid_audit.json` | `grids.boot.grid.lo` | 2dp |
| `robust.dense_grid.hi` | 2.50 | `paper_tables/headroom_grid_audit.json` | `grids.boot.grid.hi` | 2dp |
| `robust.dense_grid.step` | 0.02 | `paper_tables/headroom_grid_audit.json` | `grids.boot.grid.step` | 2dp |
| `robust.ferplus_fine_argmin` | 0.46 | `paper_tables/headroom_grid_audit.json` | `grids.fine.T_argmin` | 2dp |
| `robust.ferplus_deployed_arm` | 0.5063 | `paper_tables/headroom_grid_audit.json` | `grids.run.T_argmin` | 4dp |
| `robust.jsd_optimum` | 0.74 | `paper_tables/jsd_sensitivity.json` | `T_jsd_values_across_slices[0]` | 2dp |
| `robust.smallest_stratum_n` | 28 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 6-7"].n` | int |
| `intro.pooled_n_points` | 14 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.n_points` | int |
| `intro.pooled_rho` | 0.79 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.spearman_abs_signed_gap` | 2dp |
| `intro.asym_rafdb` | 1.77 | `paper_tables/asymmetry_estimand.json` | `comparisons[2].ratio_absolute` | 2dp |
| `intro.asym_ferplus` | 2.04 | `paper_tables/asymmetry_estimand.json` | `comparisons[5].ratio_absolute` | 2dp |
| `intro.logitstd_dece_min` | 0.086 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|primary"].d_ece_mean` | 3dp |
| `intro.logitstd_dece_max` | 0.139 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|vae9182"].d_ece_mean` | 3dp |
| `intro.logitstd_noise_median` | 27 | `paper_tables/noise_units.json` | `summary.median` | int |
| `intro.tstar_ece_ferplus` | 0.45 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_ece` | 2dp |
| `intro.tstar_jsd_ferplus` | 0.74 | `ferplus_jsd/ferplus_jsd.json` | `T_star_jsd.T` | 2dp |
| `intro.teacher_entropy_tjsd` | 0.412 | `ferplus_jsd/ferplus_jsd.json` | `entropy_correlation.T_jsd.teacher_mean_entropy` | 3dp |
| `intro.human_entropy` | 0.440 | `ferplus_jsd/ferplus_jsd.json` | `human_mean_entropy` | 3dp |
| `intro.audit_n_runs` | 131 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.n` | int |
| `intro.selection_inflation` | +0.77 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.mean` | 2dp |
| `intro.orderstat_k50` | +0.645 | `selection_audit/selection_gain.json` | `per_k["50"].a2_pure_order_statistic.mean` | 3dp |
| `intro.orderstat_k100` | +0.764 | `selection_audit/selection_gain.json` | `per_k["100"].a2_pure_order_statistic.mean` | 3dp |
| `intro.asymmetry_min` | 1.8 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.min` | 1dp |
| `intro.asymmetry_max` | 2.0 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.max` | 1dp |
| `intro.compression_ratio` | 25.9 | `paper_tables/efficiency_retention.json` | `compression.params_ratio` | 1dp |
| `intro.retention_swa` | 97.96 | `paper_tables/efficiency_retention.json` | `headline.retention_pct_swa` | 2dp |
| `intro.audit_n_runs_2` | 131 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.n` | int |
| `related_work.asymmetry_min` | 1.8 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.min` | 1dp |
| `related_work.asymmetry_max` | 2.0 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.max` | 1dp |
| `related_work.ferplus_tstar_ece` | 0.45 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_ece` | 2dp |
| `related_work.ferplus_tstar_jsd` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(a) all rows"].T_jsd` | 2dp |
| `related_work.selection_inflation` | +0.77 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.mean` | 2dp |
| `related_work.orderstat_k50` | +0.645 | `selection_audit/selection_gain.json` | `per_k["50"].a2_pure_order_statistic.mean` | 3dp |
| `related_work.orderstat_k100` | 0.764 | `paper_tables/order_stat_trend.json` | `results["100"].a2_raw.mean` | 3dp |
| `methodology.votes_below_ten_all_folds` | 29.3 | `paper_tables/ferplus_abstention_entropy.json` | `share_below_ten_all_folds` | 1dp |
| `results.jsd_student_ts` | 0.0545 | `paper_tables/student_ts_baseline.json` | `aggregate.jsd.student_ts[0]` | 4dp |
| `results.jsd_tstar_arm` | 0.0587 | `paper_tables/student_ts_baseline.json` | `aggregate.jsd.tstar_arm[0]` | 4dp |
| `results.ferplus_best_swa_ece` | +0.0069 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.mean` | 4dp |
| `meth.ferplus_deployed_arm_is_argmin` | 0.5063 | `paper_tables/headroom_grid_audit.json` | `grids.run.T_argmin` | 4dp |
| `meth.ferplus_run_grid_reduction` | 0.1126 | `paper_tables/headroom_grid_audit.json` | `grids.run.headroom` | 4dp |
| `meth.ferplus_fine_grid_n` | 196 | `paper_tables/headroom_grid_audit.json` | `grids.fine.grid.n` | int |
| `meth.ferplus_fine_grid_step` | 0.02 | `paper_tables/headroom_grid_audit.json` | `grids.fine.grid.step` | 2dp |
| `meth.ferplus_fine_argmin_T` | 0.46 | `paper_tables/headroom_grid_audit.json` | `grids.fine.T_argmin` | 2dp |
| `meth.ferplus_fine_headroom` | 0.1198 | `paper_tables/headroom_grid_audit.json` | `grids.fine.headroom` | 4dp |
| `meth.max_criterion_dT` | 0.074 | `paper_tables/tstar_sensitivity.json` | `max_abs_dT` | 3dp |
| `meth.max_criterion_cost` | 0.0085 | `paper_tables/tstar_sensitivity.json` | `max_d_ece` | 4dp |
| `meth.stage1_half_fold_fit` | 1.3406 | `paper_tables/tstar_provenance.json` | `half_fold_fits.stage1` | 4dp |
| `meth.stage1_full_fold_fit` | 1.3494 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 4dp |
| `meth.halfsplit_shift_rafdb_max` | 0.014 | `paper_tables/tstar_stability.json` | `results.primary.absdiff_nll_A_B` | 3dp |
| `meth.halfsplit_shift_ferplus` | 0.026 | `paper_tables/tstar_stability.json` | `results.ferplus.absdiff_nll_A_B` | 3dp |
| `meth.student_params_m` | 2.248 | `paper_tables/efficiency_retention.json` | `student.params_m` | 3dp |
| `meth.student_gmacs` | 0.329 | `paper_tables/efficiency_retention.json` | `student.flops_g` | 3dp |
| `meth.control_teacher_ece_T1` | 0.0136 | `paper_tables/headroom_review.json` | `rafdb_teachers.vae9182.ece_T1` | 4dp |
| `meth.control_tstar_nll` | 0.983 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 3dp |
| `meth.control_headroom_point` | +0.0023 | `paper_tables/bootstrap_cis.json` | `results.vae9182.point.headroom_eq8` | 4dp |
| `meth.control_headroom_ci_lo` | +0.0000 | `paper_tables/bootstrap_cis.json` | `results.vae9182.ci95.headroom_eq8[0]` | 4dp |
| `meth.control_headroom_ci_hi` | +0.0080 | `paper_tables/bootstrap_cis.json` | `results.vae9182.ci95.headroom_eq8[1]` | 4dp |
| `meth.stage1_headroom_point_boot` | +0.0232 | `paper_tables/bootstrap_cis.json` | `results.stage1.point.headroom_eq8` | 4dp |
| `meth.stage1_headroom_ci_lo` | +0.0151 | `paper_tables/bootstrap_cis.json` | `results.stage1.ci95.headroom_eq8[0]` | 4dp |
| `meth.stage1_headroom_ci_hi` | +0.0305 | `paper_tables/bootstrap_cis.json` | `results.stage1.ci95.headroom_eq8[1]` | 4dp |
| `meth.primary_headroom_point_boot` | +0.0213 | `paper_tables/bootstrap_cis.json` | `results.primary.point.headroom_eq8` | 4dp |
| `meth.primary_headroom_ci_lo` | +0.0154 | `paper_tables/bootstrap_cis.json` | `results.primary.ci95.headroom_eq8[0]` | 4dp |
| `meth.primary_headroom_ci_hi` | +0.0280 | `paper_tables/bootstrap_cis.json` | `results.primary.ci95.headroom_eq8[1]` | 4dp |
| `meth.stage1_tstar_nll_3dp` | 1.349 | `paper_tables/tstar_sensitivity.json` | `results.stage1.T_star_nll` | 3dp |
| `meth.stage1_headroom_eq8_review` | +0.022 | `paper_tables/headroom_review.json` | `rafdb_teachers.stage1.headroom_eq8` | 3dp |
| `meth.ferplus_signed_gap_T1` | -0.128 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].signed_gap` | 3dp |
| `meth.ferplus_tstar_nll_2dp` | 0.51 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 2dp |
| `meth.ferplus_run_headroom_3dp` | 0.113 | `paper_tables/headroom_grid_audit.json` | `grids.run.headroom` | 3dp |
| `meth.ferplus_fine_step_2` | 0.02 | `paper_tables/headroom_grid_audit.json` | `grids.fine.grid.step` | 2dp |
| `meth.ferplus_fine_headroom_3dp` | 0.120 | `paper_tables/headroom_grid_audit.json` | `grids.fine.headroom` | 3dp |
| `meth.ferplus_tstar_ece_3dp` | 0.453 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_ece` | 3dp |
| `meth.ferplus_tstar_ece_grid` | 0.46 | `paper_tables/headroom_grid_audit.json` | `ferplus_T_star_ece.fine_grid_argmin` | 2dp |
| `meth.ferplus_tstar_nll_3dp` | 0.506 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 3dp |
| `meth.ferplus_tstar_jsd` | 0.74 | `ferplus_jsd/ferplus_jsd.json` | `T_star_jsd.T` | 2dp |
| `meth.ferplus_tstar_jsd_2` | 0.74 | `ferplus_jsd/ferplus_jsd.json` | `T_star_jsd.T` | 2dp |
| `meth.teacher_entropy_at_tjsd` | 0.412 | `ferplus_jsd/ferplus_jsd.json` | `entropy_correlation.T_jsd.teacher_mean_entropy` | 3dp |
| `meth.human_mean_entropy` | 0.440 | `ferplus_jsd/ferplus_jsd.json` | `human_mean_entropy` | 3dp |
| `meth.entropy_pearson_T1` | 0.724 | `ferplus_jsd/ferplus_jsd.json` | `entropy_correlation.T1.pearson` | 3dp |
| `meth.entropy_pearson_Tjsd` | 0.711 | `ferplus_jsd/ferplus_jsd.json` | `entropy_correlation.T_jsd.pearson` | 3dp |
| `meth.ferplus_tstar_jsd_3` | 0.74 | `ferplus_jsd/ferplus_jsd.json` | `T_star_jsd.T` | 2dp |
| `s4.arch.teacher_params_m` | 58.3 | `paper_tables/efficiency_retention.json` | `teacher.params_m` | 1dp |
| `s4.arch.teacher_gmacs` | 8.48 | `paper_tables/efficiency_retention.json` | `teacher.flops_g` | 2dp |
| `s4.arch.student_params_m` | 2.248 | `paper_tables/efficiency_retention.json` | `student.params_m` | 3dp |
| `s4.arch.student_gmacs` | 0.329 | `paper_tables/efficiency_retention.json` | `student.flops_g` | 3dp |
| `s4.arch.student_size_mb` | 8.8 | `paper_tables/efficiency_retention.json` | `student.size_mb` | 1dp |
| `s4.audit.inclusion_n` | 131 | `paper_tables/audit_population.json` | `n_total` | int |
| `s4.crit.mde_pct_min` | 3 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_pct_min` | int |
| `s4.crit.mde_pct_max` | 19 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_pct_max` | int |
| `s4.eff.student_params_m` | 2.248 | `paper_tables/efficiency_retention.json` | `student.params_m` | 3dp |
| `s4.eff.student_gmacs` | 0.329 | `paper_tables/efficiency_retention.json` | `student.flops_g` | 3dp |
| `s4.eff.ratio_params` | 25.9 | `paper_tables/efficiency_retention.json` | `compression.params_ratio` | 1dp |
| `s4.eff.ratio_flops` | 25.8 | `paper_tables/efficiency_retention.json` | `compression.flops_ratio` | 1dp |
| `s4.eff.ratio_size` | 62.9 | `paper_tables/efficiency_retention.json` | `compression.size_ratio` | 1dp |
| `s4.eff.retention_swa` | 97.96 | `paper_tables/efficiency_retention.json` | `headline.retention_pct_swa` | 2dp |
| `s4.eff.retention_best` | 98.32 | `paper_tables/efficiency_retention.json` | `headline.retention_pct_best` | 2dp |
| `res.ferplus_tstar_ece` | 0.45 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_ece` | 2dp |
| `res.ferplus_tstar_nll` | 0.51 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 2dp |
| `res.ferplus_tstar_jsd` | 0.74 | `ferplus_jsd/ferplus_jsd.json` | `T_star_jsd.T` | 2dp |
| `res.teacher_entropy_tjsd` | 0.412 | `ferplus_jsd/ferplus_jsd.json` | `entropy_correlation.T_jsd.teacher_mean_entropy` | 3dp |
| `res.human_entropy` | 0.440 | `ferplus_jsd/ferplus_jsd.json` | `human_mean_entropy` | 3dp |
| `res.jsd_completerow_n` | 1977 | `paper_tables/jsd_sensitivity.json` | `results["(b) vote sum = 10"].n` | int |
| `res.tstar_jsd_slices` | 0.74 | `paper_tables/jsd_sensitivity.json` | `T_jsd_values_across_slices[0]` | 2dp |
| `res.student_ece_min` | 0.0185 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].ece[0]` | 4dp |
| `res.student_ece_min_sd` | 0.0016 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.5063"].ece[1]` | 4dp |
| `res.student_jsd_min` | 0.0536 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].jsd[0]` | 4dp |
| `res.student_jsd_min_sd` | 0.0004 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.74"].jsd[1]` | 4dp |
| `res.rho_min` | 0.667 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["0.26"].rho` | 3dp |
| `res.rho_max` | 0.704 | `ferplus_jsd/ferplus_student_jsd.json` | `by_checkpoint.swa["1.0"].rho` | 3dp |
| `res.jsd_span_raw` | 0.0201 | `paper_tables/jsd_collapse_audit.json` | `numerator.value` | 4dp |
| `res.jsd_seed_sd_mean` | 0.00050 | `paper_tables/jsd_collapse_audit.json` | `R_noise.seed_sd_by_convention["mean sd"]` | 5dp |
| `res.native_ece_raw` | 0.0783 | `paper_tables/r3w1_joint_optimum.json` | `arms["1.0"].ece_arm[0]` | 4dp |
| `res.native_ece_raw_sd` | 0.0046 | `paper_tables/r3w1_joint_optimum.json` | `arms["1.0"].ece_arm[1]` | 4dp |
| `res.native_ece_ts` | 0.0203 | `paper_tables/r3w1_joint_optimum.json` | `arms["1.0"].ece_ts[0]` | 4dp |
| `res.native_ece_ts_sd` | 0.0017 | `paper_tables/r3w1_joint_optimum.json` | `arms["1.0"].ece_ts[1]` | 4dp |
| `res.teacherside_ece` | 0.0185 | `paper_tables/r3w1_joint_optimum.json` | `arms["0.5063"].ece_arm[0]` | 4dp |
| `res.teacherside_ece_sd` | 0.0016 | `paper_tables/r3w1_joint_optimum.json` | `arms["0.5063"].ece_arm[1]` | 4dp |
| `res.tost_p` | 0.22 | `paper_tables/equivalence_tests.json` | `tests[unit=ECE].p_tost` | 2dp |
| `res.teacher_selection_gain_swa` | +0.35 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.per_checkpoint.by_ckpt.swa.cost_of_wrong_pick_pp` | 2dp |
| `res.ferplus_control_acc_sd` | 0.37 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.acc_sd` | 2dp |
| `res.student_T_lo` | 0.676 | `paper_tables/r3w1_joint_optimum.json` | `per_seed["1.0"]["43"].T_s[0]` | 3dp |
| `res.student_T_hi` | 0.723 | `paper_tables/r3w1_joint_optimum.json` | `per_seed["1.0"]["42"].T_s[1]` | 3dp |
| `res.corner_ece_min` | 0.0185 | `paper_tables/r3w1_joint_optimum.json` | `corner.ECE_min` | 4dp |
| `res.corner_jsd_min` | 0.0536 | `paper_tables/r3w1_joint_optimum.json` | `corner.JSD_min` | 4dp |
| `res.occ_native_ece` | 0.0203 | `paper_tables/r3w1_joint_optimum.json` | `occupancy["1.0"].ece` | 4dp |
| `res.occ_native_ece_sd` | 0.0017 | `paper_tables/r3w1_joint_optimum.json` | `occupancy["1.0"].ece_sd` | 4dp |
| `res.occ_native_jsd` | 0.0545 | `paper_tables/r3w1_joint_optimum.json` | `occupancy["1.0"].jsd` | 4dp |
| `res.occ_native_jsd_sd` | 0.0005 | `paper_tables/r3w1_joint_optimum.json` | `occupancy["1.0"].jsd_sd` | 4dp |
| `res.jsd_span_raw_2` | 0.0201 | `paper_tables/jsd_collapse_audit.json` | `numerator.value` | 4dp |
| `res.jsd_span_ts` | 0.00054 | `paper_tables/jsd_collapse_audit.json` | `R_collapse.denominator` | 5dp |
| `res.jsd_collapse_ratio` | 37 | `paper_tables/jsd_collapse_audit.json` | `R_collapse.value` | int |
| `res.gap_happiness_native` | +0.028 | `paper_tables/perclass_crossing.json` | `rows[cls=Happiness].gap_native` | 3dp |
| `res.n_happiness` | 1185 | `paper_tables/perclass_crossing.json` | `rows[cls=Happiness].n` | int |
| `res.gap_fear_native` | +0.305 | `paper_tables/perclass_crossing.json` | `rows[cls=Fear].gap_native` | 3dp |
| `res.n_fear` | 74 | `paper_tables/perclass_crossing.json` | `rows[cls=Fear].n` | int |
| `res.cross_happiness` | 1.46 | `paper_tables/perclass_crossing.json` | `rows[cls=Happiness].crossing_T` | 2dp |
| `res.cross_surprise` | 1.62 | `paper_tables/perclass_crossing.json` | `rows[cls=Surprise].crossing_T` | 2dp |
| `res.cross_sadness` | 1.70 | `paper_tables/perclass_crossing.json` | `rows[cls=Sadness].crossing_T` | 2dp |
| `res.cross_anger` | 1.82 | `paper_tables/perclass_crossing.json` | `rows[cls=Anger].crossing_T` | 2dp |
| `res.gap_disgust_T22` | +0.063 | `paper_tables/perclass_crossing.json` | `rows[cls=Disgust].gap_T22` | 3dp |
| `res.gap_happiness_T22` | -0.110 | `paper_tables/perclass_crossing.json` | `rows[cls=Happiness].gap_T22` | 3dp |
| `res.gap_neutral_T22` | -0.126 | `paper_tables/perclass_crossing.json` | `rows[cls=Neutral].gap_T22` | 3dp |
| `res.gap_sadness_native` | +0.087 | `paper_tables/perclass_crossing.json` | `rows[cls=Sadness].gap_native` | 3dp |
| `res.gap_surprise_native` | +0.066 | `paper_tables/perclass_crossing.json` | `rows[cls=Surprise].gap_native` | 3dp |
| `res.n_fear_2` | 74 | `paper_tables/perclass_crossing.json` | `rows[cls=Fear].n` | int |
| `res.audit_n_total` | 131 | `paper_tables/audit_population.json` | `n_total` | int |
| `res.audit_offstandard` | 28 | `paper_tables/audit_population.json` | `off_standard_count` | int |
| `res.audit_offstandard_pct` | 21 | `paper_tables/audit_population.json` | `off_standard_pct` | int |
| `res.selection_inflation` | +0.77 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.mean` | 2dp |
| `res.selection_inflation_sd` | 0.43 | `selection_audit/selection_gain.json` | `audit_deltas.b_best_minus_last.d_acc.sd` | 2dp |
| `res.selection_n_positive` | 129 | `selection_audit/selection_distribution.json` | `d_acc_pp.n_positive` | int |
| `res.selection_n_runs` | 131 | `selection_audit/selection_distribution.json` | `d_acc_pp.n` | int |
| `res.ferplus_selection_inflation` | +0.50 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].acc_pp.mean` | 2dp |
| `res.ferplus_selection_inflation_sd` | 0.21 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].acc_pp.sd` | 2dp |
| `res.orderstat_k50` | +0.645 | `selection_audit/selection_gain.json` | `per_k["50"].a2_pure_order_statistic.mean` | 3dp |
| `res.orderstat_k50_sd` | 0.203 | `selection_audit/selection_gain.json` | `per_k["50"].a2_pure_order_statistic.sd` | 3dp |
| `res.orderstat_k100` | +0.764 | `selection_audit/selection_gain.json` | `per_k["100"].a2_pure_order_statistic.mean` | 3dp |
| `res.orderstat_k100_sd` | 0.259 | `selection_audit/selection_gain.json` | `per_k["100"].a2_pure_order_statistic.sd` | 3dp |
| `res.orderstat_n_runs` | 131 | `selection_audit/selection_gain.json` | `per_k["100"].n_runs` | int |
| `res.orderstat_k50_detr` | +0.640 | `paper_tables/order_stat_trend.json` | `results["50"].a2_detrended.mean` | 3dp |
| `res.orderstat_k50_detr_sd` | 0.218 | `paper_tables/order_stat_trend.json` | `results["50"].a2_detrended.sd` | 3dp |
| `res.orderstat_k100_detr` | +0.728 | `paper_tables/order_stat_trend.json` | `results["100"].a2_detrended.mean` | 3dp |
| `res.orderstat_k100_detr_sd` | 0.238 | `paper_tables/order_stat_trend.json` | `results["100"].a2_detrended.sd` | 3dp |
| `res.window_drift_k100` | -0.015 | `paper_tables/order_stat_trend.json` | `results["100"].window_drift_pp.mean` | 3dp |
| `res.rafdb_ece_contrast` | -0.0029 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.mean` | 4dp |
| `res.rafdb_ece_contrast_sd` | 0.0092 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.sd` | 4dp |
| `res.rafdb_ece_contrast_n` | 131 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.n` | int |
| `res.rafdb_ece_contrast_se` | 0.0008 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.se` | 4dp |
| `res.rafdb_ece_contrast_t` | -3.57 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.t` | 2dp |
| `res.rafdb_ece_contrast_p` | 0.0005 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.p` | 4dp |
| `res.rafdb_ece_ci_lo` | -0.0045 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.ci_lo` | 4dp |
| `res.rafdb_ece_ci_hi` | -0.0013 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-last"].ece.ci_hi` | 4dp |
| `res.ferplus_ece_contrast` | +0.0041 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.mean` | 4dp |
| `res.ferplus_ece_contrast_sd` | 0.0074 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.sd` | 4dp |
| `res.ferplus_ece_contrast_n` | 12 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.n` | int |
| `res.ferplus_ece_contrast_se` | 0.0021 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.se` | 4dp |
| `res.ferplus_ece_contrast_t` | +1.90 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.t` | 2dp |
| `res.ferplus_ece_contrast_p` | 0.084 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-last"].ece.p` | 3dp |
| `res.rafdb_bestswa_acc` | +0.13 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].acc_pp.mean` | 2dp |
| `res.rafdb_bestswa_acc_se` | 0.024 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].acc_pp.se` | 3dp |
| `res.rafdb_bestswa_acc_t` | 5.4 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].acc_pp.t` | 1dp |
| `res.ferplus_bestswa_acc` | +0.22 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.mean` | 2dp |
| `res.ferplus_bestswa_acc_se` | 0.061 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.se` | 3dp |
| `res.ferplus_bestswa_acc_t` | 3.7 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.t` | 1dp |
| `res.ferplus_bestswa_acc_p` | 0.003 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].acc_pp.p` | 3dp |
| `res.rafdb_bestswa_ece` | -0.0006 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].ece.mean` | 4dp |
| `res.rafdb_bestswa_ece_se` | 0.0011 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].ece.se` | 4dp |
| `res.rafdb_bestswa_ece_t` | -0.53 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].ece.t` | 2dp |
| `res.rafdb_bestswa_ece_p` | 0.59 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].ece.p` | 2dp |
| `res.ferplus_bestswa_ece_sd` | 0.0088 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.sd` | 4dp |
| `res.ferplus_bestswa_ece_n` | 12 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.n` | int |
| `res.ferplus_bestswa_ece_se` | 0.0025 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.se` | 4dp |
| `res.ferplus_bestswa_ece_t` | +2.71 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.t` | 2dp |
| `res.ferplus_bestswa_ece_p` | 0.020 | `paper_tables/selection_audit_inference.json` | `datasets["FERPlus"].contrasts["best-swa"].ece.p` | 3dp |
| `res.student_params` | 2.248 | `paper_tables/efficiency_retention.json` | `student.params_m` | 3dp |
| `res.student_flops` | 0.329 | `paper_tables/efficiency_retention.json` | `student.flops_g` | 3dp |
| `res.teacher_params` | 58.334 | `paper_tables/efficiency_retention.json` | `teacher.params_m` | 3dp |
| `res.teacher_flops` | 8.483 | `paper_tables/efficiency_retention.json` | `teacher.flops_g` | 3dp |
| `res.params_ratio` | 25.9 | `paper_tables/efficiency_retention.json` | `compression.params_ratio` | 1dp |
| `res.flops_ratio` | 25.8 | `paper_tables/efficiency_retention.json` | `compression.flops_ratio` | 1dp |
| `res.size_ratio` | 62.9 | `paper_tables/efficiency_retention.json` | `compression.size_ratio` | 1dp |
| `res.retention_swa` | 97.96 | `paper_tables/efficiency_retention.json` | `by_checkpoint.swa.retention_pct` | 2dp |
| `res.retention_best` | 98.32 | `paper_tables/efficiency_retention.json` | `by_checkpoint.best.retention_pct` | 2dp |
| `res.speedup_gpu_b1` | 1.93 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cuda][batch=1][dtype=fp32].speedup` | 2dp |
| `res.speedup_gpu_b32` | 3.91 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cuda][batch=32][dtype=fp32].speedup` | 2dp |
| `res.speedup_cpu_b1` | 4.01 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cpu][batch=1][dtype=fp32].speedup` | 2dp |
| `res.speedup_cpu_b32` | 4.43 | `p5_efficiency/latency_benchmark.json` | `speedups[device=cpu][batch=32][dtype=fp32].speedup` | 2dp |
| `s5.tstar_stage1` | 1.34 | `paper_tables/tstar_provenance.json` | `half_fold_fits.stage1` | 2dp |
| `s5.teacher_ece_T1` | 0.0378 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].teacher_ece` | 4dp |
| `s5.teacher_ece_Tstar` | 0.0159 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].teacher_ece` | 4dp |
| `s5.stu_ece_T1` | 0.0731 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.swa.ece_mean` | 4dp |
| `s5.stu_ece_T1_sd` | 0.0012 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[1].by_ckpt.swa.ece_sd` | 4dp |
| `s5.stu_ece_Tstar` | 0.0428 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.ece_mean` | 4dp |
| `s5.stu_ece_Tstar_sd` | 0.0003 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.ece_sd` | 4dp |
| `s5.stu_ece_T22` | 0.1008 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.swa.ece_mean` | 4dp |
| `s5.stu_ece_T22_sd` | 0.0025 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[4].by_ckpt.swa.ece_sd` | 4dp |
| `s5.spread_min` | 0.0003 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.ece_sd` | 4dp |
| `s5.spread_max` | 0.0029 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.swa.ece_sd` | 4dp |
| `s5.acc_lo` | 89.43 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[3].by_ckpt.swa.acc_mean` | 2dp |
| `s5.acc_hi` | 89.73 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_stage1.points[2].by_ckpt.swa.acc_mean` | 2dp |
| `s5.tstar_stage1_est` | 1.34 | `paper_tables/tstar_provenance.json` | `half_fold_fits.stage1` | 2dp |
| `s5.tstar_ferplus_est` | 0.51 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 2dp |
| `s5.ferplus_nll_argmin` | 0.74 | `paper_tables/robustness_metrics.json` | `series["FERPlus"].metrics.nll.argmin_T_all_seeds` | 2dp |
| `s5.ctrl_teacher_ece` | 0.0136 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].teacher_ece` | 4dp |
| `s5.ctrl_tstar` | 0.98 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 2dp |
| `s5.ctrl_ece_T1` | 0.0330 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_mean` | 4dp |
| `s5.ctrl_ece_T1_sd` | 0.0020 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[1].by_ckpt.swa.ece_sd` | 4dp |
| `s5.ctrl_ece_085` | 0.0447 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[0].by_ckpt.swa.ece_mean` | 4dp |
| `s5.ctrl_ece_134` | 0.0647 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[2].by_ckpt.swa.ece_mean` | 4dp |
| `s5.ctrl_ece_170` | 0.1282 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[3].by_ckpt.swa.ece_mean` | 4dp |
| `s5.ctrl_ece_220` | 0.2109 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_mean` | 4dp |
| `s5.ctrl_ece_220_sd` | 0.0034 | `p1_dose_response/two_dataset_overlay.json` | `arms.rafdb_vae9182.points[4].by_ckpt.swa.ece_sd` | 4dp |
| `s5.ctrl_ratio_085` | 5.9 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["0.85"].ratio` | 1dp |
| `s5.ctrl_ratio_134` | 15.9 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["1.3406"].ratio` | 1dp |
| `s5.ctrl_tstar_nll` | 0.983 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_nll` | 3dp |
| `s5.ctrl_tstar_ece` | 1.057 | `paper_tables/tstar_sensitivity.json` | `results.vae9182.T_star_ece` | 3dp |
| `s5.ref095_mean` | -0.0033 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["0.95"].mean` | 4dp |
| `s5.ref095_sd` | 0.0042 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["0.95"].sd` | 4dp |
| `s5.ref095_ratio` | 1.68 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["0.95"].ratio` | 2dp |
| `s5.ref110_mean` | +0.0020 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["1.1"].mean` | 4dp |
| `s5.ref110_sd` | 0.0045 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["1.1"].sd` | 4dp |
| `s5.ref110_ratio` | 0.98 | `paper_tables/control_grid_refinement.json` | `gaps_vs_T1["1.1"].ratio` | 2dp |
| `s5.ref095_ece` | 0.0296 | `paper_tables/control_grid_refinement.json` | `series["0.95"].ece_mean` | 4dp |
| `s5.ref100_ece` | 0.0330 | `paper_tables/control_grid_refinement.json` | `series["1.0"].ece_mean` | 4dp |
| `s5.miscal_seed1` | +0.0011 | `adaptive_t_headroom/adaptive_t_headroom.json` | `block_b_miscalibration_causal.d_ece_all[0]` | 4dp |
| `s5.miscal_seed2` | -0.0053 | `adaptive_t_headroom/adaptive_t_headroom.json` | `block_b_miscalibration_causal.d_ece_all[1]` | 4dp |
| `s5.miscal_mean` | -0.0021 | `adaptive_t_headroom/adaptive_t_headroom.json` | `block_b_miscalibration_causal.d_ece_mean` | 4dp |
| `s5.miscal_sd` | 0.0045 | `adaptive_t_headroom/adaptive_t_headroom.json` | `block_b_miscalibration_causal.d_ece_sd` | 4dp |
| `s5.fer_teacher_ece` | 0.1282 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].teacher_ece` | 4dp |
| `s5.fer_signed_gap` | -0.1277 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].signed_gap` | 4dp |
| `s5.fer_tstar` | 0.51 | `paper_tables/tstar_sensitivity.json` | `results.ferplus.T_star_nll` | 2dp |
| `s5.fer_ece_T1` | 0.0783 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.ece_mean` | 4dp |
| `s5.fer_ece_T1_sd` | 0.0046 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[3].by_ckpt.swa.ece_sd` | 4dp |
| `s5.fer_ece_Tstar` | 0.0185 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.swa.ece_mean` | 4dp |
| `s5.fer_ece_Tstar_sd` | 0.0016 | `p1_dose_response/two_dataset_overlay.json` | `arms.ferplus.points[1].by_ckpt.swa.ece_sd` | 4dp |
| `s5.fer_d_pooled` | 17.4 | `paper_tables/inferential_tests.json` | `ferplus_effect.d_pooled` | 1dp |
| `s5.fer_dz` | 18.3 | `paper_tables/inferential_tests.json` | `ferplus_effect.d_z_paired` | 1dp |
| `s5.fer_pholm` | 0.003 | `paper_tables/inferential_tests.json` | `results[5].p_holm` | 3dp |
| `s5.pooled_n1` | 14 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.n_points` | int |
| `s5.pooled_rho_swa` | 0.789 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.spearman_abs_signed_gap` | 3dp |
| `s5.pooled_rho_best` | 0.895 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.best.spearman_abs_signed_gap` | 3dp |
| `s5.pooled_rho_last` | 0.877 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.last.spearman_abs_signed_gap` | 3dp |
| `s5.pooled_n2` | 14 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.n_points` | int |
| `s5.pooled_n3` | 14 | `paper_tables/bootstrap_cis.json` | `results.pooled_rho.n_points` | int |
| `s5.boot_rho` | 0.789 | `paper_tables/bootstrap_cis.json` | `results.pooled_rho.point` | 3dp |
| `s5.boot_lo` | 0.577 | `paper_tables/bootstrap_cis.json` | `results.pooled_rho.ci95_cluster_bootstrap[0]` | 3dp |
| `s5.boot_hi` | 1.000 | `paper_tables/bootstrap_cis.json` | `results.pooled_rho.ci95_cluster_bootstrap[1]` | 3dp |
| `s5.pooled_signed` | -0.407 | `p1_dose_response/two_dataset_overlay.json` | `pooled_stats.swa.spearman_signed_gap` | 3dp |
| `s5.collapse_510_mean` | -0.0391 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 5.10"].mean` | 4dp |
| `s5.collapse_510_sd` | 0.0032 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 5.10"].sd` | 4dp |
| `s5.collapse_1020_mean` | -0.0324 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 10.20"].mean` | 4dp |
| `s5.collapse_1020_sd` | 0.0029 | `paper_tables/RESULTS_TABLES.json` | `T11_collapse.pairs["T·τ = 10.20"].sd` | 4dp |
| `s5.tau_at_T170_mean` | +0.0042 | `paper_tables/tau_t_factorial.json` | `marginal_contrasts[0].d_ece_mean` | 4dp |
| `s5.tau_at_T170_sd` | 0.0028 | `paper_tables/tau_t_factorial.json` | `marginal_contrasts[0].d_ece_sd` | 4dp |
| `s5.tau_at_T085_mean` | -0.0025 | `paper_tables/tau_t_factorial.json` | `marginal_contrasts[2].d_ece_mean` | 4dp |
| `s5.tau_at_T085_sd` | 0.0044 | `paper_tables/tau_t_factorial.json` | `marginal_contrasts[2].d_ece_sd` | 4dp |
| `s5.T_at_tau6_mean` | -0.0349 | `paper_tables/tau_t_factorial.json` | `marginal_contrasts[1].d_ece_mean` | 4dp |
| `s5.T_at_tau6_sd` | 0.0045 | `paper_tables/tau_t_factorial.json` | `marginal_contrasts[1].d_ece_sd` | 4dp |
| `s5.alpha05_gap` | +0.0327 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.5"].mean` | 4dp |
| `s5.alpha09_gap` | -0.0352 | `paper_tables/RESULTS_TABLES.json` | `T12_alpha.gaps["0.9"].mean` | 4dp |
| `s5.asym_rafdb` | 1.77 | `paper_tables/asymmetry_estimand.json` | `comparisons[2].ratio_absolute` | 2dp |
| `s5.asym_rafdb_lo` | 1.50 | `paper_tables/asymmetry_estimand.json` | `comparisons[2].ci_absolute[0]` | 2dp |
| `s5.asym_rafdb_hi` | 2.13 | `paper_tables/asymmetry_estimand.json` | `comparisons[2].ci_absolute[1]` | 2dp |
| `s5.asym_ferplus` | 2.04 | `paper_tables/asymmetry_estimand.json` | `comparisons[5].ratio_absolute` | 2dp |
| `s5.asym_ferplus_lo` | 1.64 | `paper_tables/asymmetry_estimand.json` | `comparisons[5].ci_absolute[0]` | 2dp |
| `s5.asym_ferplus_hi` | 2.48 | `paper_tables/asymmetry_estimand.json` | `comparisons[5].ci_absolute[1]` | 2dp |
| `s5.asym_min` | 1.8 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.min` | 1dp |
| `s5.asym_max` | 2.0 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.max` | 1dp |
| `s5.asym_six_mean` | 1.74 | `paper_tables/asymmetry_estimand.json` | `summary.all_six.absolute.mean` | 2dp |
| `s5.asym_six_sd` | 0.43 | `paper_tables/asymmetry_estimand.json` | `summary.all_six.absolute.sd` | 2dp |
| `s5.asym_ctrl1_lo` | 0.89 | `paper_tables/asymmetry_estimand.json` | `comparisons[3].ci_absolute[0]` | 2dp |
| `s5.asym_ctrl1_hi` | 2.19 | `paper_tables/asymmetry_estimand.json` | `comparisons[3].ci_absolute[1]` | 2dp |
| `s5.asym_ctrl2_lo` | 0.90 | `paper_tables/asymmetry_estimand.json` | `comparisons[4].ci_absolute[0]` | 2dp |
| `s5.asym_ctrl2_hi` | 1.46 | `paper_tables/asymmetry_estimand.json` | `comparisons[4].ci_absolute[1]` | 2dp |
| `s5.params_ratio` | 3.16 | `p5_efficiency/p5_efficiency.json` | `params_spread_ratio` | 2dp |
| `s5.capacity_span` | 0.00235 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.swa.capacity_span` | 5dp |
| `s5.teacher_span` | 0.1780 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.swa.teacher_span` | 4dp |
| `s5.lever_swa` | 76 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.swa.ratio` | int |
| `s5.lever_best` | 79 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.best.ratio` | int |
| `s5.lever_last` | 27 | `paper_tables/RESULTS_TABLES.json` | `T10_axis_spans.last.ratio` | int |
| `s5.lever_im_swa` | 69 | `paper_tables/g42_init_matched_lever.json` | `rows[0].ratio_init_matched` | int |
| `s5.lever_im_best` | 75 | `paper_tables/g42_init_matched_lever.json` | `rows[1].ratio_init_matched` | int |
| `s5.lever_im_last` | 26 | `paper_tables/g42_init_matched_lever.json` | `rows[2].ratio_init_matched` | int |
| `s5.head_dacc` | -0.02 | `vich_isolation/vich_isolation_verdict.json` | `paired_delta_linear_minus_vich.d_acc_mean` | 2dp |
| `s5.head_dacc_sd` | 0.11 | `vich_isolation/vich_isolation_verdict.json` | `paired_delta_linear_minus_vich.d_acc_sd` | 2dp |
| `s5.head_dece` | +0.0062 | `vich_isolation/vich_isolation_verdict.json` | `paired_delta_linear_minus_vich.d_ece_mean` | 4dp |
| `s5.head_dece_sd` | 0.0015 | `vich_isolation/vich_isolation_verdict.json` | `paired_delta_linear_minus_vich.d_ece_sd` | 4dp |
| `s5.head_pct` | 19 | `vich_isolation/vich_isolation_verdict.json` | `paired_delta_linear_minus_vich.ece_relative_reduction_pct` | int |
| `s5.cap_dslope` | -0.006 | `a13_scratch_dose/a13_verdict.json` | `comparisons[1].d_slope` | 3dp |
| `s5.cap_env` | 0.072 | `a13_scratch_dose/a13_verdict.json` | `comparisons[1].combined_envelope` | 3dp |
| `s5.init_dslope` | -0.067 | `a13_scratch_dose/a13_verdict.json` | `comparisons[0].d_slope` | 3dp |
| `s5.init_env` | 0.036 | `a13_scratch_dose/a13_verdict.json` | `comparisons[0].combined_envelope` | 3dp |
| `s5.conf_dslope` | +0.061 | `a13_scratch_dose/a13_verdict.json` | `comparisons[2].d_slope` | 3dp |
| `s5.conf_env` | 0.080 | `a13_scratch_dose/a13_verdict.json` | `comparisons[2].combined_envelope` | 3dp |
| `s5.slope_s0712` | 0.655 | `a13_scratch_dose/a13_verdict.json` | `fits.scratch0712.slope` | 3dp |
| `s5.slope_s2248` | 0.649 | `a13_scratch_dose/a13_verdict.json` | `fits.scratch2248.slope` | 3dp |
| `s5.slope_p2248` | 0.716 | `a13_scratch_dose/a13_verdict.json` | `fits.pretrained2248.slope` | 3dp |
| `s5.oracle_acc_stage1` | -0.22 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:oracle_error"].swa.acc.mean` | 2dp |
| `s5.oracle_acc_stage1_sd` | 0.46 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:oracle_error"].swa.acc.sd_paired` | 2dp |
| `s5.oracle_acc_primary` | -0.01 | `paper_tables/criterion_applied.json` | `cells["primary/gate:oracle_error"].swa.acc.mean` | 2dp |
| `s5.oracle_acc_primary_sd` | 0.72 | `paper_tables/criterion_applied.json` | `cells["primary/gate:oracle_error"].swa.acc.sd_paired` | 2dp |
| `s5.oracle_acc_vae` | -0.23 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.acc.mean` | 2dp |
| `s5.oracle_acc_vae_sd` | 0.49 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.acc.sd_paired` | 2dp |
| `s5.oracle_ece_vae` | +0.0056 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.ece.mean` | 4dp |
| `s5.oracle_ece_vae_sd` | 0.0040 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.ece.sd_paired` | 4dp |
| `s5.oracle_ece_vae_ratio` | 2.1 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.ece.ratio_vs_control_sd` | 1dp |
| `s5.oracle_acc_vae_ratio` | 1.10 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.acc.ratio_vs_control_sd` | 2dp |
| `s5.oracle_ece_vae_pratio` | 1.4 | `paper_tables/criterion_applied.json` | `cells["vae9182/gate:oracle_error"].swa.ece.ratio_vs_paired_sd` | 1dp |
| `s5.oracle_p` | 0.134 | `paper_tables/inferential_tests.json` | `results[4].p_raw` | 3dp |
| `s5.oracle_ece_stage1` | +0.0015 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:oracle_error"].swa.ece.mean` | 4dp |
| `s5.oracle_ece_stage1_sd` | 0.0036 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:oracle_error"].swa.ece.sd_paired` | 4dp |
| `s5.oracle_ece_primary` | +0.0004 | `paper_tables/criterion_applied.json` | `cells["primary/gate:oracle_error"].swa.ece.mean` | 4dp |
| `s5.oracle_ece_primary_sd` | 0.0053 | `paper_tables/criterion_applied.json` | `cells["primary/gate:oracle_error"].swa.ece.sd_paired` | 4dp |
| `s5.mde_pct_min` | 3.2 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_pct_min` | 1dp |
| `s5.mde_pct_max` | 19.4 | `paper_tables/control_sd_mde.json` | `mde_ece_swa_pct_max` | 1dp |
| `s5.ctrl_level_vae` | 0.028 | `paper_tables/control_sd_mde.json` | `rows[checkpoint=swa][axis=ece][teacher=vae9182][class_weight_mode=none].control_level` | 3dp |
| `s5.g2g_ece` | -0.0042 | `paper_tables/criterion_applied.json` | `cells["stage1/g2g_kl"].swa.ece.mean` | 4dp |
| `s5.g2g_ece_sd` | 0.0004 | `paper_tables/criterion_applied.json` | `cells["stage1/g2g_kl"].swa.ece.sd_paired` | 4dp |
| `s5.g2g_ratio` | 3.6 | `paper_tables/criterion_applied.json` | `cells["stage1/g2g_kl"].swa.ece.ratio_vs_control_sd` | 1dp |
| `s5.g2g_pratio` | 11.9 | `paper_tables/criterion_applied.json` | `cells["stage1/g2g_kl"].swa.ece.ratio_vs_paired_sd` | 1dp |
| `s5.adaptive_stage1` | -0.0011 | `paper_tables/criterion_applied.json` | `cells["stage1/adaptive_t"].swa.ece.mean` | 4dp |
| `s5.adaptive_stage1_sd` | 0.0033 | `paper_tables/criterion_applied.json` | `cells["stage1/adaptive_t"].swa.ece.sd_paired` | 4dp |
| `s5.adaptive_primary` | +0.0023 | `paper_tables/criterion_applied.json` | `cells["primary/adaptive_t"].swa.ece.mean` | 4dp |
| `s5.adaptive_primary_ratio` | 1.5 | `paper_tables/criterion_applied.json` | `cells["primary/adaptive_t"].swa.ece.ratio_vs_control_sd` | 1dp |
| `s5.adaptive_vae` | -0.0042 | `paper_tables/criterion_applied.json` | `cells["vae9182/adaptive_t"].swa.ece.mean` | 4dp |
| `s5.adaptive_vae_ratio` | 2.10 | `paper_tables/criterion_applied.json` | `cells["vae9182/adaptive_t"].swa.ece.ratio_vs_control_sd` | 2dp |
| `s5.auroc_vae` | 0.46 | `rafdb_signal_quality/signal_quality_table.json` | `[teacher=VAE9182][signal=target_logvar].auroc_signed` | 2dp |
| `s5.auroc_stage1` | 0.70 | `rafdb_signal_quality/signal_quality_table.json` | `[teacher=Stage1][signal=target_logvar].auroc_signed` | 2dp |
| `s5.auroc_primary` | 0.84 | `rafdb_signal_quality/signal_quality_table.json` | `[teacher=Primary][signal=target_logvar].auroc_signed` | 2dp |
| `s5.ls_acc_min` | -0.12 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|vae9182"].d_acc_mean` | 2dp |
| `s5.ls_acc_max` | -0.58 | `paper_tables/noise_units.json` | `nine_cell_grid["last|vae9182"].d_acc_mean` | 2dp |
| `s5.ls_ece_min` | +0.086 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|primary"].d_ece_mean` | 3dp |
| `s5.ls_ece_max` | +0.139 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|vae9182"].d_ece_mean` | 3dp |
| `s5.ls_ece_last` | +0.159 | `paper_tables/noise_units.json` | `nine_cell_grid["last|vae9182"].d_ece_mean` | 3dp |
| `s5.ls_acc_units` | 2.4 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|primary"].acc_units` | 1dp |
| `s5.ls_ece_units_min` | 57 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|primary"].ece_units` | int |
| `s5.ls_ece_units_max` | 77 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|stage1"].ece_units` | int |
| `s5.ls_ratio_median` | 27 | `paper_tables/noise_units.json` | `summary.median` | int |
| `s5.ls_ratio_swa_min` | 23 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|primary"].ratio` | int |
| `s5.ls_ratio_floor` | 2.6 | `paper_tables/noise_units.json` | `summary.min` | 1dp |
| `s5.ls_vae_dacc` | -0.12 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|vae9182"].d_acc_mean` | 2dp |
| `s5.ls_vae_sigma_acc` | 0.37 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|vae9182"].sigma_acc` | 2dp |
| `s5.ls_vae_ece_units` | 69 | `paper_tables/noise_units.json` | `nine_cell_grid["swa|vae9182"].ece_units` | int |
| `s5.ls_pholm` | 0.003 | `paper_tables/inferential_tests.json` | `results[2].p_holm` | 3dp |
| `s5.gate_near_miss` | 1.97 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:target_logvar"].swa.ece.ratio_vs_control_sd` | 2dp |
| `s5.gate_acc_ratio` | 2.51 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:target_logvar"].swa.acc.ratio_vs_control_sd` | 2dp |
| `s5.auroc_primary2` | 0.84 | `rafdb_signal_quality/signal_quality_table.json` | `[teacher=Primary][signal=target_logvar].auroc_signed` | 2dp |
| `s5.gate_smallest` | 0.23 | `paper_tables/criterion_applied.json` | `cells["primary/gate:target_logvar"].swa.ece.ratio_vs_control_sd` | 2dp |
| `s5.auroc_stage1_2` | 0.70 | `rafdb_signal_quality/signal_quality_table.json` | `[teacher=Stage1][signal=target_logvar].auroc_signed` | 2dp |
| `s5.teacher_acc_stage1` | 92.24 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].teacher_acc` | 2dp |
| `s5.teacher_acc_primary` | 92.01 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].teacher_acc` | 2dp |
| `s5.teacher_acc_vae` | 91.82 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].teacher_acc` | 2dp |
| `s5.teacher_ece_stage1` | 0.0378 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=stage1].teacher_ece` | 4dp |
| `s5.teacher_ece_primary` | 0.0396 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=primary].teacher_ece` | 4dp |
| `s5.teacher_ece_vae` | 0.0136 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.rows[teacher=vae9182].teacher_ece` | 4dp |
| `s5.rank_acc_swa` | -0.87 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.per_checkpoint.by_ckpt.swa.spearman_teacherACC_vs_studentACC` | 2dp |
| `s5.rank_acc_best` | -0.50 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.per_checkpoint.by_ckpt.best.spearman_teacherACC_vs_studentACC` | 2dp |
| `s5.rank_ece_swa` | +0.87 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.per_checkpoint.by_ckpt.swa.spearman_negTeacherECE_vs_studentACC` | 2dp |
| `s5.rank_ece_best` | +1.00 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.per_checkpoint.by_ckpt.best.spearman_negTeacherECE_vs_studentACC` | 2dp |
| `s5.tie_swa` | 89.60 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.per_checkpoint.by_ckpt.swa.student_acc.stage1` | 2dp |
| `s5.sel_cost_best` | 0.52 | `p4_teacher_selection/p4_teacher_selection.json` | `recipe_step3_ranking.cost_of_wrong_pick_pp` | 2dp |
| `s5.largest_mech_acc` | 0.41 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_acc_mean` | 2dp |
| `s4.rafdb_rows_total` | 15339 | `paper_tables/split_identity.json` | `datasets["RAF-DB"].rows_total` | int |
| `s4.rafdb_n_train` | 12271 | `paper_tables/split_identity.json` | `datasets["RAF-DB"].n_train` | int |
| `s4.rafdb_n_reporting` | 3068 | `paper_tables/split_identity.json` | `datasets["RAF-DB"].n_reporting` | int |
| `s4.ferplus_n_train` | 28259 | `paper_tables/split_identity.json` | `datasets["FERPlus"].n_train` | int |
| `s4.ferplus_n_reporting` | 3153 | `paper_tables/split_identity.json` | `datasets["FERPlus"].n_reporting` | int |
| `related_work.student_params_m` | 2.25 | `p5_efficiency/capacity_law_check.json` | `capacity_cells_at_T1.w100ns.params_m` | 2dp |
| `s4.fpr_per_cell` | 3.5 | `paper_tables/criterion_applied.json` | `false_positive_simulation.per_cell_rate_at_median_k` | percent_of_fraction:1dp |
| `s4.fpr_family_median_k` | 0.545 | `paper_tables/criterion_applied.json` | `false_positive_simulation.family_wise_at_median_k` | 3dp |
| `s4.fpr_family_own_k` | 0.741 | `paper_tables/criterion_applied.json` | `false_positive_simulation.family_wise_at_own_k` | 3dp |
| `s4.fpr_rho_shared` | +0.393 | `paper_tables/criterion_applied.json` | `false_positive_simulation.rho_shared_control` | 3dp |
| `s4.fpr_independence_gap` | 0.009 | `paper_tables/criterion_applied.json` | `false_positive_simulation.independence_gap_own_k_minus_shared` | 3dp |
| `s5.fpr_family_median_k_2dp` | 0.54 | `paper_tables/criterion_applied.json` | `false_positive_simulation.family_wise_at_median_k` | 2dp |
| `s5.fpr_family_own_k_2dp` | 0.74 | `paper_tables/criterion_applied.json` | `false_positive_simulation.family_wise_at_own_k` | 2dp |
| `s4.manifest_total` | 90 | `paper_tables/run_manifest_census.json` | `n_manifests` | int |
| `s4.manifest_verified` | 26 | `paper_tables/run_manifest_census.json` | `n_code_state_verified` | int |
| `s4.manifest_retroactive` | 62 | `paper_tables/run_manifest_census.json` | `n_retroactive_unverified` | int |
| `s4.manifest_unfinished` | 2 | `paper_tables/run_manifest_census.json` | `n_unfinished` | int |
| `s5.top_bin_raw` | 89.9 | `reliability/reliability_diagram.json` | `conditions["T=1"].top_bin.share_pct` | 1dp |
| `s5.top_bin_calibrated` | 82.7 | `reliability/reliability_diagram.json` | `conditions["T=1.3406"].top_bin.share_pct` | 1dp |
| `s5.target_logvar_dece` | -0.0041 | `paper_tables/criterion_applied.json` | `cells["stage1/gate:target_logvar"].swa.ece.mean` | 4dp |
| `s5.perclass_gap_fear_T22` | +0.165 | `reliability/perclass_calibration.json` | `classes.Fear.gap_mean[4]` | 3dp |
| `s5.argmax_in_k50` | 34 | `selection_audit/selection_gain.json` | `per_k["50"].argmax_in_last_K_frac` | percent_of_fraction:int |
| `s5.argmax_in_k100` | 67 | `selection_audit/selection_gain.json` | `per_k["100"].argmax_in_last_K_frac` | percent_of_fraction:int |
| `s5.best_swa_p_mantissa` | 4.3 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].acc_pp.p` | sci_mantissa:1dp |
| `s5.best_swa_p_exponent` | -7 | `paper_tables/selection_audit_inference.json` | `datasets["RAF-DB"].contrasts["best-swa"].acc_pp.p` | sci_exponent |
| `s4.ferplus_raw_fold0` | 28559 | `paper_tables/split_identity.json` | `datasets["FERPlus"].unfiltered_by_fold["0"]` | int |
| `s4.ferplus_raw_fold1` | 3579 | `paper_tables/split_identity.json` | `datasets["FERPlus"].unfiltered_by_fold["1"]` | int |
| `s4.ferplus_raw_fold2` | 3573 | `paper_tables/split_identity.json` | `datasets["FERPlus"].unfiltered_by_fold["2"]` | int |
| `s4.prereg_lead_max_h` | 12 | `paper_tables/prereg_lead_audit.json` | `items.A8.lead_hours` | int_floor |
| `meth.stage1_headroom_point_boot2` | +0.0232 | `paper_tables/bootstrap_cis.json` | `results.stage1.point.headroom_eq8` | 4dp |
| `s5.audit.growth_n116` | 116 | `selection_audit/selection_optimism_headline.json` | `stability_across_inclusion_sets.series[0].n` | int |
| `s5.audit.growth_n125` | 125 | `selection_audit/selection_optimism_headline.json` | `stability_across_inclusion_sets.series[1].n` | int |
| `s5.audit.growth_n131` | 131 | `selection_audit/selection_optimism_headline.json` | `stability_across_inclusion_sets.series[2].n` | int |
| `s5.audit.growth_span_pp` | 0.02 | `selection_audit/selection_optimism_headline.json` | `stability_across_inclusion_sets.span_pp` | 2dp |
| `tab_collapse.pair.tau3_T1.70.tau` | 3 | `paper_tables/tau_t_factorial.json` | `arms["tau3_T1.70"].tau` | int |
| `tab_collapse.pair.tau3_T1.70.T` | 1.70 | `paper_tables/tau_t_factorial.json` | `arms["tau3_T1.70"].T` | 2dp |
| `tab_collapse.pair.tau6_T0.85.tau` | 6 | `paper_tables/tau_t_factorial.json` | `arms["tau6_T0.85"].tau` | int |
| `tab_collapse.pair.tau6_T0.85.T` | 0.85 | `paper_tables/tau_t_factorial.json` | `arms["tau6_T0.85"].T` | 2dp |
| `tab_collapse.pair.tau6_T1.70.tau` | 6 | `paper_tables/tau_t_factorial.json` | `arms["tau6_T1.70"].tau` | int |
| `tab_collapse.pair.tau6_T1.70.T` | 1.70 | `paper_tables/tau_t_factorial.json` | `arms["tau6_T1.70"].T` | 2dp |
| `tab_collapse.pair.tau12_T0.85.tau` | 12 | `paper_tables/tau_t_factorial.json` | `arms["tau12_T0.85"].tau` | int |
| `tab_collapse.pair.tau12_T0.85.T` | 0.85 | `paper_tables/tau_t_factorial.json` | `arms["tau12_T0.85"].T` | 2dp |
| `tab_paired.stage1.adaptive_t.d_acc_mean` | +0.16 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_paired.stage1.adaptive_t.d_acc_sd` | 0.32 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/adaptive_t"].swa.d_acc_sd` | 2dp |
| `tab_paired.stage1.adaptive_t.d_ece_mean` | -0.0011 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_paired.stage1.adaptive_t.d_ece_sd` | 0.0033 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/adaptive_t"].swa.d_ece_sd` | 4dp |
| `tab_paired.stage1.g2g_kl.d_acc_mean` | +0.41 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_acc_mean` | 2dp |
| `tab_paired.stage1.g2g_kl.d_acc_sd` | 0.38 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_acc_sd` | 2dp |
| `tab_paired.stage1.g2g_kl.d_ece_mean` | -0.0042 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_ece_mean` | 4dp |
| `tab_paired.stage1.g2g_kl.d_ece_sd` | 0.0004 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/g2g_kl"].swa.d_ece_sd` | 4dp |
| `tab_paired.stage1.gate:mean_logvar.d_acc_mean` | -0.10 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_acc_mean` | 2dp |
| `tab_paired.stage1.gate:mean_logvar.d_acc_sd` | 0.12 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_acc_sd` | 2dp |
| `tab_paired.stage1.gate:mean_logvar.d_ece_mean` | -0.0012 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_ece_mean` | 4dp |
| `tab_paired.stage1.gate:mean_logvar.d_ece_sd` | 0.0010 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:mean_logvar"].swa.d_ece_sd` | 4dp |
| `tab_paired.stage1.gate:target_logvar.d_acc_mean` | +0.25 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_acc_mean` | 2dp |
| `tab_paired.stage1.gate:target_logvar.d_acc_sd` | 0.28 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_acc_sd` | 2dp |
| `tab_paired.stage1.gate:target_logvar.d_ece_mean` | -0.0041 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_ece_mean` | 4dp |
| `tab_paired.stage1.gate:target_logvar.d_ece_sd` | 0.0023 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:target_logvar"].swa.d_ece_sd` | 4dp |
| `tab_paired.stage1.gate:oracle_error.d_acc_mean` | -0.22 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_acc_mean` | 2dp |
| `tab_paired.stage1.gate:oracle_error.d_acc_sd` | 0.46 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_acc_sd` | 2dp |
| `tab_paired.stage1.gate:oracle_error.d_ece_mean` | +0.0015 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_ece_mean` | 4dp |
| `tab_paired.stage1.gate:oracle_error.d_ece_sd` | 0.0036 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/gate:oracle_error"].swa.d_ece_sd` | 4dp |
| `tab_paired.stage1.logit_std.d_acc_mean` | -0.23 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_paired.stage1.logit_std.d_acc_sd` | 0.20 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_acc_sd` | 2dp |
| `tab_paired.stage1.logit_std.d_ece_mean` | +0.0906 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_paired.stage1.logit_std.d_ece_sd` | 0.0023 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["stage1/logit_std"].swa.d_ece_sd` | 4dp |
| `tab_paired.primary.adaptive_t.d_acc_mean` | -0.39 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_paired.primary.adaptive_t.d_acc_sd` | 0.37 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/adaptive_t"].swa.d_acc_sd` | 2dp |
| `tab_paired.primary.adaptive_t.d_ece_mean` | +0.0023 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_paired.primary.adaptive_t.d_ece_sd` | 0.0007 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/adaptive_t"].swa.d_ece_sd` | 4dp |
| `tab_paired.primary.g2g_kl.d_acc_mean` | -0.14 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/g2g_kl"].swa.d_acc_mean` | 2dp |
| `tab_paired.primary.g2g_kl.d_acc_sd` | 0.36 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/g2g_kl"].swa.d_acc_sd` | 2dp |
| `tab_paired.primary.g2g_kl.d_ece_mean` | -0.0016 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/g2g_kl"].swa.d_ece_mean` | 4dp |
| `tab_paired.primary.g2g_kl.d_ece_sd` | 0.0027 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/g2g_kl"].swa.d_ece_sd` | 4dp |
| `tab_paired.primary.gate:mean_logvar.d_acc_mean` | +0.20 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_acc_mean` | 2dp |
| `tab_paired.primary.gate:mean_logvar.d_acc_sd` | 0.85 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_acc_sd` | 2dp |
| `tab_paired.primary.gate:mean_logvar.d_ece_mean` | -0.0056 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_ece_mean` | 4dp |
| `tab_paired.primary.gate:mean_logvar.d_ece_sd` | 0.0092 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:mean_logvar"].swa.d_ece_sd` | 4dp |
| `tab_paired.primary.gate:target_logvar.d_acc_mean` | -0.09 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_acc_mean` | 2dp |
| `tab_paired.primary.gate:target_logvar.d_acc_sd` | 0.44 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_acc_sd` | 2dp |
| `tab_paired.primary.gate:target_logvar.d_ece_mean` | -0.0008 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_ece_mean` | 4dp |
| `tab_paired.primary.gate:target_logvar.d_ece_sd` | 0.0030 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:target_logvar"].swa.d_ece_sd` | 4dp |
| `tab_paired.primary.gate:oracle_error.d_acc_mean` | -0.01 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_acc_mean` | 2dp |
| `tab_paired.primary.gate:oracle_error.d_acc_sd` | 0.72 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_acc_sd` | 2dp |
| `tab_paired.primary.gate:oracle_error.d_ece_mean` | +0.0004 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_ece_mean` | 4dp |
| `tab_paired.primary.gate:oracle_error.d_ece_sd` | 0.0053 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/gate:oracle_error"].swa.d_ece_sd` | 4dp |
| `tab_paired.primary.logit_std.d_acc_mean` | -0.32 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_paired.primary.logit_std.d_acc_sd` | 0.25 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_acc_sd` | 2dp |
| `tab_paired.primary.logit_std.d_ece_mean` | +0.0859 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_paired.primary.logit_std.d_ece_sd` | 0.0058 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["primary/logit_std"].swa.d_ece_sd` | 4dp |
| `tab_paired.vae9182.adaptive_t.d_acc_mean` | +0.28 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_acc_mean` | 2dp |
| `tab_paired.vae9182.adaptive_t.d_acc_sd` | 0.57 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_acc_sd` | 2dp |
| `tab_paired.vae9182.adaptive_t.d_ece_mean` | -0.0042 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_ece_mean` | 4dp |
| `tab_paired.vae9182.adaptive_t.d_ece_sd` | 0.0047 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/adaptive_t"].swa.d_ece_sd` | 4dp |
| `tab_paired.vae9182.g2g_kl.d_acc_mean` | +0.16 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_acc_mean` | 2dp |
| `tab_paired.vae9182.g2g_kl.d_acc_sd` | 0.41 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_acc_sd` | 2dp |
| `tab_paired.vae9182.g2g_kl.d_ece_mean` | +0.0009 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_ece_mean` | 4dp |
| `tab_paired.vae9182.g2g_kl.d_ece_sd` | 0.0043 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/g2g_kl"].swa.d_ece_sd` | 4dp |
| `tab_paired.vae9182.gate:mean_logvar.d_acc_mean` | -0.27 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_acc_mean` | 2dp |
| `tab_paired.vae9182.gate:mean_logvar.d_acc_sd` | 0.67 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_acc_sd` | 2dp |
| `tab_paired.vae9182.gate:mean_logvar.d_ece_mean` | +0.0015 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_ece_mean` | 4dp |
| `tab_paired.vae9182.gate:mean_logvar.d_ece_sd` | 0.0046 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:mean_logvar"].swa.d_ece_sd` | 4dp |
| `tab_paired.vae9182.gate:oracle_error.d_acc_mean` | -0.23 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_acc_mean` | 2dp |
| `tab_paired.vae9182.gate:oracle_error.d_acc_sd` | 0.49 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_acc_sd` | 2dp |
| `tab_paired.vae9182.gate:oracle_error.d_ece_mean` | +0.0056 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_ece_mean` | 4dp |
| `tab_paired.vae9182.gate:oracle_error.d_ece_sd` | 0.0040 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/gate:oracle_error"].swa.d_ece_sd` | 4dp |
| `tab_paired.vae9182.logit_std.d_acc_mean` | -0.12 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_acc_mean` | 2dp |
| `tab_paired.vae9182.logit_std.d_acc_sd` | 0.82 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_acc_sd` | 2dp |
| `tab_paired.vae9182.logit_std.d_ece_mean` | +0.1388 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_ece_mean` | 4dp |
| `tab_paired.vae9182.logit_std.d_ece_sd` | 0.0013 | `paper_tables/RESULTS_TABLES.json` | `T5_mechanisms["vae9182/logit_std"].swa.d_ece_sd` | 4dp |
| `s5.control_prereg_lead_s` | 20 | `paper_tables/prereg_lead_audit.json` | `items.A1.lead_seconds` | int_floor |
| `s57.ece_collapse_factor` | 6.4 | `paper_tables/ferplus_scaled_ece_axis.json` | `collapse.ece.factor` | 1dp |
| `s57.ece_spread_removed_pct` | 84.3 | `paper_tables/ferplus_scaled_ece_axis.json` | `removal.ece.spread_removed_frac` | percent_of_fraction:1dp |
| `s57.jsd_collapse_ref` | 37 | `paper_tables/ferplus_scaled_ece_axis.json` | `collapse.jsd.factor` | int |
| `s57.scaled_best_ece` | 0.0203 | `paper_tables/ferplus_scaled_ece_axis.json` | `scaled_best_arm.ts_ece[0]` | 4dp |
| `s57.scaled_worst_ece` | 0.0296 | `paper_tables/ferplus_scaled_ece_axis.json` | `scaled_worst_arm.ts_ece[0]` | 4dp |
| `s57.rafdb_removed_stage1` | 82 | `paper_tables/rafdb_student_ts_dose.json` | `collapse.stage1.spread_removed_frac` | percent_of_fraction:int |
| `s57.rafdb_removed_vae` | 90 | `paper_tables/rafdb_student_ts_dose.json` | `collapse.vae9182.spread_removed_frac` | percent_of_fraction:int |
| `s57.rafdb_stage1_scaled_best_T` | 1.3406 | `paper_tables/rafdb_student_ts_dose.json` | `seed_consistency.stage1.scaled_best_T` | 4dp |
| `s57.rafdb_residual_stage1` | 0.0103 | `paper_tables/rafdb_student_ts_dose.json` | `spans["stage1/ts"].span` | 4dp |
| `s57.rafdb_residual_vae` | 0.0187 | `paper_tables/rafdb_student_ts_dose.json` | `spans["vae9182/ts"].span` | 4dp |
| `s57.rafdb_tstar_native_gap` | 0.0011 | `paper_tables/rafdb_student_ts_dose.json` | `tstar_vs_native.stage1.gap_scaled` | 4dp |
| `s57.unscaled_control_sd` | 0.0046 | `paper_tables/ferplus_scaled_ece_axis.json` | `arms["1.0"].raw_ece[1]` | 4dp |
| `s11.tjsd_stratum67` | 0.88 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 6-7"].T_jsd` | 2dp |
| `s11.tjsd_stratum89` | 0.74 | `paper_tables/jsd_sensitivity.json` | `results["(c) stratum 8-9"].T_jsd` | 2dp |
| `s52.asymmetry_min_2dp` | 1.77 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.min` | 2dp |
| `s52.asymmetry_max_2dp` | 2.04 | `paper_tables/asymmetry_estimand.json` | `summary.interpolated_only.absolute.max` | 2dp |
