"""Component C (Phase 0): correlate human (10-rater) uncertainty against
teacher uncertainty signals on the FERPlus majority validation split.

Modeled on tools/evaluate_teacher.py's shape: --config/--checkpoint YAML +
strict checkpoint load + build_dataloader + deterministic eval pass, but
outputs a per-sample CSV, a correlations.json (Pearson/Spearman + p-values),
one scatter PNG per signal, and a manifest -- instead of accuracy metrics.

Requires a config with votes_sum > 0 (FERPlus 10-rater vote distribution),
e.g. configs/FERPlus_8_teacher_vae_ce_kld.yaml (majority split, vae_head=True).

Usage:
    python tools/analyze_uncertainty_human.py \
        --config configs/FERPlus_8_teacher_vae_ce_kld.yaml \
        --checkpoint checkpoints/ferplus_processed_posterv2_best.pt
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_utils.builder import build_dataloader
from kd_common import extract_logits, extract_mu_logvar, load_checkpoint_checked
from kd_uncertainty import entropy_from_probabilities, mean_logvar, target_logvar, top2_logvar
from trials.models import create_model
from utils.configs import load_yaml

SIGNAL_NAMES = ("mean_logvar", "target_logvar", "top2_logvar", "entropy_t1", "entropy_t4")


def entropy_of_rows(probabilities, eps=1e-12):
    """Shannon entropy of each row of a [N, C] numpy array of probabilities."""
    clipped = np.clip(probabilities, eps, 1.0)
    return -(clipped * np.log(clipped)).sum(axis=1)


def sha256_of_file(path, chunk_size=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


@torch.no_grad()
def collect_signals(model, val_loader, device, max_batches=0):
    image_paths, labels_all = [], []
    human_entropy_batches = []
    signals = {name: [] for name in SIGNAL_NAMES}
    has_mu_logvar = None

    for batch_id, batch in enumerate(val_loader):
        if max_batches and batch_id >= max_batches:
            break
        idxs, images, labels, label_em, paths = batch
        if not torch.is_tensor(label_em) or label_em.numel() == 0:
            raise RuntimeError(
                "Batch has no vote distribution (label_em); the configured dataset/config "
                "must have votes_sum > 0 (FERPlus 10-rater votes)."
            )
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        output = model(images)
        logits = extract_logits(output)
        mu, logvar = extract_mu_logvar(output)
        if has_mu_logvar is None:
            has_mu_logvar = mu is not None and logvar is not None
            if not has_mu_logvar:
                print("Warning: teacher head exposes no mu/logvar; only entropy signals will be computed.")

        probabilities_t1 = torch.softmax(logits, dim=1)
        probabilities_t4 = torch.softmax(logits / 4.0, dim=1)

        image_paths.extend(list(paths))
        labels_all.extend(labels.detach().cpu().tolist())
        human_entropy_batches.append(entropy_of_rows(label_em.detach().cpu().numpy()))
        signals["entropy_t1"].append(entropy_from_probabilities(probabilities_t1).detach().cpu().numpy())
        signals["entropy_t4"].append(entropy_from_probabilities(probabilities_t4).detach().cpu().numpy())

        if has_mu_logvar:
            signals["mean_logvar"].append(mean_logvar(logvar).detach().cpu().numpy())
            signals["target_logvar"].append(
                target_logvar(logvar, labels, probabilities_t4).detach().cpu().numpy()
            )
            signals["top2_logvar"].append(top2_logvar(probabilities_t4, logvar).detach().cpu().numpy())

    human_entropy = np.concatenate(human_entropy_batches) if human_entropy_batches else np.array([])
    for name in list(signals.keys()):
        signals[name] = np.concatenate(signals[name]) if signals[name] else None
    return image_paths, labels_all, human_entropy, signals


def compute_correlations(human_entropy, signals):
    from scipy import stats as scipy_stats

    correlations = {}
    for name, values in signals.items():
        if values is None:
            continue
        pearson_r, pearson_p = scipy_stats.pearsonr(human_entropy, values)
        spearman_r, spearman_p = scipy_stats.spearmanr(human_entropy, values)
        correlations[name] = {
            "pearson_r": float(pearson_r),
            "pearson_p": float(pearson_p),
            "spearman_r": float(spearman_r),
            "spearman_p": float(spearman_p),
            "n": int(len(values)),
        }
    return correlations


def write_scatter_plots(human_entropy, signals, correlations, output_dir):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    best_signal = None
    if correlations:
        best_signal = max(correlations, key=lambda name: abs(correlations[name]["pearson_r"]))

    for name, values in signals.items():
        if values is None:
            continue
        is_best = name == best_signal
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.scatter(
            human_entropy, values, alpha=0.2,
            color="crimson" if is_best else "steelblue",
            s=12,
        )
        stats_for_signal = correlations.get(name, {})
        title = f"{name} vs human entropy"
        if is_best:
            title += " (best |pearson r|)"
        ax.set_title(title)
        ax.set_xlabel("Human vote-distribution entropy")
        ax.set_ylabel(name)
        if stats_for_signal:
            ax.text(
                0.02, 0.98,
                f"pearson r={stats_for_signal['pearson_r']:.3f} (p={stats_for_signal['pearson_p']:.2g})\n"
                f"spearman r={stats_for_signal['spearman_r']:.3f} (p={stats_for_signal['spearman_p']:.2g})",
                transform=ax.transAxes, va="top", fontsize=8,
            )
        fig.tight_layout()
        fig.savefig(output_dir / f"scatter_{name}.png", dpi=150)
        plt.close(fig)
    return best_signal


def write_per_sample_csv(path, image_paths, labels_all, human_entropy, signals):
    import csv

    fieldnames = ["image_id", "label", "human_entropy"] + list(signals.keys())
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for i, image_path in enumerate(image_paths):
            row = {
                "image_id": image_path,
                "label": labels_all[i],
                "human_entropy": float(human_entropy[i]),
            }
            for name, values in signals.items():
                row[name] = float(values[i]) if values is not None else ""
            writer.writerow(row)


def main(args):
    config = argparse.Namespace()
    load_yaml(config, str(args.config))
    device = torch.device("cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu")
    config.device = device
    config.num_workers = int(args.workers)
    if args.batch_size:
        config.batch_size = int(args.batch_size)
    config.cache_img = False

    if not getattr(config, "votes_sum", 0):
        raise RuntimeError(
            "This tool requires a config with votes_sum > 0 (the FERPlus 10-rater "
            f"vote distribution); got votes_sum={getattr(config, 'votes_sum', None)} "
            f"from {args.config}. Use e.g. configs/FERPlus_8_teacher_vae_ce_kld.yaml."
        )

    model = create_model(config).to(device)
    load_checkpoint_checked(model, args.checkpoint, device=device, strict=True)
    print("Teacher loaded with strict architecture validation.")
    model.eval()

    _train_loader, val_loader = build_dataloader(config)
    if val_loader is None:
        raise RuntimeError("Validation loader is required.")
    print(f"Validation samples: {len(val_loader.dataset)}")

    image_paths, labels_all, human_entropy, signals = collect_signals(
        model, val_loader, device, max_batches=args.max_batches
    )
    if len(human_entropy) == 0:
        raise RuntimeError("No samples were processed; check --max-batches and the dataset config.")

    correlations = compute_correlations(human_entropy, signals)

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    output_dir = Path(args.output_root) / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    write_per_sample_csv(output_dir / "per_sample.csv", image_paths, labels_all, human_entropy, signals)

    best_signal = write_scatter_plots(human_entropy, signals, correlations, output_dir)
    (output_dir / "correlations.json").write_text(
        json.dumps({"correlations": correlations, "best_signal_by_abs_pearson_r": best_signal}, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "tool": "tools/analyze_uncertainty_human.py",
        "timestamp": timestamp,
        "config_path": str(args.config),
        "config": {key: str(value) for key, value in vars(config).items() if key != "device"},
        "checkpoint_path": str(args.checkpoint),
        "checkpoint_sha256": sha256_of_file(args.checkpoint),
        "checkpoint_size_bytes": Path(args.checkpoint).stat().st_size,
        "num_samples": int(len(human_entropy)),
        "signals_computed": [name for name, values in signals.items() if values is not None],
        "note": "No git commit hash: this repository is not under version control.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote outputs to: {output_dir}")
    print(json.dumps({"correlations": correlations, "best_signal_by_abs_pearson_r": best_signal}, indent=2))


def parse_args():
    parser = argparse.ArgumentParser("Human-uncertainty vs. teacher-uncertainty correlation analysis")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("evaluation_runs"))
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
