import argparse
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F
from tqdm.auto import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kd_common import extract_logits
from train_rafdb_kd import build_loaders, build_teacher


def entropy_from_probs(probs):
    return -(probs.clamp_min(1e-12) * probs.clamp_min(1e-12).log()).sum(dim=1)


@torch.no_grad()
def main():
    parser = argparse.ArgumentParser("Compare RAF-DB teacher soft targets")
    parser.add_argument("--teacher-a", type=Path, required=True)
    parser.add_argument("--teacher-b", type=Path, required=True)
    parser.add_argument("--name-a", type=str, default="teacher_a")
    parser.add_argument("--name-b", type=str, default="teacher_b")
    parser.add_argument("--aligned-dir", type=Path, default=Path("data/rafdb_aligned"))
    parser.add_argument("--metadata", type=Path, default=Path("data/rafdb_aligned/metadata_rafdb_poster_var.csv"))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--teacher-input-size", type=int, default=224)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=6.0)
    parser.add_argument("--output", type=Path, default=Path("teacher_soft_target_diagnosis.json"))
    parser.add_argument("--csv-output", type=Path, default=Path("teacher_soft_target_diagnosis_by_class.csv"))
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()

    device = torch.device("cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu")
    data_args = SimpleNamespace(
        aligned_dir=args.aligned_dir,
        metadata=args.metadata,
        train_folds=[2],
        val_folds=[3],
        train_frac=1.0,
        val_frac=1.0,
        batch_size=args.batch_size,
        workers=args.workers,
        img_size=args.img_size,
        resize_size=0,
        augment_preset="kd",
        rotation_degrees=12.0,
        color_jitter=0.2,
        random_erasing_p=0.1,
        ra_mag=7,
        balanced_sampler=False,
        class_weight_mode="effective_number",
        class_weight_beta=0.9999,
    )
    _train_loader, val_loader = build_loaders(data_args)

    teacher_args = SimpleNamespace(
        teacher_vae_head=True,
        teacher_vich_head=False,
        teacher_layer_embedding=True,
        teacher_votes_sum=0,
        teacher_vich_use_sampling=True,
        teacher_vich_logvar_min=-10.0,
        teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=-5.0,
    )

    print(f"Device: {device}")
    print(f"Loading {args.name_a}: {args.teacher_a}")
    teacher_a = build_teacher(args.teacher_a, device, teacher_args)
    print(f"Loading {args.name_b}: {args.teacher_b}")
    teacher_b = build_teacher(args.teacher_b, device, teacher_args)

    total = 0
    correct_a = 0
    correct_b = 0
    agree = 0
    both_correct = 0
    both_wrong = 0
    only_a_correct = 0
    only_b_correct = 0
    conf_a_sum = 0.0
    conf_b_sum = 0.0
    entropy_a_sum = 0.0
    entropy_b_sum = 0.0
    entropy_t_a_sum = 0.0
    entropy_t_b_sum = 0.0
    margin_a_sum = 0.0
    margin_b_sum = 0.0
    kl_a_to_b_sum = 0.0
    kl_b_to_a_sum = 0.0

    class_rows = {
        c: {
            "n": 0,
            "correct_a": 0,
            "correct_b": 0,
            "conf_a": 0.0,
            "conf_b": 0.0,
            "entropy_a": 0.0,
            "entropy_b": 0.0,
        }
        for c in range(7)
    }

    max_batches = int(args.max_batches)
    iterator = tqdm(val_loader, desc="compare teachers")
    for batch_id, (images, labels) in enumerate(iterator, start=1):
        if max_batches and batch_id > max_batches:
            break
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        logits_a = extract_logits(teacher_a(images)).float()
        logits_b = extract_logits(teacher_b(images)).float()

        probs_a = F.softmax(logits_a, dim=1)
        probs_b = F.softmax(logits_b, dim=1)
        probs_t_a = F.softmax(logits_a / float(args.temperature), dim=1)
        probs_t_b = F.softmax(logits_b / float(args.temperature), dim=1)

        pred_a = probs_a.argmax(dim=1)
        pred_b = probs_b.argmax(dim=1)
        top2_a = torch.topk(probs_a, k=2, dim=1).values
        top2_b = torch.topk(probs_b, k=2, dim=1).values

        is_correct_a = pred_a == labels
        is_correct_b = pred_b == labels
        batch_n = labels.numel()
        total += batch_n
        correct_a += is_correct_a.sum().item()
        correct_b += is_correct_b.sum().item()
        agree += (pred_a == pred_b).sum().item()
        both_correct += (is_correct_a & is_correct_b).sum().item()
        both_wrong += ((~is_correct_a) & (~is_correct_b)).sum().item()
        only_a_correct += (is_correct_a & (~is_correct_b)).sum().item()
        only_b_correct += ((~is_correct_a) & is_correct_b).sum().item()

        conf_a = probs_a.max(dim=1).values
        conf_b = probs_b.max(dim=1).values
        entropy_a = entropy_from_probs(probs_a)
        entropy_b = entropy_from_probs(probs_b)
        entropy_t_a = entropy_from_probs(probs_t_a)
        entropy_t_b = entropy_from_probs(probs_t_b)
        conf_a_sum += conf_a.sum().item()
        conf_b_sum += conf_b.sum().item()
        entropy_a_sum += entropy_a.sum().item()
        entropy_b_sum += entropy_b.sum().item()
        entropy_t_a_sum += entropy_t_a.sum().item()
        entropy_t_b_sum += entropy_t_b.sum().item()
        margin_a_sum += (top2_a[:, 0] - top2_a[:, 1]).sum().item()
        margin_b_sum += (top2_b[:, 0] - top2_b[:, 1]).sum().item()

        kl_a_to_b = F.kl_div(probs_t_a.log(), probs_t_b, reduction="none").sum(dim=1)
        kl_b_to_a = F.kl_div(probs_t_b.log(), probs_t_a, reduction="none").sum(dim=1)
        kl_a_to_b_sum += kl_a_to_b.sum().item()
        kl_b_to_a_sum += kl_b_to_a.sum().item()

        for c in range(7):
            mask = labels == c
            n = mask.sum().item()
            if n == 0:
                continue
            row = class_rows[c]
            row["n"] += n
            row["correct_a"] += is_correct_a[mask].sum().item()
            row["correct_b"] += is_correct_b[mask].sum().item()
            row["conf_a"] += conf_a[mask].sum().item()
            row["conf_b"] += conf_b[mask].sum().item()
            row["entropy_a"] += entropy_a[mask].sum().item()
            row["entropy_b"] += entropy_b[mask].sum().item()

    denom = max(1, total)
    result = {
        "n": total,
        "teacher_a": args.name_a,
        "teacher_a_ckpt": str(args.teacher_a),
        "teacher_b": args.name_b,
        "teacher_b_ckpt": str(args.teacher_b),
        "temperature": float(args.temperature),
        "max_batches": max_batches,
        "accuracy_a": 100.0 * correct_a / denom,
        "accuracy_b": 100.0 * correct_b / denom,
        "agreement": 100.0 * agree / denom,
        "both_correct": 100.0 * both_correct / denom,
        "both_wrong": 100.0 * both_wrong / denom,
        "only_a_correct": 100.0 * only_a_correct / denom,
        "only_b_correct": 100.0 * only_b_correct / denom,
        "confidence_a": conf_a_sum / denom,
        "confidence_b": conf_b_sum / denom,
        "entropy_a": entropy_a_sum / denom,
        "entropy_b": entropy_b_sum / denom,
        "entropy_t_a": entropy_t_a_sum / denom,
        "entropy_t_b": entropy_t_b_sum / denom,
        "top1_margin_a": margin_a_sum / denom,
        "top1_margin_b": margin_b_sum / denom,
        "kl_t_a_to_b": kl_a_to_b_sum / denom,
        "kl_t_b_to_a": kl_b_to_a_sum / denom,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.csv_output, "w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "class",
            "n",
            "accuracy_a",
            "accuracy_b",
            "confidence_a",
            "confidence_b",
            "entropy_a",
            "entropy_b",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for c, row in class_rows.items():
            n = max(1, row["n"])
            writer.writerow({
                "class": c,
                "n": row["n"],
                "accuracy_a": 100.0 * row["correct_a"] / n,
                "accuracy_b": 100.0 * row["correct_b"] / n,
                "confidence_a": row["conf_a"] / n,
                "confidence_b": row["conf_b"] / n,
                "entropy_a": row["entropy_a"] / n,
                "entropy_b": row["entropy_b"] / n,
            })

    print(json.dumps(result, indent=2))
    print(f"Wrote: {args.output}")
    print(f"Wrote: {args.csv_output}")


if __name__ == "__main__":
    main()
