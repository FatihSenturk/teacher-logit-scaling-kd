# Level-1 kapısı — üreticiler koşu dizinleri olmadan çalışıyor mu

> **Değişmez:** makaledeki her sayı, `results/` altındaki ham koşu dizinleri olmadan türetilebilmeli. Koşu dizinleri boyut yüzünden yayımlanmıyor; bu özellik olmadan public depo Level 1 vaadini tutamaz.

> **Neden kapı, uyanıklık değil.** 7 Ağu'da yazılan tek bir betik bu değişmezi sessizce bozdu (`tstar_provenance.py`, koşu dizinlerini tarıyordu). 18 üreticinin 17'si uyuyordu — ihlal görünmüyordu ve tesadüfen yakalandı.

> **HATA SINIFI BOŞ DEĞİLKEN GEÇTİ RAPORLANMAZ** (9 Ağu 2026 kuralı). 8 Ağu'da bu kapı "İHLAL 0" dedi ve doğruydu — ama `başka hata` sütununda 9 betik duruyordu ve o sütun "ihlal yok" demek değil, **"soru sorulamadı"** demekti. Arızalar düzeltilip sütun 0'a indiğinde arkasından üç gerçek ihlal çıktı. Artık `İHLAL == 0` yetmiyor: hata sınıfındaki her kalem ya sıfır olacak ya `DECLARED_ERRORS` içinde gerekçeli olacak.

**SONUÇ: GEÇTİ** — İHLAL 0 · beyansız "sorulamadı" 0

Kapsam `export_to_drive.EXPORTS`'tan türetilir (hangi betiğin yayımlanan artefakt ürettiği orada beyanlı); elle ikinci bir liste tutulmaz.

| betik | durum | not |
|---|---|---|
| `diagnostics/a12_realsignal_verdict.py` | GEÇTİ | — |
| `diagnostics/a13_scratch_dose_verdict.py` | GEÇTİ | — |
| `diagnostics/abs_path_gate.py` | GEÇTİ | — |
| `diagnostics/adaptive_t_headroom_table.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/asymmetry_estimand.py` | GEÇTİ | — |
| `diagnostics/audit_population.py` | GEÇTİ | — |
| `diagnostics/b015_verdict.py` | GEÇTİ | — |
| `diagnostics/bootstrap_cis.py` | GEÇTİ | — |
| `diagnostics/build_replicate_queue.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/build_runs_ledger.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/capacity_law_check.py` | GEÇTİ | — |
| `diagnostics/control_grid_refinement.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/control_sd_mde.py` | GEÇTİ | — |
| `diagnostics/criterion_applied.py` | GEÇTİ | — |
| `diagnostics/denominator_table.py` | GEÇTİ | — |
| `diagnostics/dose_response_per_seed.py` | GEÇTİ | — |
| `diagnostics/efficiency_retention.py` | GEÇTİ | — |
| `diagnostics/equivalence_tests.py` | GEÇTİ | — |
| `diagnostics/ferplus_abstention_entropy.py` | GEÇTİ | — |
| `diagnostics/ferplus_human_vote_jsd.py` | GEÇTİ | — |
| `diagnostics/ferplus_selection_audit.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/ferplus_student_jsd.py` | GEÇTİ | — |
| `diagnostics/g42_init_matched_lever.py` | GEÇTİ | — |
| `diagnostics/graphical_abstract.py` | GEÇTİ | — |
| `diagnostics/headroom_grid_audit.py` | GEÇTİ | — |
| `diagnostics/headroom_review.py` | GEÇTİ | — |
| `diagnostics/holm_family.py` | GEÇTİ | — |
| `diagnostics/inferential_tests.py` | GEÇTİ | — |
| `diagnostics/jsd_collapse_audit.py` | GEÇTİ | — |
| `diagnostics/jsd_sensitivity.py` | GEÇTİ | — |
| `diagnostics/latency_benchmark.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/level1_gate.py` | muaf | kapının kendisi — kendini koşturmak özyineleme olur |
| `diagnostics/mechanism_diagnostic_figure.py` | GEÇTİ | — |
| `diagnostics/mechanism_grid_gaps.py` | GEÇTİ | — |
| `diagnostics/mechanism_specs.py` | GEÇTİ | — |
| `diagnostics/monotonicity_test.py` | GEÇTİ | — |
| `diagnostics/noise_units.py` | GEÇTİ | — |
| `diagnostics/number_audit_round3.py` | GEÇTİ | — |
| `diagnostics/number_ledger.py` | GEÇTİ | — |
| `diagnostics/order_stat_trend.py` | GEÇTİ | — |
| `diagnostics/p2_gate_oracle_verdict.py` | GEÇTİ | — |
| `diagnostics/p4_teacher_selection_recipe.py` | GEÇTİ | — |
| `diagnostics/p5_efficiency_frontier.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/p5_oracle_replication_verdict.py` | GEÇTİ | — |
| `diagnostics/p6_verdict.py` | GEÇTİ | — |
| `diagnostics/paper_tables.py` | GEÇTİ | — |
| `diagnostics/perclass_calibration.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/perclass_crossing_table.py` | GEÇTİ | — |
| `diagnostics/prereg_lead_audit.py` | GEÇTİ | — |
| `diagnostics/public_repo_staleness.py` | GEÇTİ | — |
| `diagnostics/public_repo_sync.py` | GEÇTİ | — |
| `diagnostics/public_scope_buckets.py` | GEÇTİ | — |
| `diagnostics/public_scope_scan.py` | GEÇTİ | — |
| `diagnostics/publish_epoch_curves.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/publish_student_logits.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/r3w1_joint_optimum.py` | GEÇTİ | — |
| `diagnostics/rafdb_signal_quality_table.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/regression_line_provenance.py` | GEÇTİ | — |
| `diagnostics/reliability_diagram.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/robustness_metrics.py` | GEÇTİ | — |
| `diagnostics/run_manifest_census.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/section54_numbers.py` | GEÇTİ | — |
| `diagnostics/selection_audit_inference.py` | GEÇTİ | — |
| `diagnostics/selection_audit_table.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/selection_distribution_figure.py` | GEÇTİ | — |
| `diagnostics/selection_gain_estimator.py` | GEÇTİ | — |
| `diagnostics/selection_optimism_headline.py` | GEÇTİ | — |
| `diagnostics/selection_robustness.py` | GEÇTİ | — |
| `diagnostics/split_identity.py` | GEÇTİ | — |
| `diagnostics/status_heartbeat.py` | muaf | Level 3 — koşu dizini okumak işi |
| `diagnostics/student_ts_baseline.py` | GEÇTİ | — |
| `diagnostics/t5_pairing_diff.py` | GEÇTİ | — |
| `diagnostics/tau_t_factorial.py` | GEÇTİ | — |
| `diagnostics/teacher_ece_grid.py` | GEÇTİ | — |
| `diagnostics/tstar_provenance.py` | GEÇTİ | — |
| `diagnostics/tstar_sensitivity.py` | GEÇTİ | — |
| `diagnostics/tstar_stability.py` | GEÇTİ | — |
| `diagnostics/two_dataset_overlay.py` | GEÇTİ | — |
| `diagnostics/vich_isolation_verdict.py` | muaf | Level 3 — koşu dizini okumak işi |

**Muaf betikler** koşu dizinlerini okumak ZORUNDA — işleri o (defter kurma, checkpoint ölçme, canlı koşu bulma). Level 3'türler ve README'de öyle etiketlidirler; muafiyet burada **beyan** olarak durur, çıkarım olarak değil.

> "başka hata" ihlal değildir ama **temiz de değildir**: betik koşu dizinlerine dokunmadan düştü (eksik girdi, eksik bağımlılık, argparse, konsol kodlaması), yani Level-1 sorusu **sorulamadı**. Ayrı sütunda tutuluyor ki Level-1 sorusu başka arızalarla karışmasın — ama sütun boş değilken kapı GEÇTİ demez.

---

Üretici: `diagnostics/level1_gate.py`

