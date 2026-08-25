"""Throwaway diagnostic (READ-ONLY on training code): B1 teacher sanity +
B4 sigma/gate health, run through the EXACT same build_loaders/build_teacher
pipeline that train_rafdb_kd.py uses for its teacher branch.

Does not modify any training code/configs/checkpoints. Cheap: one forward
pass over the RAF-DB val split (fold 3, n=3068), batch_size=32, workers=0,
no_grad, fp32 (no AMP) to keep this simple and side-effect-free while the
live teacher retrain shares the GPU.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from kd_common import extract_logits, extract_mu_logvar  # noqa: E402
from kd_uncertainty import mean_logvar, entropy_from_probabilities, resolve_uncertainty, gate_alpha  # noqa: E402
from train_rafdb_kd import build_loaders, build_teacher  # noqa: E402


def ece_15bin(confidences, correct, n_bins=15):
    bins = torch.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(confidences)
    details = []
    for i in range(n_bins):
        lo, hi = bins[i].item(), bins[i + 1].item()
        mask = (confidences > lo) & (confidences <= hi) if i > 0 else (confidences >= lo) & (confidences <= hi)
        cnt = mask.sum().item()
        if cnt == 0:
            continue
        acc_bin = correct[mask].float().mean().item()
        conf_bin = confidences[mask].mean().item()
        ece += (cnt / n) * abs(acc_bin - conf_bin)
        details.append((lo, hi, cnt, acc_bin, conf_bin))
    return ece, details


def percentile(t, q):
    return torch.quantile(t.float(), q).item()


def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    data_args = SimpleNamespace(
        aligned_dir=Path("data/rafdb_aligned"),
        metadata=Path("data/rafdb_aligned/metadata_rafdb_poster_var.csv"),
        train_folds=[2],
        val_folds=[3],
        train_frac=1.0,
        val_frac=1.0,
        batch_size=32,
        workers=0,
        img_size=224,
        resize_size=0,
        augment_preset="kd",
        rotation_degrees=12.0,
        color_jitter=0.2,
        random_erasing_p=0.1,
        ra_mag=7,
        balanced_sampler=False,
        class_weight_mode="none",
        class_weight_beta=0.9999,
        no_train_augment=False,
        teacher_cache=None,
    )
    _train_loader, val_loader = build_loaders(data_args)
    print(f"Val loader: {len(val_loader.dataset)} samples")

    teacher_args = SimpleNamespace(
        teacher_vae_head=False,
        teacher_vich_head=True,
        teacher_layer_embedding=True,
        teacher_votes_sum=0,
        teacher_vich_use_sampling=True,
        teacher_vich_logvar_min=-10.0,
        teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=0.0,
    )
    teacher_ckpt = PROJECT_ROOT / "checkpoints" / "teacher_rafdb_vich_recipe_best.pt"
    print(f"Loading teacher: {teacher_ckpt}")
    teacher = build_teacher(teacher_ckpt, device, teacher_args)

    temperature = 6.0
    gate_alpha_lo, gate_alpha_hi, gate_k, gate_tau = 0.1, 0.7, 2.0, 0.0

    all_correct = []
    all_conf = []
    all_entropy = []
    all_margin = []
    all_logvar_mean = []
    all_gate_u = []
    cm = torch.zeros(7, 7, dtype=torch.long)

    with torch.no_grad():
        for images, labels in val_loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            output = teacher(images)
            logits = extract_logits(output).float()
            mu, logvar = extract_mu_logvar(output)
            probs = F.softmax(logits, dim=1)
            pred = probs.argmax(dim=1)
            conf, _ = probs.max(dim=1)
            top2 = torch.topk(probs, k=2, dim=1).values
            margin = top2[:, 0] - top2[:, 1]
            entropy = entropy_from_probabilities(probs)

            all_correct.append((pred == labels).cpu())
            all_conf.append(conf.cpu())
            all_entropy.append(entropy.cpu())
            all_margin.append(margin.cpu())
            for t, p in zip(labels.cpu().tolist(), pred.cpu().tolist()):
                cm[t, p] += 1

            if logvar is not None:
                lv_mean = mean_logvar(logvar)
                all_logvar_mean.append(lv_mean.cpu())
                teacher_probs_T = F.softmax(logits / temperature, dim=1)
                u = resolve_uncertainty("mean_logvar", teacher_probs_T, mu, logvar, labels)
                # batch-norm the uncertainty signal the same way UncertaintyNormalizer("batch") would,
                # but computed globally after the loop below instead (see note).
                all_gate_u.append(u.cpu())

    correct = torch.cat(all_correct)
    conf = torch.cat(all_conf)
    entropy = torch.cat(all_entropy)
    margin = torch.cat(all_margin)
    n = len(correct)
    acc = correct.float().mean().item() * 100.0
    ece, ece_details = ece_15bin(conf, correct, n_bins=15)

    result = {
        "teacher_ckpt": str(teacher_ckpt),
        "n": n,
        "img_size": 224,
        "teacher_input_size": 224,
        "amp": False,
        "top1_acc_pct": acc,
        "mean_softmax_entropy_nats": entropy.mean().item(),
        "mean_max_prob": conf.mean().item(),
        "mean_top1_top2_margin": margin.mean().item(),
        "ece_15bin": ece,
    }

    if all_logvar_mean:
        lv = torch.cat(all_logvar_mean)
        u = torch.cat(all_gate_u)
        u_hat = (u - u.mean()) / (u.std(unbiased=False) + 1e-6)
        alpha_i = gate_alpha(u_hat, gate_alpha_lo, gate_alpha_hi, gate_k, gate_tau)
        result["teacher_mean_logvar_min"] = percentile(lv, 0.0)
        result["teacher_mean_logvar_p25"] = percentile(lv, 0.25)
        result["teacher_mean_logvar_median"] = percentile(lv, 0.50)
        result["teacher_mean_logvar_p75"] = percentile(lv, 0.75)
        result["teacher_mean_logvar_max"] = percentile(lv, 1.0)
        result["gate_alpha_mean"] = alpha_i.mean().item()
        result["gate_alpha_frac_lt_0.1+eps"] = (alpha_i < (gate_alpha_lo + 0.01)).float().mean().item()
        result["gate_alpha_frac_gt_0.9x_hi"] = (alpha_i > 0.9 * gate_alpha_hi).float().mean().item()
        result["gate_alpha_min"] = alpha_i.min().item()
        result["gate_alpha_max"] = alpha_i.max().item()
    else:
        result["teacher_mu_logvar"] = "NOT EXPOSED by extract_mu_logvar() for this checkpoint/config"

    print(json.dumps(result, indent=2))
    print("\nConfusion matrix (rows=true 0..6 Surprise,Fear,Disgust,Happiness,Sadness,Anger,Neutral; cols=pred):")
    print(cm.numpy())

    out_path = PROJECT_ROOT / "diagnostics" / "b1_b4_teacher_sanity_result.json"
    result["confusion_matrix"] = cm.tolist()
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote: {out_path}")


if __name__ == "__main__":
    main()
