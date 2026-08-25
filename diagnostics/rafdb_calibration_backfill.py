"""Read-only diagnostic: calibration backfill for all finished RAF-DB student
runs in the 3-teacher x 6-condition matrix (both the 400e_swa200 grid, fully
finished, and the in-progress 200e_noSWA grid -- only runs with a
metrics_best.json are included, so an in-progress stage is simply absent).

No retraining, no config edits. CPU-only so it cannot contend with / crash
into whatever GPU training job may still be running concurrently.

Outputs under diagnostics/rafdb_calibration_backfill/:
  - logits/{run_id}.npz          (logits + labels, per run, for reuse)
  - calibration_table.csv        (run_id, teacher, condition, recipe, best_epoch, acc, ece, mce, brier, nll)
  - ece_delta_pivot.csv           (ECE delta vs. each teacher+recipe's own baseline)
  - sanity1_primary_gate_vs_g2g.json
  - sanity2_epoch_cap/*.png + sanity2_epoch_cap_report.json
"""
import csv
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from kd_common import extract_logits, clean_state_dict  # noqa: E402
from train_rafdb_kd import build_loaders, build_student  # noqa: E402

OUT_DIR = PROJECT_ROOT / "diagnostics" / "rafdb_calibration_backfill"
LOGITS_DIR = OUT_DIR / "logits"
LOGITS_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = torch.device("cpu")

RESULTS_DIR = PROJECT_ROOT / "results" / "unified_students"

# (run_id, teacher, condition, recipe, run_dir)
REGISTRY = [
    ("stage1_baseline_swa200", "Stage1", "baseline", "400e_swa200", "RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200/2026-07-18-01-45-58"),
    ("stage1_gate_swa200", "Stage1", "gate", "400e_swa200", "RAFDB_stage1_gate_noclassweight_b070_T6_224_400e_swa200/2026-07-19-08-10-43"),
    ("stage1_g2g_kl_swa200", "Stage1", "g2g_kl", "400e_swa200", "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200/2026-07-18-10-33-06"),
    ("stage1_logit_std_swa200", "Stage1", "logit_std", "400e_swa200", "RAFDB_stage1_logit_std_b070_T6_224_400e_swa200/2026-07-18-14-39-16"),
    ("stage1_adaptive_t_swa200", "Stage1", "adaptive_t", "400e_swa200", "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200/2026-07-18-18-42-25"),
    ("stage1_ctkd_swa200", "Stage1", "ctkd", "400e_swa200", "RAFDB_stage1_ctkd_b070_T6_224_400e_swa200/2026-07-18-22-50-12"),

    ("primary_baseline_swa200", "Primary", "baseline", "400e_swa200", "RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200/2026-07-18-06-19-36"),
    ("primary_gate_swa200", "Primary", "gate", "400e_swa200", "RAFDB_primary_gate_noclassweight_b070_T6_224_400e_swa200/2026-07-19-10-39-49"),
    ("primary_g2g_kl_swa200", "Primary", "g2g_kl", "400e_swa200", "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200/2026-07-19-02-59-54"),
    ("primary_logit_std_swa200", "Primary", "logit_std", "400e_swa200", "RAFDB_primary_logit_std_b070_T6_224_400e_swa200/2026-07-18-03-53-27"),
    ("primary_adaptive_t_swa200", "Primary", "adaptive_t", "400e_swa200", "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200/2026-07-18-08-02-57"),
    ("primary_ctkd_swa200", "Primary", "ctkd", "400e_swa200", "RAFDB_primary_ctkd_b070_T6_224_400e_swa200/2026-07-18-12-08-02"),

    ("vae9182_baseline_swa200", "VAE9182", "baseline", "400e_swa200", "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200/2026-06-20-08-38-09"),
    ("vae9182_gate_swa200", "VAE9182", "gate", "400e_swa200", "RAFDB_vae9182_gate_noclassweight_b070_T6_224_400e_swa200/2026-07-19-13-01-18"),
    ("vae9182_g2g_kl_swa200", "VAE9182", "g2g_kl", "400e_swa200", "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200/2026-07-18-16-18-13"),
    ("vae9182_logit_std_swa200", "VAE9182", "logit_std", "400e_swa200", "RAFDB_vae9182_logit_std_b070_T6_224_400e_swa200/2026-07-18-20-26-49"),
    ("vae9182_adaptive_t_swa200", "VAE9182", "adaptive_t", "400e_swa200", "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200/2026-07-19-00-33-08"),
    ("vae9182_ctkd_swa200", "VAE9182", "ctkd", "400e_swa200", "RAFDB_vae9182_ctkd_b070_T6_224_400e_swa200/2026-07-19-04-36-29"),

    ("stage1_baseline_noswa", "Stage1", "baseline", "200e_noSWA", "RAFDB_stage1_baseline_b070_T6_224_200e_noSWA/2026-07-19-15-21-14"),
    ("stage1_gate_noswa", "Stage1", "gate", "200e_noSWA", "RAFDB_stage1_gate_b070_T6_224_200e_noSWA/2026-07-19-16-32-23"),
]


def find_finished_runs():
    """Only include registry entries whose metrics_best.json actually exists
    right now -- an in-progress stage in the 200e_noSWA grid is simply absent,
    no special-casing needed."""
    finished = []
    for run_id, teacher, condition, recipe, rel_dir in REGISTRY:
        run_dir = RESULTS_DIR / rel_dir
        metrics_path = run_dir / "metrics_best.json"
        ckpt_path = run_dir / "best_checkpoint.pth"
        if metrics_path.exists() and ckpt_path.exists():
            finished.append({
                "run_id": run_id, "teacher": teacher, "condition": condition,
                "recipe": recipe, "run_dir": run_dir,
                "metrics_path": metrics_path, "ckpt_path": ckpt_path,
            })
        else:
            print(f"[skip] {run_id}: not finished yet ({run_dir})")
    return finished


def build_val_loader_once():
    data_args = SimpleNamespace(
        aligned_dir=PROJECT_ROOT / "data/rafdb_aligned",
        metadata=PROJECT_ROOT / "data/rafdb_aligned/metadata_rafdb_poster_var.csv",
        train_folds=[2], val_folds=[3], train_frac=1.0, val_frac=1.0,
        batch_size=64, workers=0, img_size=224, resize_size=0,
        augment_preset="kd", rotation_degrees=12.0, color_jitter=0.2,
        random_erasing_p=0.1, ra_mag=7, balanced_sampler=False,
        class_weight_mode="none", class_weight_beta=0.9999,
        no_train_augment=False, teacher_cache=None,
    )
    _train_loader, val_loader = build_loaders(data_args)
    return val_loader


STUDENT_ARGS = SimpleNamespace(
    student_head_type="vich", width_mult=1.0, dropout=0.5,
    student_layer_embedding=True, student_vae_head=False,
    student_lightweight_layer_embedding=True, student_layer_embedding_layers=3,
    student_embedding_dim=768, student_feature_adapter_dim=0,
    use_vich_sampling=False, vich_logvar_min=-10.0, vich_logvar_max=10.0,
    vich_init_logvar_bias=-5.0, student_pretrained=False,
)


def load_student(ckpt_path):
    student = build_student(STUDENT_ARGS, DEVICE)
    ckpt = torch.load(str(ckpt_path), map_location=DEVICE, weights_only=False)
    student.load_state_dict(clean_state_dict(ckpt["model_state_dict"]), strict=True)
    student.eval()
    return student, ckpt


def compute_ece_mce(probs, labels, n_bins=15):
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece, mce = 0.0, 0.0
    n = len(labels)
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
    return float(ece), float(mce)


def compute_brier_nll(probs, labels, num_classes=7):
    one_hot = np.eye(num_classes)[labels]
    brier = float(np.mean(np.sum((probs - one_hot) ** 2, axis=1)))
    true_probs = np.clip(probs[np.arange(len(labels)), labels], 1e-12, 1.0)
    nll = float(-np.mean(np.log(true_probs)))
    return brier, nll


def main():
    finished = find_finished_runs()
    print(f"\n{len(finished)}/{len(REGISTRY)} registry runs finished; proceeding with those.\n")

    val_loader = build_val_loader_once()
    all_images, all_labels = [], []
    for images, labels in val_loader:
        all_images.append(images)
        all_labels.append(labels)
    all_images = torch.cat(all_images, dim=0)
    all_labels_t = torch.cat(all_labels, dim=0)
    labels_np = all_labels_t.numpy()
    print(f"Val (fold 3) set: {len(labels_np)} images, loaded once, reused across all runs.\n")

    rows = []
    run_logits = {}  # run_id -> (logits_np, preds_np), for sanity #1

    for entry in finished:
        run_id = entry["run_id"]
        metrics = json.loads(entry["metrics_path"].read_text())
        logged_acc = metrics["accuracy"]
        best_epoch = metrics["best_epoch"]

        student, ckpt = load_student(entry["ckpt_path"])
        with torch.no_grad():
            batch_logits = []
            for i in range(0, all_images.shape[0], 128):
                chunk = all_images[i:i + 128]
                out = student(chunk)
                batch_logits.append(extract_logits(out))
            logits = torch.cat(batch_logits, dim=0)

        logits_np = logits.numpy()
        probs_np = F.softmax(logits, dim=1).numpy()
        preds_np = probs_np.argmax(axis=1)

        recomputed_acc = float((preds_np == labels_np).mean() * 100.0)
        acc_mismatch = abs(recomputed_acc - logged_acc)

        ece, mce = compute_ece_mce(probs_np, labels_np, n_bins=15)
        brier, nll = compute_brier_nll(probs_np, labels_np, num_classes=7)

        np.savez(LOGITS_DIR / f"{run_id}.npz", logits=logits_np, labels=labels_np, preds=preds_np)
        run_logits[run_id] = (logits_np, preds_np)

        rows.append({
            "run_id": run_id, "teacher": entry["teacher"], "condition": entry["condition"],
            "recipe": entry["recipe"], "seed": 42, "best_epoch": best_epoch,
            "logged_acc": logged_acc, "recomputed_acc": recomputed_acc,
            "acc_mismatch_pp": acc_mismatch, "acc_mismatch_flag": acc_mismatch > 0.05,
            "ece": ece, "mce": mce, "brier": brier, "nll": nll,
        })
        flag_str = "  <-- ACC MISMATCH > 0.05pp" if acc_mismatch > 0.05 else ""
        print(f"[{run_id}] acc={recomputed_acc:.4f}% (logged {logged_acc:.4f}%, diff {acc_mismatch:.4f}pp) "
              f"ece={ece:.4f} mce={mce:.4f} brier={brier:.4f} nll={nll:.4f}{flag_str}")

    csv_path = OUT_DIR / "calibration_table.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {csv_path}")

    baseline_ece = {}
    for r in rows:
        if r["condition"] == "baseline":
            baseline_ece[(r["teacher"], r["recipe"])] = r["ece"]
    pivot_rows = []
    for r in rows:
        key = (r["teacher"], r["recipe"])
        base = baseline_ece.get(key)
        pivot_rows.append({
            "teacher": r["teacher"], "recipe": r["recipe"], "condition": r["condition"],
            "ece": r["ece"], "baseline_ece": base,
            "ece_delta_vs_baseline": (r["ece"] - base) if base is not None else None,
        })
    pivot_path = OUT_DIR / "ece_delta_pivot.csv"
    with open(pivot_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(pivot_rows[0].keys()))
        writer.writeheader()
        writer.writerows(pivot_rows)
    print(f"Wrote {pivot_path}")

    # --- Sanity #1: primary_gate vs primary_g2g_kl (identical logged accuracy) ---
    sanity1 = {}
    if "primary_gate_swa200" in run_logits and "primary_g2g_kl_swa200" in run_logits:
        _, preds_gate = run_logits["primary_gate_swa200"]
        _, preds_g2g = run_logits["primary_g2g_kl_swa200"]
        n_diff = int((preds_gate != preds_g2g).sum())
        n_total = len(preds_gate)
        sanity1["n_differing_predictions"] = n_diff
        sanity1["n_total"] = n_total
        sanity1["pct_differing"] = round(100.0 * n_diff / n_total, 4)
        sanity1["identical_predictions"] = (n_diff == 0)

        g2g_log_path = RESULTS_DIR / "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200" / "2026-07-19-02-59-54" / "training_log.csv"
        g2g_stats = {"error": "log file not found"}
        if g2g_log_path.exists():
            lines = g2g_log_path.read_text(errors="ignore").splitlines()
            header = lines[0].split(",")
            if "g2g_term" in header:
                idx = header.index("g2g_term")
                values = []
                for line in lines[1:]:
                    parts = line.split(",")
                    if len(parts) > idx and parts[idx].strip() not in ("", "None"):
                        try:
                            values.append(float(parts[idx]))
                        except ValueError:
                            pass
                if values:
                    g2g_stats = {
                        "n_epochs_logged": len(values),
                        "g2g_term_min": min(values),
                        "g2g_term_mean": sum(values) / len(values),
                        "g2g_term_max": max(values),
                        "all_nonzero": all(v != 0.0 for v in values),
                        "any_nonzero": any(v != 0.0 for v in values),
                    }
                else:
                    g2g_stats = {"error": "g2g_term column present but no parseable values"}
            else:
                g2g_stats = {"error": f"no g2g_term column in header: {header}"}
        sanity1["g2g_term_training_log_stats"] = g2g_stats
    else:
        sanity1["error"] = "one or both runs missing from finished set"
    (OUT_DIR / "sanity1_primary_gate_vs_g2g.json").write_text(json.dumps(sanity1, indent=2), encoding="utf-8")
    print(f"\nSanity #1: {json.dumps(sanity1, indent=2)}")

    # --- Sanity #2: epoch-cap check for best_epoch >= 390 ---
    sanity2_dir = OUT_DIR / "sanity2_epoch_cap"
    sanity2_dir.mkdir(exist_ok=True)
    sanity2_report = []
    for entry, r in zip(finished, rows):
        if r["best_epoch"] < 390:
            continue
        log_path = entry["run_dir"] / "training_log.csv"
        if not log_path.exists():
            continue
        lines = log_path.read_text(errors="ignore").splitlines()
        header = lines[0].split(",")
        try:
            epoch_idx = header.index("epoch")
        except ValueError:
            epoch_idx = 0
        val_acc_idx = None
        for cand in ["val_acc", "val_accuracy", "acc_val", "accuracy"]:
            if cand in header:
                val_acc_idx = header.index(cand)
                break
        if val_acc_idx is None:
            sanity2_report.append({"run_id": r["run_id"], "error": f"no val-acc column found in header: {header}"})
            continue
        epochs, val_accs = [], []
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) <= max(epoch_idx, val_acc_idx):
                continue
            try:
                epochs.append(int(float(parts[epoch_idx])))
                val_accs.append(float(parts[val_acc_idx]))
            except ValueError:
                continue
        last50_epochs = epochs[-50:]
        last50_accs = val_accs[-50:]
        if len(last50_accs) >= 2:
            slope = np.polyfit(range(len(last50_accs)), last50_accs, 1)[0]
            still_ascending = slope > 0.001
        else:
            slope, still_ascending = None, None

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(last50_epochs, last50_accs, marker="o", markersize=2)
        ax.axvline(r["best_epoch"], color="red", linestyle="--", label=f"best_epoch={r['best_epoch']}")
        ax.set_title(f"{r['run_id']}: last 50 epochs val_acc")
        ax.set_xlabel("epoch")
        ax.set_ylabel("val_acc (%)")
        ax.legend()
        fig.tight_layout()
        png_path = sanity2_dir / f"{r['run_id']}_last50.png"
        fig.savefig(png_path, dpi=100)
        plt.close(fig)

        sanity2_report.append({
            "run_id": r["run_id"], "best_epoch": r["best_epoch"],
            "last50_slope_per_epoch": float(slope) if slope is not None else None,
            "still_ascending_at_cap": still_ascending,
            "plot": str(png_path),
        })
    (sanity2_dir / "sanity2_epoch_cap_report.json").write_text(json.dumps(sanity2_report, indent=2), encoding="utf-8")
    print(f"\nSanity #2: {json.dumps(sanity2_report, indent=2)}")


if __name__ == "__main__":
    main()
