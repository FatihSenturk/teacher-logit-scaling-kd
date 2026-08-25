import argparse
import csv
import json
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


CLASS_NAMES = [
    "Surprise",
    "Fear",
    "Disgust",
    "Happiness",
    "Sadness",
    "Anger",
    "Neutral",
]


def _safe_name(value):
    value = str(value)
    value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    value = value.strip("._")
    return value[:180] or "run"


def _read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_csv_dicts(path):
    rows = []
    try:
        with Path(path).open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows.extend(reader)
    except Exception:
        pass
    return rows


def _read_confusion(path):
    try:
        matrix = np.loadtxt(str(path), delimiter=",")
    except Exception:
        return None
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        return None
    return matrix.astype(float)


def _as_percent(value):
    if value is None or value == "":
        return None
    try:
        value = float(value)
    except Exception:
        return None
    if abs(value) <= 1.0:
        return value * 100.0
    return value


def _as_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _format_float(value, digits=4):
    if value is None:
        return ""
    try:
        if math.isnan(float(value)):
            return ""
    except Exception:
        return ""
    return f"{float(value):.{digits}f}"


def _short_label(row):
    name = row.get("run_name") or row.get("run_id") or ""
    name = name.replace("RAFDB_", "")
    name = name.replace("betaKD_", "")
    name = name.replace("lightle_vich_", "lv_")
    name = name.replace("best_400e_swa200", "400_swa200")
    name = name.replace("200e_noSWA", "200_noSWA")
    return name[:42]


def _discover_run_dirs(results_roots):
    run_dirs = {}
    for root in results_roots:
        root = Path(root)
        if not root.exists():
            continue
        candidate_files = []
        candidate_files.extend(root.rglob("metrics_best.json"))
        candidate_files.extend(root.rglob("training_log.csv"))
        candidate_files.extend(root.rglob("confusion_matrix.csv"))
        candidate_files.extend(root.rglob("config.json"))
        for file_path in candidate_files:
            path_text = str(file_path).lower()
            if "rafdb" not in path_text and "raf-db" not in path_text:
                continue
            run_dir = file_path.parent
            run_dirs[str(run_dir.resolve())] = run_dir
    return sorted(run_dirs.values(), key=lambda p: str(p).lower())


def _load_run(run_dir):
    config = _read_json(run_dir / "config.json")
    best = _read_json(run_dir / "metrics_best.json")
    swa = _read_json(run_dir / "metrics_swa.json")
    last = _read_json(run_dir / "metrics_last.json")

    run_name = config.get("name") or best.get("name") or run_dir.parent.name
    timestamp = run_dir.name
    run_id = f"{run_name}__{timestamp}"

    rows = []
    for split, payload in [("best", best), ("swa", swa), ("last", last)]:
        if not payload:
            continue
        rows.append({
            "run_id": run_id,
            "run_name": run_name,
            "timestamp": timestamp,
            "checkpoint_type": split,
            "dataset": payload.get("dataset", config.get("dataset", "RAF-DB")),
            "model": payload.get("model", config.get("model", "MobileNetV2Plus")),
            "head": payload.get("head", config.get("student_head_type", "")),
            "accuracy": _as_percent(payload.get("accuracy")),
            "precision": _as_percent(payload.get("precision")),
            "recall": _as_percent(payload.get("recall")),
            "macro_f1": _as_percent(payload.get("macro_f1")),
            "weighted_f1": _as_percent(payload.get("weighted_f1")),
            "params_m": _as_float(payload.get("params_m")),
            "flops_g": _as_float(payload.get("flops_g")),
            "size_mb": _as_float(payload.get("size_mb")),
            "best_epoch": payload.get("best_epoch") or payload.get("epoch"),
            "input_resolution": payload.get("input_resolution") or config.get("img_size") or config.get("val_size"),
            "teacher_ckpt": config.get("teacher_ckpt", ""),
            "temperature": config.get("temperature", ""),
            "alpha": config.get("alpha", ""),
            "dropout": config.get("dropout", ""),
            "swa_start": config.get("swa_start", ""),
            "path": str(run_dir),
        })

    incomplete = {
        "run_id": run_id,
        "run_name": run_name,
        "timestamp": timestamp,
        "path": str(run_dir),
        "has_metrics_best": (run_dir / "metrics_best.json").exists(),
        "has_training_log": (run_dir / "training_log.csv").exists(),
        "has_confusion_matrix": (run_dir / "confusion_matrix.csv").exists(),
        "has_confusion_matrix_swa": (run_dir / "confusion_matrix_swa.csv").exists(),
    }
    return rows, incomplete


def _write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not fieldnames:
        keys = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown_table(path, rows, columns, limit=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    selected = rows[:limit] if limit else rows
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in selected:
        values = []
        for column in columns:
            value = row.get(column, "")
            if isinstance(value, float):
                value = _format_float(value, 4)
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot_heatmap(matrix, labels_x, labels_y, title, output_path, cmap="viridis", vmin=None, vmax=None, fmt=".1f"):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    matrix = np.array(matrix, dtype=float)
    height = max(5.0, 0.45 * len(labels_y) + 2.2)
    width = max(7.0, 0.55 * len(labels_x) + 2.4)
    fig, ax = plt.subplots(figsize=(width, height), dpi=150)
    im = ax.imshow(matrix, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(np.arange(len(labels_x)))
    ax.set_yticks(np.arange(len(labels_y)))
    ax.set_xticklabels(labels_x, rotation=35, ha="right")
    ax.set_yticklabels(labels_y)
    ax.set_title(title)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            if np.isnan(value):
                text = ""
            else:
                text = format(value, fmt)
            color = "white" if im.norm(value) > 0.55 else "black"
            ax.text(j, i, text, ha="center", va="center", fontsize=7, color=color)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def _plot_confusion(matrix, title, output_path, normalize=False):
    if normalize:
        denom = matrix.sum(axis=1, keepdims=True)
        denom[denom == 0] = 1.0
        values = matrix / denom * 100.0
        _plot_heatmap(
            values,
            CLASS_NAMES,
            CLASS_NAMES,
            title,
            output_path,
            cmap="Blues",
            vmin=0.0,
            vmax=100.0,
            fmt=".1f",
        )
    else:
        _plot_heatmap(
            matrix,
            CLASS_NAMES,
            CLASS_NAMES,
            title,
            output_path,
            cmap="Blues",
            fmt=".0f",
        )


def _class_metrics_from_confusion(matrix):
    diag = np.diag(matrix)
    row_sum = matrix.sum(axis=1)
    col_sum = matrix.sum(axis=0)
    recall = np.divide(diag, row_sum, out=np.zeros_like(diag), where=row_sum > 0)
    precision = np.divide(diag, col_sum, out=np.zeros_like(diag), where=col_sum > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros_like(diag), where=(precision + recall) > 0)
    return precision * 100.0, recall * 100.0, f1 * 100.0


def _plot_scatter(rows, x_key, y_key, output_path, title, xlabel, ylabel):
    points = [row for row in rows if row.get(x_key) is not None and row.get(y_key) is not None]
    if not points:
        return
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(9, 6), dpi=150)
    x = [float(row[x_key]) for row in points]
    y = [float(row[y_key]) for row in points]
    resolutions = [str(row.get("input_resolution") or "?") for row in points]
    unique_res = sorted(set(resolutions))
    colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(unique_res))))
    color_map = {res: colors[i] for i, res in enumerate(unique_res)}
    for row, x_value, y_value, res in zip(points, x, y, resolutions):
        ax.scatter(x_value, y_value, s=55, color=color_map[res], label=f"{res}px" if f"{res}px" not in ax.get_legend_handles_labels()[1] else None)
    top = sorted(points, key=lambda row: row.get(y_key) or -1, reverse=True)[:12]
    for row in top:
        ax.annotate(
            _short_label(row),
            (float(row[x_key]), float(row[y_key])),
            textcoords="offset points",
            xytext=(5, 4),
            fontsize=7,
        )
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    ax.legend(title="Input", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def _plot_training_curves(run_dirs, best_rows, output_dir, top_n=12):
    output_dir = Path(output_dir)
    curves_dir = output_dir / "training_curves"
    curves_dir.mkdir(parents=True, exist_ok=True)
    ranked_names = {row["run_id"] for row in best_rows[:top_n]}
    aggregate = []
    for run_dir in run_dirs:
        config = _read_json(run_dir / "config.json")
        best = _read_json(run_dir / "metrics_best.json")
        run_name = config.get("name") or best.get("name") or run_dir.parent.name
        run_id = f"{run_name}__{run_dir.name}"
        rows = _read_csv_dicts(run_dir / "training_log.csv")
        if not rows:
            continue
        epochs = [_as_float(row.get("epoch")) for row in rows]
        val_acc = [_as_percent(row.get("val_acc")) for row in rows]
        train_acc = [_as_percent(row.get("train_acc")) for row in rows]
        train_loss = [_as_float(row.get("train_loss")) for row in rows]
        val_loss = [_as_float(row.get("val_loss")) for row in rows]
        lr = [_as_float(row.get("lr")) for row in rows]

        fig, axes = plt.subplots(3, 1, figsize=(9, 9), dpi=150, sharex=True)
        axes[0].plot(epochs, train_acc, label="train_acc")
        axes[0].plot(epochs, val_acc, label="val_acc")
        axes[0].set_ylabel("Accuracy (%)")
        axes[0].grid(True, alpha=0.25)
        axes[0].legend()
        axes[1].plot(epochs, train_loss, label="train_loss")
        axes[1].plot(epochs, val_loss, label="val_loss")
        axes[1].set_ylabel("Loss")
        axes[1].grid(True, alpha=0.25)
        axes[1].legend()
        axes[2].plot(epochs, lr, label="lr")
        axes[2].set_ylabel("LR")
        axes[2].set_xlabel("Epoch")
        axes[2].grid(True, alpha=0.25)
        axes[2].legend()
        fig.suptitle(run_name)
        fig.tight_layout()
        fig.savefig(curves_dir / f"{_safe_name(run_id)}.png")
        plt.close(fig)

        if run_id in ranked_names:
            aggregate.append((run_id, epochs, val_acc))

    if aggregate:
        fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
        for run_id, epochs, val_acc in aggregate:
            ax.plot(epochs, val_acc, label=_safe_name(run_id)[:42])
        ax.set_title(f"RAF-DB Validation Accuracy Curves - Top {len(aggregate)}")
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Validation accuracy (%)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(output_dir / "figures" / "val_accuracy_curves_top.png")
        plt.close(fig)


def _build_confusion_outputs(run_dirs, best_rows, output_dir, top_n_delta=8):
    output_dir = Path(output_dir)
    cm_dir = output_dir / "confusion_matrices"
    delta_dir = output_dir / "delta_confusion_vs_best"
    cm_dir.mkdir(parents=True, exist_ok=True)
    delta_dir.mkdir(parents=True, exist_ok=True)

    per_class_rows = []
    matrices = {}
    run_meta = {}

    for run_dir in run_dirs:
        config = _read_json(run_dir / "config.json")
        best = _read_json(run_dir / "metrics_best.json")
        run_name = config.get("name") or best.get("name") or run_dir.parent.name
        run_id = f"{run_name}__{run_dir.name}"

        for split, file_name in [("best", "confusion_matrix.csv"), ("swa", "confusion_matrix_swa.csv"), ("ema", "confusion_matrix_ema.csv")]:
            matrix = _read_confusion(run_dir / file_name)
            if matrix is None:
                continue
            key = f"{run_id}__{split}"
            matrices[key] = matrix
            run_meta[key] = {
                "run_id": run_id,
                "run_name": run_name,
                "timestamp": run_dir.name,
                "checkpoint_type": split,
            }
            safe = _safe_name(key)
            _plot_confusion(matrix, f"{run_name} ({split}) - counts", cm_dir / f"{safe}_counts.png", normalize=False)
            _plot_confusion(matrix, f"{run_name} ({split}) - row normalized (%)", cm_dir / f"{safe}_normalized.png", normalize=True)

            precision, recall, f1 = _class_metrics_from_confusion(matrix)
            for idx, class_name in enumerate(CLASS_NAMES):
                per_class_rows.append({
                    "run_id": run_id,
                    "run_name": run_name,
                    "timestamp": run_dir.name,
                    "checkpoint_type": split,
                    "class_index": idx,
                    "class_name": class_name,
                    "precision": precision[idx],
                    "recall": recall[idx],
                    "f1": f1[idx],
                    "support": int(matrix[idx].sum()),
                })

    _write_csv(output_dir / "per_class_metrics.csv", per_class_rows)

    best_matrix_key = None
    if best_rows:
        best_run_id = best_rows[0]["run_id"]
        candidate = f"{best_run_id}__best"
        if candidate in matrices:
            best_matrix_key = candidate
    if best_matrix_key:
        ref = matrices[best_matrix_key]
        ref_norm = ref / np.maximum(ref.sum(axis=1, keepdims=True), 1.0) * 100.0
        ranked_keys = []
        ranked_ids = [row["run_id"] for row in best_rows[:top_n_delta]]
        for run_id in ranked_ids:
            key = f"{run_id}__best"
            if key in matrices and key != best_matrix_key:
                ranked_keys.append(key)
        for key in ranked_keys:
            matrix = matrices[key]
            norm = matrix / np.maximum(matrix.sum(axis=1, keepdims=True), 1.0) * 100.0
            delta = norm - ref_norm
            meta = run_meta[key]
            _plot_heatmap(
                delta,
                CLASS_NAMES,
                CLASS_NAMES,
                f"Delta vs best reference: {meta['run_name']} - ref {run_meta[best_matrix_key]['run_name']}",
                delta_dir / f"{_safe_name(key)}_delta_vs_best.png",
                cmap="coolwarm",
                vmin=-25.0,
                vmax=25.0,
                fmt=".1f",
            )

    return per_class_rows


def _plot_per_class_heatmaps(per_class_rows, best_rows, output_dir, top_n=12):
    if not per_class_rows:
        return
    output_dir = Path(output_dir)
    figures_dir = output_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    top_ids = [row["run_id"] for row in best_rows[:top_n]]
    labels = []
    recall_matrix = []
    f1_matrix = []
    for run_id in top_ids:
        rows = [
            row for row in per_class_rows
            if row["run_id"] == run_id and row["checkpoint_type"] == "best"
        ]
        if not rows:
            continue
        rows = sorted(rows, key=lambda row: int(row["class_index"]))
        labels.append(_short_label({"run_id": run_id, "run_name": rows[0]["run_name"]}))
        recall_matrix.append([float(row["recall"]) for row in rows])
        f1_matrix.append([float(row["f1"]) for row in rows])
    if recall_matrix:
        _plot_heatmap(
            recall_matrix,
            CLASS_NAMES,
            labels,
            "RAF-DB Per-Class Recall (%) - Best Checkpoints",
            figures_dir / "per_class_recall_heatmap_best.png",
            cmap="YlGnBu",
            vmin=0.0,
            vmax=100.0,
            fmt=".1f",
        )
    if f1_matrix:
        _plot_heatmap(
            f1_matrix,
            CLASS_NAMES,
            labels,
            "RAF-DB Per-Class F1 (%) - Best Checkpoints",
            figures_dir / "per_class_f1_heatmap_best.png",
            cmap="YlGnBu",
            vmin=0.0,
            vmax=100.0,
            fmt=".1f",
        )


def _write_readme(output_dir, best_rows, incomplete_rows):
    output_dir = Path(output_dir)
    top = best_rows[:10]
    lines = [
        "# RAF-DB Visual Analysis",
        "",
        "This folder is generated from local RAF-DB teacher/student experiment artifacts.",
        "",
        "## Main Files",
        "- `leaderboard_best.csv`: best-checkpoint ranking.",
        "- `leaderboard_all_checkpoints.csv`: best/SWA/last rows when available.",
        "- `per_class_metrics.csv`: per-class precision/recall/F1/support derived from confusion matrices.",
        "- `figures/accuracy_vs_flops.png`: accuracy-efficiency Pareto view.",
        "- `figures/accuracy_vs_params.png`: accuracy-parameter view.",
        "- `figures/per_class_recall_heatmap_best.png`: class-level recall comparison.",
        "- `figures/per_class_f1_heatmap_best.png`: class-level F1 comparison.",
        "- `figures/val_accuracy_curves_top.png`: validation curves of top runs.",
        "- `confusion_matrices/`: count and normalized confusion matrices.",
        "- `delta_confusion_vs_best/`: normalized confusion deltas against the best run.",
        "",
        "## Top Best Checkpoints",
        "",
        "| Rank | Run | Accuracy | Macro-F1 | Weighted-F1 | Params M | FLOPs G | Epoch | Path |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for idx, row in enumerate(top, start=1):
        lines.append(
            "| {rank} | {run} | {acc} | {mf1} | {wf1} | {params} | {flops} | {epoch} | `{path}` |".format(
                rank=idx,
                run=row.get("run_name", ""),
                acc=_format_float(row.get("accuracy"), 4),
                mf1=_format_float(row.get("macro_f1"), 4),
                wf1=_format_float(row.get("weighted_f1"), 4),
                params=_format_float(row.get("params_m"), 4),
                flops=_format_float(row.get("flops_g"), 4),
                epoch=row.get("best_epoch", ""),
                path=row.get("path", ""),
            )
        )
    incomplete = [row for row in incomplete_rows if not row.get("has_metrics_best")]
    if incomplete:
        lines.extend([
            "",
            "## Incomplete Runs",
            "",
            "These runs were discovered but do not have `metrics_best.json` yet.",
            "",
            "| Run | Timestamp | Has Log | Has Confusion | Path |",
            "| --- | --- | --- | --- | --- |",
        ])
        for row in incomplete:
            lines.append(
                f"| {row.get('run_name', '')} | {row.get('timestamp', '')} | {row.get('has_training_log')} | {row.get('has_confusion_matrix')} | `{row.get('path', '')}` |"
            )
    output_dir.joinpath("README_RAFDB_VISUAL_ANALYSIS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser("Build RAF-DB visual analysis package from local results.")
    parser.add_argument("--results-root", action="append", default=None, help="Root folder to scan. Can be passed more than once.")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/rafdb_visual_analysis"))
    parser.add_argument("--top-n", type=int, default=12)
    args = parser.parse_args()

    results_roots = args.results_root or ["results/unified_students", "results"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "figures").mkdir(parents=True, exist_ok=True)

    run_dirs = _discover_run_dirs(results_roots)
    all_rows = []
    incomplete_rows = []
    for run_dir in run_dirs:
        rows, incomplete = _load_run(run_dir)
        all_rows.extend(rows)
        incomplete_rows.append(incomplete)

    best_rows = [row for row in all_rows if row["checkpoint_type"] == "best" and row.get("accuracy") is not None]
    best_rows = sorted(best_rows, key=lambda row: row.get("accuracy") or -1.0, reverse=True)
    all_rows = sorted(all_rows, key=lambda row: (row.get("accuracy") is not None, row.get("accuracy") or -1.0), reverse=True)

    _write_csv(output_dir / "leaderboard_best.csv", best_rows)
    _write_csv(output_dir / "leaderboard_all_checkpoints.csv", all_rows)
    _write_csv(output_dir / "discovered_runs.csv", incomplete_rows)
    _write_markdown_table(
        output_dir / "leaderboard_best_top.md",
        best_rows,
        ["run_name", "timestamp", "accuracy", "macro_f1", "weighted_f1", "params_m", "flops_g", "best_epoch", "path"],
        limit=args.top_n,
    )

    _plot_scatter(
        best_rows,
        "flops_g",
        "accuracy",
        output_dir / "figures" / "accuracy_vs_flops.png",
        "RAF-DB Best Accuracy vs FLOPs",
        "FLOPs (G)",
        "Best accuracy (%)",
    )
    _plot_scatter(
        best_rows,
        "params_m",
        "accuracy",
        output_dir / "figures" / "accuracy_vs_params.png",
        "RAF-DB Best Accuracy vs Parameters",
        "Parameters (M)",
        "Best accuracy (%)",
    )

    per_class_rows = _build_confusion_outputs(run_dirs, best_rows, output_dir, top_n_delta=args.top_n)
    _plot_per_class_heatmaps(per_class_rows, best_rows, output_dir, top_n=args.top_n)
    _plot_training_curves(run_dirs, best_rows, output_dir, top_n=args.top_n)
    _write_readme(output_dir, best_rows, incomplete_rows)

    print(f"Discovered run dirs: {len(run_dirs)}")
    print(f"Best metric rows: {len(best_rows)}")
    print(f"All metric rows: {len(all_rows)}")
    print(f"Wrote report: {output_dir}")
    if best_rows:
        best = best_rows[0]
        print(
            "Top run: "
            f"{best.get('run_name')} | acc={_format_float(best.get('accuracy'), 4)} | "
            f"macro_f1={_format_float(best.get('macro_f1'), 4)} | path={best.get('path')}"
        )


if __name__ == "__main__":
    main()
