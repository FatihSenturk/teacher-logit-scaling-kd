# Üretici tazeliği — kapının yapısal kör noktası

> **Sorun:** `table_diff_gate` artefaktı kabul edilmiş temel çizgisiyle karşılaştırır, üreticinin taze çıktısıyla değil. "Üretici değişti, artefakt yeniden üretilmedi" durumu bu yüzden bütün kapılardan geçer. Bu kapı tam o durumu ölçer.

Üretici→artefakt eşlemesi `export_to_drive.EXPORTS`ten, Level-3 beyanı `level1_gate.ALLOWED`dan **ithal** edilir.

| | |
|---|---|
| denetlenen üretici | 71 |
| Katman A (koş + bayt karşılaştır) | 56 |
| Katman B (kaynak parmak izi) | 15 |
| **BAYAT** (artefakt üreticisinden geri) | **0** |
| **KAYNAK AYRIŞMASI** | **0** |
| ölçülemez (Katman B, artefakt commit'lenmemiş) | 0 |
| başka hata / zaman aşımı | 0 |
| beyansız yan çıktı yazan üretici | 1 |
| koşu başında zaten değişmiş dosya | 0 |

## Beyansız yan çıktı

Anlık kopya yalnız bandın BEYAN ETTİĞİ artefaktları kapsar. Aşağıdaki üreticiler koşunca beyan edilmemiş bir dosyayı daha değiştirdi; kapı bunları koşudan önce temiz olmaları koşuluyla `git checkout --` ile geri aldı, ama **bant beyanı ile üreticinin fiilî çıktısı ayrışıyor** demektir. Bir dosyanın bantta olmaması iki ayrı şey olabilir: unutulmuş olması, ya da bayt karşılaştırılamaz olması (ör. PDF'in `/CreationDate` damgası).

| üretici | beyansız yazdığı dosya |
|---|---|
| `diagnostics/selection_distribution_figure.py` | `paper/figures/selection_distribution.pdf` |

## Ölçülen süreler (Katman A adayları)

n=56 · min 0.1 s · medyan 0.2 s · maks 43.6 s · toplam 223 s · eşik **90 s**

En pahalı beş üretici:

| üretici | saniye |
|---|---|
| `diagnostics/criterion_applied.py` | 43.6 |
| `diagnostics/bootstrap_cis.py` | 38.3 |
| `diagnostics/headroom_grid_audit.py` | 25.6 |
| `diagnostics/teacher_ece_grid.py` | 24.7 |
| `diagnostics/tstar_sensitivity.py` | 7.2 |

## Katman B'nin SINIRI (peşinen)

Kaynak parmak izi yalnız **üretici değişti**yi görür. **Girdi verisi değişti**yi görmez: bir koşu eklenir, bir CSV tazelenir, bir logit önbelleği büyür — üreticinin kaynağı aynı kaldığı sürece bu kapı sessizdir. Katman A ikisini de görür. Aşağıdaki tabloda B satırındaki her artefakt, bu yarım korumayla duruyor demektir.

## Artefakt başına katman

| üretici | katman | neden | artefakt | durum |
|---|---|---|---|---|
| `diagnostics/a12_realsignal_verdict.py` | **A** | ölçülen süre 0.1 s | `diagnostics/a12_realsignal_gate/a12_verdict.md`<br>`diagnostics/a12_realsignal_gate/a12_verdict.json` | geçti |
| `diagnostics/a13_scratch_dose_verdict.py` | **A** | ölçülen süre 0.1 s | `diagnostics/a13_scratch_dose/a13_verdict.md`<br>`diagnostics/a13_scratch_dose/a13_verdict.json` | geçti |
| `diagnostics/asymmetry_estimand.py` | **A** | ölçülen süre 7.1 s | `diagnostics/paper_tables/asymmetry_estimand.md`<br>`diagnostics/paper_tables/asymmetry_estimand.json` | geçti |
| `diagnostics/audit_population.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/audit_population.md`<br>`diagnostics/paper_tables/audit_population.json` | geçti |
| `diagnostics/b015_verdict.py` | **A** | ölçülen süre 0.1 s | `diagnostics/selection_audit/b015_verdict.json` | geçti |
| `diagnostics/bootstrap_cis.py` | **A** | ölçülen süre 41.7 s | `diagnostics/paper_tables/bootstrap_cis.md`<br>`diagnostics/paper_tables/bootstrap_cis.json` | geçti |
| `diagnostics/capacity_law_check.py` | **A** | ölçülen süre 0.1 s | `diagnostics/p5_efficiency/capacity_law_check.json` | geçti |
| `diagnostics/control_sd_mde.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/control_sd_mde.md`<br>`diagnostics/paper_tables/control_sd_mde.json` | geçti |
| `diagnostics/criterion_applied.py` | **A** | ölçülen süre 0.6 s | `diagnostics/paper_tables/criterion_applied.md`<br>`diagnostics/paper_tables/criterion_applied.json` | geçti |
| `diagnostics/denominator_table.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/denominator_table.md`<br>`diagnostics/paper_tables/denominator_table.json` | geçti |
| `diagnostics/dose_response_per_seed.py` | **A** | ölçülen süre 5.3 s | `diagnostics/paper_tables/dose_response_per_seed.md`<br>`diagnostics/paper_tables/dose_response_per_seed.json` | geçti |
| `diagnostics/efficiency_retention.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/efficiency_retention.md`<br>`diagnostics/paper_tables/efficiency_retention.json` | geçti |
| `diagnostics/equivalence_tests.py` | **A** | ölçülen süre 0.6 s | `diagnostics/paper_tables/equivalence_tests.md`<br>`diagnostics/paper_tables/equivalence_tests.json` | geçti |
| `diagnostics/ferplus_abstention_entropy.py` | **A** | ölçülen süre 1.8 s | `diagnostics/paper_tables/ferplus_abstention_entropy.md`<br>`diagnostics/paper_tables/ferplus_abstention_entropy.json` | geçti |
| `diagnostics/ferplus_human_vote_jsd.py` | **A** | ölçülen süre 5.1 s | `diagnostics/ferplus_jsd/ferplus_jsd.json` | geçti |
| `diagnostics/ferplus_student_jsd.py` | **A** | ölçülen süre 4.7 s | `diagnostics/ferplus_jsd/ferplus_student_jsd.json`<br>`diagnostics/ferplus_jsd/ferplus_student_jsd_rows.json` | geçti |
| `diagnostics/g42_init_matched_lever.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/g42_init_matched_lever.md`<br>`diagnostics/paper_tables/g42_init_matched_lever.json` | geçti |
| `diagnostics/graphical_abstract.py` | **A** | ölçülen süre 0.8 s | `paper/figures/graphical_abstract.png` | geçti |
| `diagnostics/headroom_grid_audit.py` | **A** | ölçülen süre 31.1 s | `diagnostics/paper_tables/headroom_grid_audit.md`<br>`diagnostics/paper_tables/headroom_grid_audit.json` | geçti |
| `diagnostics/headroom_review.py` | **A** | ölçülen süre 0.0 s | `diagnostics/paper_tables/headroom_review.md`<br>`diagnostics/paper_tables/headroom_review.json` | geçti |
| `diagnostics/holm_family.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/holm_family.md`<br>`diagnostics/paper_tables/holm_family.json` | geçti |
| `diagnostics/inferential_tests.py` | **A** | ölçülen süre 0.6 s | `diagnostics/paper_tables/inferential_tests.md`<br>`diagnostics/paper_tables/inferential_tests.json` | geçti |
| `diagnostics/jsd_collapse_audit.py` | **A** | ölçülen süre 5.0 s | `diagnostics/paper_tables/jsd_collapse_audit.md`<br>`diagnostics/paper_tables/jsd_collapse_audit.json` | geçti |
| `diagnostics/jsd_sensitivity.py` | **A** | ölçülen süre 6.0 s | `diagnostics/paper_tables/jsd_sensitivity.md`<br>`diagnostics/paper_tables/jsd_sensitivity.json` | geçti |
| `diagnostics/mechanism_diagnostic_figure.py` | **A** | ölçülen süre 0.7 s | `diagnostics/paper_tables/mechanism_diagnostic.json`<br>`diagnostics/paper_tables/mechanism_diagnostic.png` | geçti |
| `diagnostics/mechanism_grid_gaps.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/mechanism_grid_gaps.md`<br>`diagnostics/paper_tables/mechanism_grid_gaps.json` | geçti |
| `diagnostics/mechanism_specs.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/mechanism_specs.md`<br>`diagnostics/paper_tables/mechanism_specs.json` | geçti |
| `diagnostics/monotonicity_test.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/monotonicity_test.md`<br>`diagnostics/paper_tables/monotonicity_test.json` | geçti |
| `diagnostics/noise_units.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/noise_units.md`<br>`diagnostics/paper_tables/noise_units.json` | geçti |
| `diagnostics/number_audit_round3.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/number_audit_round3.md`<br>`diagnostics/paper_tables/number_audit_round3.json` | geçti |
| `diagnostics/order_stat_trend.py` | **A** | ölçülen süre 0.2 s | `diagnostics/paper_tables/order_stat_trend.md`<br>`diagnostics/paper_tables/order_stat_trend.json` | geçti |
| `diagnostics/p2_gate_oracle_verdict.py` | **A** | ölçülen süre 0.1 s | `diagnostics/p2_gate_oracle/p2_verdict.md`<br>`diagnostics/p2_gate_oracle/p2_verdict.json` | geçti |
| `diagnostics/p4_teacher_selection_recipe.py` | **A** | ölçülen süre 0.1 s | `diagnostics/p4_teacher_selection/p4_teacher_selection.json` | geçti |
| `diagnostics/p5_oracle_replication_verdict.py` | **A** | ölçülen süre 0.1 s | `diagnostics/p5_oracle_replication/p5_verdict.md`<br>`diagnostics/p5_oracle_replication/p5_verdict.json` | geçti |
| `diagnostics/p6_verdict.py` | **A** | ölçülen süre 5.3 s | `diagnostics/paper_tables/p6_collapse_test.md`<br>`diagnostics/paper_tables/p6_collapse_test.json` | geçti |
| `diagnostics/paper_tables.py` | **A** | ölçülen süre 5.0 s | `paper/tables/tab_app_paired_sd.tex`<br>`diagnostics/paper_tables/RESULTS_TABLES.md`<br>`diagnostics/paper_tables/RESULTS_TABLES.json` | geçti |
| `diagnostics/perclass_crossing_table.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/perclass_crossing.md`<br>`diagnostics/paper_tables/perclass_crossing.json` | geçti |
| `diagnostics/prereg_lead_audit.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/prereg_lead_audit.md`<br>`diagnostics/paper_tables/prereg_lead_audit.json` | geçti |
| `diagnostics/r3w1_joint_optimum.py` | **A** | ölçülen süre 5.0 s | `diagnostics/paper_tables/r3w1_joint_optimum.md`<br>`diagnostics/paper_tables/r3w1_joint_optimum.json` | geçti |
| `diagnostics/regression_line_provenance.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/regression_line_provenance.md`<br>`diagnostics/paper_tables/regression_line_provenance.json` | geçti |
| `diagnostics/robustness_metrics.py` | **A** | ölçülen süre 5.8 s | `diagnostics/paper_tables/robustness_metrics.md`<br>`diagnostics/paper_tables/robustness_metrics.json` | geçti |
| `diagnostics/section54_numbers.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/section54_numbers.md`<br>`diagnostics/paper_tables/section54_numbers.json` | geçti |
| `diagnostics/selection_audit_inference.py` | **A** | ölçülen süre 0.6 s | `diagnostics/paper_tables/selection_audit_inference.md`<br>`diagnostics/paper_tables/selection_audit_inference.json` | geçti |
| `diagnostics/selection_distribution_figure.py` | **A** | ölçülen süre 5.4 s | `diagnostics/selection_audit/selection_distribution.json` | geçti |
| `diagnostics/selection_gain_estimator.py` | **A** | ölçülen süre 0.3 s | `diagnostics/selection_audit/selection_gain.json` | geçti |
| `diagnostics/selection_optimism_headline.py` | **A** | ölçülen süre 0.1 s | `diagnostics/selection_audit/selection_optimism_headline.json` | geçti |
| `diagnostics/selection_robustness.py` | **A** | ölçülen süre 0.1 s | `diagnostics/selection_audit/selection_robustness.json` | geçti |
| `diagnostics/split_identity.py` | **A** | ölçülen süre 0.2 s | `diagnostics/paper_tables/split_identity.md`<br>`diagnostics/paper_tables/split_identity.json`<br>`diagnostics/split_identity/rafdb_fold_class_counts.json` | geçti |
| `diagnostics/student_ts_baseline.py` | **A** | ölçülen süre 4.9 s | `diagnostics/paper_tables/student_ts_baseline.md`<br>`diagnostics/paper_tables/student_ts_baseline.json` | geçti |
| `diagnostics/t5_pairing_diff.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/t5_pairing_diff.md`<br>`diagnostics/paper_tables/t5_pairing_diff.json` | geçti |
| `diagnostics/tau_t_factorial.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/tau_t_factorial.md`<br>`diagnostics/paper_tables/tau_t_factorial.json` | geçti |
| `diagnostics/teacher_ece_grid.py` | **A** | ölçülen süre 9.3 s | `diagnostics/teacher_ece_grid/teacher_ece_grid.json` | geçti |
| `diagnostics/tstar_provenance.py` | **A** | ölçülen süre 0.1 s | `diagnostics/paper_tables/tstar_provenance.md`<br>`diagnostics/paper_tables/tstar_provenance.json` | geçti |
| `diagnostics/tstar_sensitivity.py` | **A** | ölçülen süre 7.5 s | `diagnostics/paper_tables/tstar_sensitivity.md`<br>`diagnostics/paper_tables/tstar_sensitivity.json` | geçti |
| `diagnostics/tstar_stability.py` | **A** | ölçülen süre 5.8 s | `diagnostics/paper_tables/tstar_stability.md`<br>`diagnostics/paper_tables/tstar_stability.json` | geçti |
| `diagnostics/two_dataset_overlay.py` | **A** | ölçülen süre 6.0 s | `diagnostics/p1_dose_response/two_dataset_overlay.json` | geçti |
| `diagnostics/adaptive_t_headroom_table.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/adaptive_t_headroom/adaptive_t_headroom.json` | geçti |
| `diagnostics/build_replicate_queue.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/replicate_queue_build.md` | geçti |
| `diagnostics/build_runs_ledger.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `runs.csv`<br>`diagnostics/paper_tables/run_mechanism_params.json` | geçti |
| `diagnostics/control_grid_refinement.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/paper_tables/control_grid_refinement.md`<br>`diagnostics/paper_tables/control_grid_refinement.json` | geçti |
| `diagnostics/ferplus_selection_audit.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/selection_audit/ferplus_selection_audit.csv` | geçti |
| `diagnostics/latency_benchmark.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/p5_efficiency/latency_benchmark.json`<br>`diagnostics/p5_efficiency/latency_benchmark_session2.json` | geçti |
| `diagnostics/p5_efficiency_frontier.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/p5_efficiency/p5_efficiency.json` | geçti |
| `diagnostics/perclass_calibration.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/reliability/perclass_calibration.json` | geçti |
| `diagnostics/publish_epoch_curves.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/epoch_curves_MANIFEST.json` | geçti |
| `diagnostics/publish_student_logits.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/student_logits/MANIFEST.json` | geçti |
| `diagnostics/rafdb_signal_quality_table.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/rafdb_signal_quality/signal_quality_table.json` | geçti |
| `diagnostics/reliability_diagram.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/reliability/reliability_diagram.json` | geçti |
| `diagnostics/run_manifest_census.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/paper_tables/run_manifest_census.md`<br>`diagnostics/paper_tables/run_manifest_census.json` | geçti |
| `diagnostics/selection_audit_table.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/selection_audit/README.md`<br>`diagnostics/selection_audit/selection_audit.csv`<br>`diagnostics/selection_audit/selection_audit_unfrozen.csv` | geçti |
| `diagnostics/vich_isolation_verdict.py` | **B** | Level-3 beyanlı: koşu dizinlerini okumak İŞİ | `diagnostics/vich_isolation/vich_isolation_verdict.json` | geçti |

---

Üretici: `diagnostics/producer_freshness_gate.py` · süre ölçümü: `--measure` · **kapı artefaktı DEĞİŞTİRMEZ**: Katman A koşudan önce baytları anlık kopyalar ve koşudan sonra her durumda geri yazar.

