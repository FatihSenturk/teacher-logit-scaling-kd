"""Component E (Phase 0): cache a teacher's per-sample logits/mu/logvar for a
dataset split to a single .npz, for reuse by augmentation-free analysis
tools (e.g. tools/analyze_uncertainty_human.py) and Component C-style work.

HARD CONSTRAINT: this cache is only valid for a deterministic, augmentation-
free transform pipeline (resize + optional center-crop, no random ops).
This tool always forces the dataset's "valid" transform (see
dataset_utils/transforms.py::get_data_transforms) for whichever split is
requested -- never the augmented "train" transform -- and labels the output
filename/manifest accordingly. train_*_kd.py's --teacher-cache flag must
hard-error if training augmentation is enabled while a cache is supplied
(see PHASE0_NOTES.md); this cache must never be used for the main,
augmented training recipe.

Only supports datasets backed by dataset_utils.image_dataset.ImageDataset
(RAFDB, FER2013/FERPlus, etc. -- see dataset_utils/builder.py's routing).
AffectNet+ uses a different dataset/transform pipeline and is out of scope
here; using this tool on it raises NotImplementedError rather than silently
producing an unlabeled or wrong cache.

Usage:
    python tools/cache_teacher_outputs.py \
        --config configs/RAFDB_posterv2_vich.yaml \
        --checkpoint checkpoints/teacher_vich9237_best.pt \
        --split val
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dataset_utils.image_dataset import ImageDataset
from dataset_utils.transforms import get_data_transforms
from kd_common import extract_logits, extract_mu_logvar, load_checkpoint_checked
from trials.models import create_model
from utils.configs import load_yaml

_IMAGE_DATASET_NAMES = {
    "CUB200-2011", "ISIC2024", "SCUTv2", "AffectNet", "RAFDB", "AffectNet_RAFDB", "FER2013",
}


def sha256_of_file(path, chunk_size=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_deterministic_loader(config, split, batch_size, workers):
    dataset_name = str(getattr(config, "dataset_name", ""))
    if dataset_name not in _IMAGE_DATASET_NAMES:
        raise NotImplementedError(
            "tools/cache_teacher_outputs.py only supports "
            f"dataset_utils.image_dataset.ImageDataset-backed datasets ({sorted(_IMAGE_DATASET_NAMES)}); "
            f"got dataset_name={dataset_name!r} (e.g. AffectNet+ uses a different dataset/transform "
            "pipeline and is not wired here)."
        )
    # Always the deterministic "valid" transform -- regardless of which
    # physical split (train-fold or val-fold rows) is being cached.
    deterministic_transform = get_data_transforms(config)["valid"]

    if split == "train":
        root, folds, frac, size = config.train_root, config.train_folds, config.train_frac, config.train_size
    else:
        root, folds, frac, size = config.val_root, config.val_folds, config.val_frac, config.val_size

    dataset = ImageDataset(
        root=root,
        transform=deterministic_transform,
        data_size=size,
        cache_img=False,
        csv=config.metadata,
        folds=folds,
        frac=frac,
        votes_sum=getattr(config, "votes_sum", 0),
    )
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=workers)
    return loader, dataset_name, str(deterministic_transform)


@torch.no_grad()
def cache_outputs(model, loader, device, max_batches=0):
    all_logits, all_mu, all_logvar, all_labels, all_paths = [], [], [], [], []
    has_mu_logvar = None
    for batch_id, batch in enumerate(loader):
        if max_batches and batch_id >= max_batches:
            break
        _idxs, images, labels, _label_em, paths = batch
        images = images.to(device, non_blocking=True)
        output = model(images)
        logits = extract_logits(output)
        mu, logvar = extract_mu_logvar(output)
        if has_mu_logvar is None:
            has_mu_logvar = mu is not None and logvar is not None
            if not has_mu_logvar:
                print("Warning: teacher head exposes no mu/logvar; caching logits only.")
        all_logits.append(logits.detach().cpu().numpy())
        if has_mu_logvar:
            all_mu.append(mu.detach().cpu().numpy())
            all_logvar.append(logvar.detach().cpu().numpy())
        all_labels.append(labels.detach().cpu().numpy())
        all_paths.extend(list(paths))

    logits_arr = np.concatenate(all_logits, axis=0)
    labels_arr = np.concatenate(all_labels, axis=0)
    mu_arr = np.concatenate(all_mu, axis=0) if has_mu_logvar else None
    logvar_arr = np.concatenate(all_logvar, axis=0) if has_mu_logvar else None
    return logits_arr, mu_arr, logvar_arr, labels_arr, all_paths


def main(args):
    config = argparse.Namespace()
    load_yaml(config, str(args.config))
    device = torch.device("cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu")
    config.device = device
    config.cache_img = False

    model = create_model(config).to(device)
    load_checkpoint_checked(model, args.checkpoint, device=device, strict=True)
    print("Teacher loaded with strict architecture validation.")
    model.eval()

    batch_size = int(args.batch_size or getattr(config, "batch_size", 32))
    loader, dataset_name, transform_repr = build_deterministic_loader(
        config, args.split, batch_size, int(args.workers)
    )
    print(f"Caching '{args.split}' split ({dataset_name}): {len(loader.dataset)} samples, no augmentation.")

    logits, mu, logvar, labels, paths = cache_outputs(model, loader, device, max_batches=args.max_batches)
    if logits.shape[0] == 0:
        raise RuntimeError("No samples were processed; check --max-batches and the dataset config.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{dataset_name}_{args.split}_noaugment"
    npz_path = args.output_dir / f"{stem}.npz"
    payload = {
        "logits": logits,
        "labels": labels,
        "paths": np.array(paths, dtype=object),
        "class_order": np.arange(logits.shape[1]),
    }
    if mu is not None:
        payload["mu"] = mu
        payload["logvar"] = logvar
    np.savez(npz_path, **payload)

    manifest = {
        "tool": "tools/cache_teacher_outputs.py",
        "checkpoint_path": str(args.checkpoint),
        "checkpoint_sha256": sha256_of_file(args.checkpoint),
        "config_path": str(args.config),
        "dataset_name": dataset_name,
        "split": args.split,
        "transform": transform_repr,
        "deterministic": True,
        "augmentation": "none",
        "num_classes": int(logits.shape[1]),
        "num_samples": int(logits.shape[0]),
        "has_mu_logvar": mu is not None,
        "npz_path": str(npz_path),
        "npz_load_note": "paths is an object array; load with np.load(path, allow_pickle=True).",
        "note": "No git commit hash: this repository is not under version control.",
    }
    manifest_path = args.output_dir / f"{stem}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {npz_path}")
    print(f"Wrote {manifest_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        "Cache teacher logits/mu/logvar for a deterministic (no-augmentation) dataset split"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "val"], default="val")
    parser.add_argument("--output-dir", type=Path, default=Path("teacher_output_cache"))
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--max-batches", type=int, default=0)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
