"""Read-only diagnostic: signal-quality table for teacher uncertainty proxies.

For each of the 3 RAF-DB teachers (Stage1-VICH, Primary-VICH, VAE9182),
forwards the full fold-3 val set once and computes several candidate
"uncertainty" signals against the teacher's own prediction error, reporting
SIGNED AUROC (not folded to |AUROC-0.5|) so the direction of each signal is
visible: AUROC < 0.5 means "higher signal value -> LESS likely to be wrong"
(a confidence-flavored signal), AUROC > 0.5 means "higher signal value ->
MORE likely to be wrong" (the direction gate's mean_logvar was designed to
have), AUROC ~ 0.5 means uninformative.

No config changed, no training started/resumed. CPU-only.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from kd_common import extract_logits, extract_mu_logvar  # noqa: E402
from train_rafdb_kd import build_teacher, build_loaders  # noqa: E402

OUT_DIR = PROJECT_ROOT / "diagnostics" / "rafdb_signal_quality"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = torch.device("cpu")

TEACHERS = {
    "Stage1": {
        "ckpt": PROJECT_ROOT / "results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/best.pt",
        "vae_head": False, "vich_head": True, "vich_init_logvar_bias": 0.0,
    },
    "Primary": {
        "ckpt": PROJECT_ROOT / "checkpoints/teacher_rafdb_vich_recipe_best.pt",
        "vae_head": False, "vich_head": True, "vich_init_logvar_bias": 0.0,
    },
    "VAE9182": {
        "ckpt": PROJECT_ROOT / "results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/best.pt",
        "vae_head": True, "vich_head": False, "vich_init_logvar_bias": -5.0,
    },
}


def build_one_teacher(spec):
    args = SimpleNamespace(
        teacher_vae_head=spec["vae_head"], teacher_layer_embedding=True, teacher_votes_sum=0,
        teacher_vich_head=spec["vich_head"], teacher_vich_use_sampling=True,
        teacher_vich_logvar_min=-10.0, teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=spec["vich_init_logvar_bias"],
    )
    return build_teacher(spec["ckpt"], DEVICE, args)


def auroc(y_true, y_score):
    from sklearn.metrics import roc_auc_score
    if len(set(y_true.tolist())) < 2:
        return None
    return float(roc_auc_score(y_true, y_score))


def target_logvar(logvar, labels):
    return logvar.gather(1, labels.view(-1, 1)).squeeze(1)


def top2_logvar(probs, logvar):
    idx = probs.topk(2, dim=1).indices
    return logvar.gather(1, idx).mean(dim=1)


def main():
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
    all_images, all_labels = [], []
    for images, labels in val_loader:
        all_images.append(images)
        all_labels.append(labels)
    all_images = torch.cat(all_images, dim=0)
    all_labels = torch.cat(all_labels, dim=0)

    rows = []
    for name, spec in TEACHERS.items():
        teacher = build_one_teacher(spec)
        teacher.eval()
        with torch.no_grad():
            all_logits, all_mu, all_logvar = [], [], []
            for i in range(0, all_images.shape[0], 128):
                chunk = all_images[i:i + 128]
                out = teacher(chunk)
                lg = extract_logits(out)
                mu, logvar = extract_mu_logvar(out)
                all_logits.append(lg)
                all_mu.append(mu)
                all_logvar.append(logvar)
        logits = torch.cat(all_logits, dim=0)
        mu = torch.cat(all_mu, dim=0)
        logvar = torch.cat(all_logvar, dim=0)

        probs = F.softmax(logits, dim=1)
        preds = probs.argmax(dim=1)
        error = (preds != all_labels).long().numpy()
        own_acc = float((preds == all_labels).float().mean() * 100.0)

        top2_probs, top2_idx = probs.topk(2, dim=1)
        margin = (top2_probs[:, 0] - top2_probs[:, 1]).numpy()
        msp = top2_probs[:, 0].numpy()
        entropy = (-(probs * torch.log(probs.clamp_min(1e-12))).sum(dim=1)).numpy()

        signals = {
            "mean_logvar": logvar.mean(dim=1).numpy(),
            "target_logvar": target_logvar(logvar, all_labels).numpy(),
            "top2_logvar": top2_logvar(probs, logvar).numpy(),
            "max_logvar": logvar.max(dim=1).values.numpy(),
            "entropy": entropy,
            "msp": msp,
            "margin": margin,
        }

        for signal_name, values in signals.items():
            a = auroc(error, values)
            rows.append({
                "teacher": name, "own_acc": own_acc, "signal": signal_name,
                "auroc_signed": a,
                "informativeness_abs_auroc_minus_half": (abs(a - 0.5) if a is not None else None),
                "direction": (
                    "higher->more error (uncertainty-like)" if (a is not None and a > 0.5)
                    else "higher->less error (confidence-like)" if (a is not None and a < 0.5)
                    else "uninformative/undefined"
                ),
            })
            print(f"[{name}] {signal_name}: AUROC={a:.4f}" if a is not None else f"[{name}] {signal_name}: AUROC=N/A")

    out_path = OUT_DIR / "signal_quality_table.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")

    import csv
    csv_path = OUT_DIR / "signal_quality_table.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
