import argparse
import copy
import csv
import itertools
import json
import os
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from PIL import Image
from torch.optim.swa_utils import AveragedModel, SWALR, update_bn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from torchvision import transforms
from tqdm.auto import tqdm

from kd_common import (
    AverageMeter,
    DistillationLoss,
    ModelEMA,
    SwanLabTracker,
    append_training_log,
    clean_state_dict,
    create_training_log,
    evaluate_detailed,
    extract_logits,
    extract_mu_logvar,
    labels_to_distribution,
    load_checkpoint_checked,
    measure_flops,
    mix_targets,
    mixup_batch,
    run_kd_smoke_test,
    save_checkpoint,
    set_seed,
    setup_run_logging,
    teacher_probabilities_from_logits,
    write_confusion_outputs,
    write_metrics_json,
    write_parameter_summary,
)
from models.mobilenetv2_plus import mobilenetv2_plus
from trails.posterv2.PosterV2_7cls import pyramid_trans_expr2


class RecorderMeter:
    def __init__(self, *args, **kwargs):
        pass


class RecorderMeter1:
    def __init__(self, *args, **kwargs):
        pass


class RAFDBDataset(Dataset):
    def __init__(self, root, metadata, folds, transform=None, frac=1.0, return_path=False):
        self.root = Path(root)
        self.transform = transform
        self.return_path = bool(return_path)
        df = pd.read_csv(metadata)
        if folds:
            df = df[df["fold"].isin(folds)]
        if frac != 1.0:
            df = df.sample(frac=float(frac), random_state=42)
        self.samples = [(self.root / row.path, int(row.label)) for row in df.itertuples()]

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        image_path, label = self.samples[index]
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Failed to read image: {image_path}")
        image = Image.fromarray(image[:, :, ::-1])
        if self.transform is not None:
            image = self.transform(image)
        if self.return_path:
            return image, label, str(image_path)
        return image, label


def build_teacher(teacher_ckpt, device, args):
    teacher = pyramid_trans_expr2(
        num_classes=7,
        vae=args.teacher_vae_head,
        layer_embedding=args.teacher_layer_embedding,
        votes_sum=args.teacher_votes_sum,
        vich=args.teacher_vich_head,
        vich_use_sampling=args.teacher_vich_use_sampling,
        vich_logvar_min=args.teacher_vich_logvar_min,
        vich_logvar_max=args.teacher_vich_logvar_max,
        vich_init_logvar_bias=args.teacher_vich_init_logvar_bias,
    )
    load_checkpoint_checked(teacher, teacher_ckpt, device=device, strict=True)
    print("Teacher loaded with strict architecture validation.")
    teacher.to(device)
    teacher.eval()
    for param in teacher.parameters():
        param.requires_grad = False
    return teacher


def build_student(args, device):
    if getattr(args, "student_arch", "plus") == "vanilla_mnv2":
        # Vanilla torchvision MobileNetV2 baseline (no ECA/GeM/LightLE/VICH) for the
        # architecture-frontier ablation. Plain-KD compatible: returns a bare logits
        # tensor, which extract_logits/DistillationLoss already handle. Any g2g/gate
        # flag is meaningless here (no mu/logvar) and must not be paired with it.
        from torchvision.models import mobilenet_v2
        student = mobilenet_v2(weights=None, width_mult=args.width_mult)
        if args.student_pretrained and args.width_mult == 1.0:
            local_ckpt = (
                Path(__file__).resolve().parent
                / "pretrained" / "hub" / "checkpoints" / "mobilenet_v2-b0353104.pth"
            )
            if local_ckpt.exists():
                sd = torch.load(local_ckpt, map_location="cpu", weights_only=False)
                student.load_state_dict(sd, strict=True)  # 1000-class, before head swap
                print(f"Vanilla MNv2: loaded ImageNet weights {local_ckpt}")
            else:
                print(f"Vanilla MNv2: local ImageNet checkpoint missing at {local_ckpt}; training from scratch.")
        elif args.student_pretrained:
            print("Vanilla MNv2: skipping ImageNet pretrained load because width_mult is not 1.0.")
        student.classifier[1] = nn.Linear(student.last_channel, 7)
        return student.to(device)
    head_type = args.student_head_type
    if args.student_vae_head and head_type == "linear":
        head_type = "vae"
    student = mobilenetv2_plus(
        num_classes=7,
        width_mult=args.width_mult,
        dropout_rate=args.dropout,
        layer_embedding=args.student_layer_embedding,
        vae_head=args.student_vae_head,
        head_type=head_type,
        lightweight_layer_embedding=args.student_lightweight_layer_embedding,
        lightweight_layer_embedding_layers=args.student_layer_embedding_layers,
        embedding_dim=args.student_embedding_dim,
        feature_adapter_dim=args.student_feature_adapter_dim,
        use_vich_sampling=args.use_vich_sampling,
        vich_logvar_min=args.vich_logvar_min,
        vich_logvar_max=args.vich_logvar_max,
        vich_init_logvar_bias=args.vich_init_logvar_bias,
    )
    if args.student_pretrained and args.width_mult == 1.0:
        student.load_pretrained_weights()
    elif args.student_pretrained:
        print("Skipping ImageNet pretrained load because width_mult is not 1.0.")
    return student.to(device)


def compute_class_weights_from_labels(
    labels,
    num_classes=7,
    mode="effective_number",
    effective_beta=0.9999,
):
    labels = torch.as_tensor(labels, dtype=torch.long)
    counts = torch.bincount(labels, minlength=int(num_classes)).float().clamp_min(1.0)
    if mode == "inverse_freq":
        weights = counts.sum() / counts
    elif mode == "effective_number":
        beta = float(effective_beta)
        weights = (1.0 - beta) / (1.0 - torch.pow(torch.full_like(counts, beta), counts))
    else:
        raise ValueError(f"Unsupported class weight mode: {mode}")
    return weights / weights.mean().clamp_min(1e-12)


def build_loaders(args):
    resize_size = int(args.resize_size) if args.resize_size else int(args.img_size)
    if args.augment_preset == "poster_var_rafdb":
        train_transform = transforms.Compose([
            transforms.Resize((resize_size, resize_size)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(args.rotation_degrees),
            transforms.RandomCrop(args.img_size),
            transforms.ColorJitter(
                brightness=args.color_jitter,
                contrast=args.color_jitter,
                saturation=args.color_jitter,
                hue=0.0,
            ) if args.color_jitter > 0 else transforms.Lambda(lambda x: x),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=args.random_erasing_p),
        ])
    else:
        train_transform = transforms.Compose([
            transforms.Resize((args.img_size, args.img_size)),
            transforms.RandAugment(num_ops=2, magnitude=args.ra_mag),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=args.random_erasing_p),
        ])
    if args.augment_preset == "poster_var_rafdb":
        val_transform = transforms.Compose([
            transforms.Resize((resize_size, resize_size)),
            transforms.CenterCrop(args.img_size),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    else:
        val_transform = transforms.Compose([
            transforms.Resize((args.img_size, args.img_size)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])
    if args.no_train_augment:
        # Structural determinism guard for --teacher-cache: force the train
        # loader onto the same deterministic pipeline as validation, rather
        # than trying to enumerate/disable each augmentation knob individually.
        train_transform = val_transform

    train_ds = RAFDBDataset(
        args.aligned_dir, args.metadata, args.train_folds, train_transform, args.train_frac,
        return_path=bool(args.teacher_cache),
    )
    val_ds = RAFDBDataset(args.aligned_dir, args.metadata, args.val_folds, val_transform, args.val_frac)
    train_sampler = None
    train_shuffle = True
    if args.balanced_sampler:
        train_labels = [label for _path, label in train_ds.samples]
        class_weights = compute_class_weights_from_labels(
            train_labels,
            num_classes=7,
            mode=args.class_weight_mode if args.class_weight_mode != "none" else "effective_number",
            effective_beta=args.class_weight_beta,
        )
        sample_weights = class_weights[torch.as_tensor(train_labels, dtype=torch.long)].double()
        train_sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True,
        )
        train_shuffle = False
    train_loader = DataLoader(
        train_ds,
        batch_size=args.batch_size,
        shuffle=train_shuffle,
        sampler=train_sampler,
        num_workers=args.workers,
        pin_memory=True,
        persistent_workers=args.workers > 0,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=True,
        persistent_workers=args.workers > 0,
    )
    return train_loader, val_loader


def _prepare_teacher_images(images, teacher_input_size):
    teacher_input_size = int(teacher_input_size)
    if teacher_input_size <= 0 or images.shape[-2:] == (teacher_input_size, teacher_input_size):
        return images
    return F.interpolate(
        images,
        size=(teacher_input_size, teacher_input_size),
        mode="bilinear",
        align_corners=False,
        antialias=True,
    )


def load_teacher_cache(cache_path):
    """Load a tools/cache_teacher_outputs.py .npz into a path->{logits,[mu,logvar]} lookup.

    Only meaningful with --no-train-augment (see build_loaders): the cache was
    built from a deterministic, augmentation-free pass, so it must only be
    matched against equally deterministic training images.
    """
    data = np.load(cache_path, allow_pickle=True)
    if "logits" not in data.files or "paths" not in data.files:
        raise RuntimeError(f"Teacher cache {cache_path} is missing required 'logits'/'paths' arrays.")
    has_mu_logvar = "mu" in data.files and "logvar" in data.files
    lookup = {}
    for i, path in enumerate(data["paths"]):
        entry = {"logits": data["logits"][i]}
        if has_mu_logvar:
            entry["mu"] = data["mu"][i]
            entry["logvar"] = data["logvar"][i]
        lookup[str(path)] = entry
    print(f"Loaded teacher cache: {cache_path} ({len(lookup)} samples, mu/logvar={has_mu_logvar}).")
    return lookup


def lookup_teacher_cache(cache, paths, device):
    try:
        entries = [cache[str(path)] for path in paths]
    except KeyError as exc:
        raise RuntimeError(
            f"Teacher cache is missing an entry for path {exc}; rebuild the cache for "
            "this exact dataset/split/fold selection."
        ) from exc
    logits = torch.as_tensor(np.stack([entry["logits"] for entry in entries]), dtype=torch.float32, device=device)
    if "mu" in entries[0]:
        mu = torch.as_tensor(np.stack([entry["mu"] for entry in entries]), dtype=torch.float32, device=device)
        logvar = torch.as_tensor(
            np.stack([entry["logvar"] for entry in entries]), dtype=torch.float32, device=device
        )
    else:
        mu = logvar = None
    return logits, mu, logvar


def _progress_iterator(loader, max_batches=0, desc="", enabled=True):
    total = len(loader)
    iterable = loader
    if max_batches:
        total = min(total, int(max_batches))
        iterable = itertools.islice(loader, total)
    if enabled:
        return tqdm(
            iterable,
            total=total,
            desc=desc,
            dynamic_ncols=True,
            leave=False,
            file=sys.__stdout__,
        )
    return iterable


class FeatureCaptureHook:
    """Capture one module output per forward pass without changing model APIs."""

    def __init__(self, module):
        self.value = None
        self.handle = module.register_forward_hook(self._hook)

    def _hook(self, _module, _inputs, output):
        self.value = output

    def clear(self):
        self.value = None

    def close(self):
        self.handle.remove()


def build_feature_projector(student, teacher, device):
    student_dim = int(getattr(student, "classifier_in_features", 0))
    teacher_dim = int(getattr(getattr(teacher, "VIT", None), "embed_dim", 0))
    if student_dim <= 0 or teacher_dim <= 0:
        raise RuntimeError(
            f"Cannot build feature projector: student_dim={student_dim}, teacher_dim={teacher_dim}."
        )
    projector = nn.Sequential(
        nn.LayerNorm(student_dim),
        nn.Linear(student_dim, teacher_dim),
    )
    return projector.to(device)


def feature_distillation_loss(student_features, teacher_features, projector, mode="mse_cosine"):
    if student_features is None or teacher_features is None:
        raise RuntimeError("Feature distillation requested, but captured features are missing.")
    student_features = student_features.flatten(1)
    teacher_features = teacher_features.detach().flatten(1)
    projected = projector(student_features)
    projected = F.normalize(projected.float(), dim=1)
    teacher_features = F.normalize(teacher_features.float(), dim=1)
    mode = str(mode).lower()
    if mode == "mse":
        return F.mse_loss(projected, teacher_features)
    if mode == "cosine":
        return 1.0 - F.cosine_similarity(projected, teacher_features, dim=1).mean()
    if mode == "mse_cosine":
        mse = F.mse_loss(projected, teacher_features)
        cosine = 1.0 - F.cosine_similarity(projected, teacher_features, dim=1).mean()
        return 0.5 * mse + 0.5 * cosine
    raise ValueError(f"Unsupported feature distillation mode: {mode}")


def train_one_epoch(
    teacher,
    student,
    loader,
    criterion,
    optimizer,
    device,
    mixup_alpha,
    max_batches=0,
    teacher_input_size=0,
    model_ema=None,
    epoch=0,
    total_epochs=0,
    show_progress=True,
    use_amp=False,
    scaler=None,
    student_feature_hook=None,
    teacher_feature_hook=None,
    feature_projector=None,
    feature_distill_weight=0.0,
    feature_distill_mode="mse_cosine",
    teacher_cache=None,
    teacher_temperature_scale=1.0,
):
    if teacher is not None:
        teacher.eval()
    student.train()
    amp_enabled = bool(use_amp and device.type == "cuda")
    losses = AverageMeter()
    hard_losses = AverageMeter()
    soft_losses = AverageMeter()
    vae_losses = AverageMeter()
    feature_losses = AverageMeter()
    accs = AverageMeter()
    g2g_meter = AverageMeter()
    ctkd_t_meter = AverageMeter()
    alpha_mean_meter = AverageMeter()
    effective_t_mean_meter = AverageMeter()
    alpha_min = alpha_max = None
    effective_t_min = effective_t_max = None
    use_feature_distill = (
        teacher is not None
        and float(feature_distill_weight) > 0.0
        and student_feature_hook is not None
        and teacher_feature_hook is not None
        and feature_projector is not None
    )
    # D1/D2/D3 all need raw teacher logits (with gradient-relevant structure
    # for CTKD); everything else keeps using the precomputed probabilities,
    # exactly as before.
    needs_raw_teacher_logits = criterion.logit_std_enable or criterion.adaptive_T_enable or criterion.ctkd_enable

    progress = _progress_iterator(
        loader,
        max_batches=max_batches,
        desc=f"epoch {epoch}/{total_epochs},train" if total_epochs else "train",
        enabled=show_progress,
    )
    for batch_id, batch in enumerate(progress):
        if teacher_cache is not None:
            images, labels, paths = batch
        else:
            images, labels = batch
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)

        if student_feature_hook is not None:
            student_feature_hook.clear()
        if teacher_feature_hook is not None:
            teacher_feature_hook.clear()

        teacher_mu = teacher_logvar = None
        original_teacher_logits = None
        teacher_probabilities = None
        teacher_features = None
        if teacher_cache is not None:
            original_teacher_logits, teacher_mu, teacher_logvar = lookup_teacher_cache(teacher_cache, paths, device)
            if teacher_temperature_scale != 1.0:
                original_teacher_logits = original_teacher_logits / teacher_temperature_scale
            teacher_probabilities = teacher_probabilities_from_logits(original_teacher_logits, criterion.temperature)
        elif teacher is not None:
            with torch.no_grad(), torch.cuda.amp.autocast(enabled=amp_enabled):
                teacher_images = _prepare_teacher_images(images, teacher_input_size)
                teacher_output = teacher(teacher_images)
                original_teacher_logits = extract_logits(teacher_output)
                if teacher_temperature_scale != 1.0:
                    # Phase B: post-hoc temperature-scale the teacher's logits by T*
                    # (fitted offline) so the student distills from the *calibrated*
                    # teacher distribution. Applied before teacher_probabilities so it
                    # feeds the soft-loss target; mu/logvar (g2g) are logit-space-
                    # independent and intentionally left unscaled.
                    original_teacher_logits = original_teacher_logits / teacher_temperature_scale
                teacher_mu, teacher_logvar = extract_mu_logvar(teacher_output)
                teacher_probabilities = teacher_probabilities_from_logits(
                    original_teacher_logits,
                    criterion.temperature,
                )
                teacher_features = teacher_feature_hook.value if use_feature_distill else None
        has_teacher = teacher_probabilities is not None

        with torch.cuda.amp.autocast(enabled=amp_enabled):
            if mixup_alpha > 0:
                mixed_images, mix_index, lam = mixup_batch(images, mixup_alpha, device)
                supervised_distribution = labels_to_distribution(
                    labels,
                    num_classes=7,
                    label_smoothing=criterion.label_smoothing,
                )
                mixed_supervised_targets = mix_targets(supervised_distribution, mix_index, lam)
                mixed_teacher_features = (
                    mix_targets(teacher_features, mix_index, lam)
                    if teacher_features is not None
                    else None
                )
                student_output = student(mixed_images)
                student_logits = extract_logits(student_output)

                criterion_kwargs = {"labels": mixed_supervised_targets}
                if has_teacher:
                    if needs_raw_teacher_logits:
                        criterion_kwargs["teacher_logits"] = mix_targets(original_teacher_logits, mix_index, lam)
                    else:
                        criterion_kwargs["teacher_probabilities"] = mix_targets(
                            teacher_probabilities, mix_index, lam
                        )
                    if teacher_mu is not None:
                        criterion_kwargs["teacher_mu"] = teacher_mu
                        criterion_kwargs["teacher_logvar"] = teacher_logvar
                loss, hard_loss, soft_loss, vae_loss = criterion(student_output, **criterion_kwargs)
                dominant_labels = labels if lam >= 0.5 else labels[mix_index]
                feature_target = mixed_teacher_features
            else:
                student_output = student(images)
                student_logits = extract_logits(student_output)

                criterion_kwargs = {"labels": labels}
                if has_teacher:
                    if needs_raw_teacher_logits:
                        criterion_kwargs["teacher_logits"] = original_teacher_logits
                    else:
                        criterion_kwargs["teacher_probabilities"] = teacher_probabilities
                    if teacher_mu is not None:
                        criterion_kwargs["teacher_mu"] = teacher_mu
                        criterion_kwargs["teacher_logvar"] = teacher_logvar
                loss, hard_loss, soft_loss, vae_loss = criterion(student_output, **criterion_kwargs)
                dominant_labels = labels
                feature_target = teacher_features

            feature_loss = loss.new_tensor(0.0)
            if use_feature_distill:
                feature_loss = feature_distillation_loss(
                    student_feature_hook.value,
                    feature_target,
                    feature_projector,
                    mode=feature_distill_mode,
                )
                loss = loss + float(feature_distill_weight) * feature_loss

        if amp_enabled and scaler is not None:
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            optimizer.step()
        if model_ema is not None:
            model_ema.update(student)

        preds = student_logits.argmax(dim=1)
        acc = (preds == dominant_labels).float().mean() * 100.0
        batch_size = images.size(0)
        losses.update(loss.item(), batch_size)
        hard_losses.update(hard_loss.item(), batch_size)
        soft_losses.update(soft_loss.item(), batch_size)
        vae_losses.update(vae_loss.item(), batch_size)
        feature_losses.update(feature_loss.item(), batch_size)
        accs.update(acc.item(), batch_size)

        if criterion.last_alpha_stats is not None:
            stats = criterion.last_alpha_stats
            alpha_min = stats["min"] if alpha_min is None else min(alpha_min, stats["min"])
            alpha_max = stats["max"] if alpha_max is None else max(alpha_max, stats["max"])
            alpha_mean_meter.update(stats["mean"], batch_size)
        if criterion.last_g2g_term is not None:
            g2g_meter.update(criterion.last_g2g_term, batch_size)
        if criterion.last_effective_T_stats is not None:
            stats = criterion.last_effective_T_stats
            effective_t_min = stats["min"] if effective_t_min is None else min(effective_t_min, stats["min"])
            effective_t_max = stats["max"] if effective_t_max is None else max(effective_t_max, stats["max"])
            effective_t_mean_meter.update(stats["mean"], batch_size)
        if criterion.last_ctkd_T is not None:
            ctkd_t_meter.update(criterion.last_ctkd_T, batch_size)

        if hasattr(progress, "set_postfix"):
            progress.set_postfix(
                loss=f"{losses.avg:.3f}",
                hard=f"{hard_losses.avg:.3f}",
                soft=f"{soft_losses.avg:.3f}",
                feat=f"{feature_losses.avg:.3f}",
                acc=f"{accs.avg:.2f}%",
            )

    diagnostics = {}
    if alpha_min is not None:
        diagnostics.update(alpha_min=alpha_min, alpha_mean=alpha_mean_meter.avg, alpha_max=alpha_max)
    if g2g_meter.count:
        diagnostics["g2g_term"] = g2g_meter.avg
    if effective_t_min is not None:
        diagnostics.update(
            effective_T_min=effective_t_min, effective_T_mean=effective_t_mean_meter.avg, effective_T_max=effective_t_max
        )
    if ctkd_t_meter.count:
        diagnostics["ctkd_T"] = ctkd_t_meter.avg

    return losses.avg, hard_losses.avg, soft_losses.avg, vae_losses.avg, feature_losses.avg, accs.avg, diagnostics


@torch.no_grad()
def validate(student, loader, device, max_batches=0, epoch=0, total_epochs=0, show_progress=True, use_amp=False):
    student.eval()
    amp_enabled = bool(use_amp and device.type == "cuda")
    losses = AverageMeter()
    accs = AverageMeter()
    progress = _progress_iterator(
        loader,
        max_batches=max_batches,
        desc=f"epoch {epoch}/{total_epochs},valid" if total_epochs else "valid",
        enabled=show_progress,
    )
    for batch_id, (images, labels) in enumerate(progress):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        with torch.cuda.amp.autocast(enabled=amp_enabled):
            logits = extract_logits(student(images))
            loss = F.cross_entropy(logits, labels)
        preds = logits.argmax(dim=1)
        acc = (preds == labels).float().mean() * 100.0
        batch_size = images.size(0)
        losses.update(loss.item(), batch_size)
        accs.update(acc.item(), batch_size)
        if hasattr(progress, "set_postfix"):
            progress.set_postfix(loss=f"{losses.avg:.3f}", acc=f"{accs.avg:.2f}%")
    return losses.avg, accs.avg


def iter_images(loader, device):
    for batch in loader:
        images = batch[0]
        yield images.to(device, non_blocking=True)


def main(args):
    # SwanLab is hard-disabled: --use-swanlab is still accepted for CLI/launcher
    # compatibility but has no effect, so it can never turn on unexpectedly.
    args.use_swanlab = False
    set_seed(args.seed)
    device = torch.device("cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu")
    run_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    save_dir = Path(args.save_root) / args.name / run_time
    save_dir.mkdir(parents=True, exist_ok=True)
    setup_run_logging(save_dir)

    print(f"RAF-DB run: {args.name}")
    print(f"Save dir: {save_dir}")
    print(f"Device: {device}")
    tracker = SwanLabTracker(
        enabled=args.use_swanlab,
        project=args.swanlab_project,
        experiment_name=args.name,
        config=vars(args),
        logdir=args.swanlab_logdir,
        mode=args.swanlab_mode,
        tags=["RAF-DB", "KD", "MobileNetV2Plus", "LightLE", "VICH"],
    )

    if args.ctkd_enable and args.mixup > 0:
        raise RuntimeError(
            "--ctkd-enable does not support --mixup > 0: mixup currently mixes softmax "
            "probabilities, but CTKD requires raw logits with gradient flowing through a "
            "differentiable softmax back into the learned temperature; mixing probabilities "
            "pre-empts that gradient path. Set --mixup 0 or disable CTKD."
        )
    if args.teacher_cache and not args.no_train_augment:
        raise RuntimeError(
            "--teacher-cache requires --no-train-augment: the cache was built from a "
            "deterministic, augmentation-free pass, so using it under augmented training "
            "would silently mismatch cached teacher outputs with augmented student inputs."
        )
    if args.teacher_cache and args.mixup > 0:
        raise RuntimeError("--teacher-cache does not support --mixup > 0; set --mixup 0.")
    if args.teacher_temperature_scale != 1.0 and (
        args.logit_std_enable or args.adaptive_t_enable or args.ctkd_enable
    ):
        if not args.allow_tempscale_with_mechanism:
            raise RuntimeError(
                "--teacher-temperature-scale != 1.0 cannot be combined with --logit-std-enable/"
                "--adaptive-t-enable/--ctkd-enable: those consume the raw teacher logits directly, so "
                "pre-scaling would double-count the temperature. Use it only with the plain soft-target "
                "KD path, or pass --allow-tempscale-with-mechanism if the pre-scale is a FIXED "
                "miscalibration injection rather than a swept variable (see that flag's help)."
            )
        print(
            f"WARNING: --teacher-temperature-scale {args.teacher_temperature_scale} combined with a "
            "temperature mechanism via --allow-tempscale-with-mechanism. The effective KD softmax is "
            "softmax(z / (T_prescale * T_mechanism)) -- the two temperatures COMPOSE MULTIPLICATIVELY. "
            "This is only interpretable when T_prescale is held FIXED across the compared arms and the "
            "mechanism flag is the single manipulated variable. Sweeping T_prescale here is DEGENERATE "
            "with sweeping the mechanism's temperature and must not be reported as a dose-response."
        )

    teacher = None if args.disable_kd else build_teacher(args.teacher_ckpt, device, args)
    teacher_cache = load_teacher_cache(args.teacher_cache) if args.teacher_cache else None
    student = build_student(args, device)
    student.input_resolution = int(args.img_size)
    train_loader, val_loader = build_loaders(args)
    print(f"Dataset loaded: {len(train_loader.dataset)} train, {len(val_loader.dataset)} val.")
    if args.balanced_sampler:
        print("Balanced sampler enabled for the training loader.")
    smoke_batch = next(iter(train_loader))
    smoke_images = smoke_batch[0]
    smoke_images = smoke_images[: min(2, smoke_images.shape[0])].to(device)
    run_kd_smoke_test(
        student,
        teacher,
        smoke_images,
        num_classes=7,
        teacher_images=_prepare_teacher_images(smoke_images, args.teacher_input_size),
    )
    flops = measure_flops(student, device, args.img_size)
    write_parameter_summary(
        student,
        save_dir,
        num_classes=7,
        head_type=args.student_head_type,
        layer_embedding_layers=args.student_layer_embedding_layers,
        flops=flops,
    )

    class_weights = None
    if args.class_weight_mode != "none":
        train_labels = [label for _path, label in train_loader.dataset.samples]
        class_weights = compute_class_weights_from_labels(
            train_labels,
            num_classes=7,
            mode=args.class_weight_mode,
            effective_beta=args.class_weight_beta,
        ).to(device)
        print(
            "Class-weighted CE enabled "
            f"({args.class_weight_mode}, beta={args.class_weight_beta}): "
            f"{[round(float(x), 4) for x in class_weights.detach().cpu()]}"
        )

    criterion = DistillationLoss(
        alpha=args.alpha,
        temperature=args.temperature,
        label_smoothing=args.label_smoothing,
        vae_kl_beta=args.student_vae_kl_beta,
        beta_vich=args.beta_vich,
        class_weights=class_weights,
        gate_enable=args.gate_enable,
        gate_uncertainty_source=args.gate_uncertainty_source,
        gate_norm=args.gate_norm,
        gate_alpha_lo=args.gate_alpha_lo,
        gate_alpha_hi=args.gate_alpha_hi,
        gate_k=args.gate_k,
        gate_tau=args.gate_tau,
        g2g_enable=args.g2g_enable,
        g2g_weight=args.g2g_weight,
        g2g_mode=args.g2g_mode,
        g2g_warmup_epochs=args.g2g_warmup_epochs,
        logit_std_enable=args.logit_std_enable,
        adaptive_T_enable=args.adaptive_t_enable,
        adaptive_T_gamma=args.adaptive_t_gamma,
        ctkd_enable=args.ctkd_enable,
        ctkd_t_min=args.ctkd_t_min,
        ctkd_t_max=args.ctkd_t_max,
        ctkd_grl_lambda_max=args.ctkd_grl_lambda_max,
    )
    criterion.to(device)
    feature_projector = None
    student_feature_hook = None
    teacher_feature_hook = None
    trainable_parameters = list(student.parameters())
    if args.ctkd_enable:
        trainable_parameters.extend(criterion.ctkd.parameters())
        print(f"CTKD enabled: learnable temperature in [{args.ctkd_t_min}, {args.ctkd_t_max}].")
    if args.feature_distill_weight > 0:
        if teacher is None:
            raise RuntimeError("--feature-distill-weight requires KD teacher; remove --disable-kd.")
        feature_projector = build_feature_projector(student, teacher, device)
        student_feature_hook = FeatureCaptureHook(student.feature_adapter)
        teacher_feature_hook = FeatureCaptureHook(teacher.VIT.se_block)
        trainable_parameters.extend(feature_projector.parameters())
        print(
            "Feature distillation enabled: "
            f"lambda={args.feature_distill_weight}, mode={args.feature_distill_mode}, "
            f"student_dim={getattr(student, 'classifier_in_features', None)}, "
            f"teacher_dim={getattr(teacher.VIT, 'embed_dim', None)}"
        )

    optimizer = optim.AdamW(trainable_parameters, lr=args.lr, weight_decay=args.weight_decay)
    amp_enabled = bool(args.use_amp and device.type == "cuda")
    scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)
    print(f"AMP enabled: {amp_enabled}")
    if args.scheduler_name == "exponential":
        scheduler = optim.lr_scheduler.ExponentialLR(optimizer, gamma=args.gamma)
    elif args.scheduler_name == "cosine":
        scheduler = optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=args.epochs,
            eta_min=args.min_lr,
        )
    else:
        scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(
            optimizer,
            T_0=args.scheduler_t0,
            T_mult=args.scheduler_t_mult,
        )
    swa_model = AveragedModel(student) if args.swa else None
    swa_scheduler = SWALR(optimizer, swa_lr=args.swa_lr) if args.swa else None
    model_ema = ModelEMA(student, decay=args.ema_decay, device=device) if args.ema else None

    with open(save_dir / "run_args.json", "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=2, default=str)
    with open(save_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(vars(args), f, indent=2, default=str)

    log_csv_path = save_dir / "training_log.csv"
    log_fields = create_training_log(log_csv_path)

    best_acc = -1.0
    best_epoch = None
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.time()
        criterion.set_epoch(epoch, args.epochs)
        train_loss, hard_loss, soft_loss, vae_loss, feature_loss, train_acc, phase0_diag = train_one_epoch(
            teacher,
            student,
            train_loader,
            criterion,
            optimizer,
            device,
            args.mixup,
            args.max_train_batches,
            args.teacher_input_size,
            model_ema,
            epoch=epoch,
            total_epochs=args.epochs,
            show_progress=args.progress,
            use_amp=amp_enabled,
            scaler=scaler,
            student_feature_hook=student_feature_hook,
            teacher_feature_hook=teacher_feature_hook,
            feature_projector=feature_projector,
            feature_distill_weight=args.feature_distill_weight,
            feature_distill_mode=args.feature_distill_mode,
            teacher_cache=teacher_cache,
            teacher_temperature_scale=args.teacher_temperature_scale,
        )
        if args.swa and epoch >= args.swa_start:
            swa_model.update_parameters(student)
            swa_scheduler.step()
        else:
            scheduler.step()
        val_loss, val_acc = validate(
            student,
            val_loader,
            device,
            args.max_val_batches,
            epoch=epoch,
            total_epochs=args.epochs,
            show_progress=args.progress,
            use_amp=amp_enabled,
        )
        elapsed = time.time() - epoch_start
        print(
            f"Epoch {epoch} ({elapsed:.1f}s): "
            f"Train Loss={train_loss:.4f} Hard={hard_loss:.4f} Soft={soft_loss:.4f} "
            f"AuxKL={vae_loss:.4f} Feat={feature_loss:.4f} "
            f"Train Acc={train_acc:.2f}% | Val Loss={val_loss:.4f} Acc={val_acc:.2f}%"
        )

        save_checkpoint(save_dir / "last_student.pth", student, val_acc, epoch, {"best_acc": best_acc})
        save_checkpoint(save_dir / "last_checkpoint.pth", student, val_acc, epoch, {"best_acc": best_acc})
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": train_loss,
            "hard_loss": hard_loss,
            "soft_loss": soft_loss,
            "aux_kl_loss": vae_loss,
            "feature_loss": feature_loss,
            "train_acc": train_acc,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "elapsed_sec": elapsed,
            "lr": optimizer.param_groups[0]["lr"],
        }
        epoch_metrics.update(phase0_diag)
        append_training_log(log_csv_path, log_fields, epoch_metrics)
        tracker.log(epoch_metrics)
        if val_acc > best_acc:
            best_acc = val_acc
            best_epoch = epoch
            save_checkpoint(save_dir / "best_student.pth", student, best_acc, epoch, {"teacher_ckpt": str(args.teacher_ckpt)})
            save_checkpoint(save_dir / "best_checkpoint.pth", student, best_acc, epoch, {"teacher_ckpt": str(args.teacher_ckpt)})
            print(f"Saved best student ({best_acc:.2f}%) at epoch {epoch}")

    if args.swa:
        print("Updating SWA BatchNorm statistics...")
        update_bn(iter_images(train_loader, device), swa_model, device=device)
        swa_loss, swa_acc = validate(swa_model, val_loader, device, args.max_val_batches)
        print(f"SWA Final Result: Loss={swa_loss:.4f} Acc={swa_acc:.2f}%")
        swa_ckpt_path = save_dir / "swa_student.pth"
        save_checkpoint(swa_ckpt_path, swa_model, swa_acc, extra={"teacher_ckpt": str(args.teacher_ckpt)})
        swa_metrics = evaluate_detailed(
            swa_model,
            val_loader,
            device,
            num_classes=7,
            max_batches=args.max_val_batches,
        )
        write_confusion_outputs(swa_metrics, save_dir, "confusion_matrix_swa")
        write_metrics_json(
            save_dir / "metrics_swa.json",
            "RAF-DB",
            7,
            swa_metrics,
            student,
            swa_ckpt_path,
            args.epochs,
            args.beta_vich,
            flops,
        )

    if model_ema is not None:
        ema_metrics = evaluate_detailed(
            model_ema.module,
            val_loader,
            device,
            num_classes=7,
            max_batches=args.max_val_batches,
        )
        ema_ckpt_path = save_dir / "ema_checkpoint.pth"
        save_checkpoint(
            ema_ckpt_path,
            model_ema.module,
            ema_metrics["accuracy"],
            epoch=args.epochs,
            extra={"teacher_ckpt": str(args.teacher_ckpt), "ema_decay": args.ema_decay},
        )
        write_confusion_outputs(ema_metrics, save_dir, "confusion_matrix_ema")
        write_metrics_json(
            save_dir / "metrics_ema.json",
            "RAF-DB",
            7,
            ema_metrics,
            student,
            ema_ckpt_path,
            args.epochs,
            args.beta_vich,
            flops,
        )
        print(f"EMA Final Result: Acc={ema_metrics['accuracy']:.2f}%")

    print("Writing final evaluation artifacts...")
    best_ckpt_path = save_dir / "best_checkpoint.pth"
    last_ckpt_path = save_dir / "last_checkpoint.pth"
    if best_ckpt_path.exists():
        best_ckpt = torch.load(best_ckpt_path, map_location=device, weights_only=False)
        student.load_state_dict(clean_state_dict(best_ckpt["model_state_dict"]), strict=True)
        best_metrics = evaluate_detailed(student, val_loader, device, num_classes=7, max_batches=args.max_val_batches)
        write_confusion_outputs(best_metrics, save_dir, "confusion_matrix")
        write_metrics_json(
            save_dir / "metrics_best.json",
            "RAF-DB",
            7,
            best_metrics,
            student,
            best_ckpt_path,
            best_ckpt.get("epoch", best_epoch),
            args.beta_vich,
            flops,
        )
    if last_ckpt_path.exists():
        last_ckpt = torch.load(last_ckpt_path, map_location=device, weights_only=False)
        student.load_state_dict(clean_state_dict(last_ckpt["model_state_dict"]), strict=True)
        last_metrics = evaluate_detailed(student, val_loader, device, num_classes=7, max_batches=args.max_val_batches)
        write_metrics_json(
            save_dir / "metrics_last.json",
            "RAF-DB",
            7,
            last_metrics,
            student,
            last_ckpt_path,
            last_ckpt.get("epoch", args.epochs),
            args.beta_vich,
            flops,
        )

    print(f"Training complete. Best Acc: {best_acc:.2f}% at epoch {best_epoch}")
    if student_feature_hook is not None:
        student_feature_hook.close()
    if teacher_feature_hook is not None:
        teacher_feature_hook.close()
    tracker.finish()


def parse_args():
    parser = argparse.ArgumentParser("RAF-DB POSTER-Var to MobileNetV2Plus KD")
    parser.add_argument("--teacher-ckpt", type=Path, default=Path(r"C:\Users\mfati\21mar\poster-var\logs\RAFDB\POSTERv2\2026-03-30-13-28-13\best.pt"))
    parser.add_argument("--teacher-vae-head", action="store_true")
    parser.add_argument("--teacher-vich-head", action="store_true")
    parser.add_argument("--teacher-layer-embedding", action="store_true", default=True)
    parser.add_argument("--no-teacher-layer-embedding", action="store_false", dest="teacher_layer_embedding")
    parser.add_argument("--teacher-votes-sum", type=int, default=0)
    parser.add_argument("--teacher-vich-use-sampling", action="store_true", default=True)
    parser.add_argument("--teacher-no-vich-sampling", action="store_false", dest="teacher_vich_use_sampling")
    parser.add_argument("--teacher-vich-logvar-min", type=float, default=-10.0)
    parser.add_argument("--teacher-vich-logvar-max", type=float, default=10.0)
    parser.add_argument("--teacher-vich-init-logvar-bias", type=float, default=-5.0)
    parser.add_argument(
        "--teacher-temperature-scale",
        type=float,
        default=1.0,
        help=(
            "Post-hoc temperature-scale the teacher logits by T* (original_teacher_logits /= T*) "
            "before computing soft targets. 1.0 = off (default). Phase B causality test: distill "
            "from a re-calibrated teacher without changing its architecture/recipe. Incompatible "
            "with --logit-std-enable/--adaptive-t-enable/--ctkd-enable (would double-scale the raw "
            "logits those consume) unless --allow-tempscale-with-mechanism is passed."
        ),
    )
    parser.add_argument(
        "--allow-tempscale-with-mechanism",
        action="store_true",
        help=(
            "Opt out of the --teacher-temperature-scale x mechanism mutual-exclusion guard. "
            "Legitimate use: the pre-scale is a FIXED, deliberate miscalibration INJECTION (same "
            "value in every compared arm) and the mechanism flag is the single manipulated variable "
            "-- e.g. taking a well-calibrated teacher, pre-scaling it to a target teacher-ECE, and "
            "asking whether a mechanism that was null on the calibrated teacher gains headroom. "
            "ILLEGITIMATE use: sweeping the pre-scale while a temperature mechanism is on -- the two "
            "temperatures compose multiplicatively, so the sweep is degenerate with the mechanism's "
            "own temperature and the resulting curve is uninterpretable as a dose-response."
        ),
    )
    parser.add_argument(
        "--teacher-input-size",
        type=int,
        default=0,
        help="Resize KD images for the teacher only; 0 uses the student input size.",
    )
    parser.add_argument("--aligned-dir", type=Path, default=Path(r"C:\dataset\rafdb_aligned"))
    parser.add_argument("--metadata", type=Path, default=Path(r"C:\dataset\rafdb_aligned\metadata_rafdb_poster_var.csv"))
    parser.add_argument("--train-folds", type=int, nargs="+", default=[2])
    parser.add_argument("--val-folds", type=int, nargs="+", default=[3])
    parser.add_argument("--train-frac", type=float, default=1.0)
    parser.add_argument("--val-frac", type=float, default=1.0)
    parser.add_argument("--name", type=str, default="RAFDB_kd_mbv2plus_posterhead")
    parser.add_argument("--save-root", type=Path, default=Path("kd_logs_rafdb"))
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--max-train-batches", type=int, default=0)
    parser.add_argument("--max-val-batches", type=int, default=0)
    parser.add_argument("--img-size", type=int, default=256)
    parser.add_argument("--resize-size", type=int, default=0)
    parser.add_argument("--augment-preset", choices=["kd", "poster_var_rafdb"], default="kd")
    parser.add_argument("--rotation-degrees", type=float, default=12.0)
    parser.add_argument("--color-jitter", type=float, default=0.2)
    parser.add_argument("--random-erasing-p", type=float, default=0.1)
    parser.add_argument("--ra-mag", type=int, default=7)
    parser.add_argument("--width-mult", type=float, default=1.0)
    parser.add_argument("--student-arch", choices=["plus", "vanilla_mnv2"], default="plus")
    parser.add_argument("--dropout", type=float, default=0.5)
    parser.add_argument("--student-pretrained", action="store_true", default=True)
    parser.add_argument("--no-student-pretrained", action="store_false", dest="student_pretrained")
    parser.add_argument("--student-head-type", choices=["linear", "vich", "vae", "le_vae"], default="linear")
    parser.add_argument("--student-layer-embedding", action="store_true")
    parser.add_argument("--student-lightweight-layer-embedding", action="store_true")
    parser.add_argument("--student-layer-embedding-layers", type=int, default=3)
    parser.add_argument("--student-vae-head", action="store_true")
    parser.add_argument("--student-embedding-dim", type=int, default=768)
    parser.add_argument("--student-feature-adapter-dim", type=int, default=0)
    parser.add_argument("--student-vae-kl-beta", type=float, default=0.001)
    parser.add_argument("--beta-vich", type=float, default=1e-4)
    parser.add_argument("--no-vich-sampling", action="store_false", dest="use_vich_sampling")
    parser.set_defaults(use_vich_sampling=True)
    parser.add_argument("--vich-logvar-min", type=float, default=-10.0)
    parser.add_argument("--vich-logvar-max", type=float, default=10.0)
    parser.add_argument("--vich-init-logvar-bias", type=float, default=-5.0)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--disable-kd", action="store_true")
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--temperature", type=float, default=6.0)
    parser.add_argument("--label-smoothing", type=float, default=0.2)
    parser.add_argument("--mixup", type=float, default=0.2)
    # --- Phase 0: Component A (uncertainty gate) ---
    parser.add_argument("--gate-enable", action="store_true")
    parser.add_argument(
        "--gate-uncertainty-source",
        choices=["mean_logvar", "target_logvar", "top2_logvar", "entropy", "oracle_error"],
        default="mean_logvar",
    )
    parser.add_argument("--gate-norm", choices=["batch", "running"], default="batch")
    parser.add_argument("--gate-alpha-lo", type=float, default=0.1)
    parser.add_argument("--gate-alpha-hi", type=float, default=0.7)
    parser.add_argument("--gate-k", type=float, default=2.0)
    parser.add_argument("--gate-tau", type=float, default=0.0)
    # --- Phase 0: Component B (Gaussian-to-Gaussian class-space distillation) ---
    parser.add_argument("--g2g-enable", action="store_true")
    parser.add_argument("--g2g-weight", type=float, default=0.0)
    parser.add_argument("--g2g-mode", choices=["kl", "w2"], default="kl")
    parser.add_argument("--g2g-warmup-epochs", type=int, default=0)
    # --- Phase 0: Component D (baseline KD methods) ---
    parser.add_argument("--logit-std-enable", action="store_true")
    parser.add_argument("--adaptive-t-enable", action="store_true")
    parser.add_argument("--adaptive-t-gamma", type=float, default=0.5)
    parser.add_argument("--ctkd-enable", action="store_true")
    parser.add_argument("--ctkd-t-min", type=float, default=1.0)
    parser.add_argument("--ctkd-t-max", type=float, default=8.0)
    parser.add_argument("--ctkd-grl-lambda-max", type=float, default=1.0)
    # --- Phase 0: Component E (teacher-output cache consumption) ---
    parser.add_argument(
        "--teacher-cache",
        type=Path,
        default=None,
        help=(
            "Path to a tools/cache_teacher_outputs.py .npz; if set, the teacher forward "
            "pass is skipped and cached logits/mu/logvar are used instead. Requires "
            "--no-train-augment and --mixup 0 (analysis/smoke runs only, not the main "
            "augmented training recipe)."
        ),
    )
    parser.add_argument(
        "--no-train-augment",
        action="store_true",
        help="Force the train loader onto the deterministic validation transform pipeline.",
    )
    parser.add_argument(
        "--feature-distill-weight",
        type=float,
        default=0.0,
        help="Training-only weight for teacher/student pre-classifier feature alignment.",
    )
    parser.add_argument(
        "--feature-distill-mode",
        choices=["mse", "cosine", "mse_cosine"],
        default="mse_cosine",
    )
    parser.add_argument("--use-amp", action="store_true", help="Enable CUDA mixed precision training for student KD.")
    parser.add_argument(
        "--class-weight-mode",
        choices=["none", "effective_number", "inverse_freq"],
        default="none",
        help="Apply class weights to the hard-label CE branch for imbalanced FER datasets.",
    )
    parser.add_argument("--class-weight-beta", type=float, default=0.9999)
    parser.add_argument(
        "--balanced-sampler",
        action="store_true",
        help="Use replacement sampling with class-balanced sample weights.",
    )
    parser.add_argument(
        "--scheduler-name",
        choices=["cosine", "cosine_warm_restarts", "exponential"],
        default="cosine_warm_restarts",
    )
    parser.add_argument("--min-lr", type=float, default=1e-6)
    parser.add_argument("--gamma", type=float, default=0.98)
    parser.add_argument("--scheduler-t0", type=int, default=10)
    parser.add_argument("--scheduler-t-mult", type=int, default=2)
    parser.add_argument("--swa", action="store_true")
    parser.add_argument("--swa-start", type=int, default=90)
    parser.add_argument("--swa-lr", type=float, default=1e-4)
    parser.add_argument("--ema", action="store_true")
    parser.add_argument("--ema-decay", type=float, default=0.999)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use-swanlab", action="store_true")
    parser.add_argument("--swanlab-project", type=str, default="Unified-FER-KD")
    parser.add_argument("--swanlab-mode", choices=["offline", "cloud"], default="offline")
    parser.add_argument("--swanlab-logdir", type=Path, default=Path("swanlog"))
    parser.add_argument("--no-progress", action="store_false", dest="progress", help="Disable live batch progress bars.")
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
