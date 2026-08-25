"""Read-only, zero-new-inference recompute: equal-mass-bin ECE/MCE from the
already-cached per-run logits (diagnostics/rafdb_calibration_backfill/logits/
*.npz, saved by rafdb_calibration_backfill.py). Adds a bin-sensitivity note by
comparing against the original equal-width-bin ECE/MCE already in
calibration_table.csv.

Also does a focused per-bin breakdown for primary_adaptive_t (the MCE=0.76
outlier) under BOTH binning schemes, to see whether that outlier is a
single-sparse-bin equal-width artifact or survives equal-mass binning too.
"""
import csv
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parent
LOGITS_DIR = BASE / "logits"


def softmax(x):
    x = x - x.max(axis=1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=1, keepdims=True)


def equal_width_ece_mce(probs, labels, n_bins=15):
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece, mce = 0.0, 0.0
    n = len(labels)
    bin_details = []
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (confidences > lo) & (confidences <= hi) if i > 0 else (confidences >= lo) & (confidences <= hi)
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        gap = abs(bin_acc - bin_conf)
        ece += (mask.sum() / n) * gap
        mce = max(mce, gap)
        bin_details.append({"range": [round(lo, 3), round(hi, 3)], "n": int(mask.sum()), "acc": float(bin_acc), "conf": float(bin_conf), "gap": float(gap)})
    return float(ece), float(mce), bin_details


def equal_mass_ece_mce(probs, labels, n_bins=15):
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)
    order = np.argsort(confidences)
    n = len(labels)
    conf_sorted = confidences[order]
    acc_sorted = accuracies[order]
    edges = np.linspace(0, n, n_bins + 1).astype(int)
    ece, mce = 0.0, 0.0
    bin_details = []
    for i in range(n_bins):
        lo_idx, hi_idx = edges[i], edges[i + 1]
        if hi_idx <= lo_idx:
            continue
        bin_conf = conf_sorted[lo_idx:hi_idx].mean()
        bin_acc = acc_sorted[lo_idx:hi_idx].mean()
        gap = abs(bin_acc - bin_conf)
        weight = (hi_idx - lo_idx) / n
        ece += weight * gap
        mce = max(mce, gap)
        bin_details.append({
            "conf_range": [round(float(conf_sorted[lo_idx]), 4), round(float(conf_sorted[hi_idx - 1]), 4)],
            "n": int(hi_idx - lo_idx), "acc": float(bin_acc), "conf": float(bin_conf), "gap": float(gap),
        })
    return float(ece), float(mce), bin_details


def main():
    rows = []
    orig_rows = {}
    with open(BASE / "calibration_table.csv") as f:
        for r in csv.DictReader(f):
            orig_rows[r["run_id"]] = r

    npz_files = sorted(LOGITS_DIR.glob("*.npz"))
    for npz_path in npz_files:
        run_id = npz_path.stem
        data = np.load(npz_path)
        logits, labels = data["logits"], data["labels"]
        probs = softmax(logits)

        ew_ece, ew_mce, _ = equal_width_ece_mce(probs, labels, n_bins=15)
        em_ece, em_mce, _ = equal_mass_ece_mce(probs, labels, n_bins=15)

        orig = orig_rows.get(run_id, {})
        rows.append({
            "run_id": run_id,
            "equal_width_ece": ew_ece, "equal_width_mce": ew_mce,
            "equal_mass_ece": em_ece, "equal_mass_mce": em_mce,
            "ece_scheme_delta": em_ece - ew_ece,
            "mce_scheme_delta": em_mce - ew_mce,
            "orig_ece_from_csv": float(orig.get("ece", "nan")),
            "orig_mce_from_csv": float(orig.get("mce", "nan")),
        })
        print(f"[{run_id}] equal-width ECE/MCE={ew_ece:.4f}/{ew_mce:.4f}  "
              f"equal-mass ECE/MCE={em_ece:.4f}/{em_mce:.4f}")

    csv_path = BASE / "ece_mce_bin_sensitivity.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {csv_path}")

    # Focused breakdown for the primary_adaptive_t MCE outlier.
    outlier_id = "primary_adaptive_t_swa200"
    outlier_path = LOGITS_DIR / f"{outlier_id}.npz"
    if outlier_path.exists():
        data = np.load(outlier_path)
        probs = softmax(data["logits"])
        labels = data["labels"]
        _, _, ew_details = equal_width_ece_mce(probs, labels, n_bins=15)
        _, _, em_details = equal_mass_ece_mce(probs, labels, n_bins=15)
        outlier_report = {"run_id": outlier_id, "equal_width_bins": ew_details, "equal_mass_bins": em_details}
        (BASE / "primary_adaptive_t_mce_outlier_breakdown.json").write_text(
            json.dumps(outlier_report, indent=2), encoding="utf-8"
        )
        print(f"\n--- {outlier_id} equal-width bin breakdown (looking for the MCE=0.76 bin) ---")
        for b in ew_details:
            flag = "  <-- LIKELY THE OUTLIER BIN" if b["gap"] > 0.5 else ""
            print(f"  range={b['range']} n={b['n']} acc={b['acc']:.3f} conf={b['conf']:.3f} gap={b['gap']:.3f}{flag}")
        print(f"\n--- {outlier_id} equal-mass bin breakdown (same run, quantile bins) ---")
        for b in em_details:
            flag = "  <-- LARGE GAP SURVIVES EQUAL-MASS BINNING" if b["gap"] > 0.5 else ""
            print(f"  conf_range={b['conf_range']} n={b['n']} acc={b['acc']:.3f} conf={b['conf']:.3f} gap={b['gap']:.3f}{flag}")
    else:
        print(f"\n[warn] {outlier_path} not found -- skipping outlier breakdown")


if __name__ == "__main__":
    main()
