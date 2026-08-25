import argparse
import json
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_utils.builder import build_dataloader
from kd_common import (
    evaluate_detailed,
    load_checkpoint_checked,
    measure_flops,
    write_confusion_outputs,
)
from trials.models import create_model
from utils.configs import load_yaml


def main(args):
    config = argparse.Namespace()
    load_yaml(config, str(args.config))
    config.device = torch.device("cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu")
    config.num_workers = int(args.workers)
    config.batch_size = int(args.batch_size or config.batch_size)
    config.cache_img = False

    model = create_model(config).to(config.device)
    checkpoint = load_checkpoint_checked(model, args.checkpoint, device=config.device, strict=True)
    train_loader, val_loader = build_dataloader(config)
    if val_loader is None:
        raise RuntimeError("Validation loader is required.")
    if args.expected_train_samples and len(train_loader.dataset) != args.expected_train_samples:
        raise RuntimeError(
            f"Train sample mismatch: expected {args.expected_train_samples}, got {len(train_loader.dataset)}."
        )
    if args.expected_val_samples and len(val_loader.dataset) != args.expected_val_samples:
        raise RuntimeError(
            f"Validation sample mismatch: expected {args.expected_val_samples}, got {len(val_loader.dataset)}."
        )

    metrics = evaluate_detailed(
        model,
        val_loader,
        config.device,
        num_classes=config.num_classes,
        max_batches=args.max_val_batches,
    )
    output_dir = Path(args.output_dir or Path(args.checkpoint).parent)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_confusion_outputs(metrics, output_dir, "confusion_matrix")
    flops = measure_flops(model, config.device, config.val_size)
    total_params = sum(parameter.numel() for parameter in model.parameters())
    head_params = 2 * (768 * int(config.num_classes) + int(config.num_classes))
    payload = {
        "dataset": config.dataset_name,
        "classes": int(config.num_classes),
        "model": "POSTERv2",
        "head": "class-level VAE",
        "layer_embedding": bool(config.layer_embedding),
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "params_m": total_params / 1e6,
        "flops_g": None if flops is None else flops / 1e9,
        "size_mb": Path(args.checkpoint).stat().st_size / (1024 * 1024),
        "best_epoch": checkpoint.get("epoch"),
        "ce_kld_beta": float(config.ce_kld_beta),
        "feature_dim": 768,
        "vae_head_params": head_params,
        "checkpoint": str(args.checkpoint),
    }
    (output_dir / "metrics_best.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (output_dir / "parameter_count.txt").write_text(
        "\n".join([
            f"total_params: {total_params}",
            f"total_params_m: {total_params / 1e6:.6f}",
            f"class_level_vae_head_params: {head_params}",
            f"expected_formula: 2 * (768 * {config.num_classes} + {config.num_classes})",
            f"flops_g: {'' if flops is None else flops / 1e9}",
        ]) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))


def parse_args():
    parser = argparse.ArgumentParser("Evaluate unified POSTERv2 teacher")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--expected-train-samples", type=int, default=0)
    parser.add_argument("--expected-val-samples", type=int, default=0)
    parser.add_argument("--max-val-batches", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
