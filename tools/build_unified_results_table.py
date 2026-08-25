import argparse
import csv
import json
from pathlib import Path


METRICS = ("accuracy", "precision", "recall", "macro_f1", "weighted_f1", "params_m", "flops_g")


def load_metrics(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def fmt(value):
    return "-" if value is None else f"{float(value):.3f}"


def main(args):
    records = []
    if args.existing_config:
        records.extend(json.loads(args.existing_config.read_text(encoding="utf-8")))
    for pair in args.pair:
        parts = pair.split("|", 2)
        if len(parts) != 3:
            raise ValueError("--pair must use DATASET|TEACHER_JSON|STUDENT_JSON")
        dataset, teacher_path, student_path = parts
        records.append({
            "dataset": dataset,
            "teacher": load_metrics(teacher_path),
            "student": load_metrics(student_path),
        })

    rows = []
    for record in records:
        teacher, student = record["teacher"], record["student"]
        teacher_acc = teacher.get("accuracy")
        student_acc = student.get("accuracy")
        teacher_params = teacher.get("params_m")
        student_params = student.get("params_m")
        teacher_flops = teacher.get("flops_g")
        student_flops = student.get("flops_g")
        rows.append({
            "dataset": record["dataset"],
            "teacher_accuracy": teacher_acc,
            "student_accuracy": student_acc,
            "student_minus_teacher": None if teacher_acc is None or student_acc is None else student_acc - teacher_acc,
            "teacher_macro_f1": teacher.get("macro_f1"),
            "student_macro_f1": student.get("macro_f1"),
            "teacher_weighted_f1": teacher.get("weighted_f1"),
            "student_weighted_f1": student.get("weighted_f1"),
            "teacher_params_m": teacher_params,
            "student_params_m": student_params,
            "compression_ratio": None if not teacher_params or not student_params else teacher_params / student_params,
            "teacher_flops_g": teacher_flops,
            "student_flops_g": student_flops,
            "flops_reduction": None if not teacher_flops or not student_flops else teacher_flops / student_flops,
        })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output.with_suffix(".csv")
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Unified Teacher-Student Results",
        "",
        "| Dataset | Teacher Acc. | Student Acc. | Delta | Teacher Macro-F1 | Student Macro-F1 | Teacher Params (M) | Student Params (M) | Compression | Teacher FLOPs (G) | Student FLOPs (G) | FLOPs Reduction |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {dataset} | {teacher_accuracy} | {student_accuracy} | {student_minus_teacher} | "
            "{teacher_macro_f1} | {student_macro_f1} | {teacher_params_m} | {student_params_m} | "
            "{compression_ratio}x | {teacher_flops_g} | {student_flops_g} | {flops_reduction}x |".format(
                **{key: fmt(value) if key != "dataset" else value for key, value in row.items()}
            )
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved: {output}")
    print(f"Saved: {csv_path}")


def parse_args():
    parser = argparse.ArgumentParser("Build unified teacher/student comparison table")
    parser.add_argument("--existing-config", type=Path, default=None)
    parser.add_argument("--pair", action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("UNIFIED_TEACHER_STUDENT_RESULTS.md"))
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
