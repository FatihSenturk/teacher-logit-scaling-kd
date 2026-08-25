"""Read-only diagnostic: verify VAE9182's head is not a silent shape-coincidence
with the two VICH teachers (Stage1, Primary) that gate/g2g_kl/adaptive_t rely on.

Does NOT modify any config, does NOT train/resume anything. CPU-only by design
so it cannot contend with (or crash into) the GPU training job that may be
running concurrently.

Writes JSON + PNG histograms under diagnostics/teacher_head_compat_audit/.
"""
import json
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

from kd_common import extract_logits, extract_mu_logvar, load_checkpoint_checked  # noqa: E402
from train_rafdb_kd import build_teacher, build_loaders, RAFDBDataset  # noqa: E402
from torchvision import transforms  # noqa: E402

OUT_DIR = PROJECT_ROOT / "diagnostics" / "teacher_head_compat_audit"
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
        teacher_vae_head=spec["vae_head"],
        teacher_layer_embedding=True,
        teacher_votes_sum=0,
        teacher_vich_head=spec["vich_head"],
        teacher_vich_use_sampling=True,
        teacher_vich_logvar_min=-10.0,
        teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=spec["vich_init_logvar_bias"],
    )
    teacher = build_teacher(spec["ckpt"], DEVICE, args)
    return teacher


# ---------------------------------------------------------------------------
# Task 1: raw state_dict key/shape audit (no model construction, just the
# checkpoint file itself) -- catches anything a strict-load might paper over
# by comparing what's literally on disk before any architecture is imposed.
# ---------------------------------------------------------------------------
def task1_raw_state_dict_audit():
    report = {}
    for name, spec in TEACHERS.items():
        ckpt = torch.load(str(spec["ckpt"]), map_location="cpu", weights_only=False)
        state_dict = ckpt.get("model", ckpt.get("model_state_dict", ckpt.get("state_dict", ckpt)))
        head_keys = {k: list(v.shape) for k, v in state_dict.items() if k.startswith("head")}
        report[name] = {
            "ckpt_path": str(spec["ckpt"]),
            "declared_head_flags": {"vae_head": spec["vae_head"], "vich_head": spec["vich_head"]},
            "head_related_keys": head_keys,
            "has_head_vae": any(k.startswith("head_vae.") for k in state_dict),
            "has_head_vich": any(k.startswith("head_vich.") for k in state_dict),
            "has_plain_head": any(k == "head.linear.weight" or k == "head.linear.bias" for k in state_dict),
        }
    return report


# ---------------------------------------------------------------------------
# Task 2: confirm the loading code path (static facts, gathered from source
# reading -- reported here alongside the empirical results for one document).
# ---------------------------------------------------------------------------
TASK2_STATIC_FINDINGS = {
    "loader_function": "train_rafdb_kd.py:build_teacher -> kd_common.load_checkpoint_checked",
    "branch_type": (
        "Single model class (trails/posterv2/vit_vae_model.py::VisionTransformer / "
        "pyramid_trans_expr2) with mutually-exclusive constructor flags vae=/vich=. "
        "forward() does `if self.vich: head_vich elif self.vae: head_vae else: head` "
        "(vit_vae_model.py:787-792) -- vae and vich are not independent branches, "
        "they select one of three heads on the SAME class."
    ),
    "head_vich_construction": (
        "self.head_vich = VICHClassifier(...) if self.vich else None "
        "(vit_vae_model.py:654) -- CONDITIONAL. A checkpoint trained with vich=False "
        "has NO head_vich.* keys in its state_dict at all."
    ),
    "head_vae_construction": (
        "self.head_vae = VaeClassifier(...) (vit_vae_model.py:653) -- UNCONDITIONAL, "
        "always present regardless of the vae/vich flags. If trained with vae=False, "
        "these params exist in the checkpoint but are dead (never touched by forward(), "
        "so never receive gradient; they sit at their random _init_vit_weights init)."
    ),
    "strict_flag_usage": (
        "grep across the whole repo: every single teacher-load call site "
        "(train_rafdb_kd.py:106, train_affectnetplus_kd.py:61, tools/evaluate_teacher.py:32, "
        "tools/analyze_uncertainty_human.py:198, tools/cache_teacher_outputs.py:129) passes "
        "strict=True. No strict=False usage exists anywhere for teacher checkpoints. "
        "kd_common.load_checkpoint_checked's own strict=False safety-net (raising on "
        "missing/unexpected keys) is therefore dead code on every call site actually used."
    ),
    "consequence": (
        "Given head_vich is conditionally absent and head_vae is unconditionally present "
        "but architecturally distinct (different class, different init, no clamp), any "
        "attempt to load a VAE-trained checkpoint with vich=True (or a VICH-trained "
        "checkpoint with vae=True after the correct vae=False) would raise "
        "`RuntimeError: Error(s) in loading state_dict ... Missing key(s)/Unexpected key(s)` "
        "from PyTorch's own strict=True check, BEFORE any forward pass. There is no "
        "code path by which a head-type mismatch loads silently."
    ),
}


# ---------------------------------------------------------------------------
# Task 3: exact tensors gate/g2g_kl/adaptive_t consume (static + shape check).
# ---------------------------------------------------------------------------
def task3_consumption_trace(teacher_mu_shape, num_classes):
    return {
        "extraction": (
            "train_rafdb_kd.py:452-454: teacher_output = teacher(teacher_images); "
            "extract_logits(teacher_output) for logits; "
            "extract_mu_logvar(teacher_output) for (teacher_mu, teacher_logvar). "
            "kd_common.extract_mu_logvar treats VaeClassifier's (out, mu, logvar) and "
            "VICHClassifier's (logits, mu, logvar) identically -- both are 3-tuples, "
            "indices [1], [2] regardless of which head produced them."
        ),
        "gate_consumption": (
            "kd_uncertainty.py: mean_logvar/target_logvar/top2_logvar all operate on "
            "teacher_logvar with shape [B, C] (C=num_classes), reducing over dim=1 to "
            "a per-sample scalar [B]. No assumption beyond 'last dim is class-indexed'."
        ),
        "g2g_consumption": (
            "kd_g2g.py: g2g_kl/g2g_w2 treat teacher_mu/teacher_logvar and "
            "student_mu/student_logvar as per-class independent diagonal Gaussians, "
            "summed over dim=1. validate_g2g_shapes() explicitly asserts "
            "teacher_mu.shape == student_mu.shape and raises RuntimeError naming the "
            "offending side otherwise -- checked on every forward(), not just at load time."
        ),
        "adaptive_t_consumption": (
            "kd_baselines.entropy_adaptive_temperature operates on teacher_logits "
            "(not mu/logvar) directly -- entropy of softmax(logits), independent of "
            "head type; does not touch mu/logvar at all."
        ),
        "shape_facts": {
            "teacher_mu_logvar_shape": list(teacher_mu_shape),
            "C_num_classes": num_classes,
            "D_latent_dim": teacher_mu_shape[-1],
            "C_equals_D": teacher_mu_shape[-1] == num_classes,
        },
        "coincidence_assessment": (
            "C==D is NOT a coincidence: vit_vae_model.py:653-654 constructs "
            "BOTH head_vae=VaeClassifier(in_features=embed_dim, out_features=num_classes) "
            "and head_vich=VICHClassifier(in_features=embed_dim, out_features=num_classes) "
            "with the identical out_features=num_classes argument. Neither head has a "
            "separate reconstruction/embedding latent dimension distinct from class "
            "count -- both are, by this codebase's deliberate design, 'class-level "
            "variational classifiers' (VICHClassifier's own docstring, line 337-343). "
            "So a shape check alone cannot and is not meant to distinguish them; the "
            "actual distinguishing facts are architectural (clamp vs. no clamp, "
            "different init, VaeClassifier's dead unused batchnorm/layernorm/dropout "
            "submodules) and are what Task 1's key audit surfaces."
        ),
    }


def eval_batch_and_full_set():
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

    torch.manual_seed(42)
    fixed_batch_images, fixed_batch_labels = [], []
    n_collected = 0
    for images, labels in val_loader:
        fixed_batch_images.append(images)
        fixed_batch_labels.append(labels)
        n_collected += images.shape[0]
        if n_collected >= 256:
            break
    fixed_images = torch.cat(fixed_batch_images, dim=0)[:256]
    fixed_labels = torch.cat(fixed_batch_labels, dim=0)[:256]

    task4_report = {}
    task5_rows = []
    teacher_mu_shape_for_task3 = None

    for name, spec in TEACHERS.items():
        teacher = build_one_teacher(spec)
        teacher.eval()

        # --- Task 4: fixed batch ---
        with torch.no_grad():
            output = teacher(fixed_images)
        logits = extract_logits(output)
        mu, logvar = extract_mu_logvar(output)
        if teacher_mu_shape_for_task3 is None and mu is not None:
            teacher_mu_shape_for_task3 = mu.shape

        logvar_np = logvar.detach().numpy().flatten()
        stats = {
            "mu_shape": list(mu.shape),
            "logvar_shape": list(logvar.shape),
            "logvar_min": float(logvar_np.min()),
            "logvar_mean": float(logvar_np.mean()),
            "logvar_max": float(logvar_np.max()),
            "logvar_std": float(logvar_np.std()),
        }
        degenerate_flags = []
        if stats["logvar_std"] < 1e-4:
            degenerate_flags.append("near-constant (std < 1e-4)")
        if abs(stats["logvar_min"]) < 1e-6 and abs(stats["logvar_max"]) < 1e-6:
            degenerate_flags.append("all-zeros")
        if stats["logvar_max"] > 9.9 or stats["logvar_min"] < -9.9:
            degenerate_flags.append("at-or-beyond-clamp-bound (may indicate saturation, or absence of clamp for VAE head)")
        stats["degenerate_flags"] = degenerate_flags
        task4_report[name] = stats

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(logvar_np, bins=20)
        ax.set_title(f"{name} teacher: logvar histogram (fixed 256-image batch)")
        ax.set_xlabel("logvar")
        ax.set_ylabel("count (per-class, per-sample)")
        fig.tight_layout()
        png_path = OUT_DIR / f"{name.lower()}_logvar_hist.png"
        fig.savefig(png_path, dpi=100)
        plt.close(fig)
        task4_report[name]["histogram_png"] = str(png_path)

        # --- Task 5: full val (fold 3) set ---
        all_logits, all_mean_logvar, all_labels = [], [], []
        with torch.no_grad():
            for images, labels in val_loader:
                out = teacher(images)
                lg = extract_logits(out)
                _mu_b, logvar_b = extract_mu_logvar(out)
                all_logits.append(lg)
                all_mean_logvar.append(logvar_b.mean(dim=1))  # gate's "mean_logvar" reduction
                all_labels.append(labels)
        all_logits = torch.cat(all_logits, dim=0)
        all_mean_logvar = torch.cat(all_mean_logvar, dim=0)
        all_labels = torch.cat(all_labels, dim=0)

        probs = F.softmax(all_logits, dim=1)
        preds = probs.argmax(dim=1)
        correct = (preds == all_labels)
        own_acc = float(correct.float().mean() * 100.0)

        # AUROC(logvar -> own top-1 error): label=1 means "teacher got it wrong"
        error_label = (~correct).long().numpy()
        logvar_score = all_mean_logvar.numpy()
        auroc = roc_auc_score_manual(error_label, logvar_score)

        # 15-bin ECE
        ece = compute_ece(probs.numpy(), all_labels.numpy(), n_bins=15)

        task5_rows.append({
            "teacher": name,
            "own_acc": own_acc,
            "auroc_logvar_vs_error": auroc,
            "ece_15bin": ece,
            "n_samples": int(all_labels.shape[0]),
        })

    return task4_report, task5_rows, teacher_mu_shape_for_task3


def roc_auc_score_manual(y_true, y_score):
    try:
        from sklearn.metrics import roc_auc_score
        if len(set(y_true.tolist())) < 2:
            return None
        return float(roc_auc_score(y_true, y_score))
    except ImportError:
        return None


def compute_ece(probs, labels, n_bins=15):
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    accuracies = (predictions == labels).astype(np.float64)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(labels)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (confidences > lo) & (confidences <= hi) if i > 0 else (confidences >= lo) & (confidences <= hi)
        if mask.sum() == 0:
            continue
        bin_acc = accuracies[mask].mean()
        bin_conf = confidences[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def main():
    print("=== Task 1: raw state_dict head-key/shape audit ===")
    task1 = task1_raw_state_dict_audit()
    print(json.dumps(task1, indent=2))

    print("\n=== Task 2: teacher-loading code path (static) ===")
    print(json.dumps(TASK2_STATIC_FINDINGS, indent=2))

    print("\n=== Tasks 4 & 5: forwarding real data through all 3 teachers (CPU) ===")
    task4, task5, mu_shape = eval_batch_and_full_set()
    print(json.dumps(task4, indent=2))
    print(json.dumps(task5, indent=2))

    print("\n=== Task 3: consumption trace ===")
    task3 = task3_consumption_trace(mu_shape, num_classes=7)
    print(json.dumps(task3, indent=2))

    full_report = {
        "task1_raw_state_dict_audit": task1,
        "task2_loading_code_path": TASK2_STATIC_FINDINGS,
        "task3_consumption_trace": task3,
        "task4_fixed_batch_stats": task4,
        "task5_full_val_metrics": task5,
    }
    out_path = OUT_DIR / "full_report.json"
    out_path.write_text(json.dumps(full_report, indent=2), encoding="utf-8")
    print(f"\nFull report written to {out_path}")


if __name__ == "__main__":
    main()
