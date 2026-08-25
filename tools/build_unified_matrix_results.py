import argparse
import csv
import json
from pathlib import Path


TASKS = (
    ("RAF-DB", 7, "RAFDB_7cls_unified_lightle_vich_{resolution}"),
    ("AffectNet+", 7, "AffectNetPlus_7cls_unified_lightle_vich_{resolution}"),
    ("AffectNet+", 8, "AffectNetPlus_8cls_unified_lightle_vich_{resolution}"),
    ("FERPlus", 8, "FERPlus_8cls_unified_lightle_vich_{resolution}"),
)
RESOLUTIONS = (112, 224, 256)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def latest_metrics(run_root, filename):
    candidates = sorted(
        (path for path in Path(run_root).glob(f"*/{filename}") if path.is_file()),
        key=lambda path: path.parent.stat().st_mtime,
        reverse=True,
    )
    return (load_json(candidates[0]), candidates[0]) if candidates else (None, None)


def teacher_reference(args, dataset, classes, affect_refs):
    if dataset == "RAF-DB":
        return load_json(args.raf_teacher_metrics)
    if dataset == "FERPlus":
        return load_json(args.fer_teacher_metrics)
    key = f"AffectNet+ {classes}-class"
    return affect_refs[key]


def fmt(value):
    return "-" if value is None else f"{float(value):.3f}"


def main(args):
    existing = load_json(args.existing_config)
    affect_refs = {item["dataset"]: item["teacher"] for item in existing}
    rows = []

    for dataset, classes, name_template in TASKS:
        teacher = teacher_reference(args, dataset, classes, affect_refs)
        for resolution in RESOLUTIONS:
            run_name = name_template.format(resolution=resolution)
            run_root = args.results_root / run_name
            best, best_path = latest_metrics(run_root, "metrics_best.json")
            ema, ema_path = latest_metrics(run_root, "metrics_ema.json")
            if best is None:
                continue

            teacher_acc = teacher.get("accuracy")
            student_acc = best.get("accuracy")
            teacher_params = teacher.get("params_m")
            student_params = best.get("params_m")
            teacher_flops = teacher.get("flops_g")
            student_flops = best.get("flops_g")
            rows.append(
                {
                    "dataset": dataset,
                    "classes": classes,
                    "resolution": resolution,
                    "teacher_accuracy": teacher_acc,
                    "best_accuracy": student_acc,
                    "ema_accuracy": None if ema is None else ema.get("accuracy"),
                    "student_minus_teacher": (
                        None if teacher_acc is None or student_acc is None else student_acc - teacher_acc
                    ),
                    "precision": best.get("precision"),
                    "recall": best.get("recall"),
                    "macro_f1": best.get("macro_f1"),
                    "weighted_f1": best.get("weighted_f1"),
                    "teacher_params_m": teacher_params,
                    "student_params_m": student_params,
                    "compression_ratio": (
                        None if not teacher_params or not student_params else teacher_params / student_params
                    ),
                    "teacher_flops_g": teacher_flops,
                    "student_flops_g": student_flops,
                    "flops_reduction": (
                        None if not teacher_flops or not student_flops else teacher_flops / student_flops
                    ),
                    "best_metrics_path": str(best_path),
                    "ema_metrics_path": None if ema_path is None else str(ema_path),
                }
            )

    if not rows:
        raise RuntimeError(f"No unified student metrics found under {args.results_root}.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.output.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Unified Teacher-Student Resolution Matrix",
        "",
        "| Dataset | Classes | Input | Teacher Acc. | Best Acc. | EMA Acc. | Delta | Precision | Recall | Macro-F1 | Weighted-F1 | Params (M) | FLOPs (G) | Compression | FLOPs Reduction |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {dataset} | {classes} | {resolution} | {teacher_accuracy} | {best_accuracy} | "
            "{ema_accuracy} | {student_minus_teacher} | {precision} | {recall} | {macro_f1} | {weighted_f1} | "
            "{student_params_m} | {student_flops_g} | {compression_ratio}x | {flops_reduction}x |".format(
                **{
                    key: value if key in {"dataset", "classes", "resolution"} else fmt(value)
                    for key, value in row.items()
                }
            )
        )

    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {args.output}")
    print(f"Saved: {csv_path}")


def parse_args():
    parser = argparse.ArgumentParser("Build the unified 112/224/256 result matrix")
    parser.add_argument("--results-root", type=Path, default=Path("results/unified_students"))
    parser.add_argument("--existing-config", type=Path, default=Path("configs/unified_existing_results.json"))
    parser.add_argument("--raf-teacher-metrics", type=Path, required=True)
    parser.add_argument("--fer-teacher-metrics", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("UNIFIED_RESOLUTION_MATRIX_RESULTS.md"))
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
