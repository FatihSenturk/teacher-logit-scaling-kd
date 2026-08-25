"""Seed-variance calibration: accuracy + 15-bin ECE mean+/-sd across seeds for the
Phase A cells (and their seed-42 originals). The new-seed runs are NOT in the
calibration backfill, so ECE is (re)computed here from each run's own
best_checkpoint on the full fold-3 val, reusing the student_halfb_eval scaffold.
Read-only, CPU."""
import glob
import json
import statistics
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "diagnostics"))

from teacher_temperature_scaling_fit import confidence_ece, build_val_images  # noqa: E402
from student_halfb_eval import student_from_run, eval_logits  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OUT = PROJECT_ROOT / "diagnostics" / "seed_variance"
OUT.mkdir(parents=True, exist_ok=True)

CELLS = {
    "T-C baseline":     ["RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200",
                         "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1",
                         "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43"],
    "T-C g2g_kl":       ["RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200",
                         "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200_seed43"],
    "T-C adaptive_t":   ["RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200",
                         "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200_seed43"],
    "T-C combined_500e":["RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200",
                         "RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200_seed1",
                         "RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200_seed43"],
    "T-B baseline":     ["RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200",
                         "RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43"],
    "T-B g2g_kl":       ["RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200",
                         "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200_seed43"],
    "T-A baseline":     ["RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200",
                         "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43"],
    "T-A g2g_kl":       ["RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200",
                         "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200_seed43"],
    # seed43 finished 2026-07-25 23:19 and was missing from this hand-maintained registry until
    # 2026-07-28, when the rebuilt runs.csv showed 3 seeds where this file showed 2. A hand-listed
    # registry silently under-counts as runs land; the discrepancy is only visible by cross-checking
    # against the ledger, so that cross-check is now part of finishing any queue.
    "T-A adaptive_t":   ["RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200",
                         "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200_seed1",
                         "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200_seed43"],
    # bridge = VAE head + VICH recipe teacher; single seed, transfer measurement
    # (not a seed-variance cell -- excluded from the delta loop below).
    "bridge_transfer":  ["RAFDB_bridge_baseline_b070_T6_224_400e_swa200_seed42"],
}
SEEDS = [42, 1, 43]


def run_dir(name):
    d = sorted(glob.glob(str(PROJECT_ROOT / "results/unified_students" / name / "*")))
    return d[-1] if d else None


def main():
    all_images, all_labels = build_val_images()
    print(f"fold-3 val n={all_images.shape[0]}\n")

    rows = {}
    for cell, names in CELLS.items():
        per_seed = []
        for seed, name in zip(SEEDS, names):
            d = run_dir(name)
            if d is None or not Path(d, "best_checkpoint.pth").exists():
                per_seed.append(None)
                continue
            logits = eval_logits(student_from_run(d), all_images)
            acc = float((logits.argmax(1) == all_labels).float().mean() * 100.0)
            ece = confidence_ece(logits, all_labels, 1.0)
            per_seed.append({"seed": seed, "acc": acc, "ece": ece})
            print(f"  {cell:<18} seed {seed:<3} acc={acc:.2f}%  ece={ece:.4f}")
        got = [p for p in per_seed if p]
        accs = [p["acc"] for p in got]
        eces = [p["ece"] for p in got]
        rows[cell] = {
            "per_seed": per_seed,
            "acc_mean": statistics.mean(accs) if accs else None,
            "acc_sd": sample_sd(accs),
            "ece_mean": statistics.mean(eces) if eces else None,
            "ece_sd": sample_sd(eces),
            "n": len(got),
        }
        print()

    print("=" * 78)
    print(f"{'cell':<20}{'acc mean±sd':<18}{'ece mean±sd':<20}{'n'}")
    for cell, r in rows.items():
        if r["acc_mean"] is not None:
            print(f"{cell:<20}{r['acc_mean']:.2f}+/-{r['acc_sd']:.2f}      "
                  f"{r['ece_mean']:.4f}+/-{r['ece_sd']:.4f}    {r['n']}")

    print("\n--- deltas vs matched baseline mean (acc / ece) ---")
    for teach, base in [("T-C", "T-C baseline"), ("T-B", "T-B baseline"), ("T-A", "T-A baseline")]:
        b = rows[base]
        for cell, r in rows.items():
            if cell.startswith(teach) and cell != base and r["acc_mean"] is not None:
                dacc = r["acc_mean"] - b["acc_mean"]
                dece = r["ece_mean"] - b["ece_mean"]
                # NOTE: this threshold is sd-dependent, so it MOVED when the campaign switched
                # from pstdev to sample sd (n-1): at n=3 the bar rises by 1/0.816 = 22.5%, making
                # "clears" strictly harder to earn. That is the correct direction -- the old bar
                # was too easy -- but any cell near the boundary must be re-read, not assumed.
                clears = "clears" if abs(dacc) > b["acc_sd"] else "within-noise"
                print(f"  {cell:<20} d_acc={dacc:+.2f}pp ({clears} of baseline sd {b['acc_sd']:.2f})  d_ece={dece:+.4f}")

    (OUT / "seed_variance_table.json").write_text(
        json.dumps({"sd_convention": SD_CONVENTION, "cells": rows}, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT / 'seed_variance_table.json'}")


if __name__ == "__main__":
    main()
