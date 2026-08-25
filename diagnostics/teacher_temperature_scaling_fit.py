"""Phase B1: post-hoc temperature-scaling fit for the 3 RAF-DB teachers.

For each teacher, forwards the full fold-3 val set once (CPU, no grad, eval),
then fits a single scalar T* by minimizing NLL of softmax(logits / T) against
the true labels (scipy.optimize.minimize_scalar, bounded [0.5, 5.0]). Reports
accuracy (T-invariant), ECE(T=1), ECE(T*), NLL(T=1), NLL(T*), and T*.

Read-only: no training code/config/checkpoint is modified; this only reads
checkpoints and computes calibration statistics.

VERIFICATION ANCHOR (do not trust T* unless this passes): ECE(T=1) computed here
must reproduce the teacher's ECE from the head-compat audit
(diagnostics/teacher_head_compat_audit/full_report.json::task5_full_val_metrics):
    Stage1 0.0378 | Primary 0.0396 | VAE9182 0.0136   (15-bin, confidence ECE)
NB: these are the *teacher* ECE values. Do NOT confuse them with the *student*
baseline ECE (0.0581/0.0654/0.0285) -- a different, separately-computed set.

Why Stage1 in particular: Phase B3 will KD-train a student with Stage1's teacher
logits divided by T* (via a new --teacher-temperature-scale flag), pushing the
teacher's ECE (0.0378) down toward VAE9182's (0.0136) WITHOUT changing head
architecture or recipe -- the causal test of whether teacher calibration alone
moves student outcomes.
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F
from scipy.optimize import minimize_scalar

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from kd_common import extract_logits  # noqa: E402
from train_rafdb_kd import build_teacher, build_loaders  # noqa: E402

OUT_DIR = PROJECT_ROOT / "diagnostics" / "teacher_temperature_scaling"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = torch.device("cpu")  # GPU is busy with the Phase A seed-replicate streams

TEACHERS = {
    "stage1": {
        "ckpt": PROJECT_ROOT / "results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/best.pt",
        "vae_head": False, "vich_head": True, "vich_init_logvar_bias": 0.0,
        "audit_ece_t1": 0.0378,
    },
    "primary": {
        "ckpt": PROJECT_ROOT / "checkpoints/teacher_rafdb_vich_recipe_best.pt",
        "vae_head": False, "vich_head": True, "vich_init_logvar_bias": 0.0,
        "audit_ece_t1": 0.0396,
    },
    "vae9182": {
        "ckpt": PROJECT_ROOT / "results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/best.pt",
        "vae_head": True, "vich_head": False, "vich_init_logvar_bias": -5.0,
        "audit_ece_t1": 0.0136,
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


def confidence_ece(logits, labels, T, n_bins=15):
    """15-bin equal-width confidence ECE on softmax(logits / T). Matches the
    method used in teacher_head_compat_audit.compute_ece exactly (bin on max
    prob; first bin is closed on the left)."""
    probs = F.softmax(logits / T, dim=1)
    conf, preds = probs.max(dim=1)
    correct = (preds == labels)
    bins = torch.linspace(0.0, 1.0, n_bins + 1)
    n = labels.shape[0]
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bins[i].item(), bins[i + 1].item()
        mask = (conf > lo) & (conf <= hi) if i > 0 else (conf >= lo) & (conf <= hi)
        cnt = mask.sum().item()
        if cnt == 0:
            continue
        bin_acc = correct[mask].float().mean().item()
        bin_conf = conf[mask].mean().item()
        ece += (cnt / n) * abs(bin_acc - bin_conf)
    return float(ece)


def nll(logits, labels, T):
    return float(F.cross_entropy(logits / T, labels).item())


def fit_temperature(logits, labels):
    res = minimize_scalar(
        lambda T: nll(logits, labels, float(T)),
        bounds=(0.5, 5.0), method="bounded",
    )
    return float(res.x)


def build_val_images():
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
    imgs, lbls = [], []
    for images, labels in val_loader:
        imgs.append(images)
        lbls.append(labels)
    return torch.cat(imgs, dim=0), torch.cat(lbls, dim=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--teachers", nargs="+", default=list(TEACHERS.keys()),
                    choices=list(TEACHERS.keys()))
    ap.add_argument("--ece-tol", type=float, default=0.003,
                    help="max |ECE(T=1) - audit value| before flagging a pipeline mismatch")
    args = ap.parse_args()

    all_images, all_labels = build_val_images()
    print(f"Val set: {all_images.shape[0]} images\n")

    results = []
    for name in args.teachers:
        spec = TEACHERS[name]
        teacher = build_one_teacher(spec)
        teacher.eval()
        with torch.no_grad():
            chunks = []
            for i in range(0, all_images.shape[0], 128):
                out = teacher(all_images[i:i + 128])
                chunks.append(extract_logits(out).float())
        logits = torch.cat(chunks, dim=0)

        preds = logits.argmax(dim=1)
        acc = float((preds == all_labels).float().mean() * 100.0)

        ece_t1 = confidence_ece(logits, all_labels, T=1.0)
        nll_t1 = nll(logits, all_labels, T=1.0)
        anchor = spec["audit_ece_t1"]
        ece_mismatch = abs(ece_t1 - anchor)
        anchor_ok = ece_mismatch <= args.ece_tol

        t_star = fit_temperature(logits, all_labels)
        ece_ts = confidence_ece(logits, all_labels, T=t_star)
        nll_ts = nll(logits, all_labels, T=t_star)

        row = {
            "teacher": name,
            "own_acc_pct": acc,
            "T_star": t_star,
            "ece_T1": ece_t1,
            "ece_Tstar": ece_ts,
            "nll_T1": nll_t1,
            "nll_Tstar": nll_ts,
            "audit_ece_T1_anchor": anchor,
            "ece_T1_mismatch_vs_audit": ece_mismatch,
            "anchor_ok": bool(anchor_ok),
        }
        results.append(row)
        flag = "OK" if anchor_ok else f"** MISMATCH > {args.ece_tol} **"
        print(f"[{name}] acc={acc:.2f}%  T*={t_star:.4f}")
        print(f"    ECE:  T=1 {ece_t1:.4f} (audit {anchor:.4f}, {flag})  ->  T* {ece_ts:.4f}")
        print(f"    NLL:  T=1 {nll_t1:.4f}  ->  T* {nll_ts:.4f}\n")

    out_path = OUT_DIR / "temperature_fit.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    if not all(r["anchor_ok"] for r in results):
        print("\nWARNING: at least one ECE(T=1) did not reproduce the audit value within tolerance. "
              "Do NOT trust T* for the mismatched teacher(s) until the pipeline is reconciled.")


if __name__ == "__main__":
    main()
