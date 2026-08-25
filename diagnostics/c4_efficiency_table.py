"""C4 efficiency table -- metrics-compile half (read-only, no new inference).

Joins params_m/flops_g/size_mb/best_epoch/accuracy (already in each finished
run's metrics_best.json) with ece (already computed in
diagnostics/rafdb_calibration_backfill/calibration_table.csv) into one table.
Reuses REGISTRY/find_finished_runs from rafdb_calibration_backfill.py as the
single source of truth for which runs exist -- does not duplicate that list.

Latency/FPS are added separately (Phase 0c, via tools/eval_rafdb_teacher_
student_table.py) since that requires a live forward pass, not a JSON compile.
"""
import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS_DIR = PROJECT_ROOT / "diagnostics"
sys.path.insert(0, str(DIAGNOSTICS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

import rafdb_calibration_backfill as backfill  # noqa: E402

OUT_DIR = DIAGNOSTICS_DIR / "c4_efficiency_table"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_ece_by_run_id():
    ece_by_run_id = {}
    csv_path = DIAGNOSTICS_DIR / "rafdb_calibration_backfill" / "calibration_table.csv"
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            ece_by_run_id[row["run_id"]] = float(row["ece"])
    return ece_by_run_id


def main():
    finished = backfill.find_finished_runs()
    ece_by_run_id = load_ece_by_run_id()

    rows = []
    for entry in finished:
        metrics = json.loads(entry["metrics_path"].read_text())
        rows.append({
            "run_id": entry["run_id"],
            "teacher": entry["teacher"],
            "condition": entry["condition"],
            "recipe": entry["recipe"],
            "best_epoch": metrics["best_epoch"],
            "accuracy": metrics["accuracy"],
            "ece": ece_by_run_id.get(entry["run_id"]),
            "params_m": metrics["params_m"],
            "flops_g": metrics["flops_g"],
            "size_mb": metrics["size_mb"],
        })

    csv_path = OUT_DIR / "efficiency_table.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {csv_path} ({len(rows)} rows)")

    md_lines = [
        "| run_id | teacher | condition | recipe | best_epoch | accuracy | ece | params_m | flops_g | size_mb |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['run_id']} | {r['teacher']} | {r['condition']} | {r['recipe']} | "
            f"{r['best_epoch']} | {r['accuracy']:.2f}% | "
            f"{r['ece']:.4f} | {r['params_m']:.4f} | {r['flops_g']:.6f} | {r['size_mb']:.2f} |"
        )
    md_path = OUT_DIR / "efficiency_table.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Wrote {md_path}")

    # All student runs share the same architecture (MobileNetV2Plus+LightLE+VICH,
    # width_mult=1.0) so params_m/flops_g/size_mb should be identical across all
    # rows -- surface this explicitly rather than let it look like an oversight.
    param_values = {round(r["params_m"], 4) for r in rows}
    flops_values = {round(r["flops_g"], 6) for r in rows}
    print(f"\nDistinct params_m values across {len(rows)} runs: {param_values}")
    print(f"Distinct flops_g values across {len(rows)} runs: {flops_values}")


if __name__ == "__main__":
    main()
