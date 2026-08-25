import argparse
import json
import os
import random
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.optim.swa_utils import AveragedModel, SWALR, update_bn
from tqdm import tqdm

from dataset_utils.builder import build_dataloader
from dataset_utils.transforms import get_data_transforms
from kd_common import (
    AverageMeter,
    DistillationLoss,
    ModelEMA,
    SwanLabTracker,
    append_training_log,
    create_training_log,
    evaluate_detailed,
    extract_logits,
    extract_mu_logvar,
    labels_to_distribution,
    load_checkpoint_checked,
    measure_flops,
    mix_targets,
    mixup_batch,
    normalize_probability_targets,
    run_kd_smoke_test,
    save_checkpoint,
    setup_run_logging,
    teacher_probabilities_from_logits,
    unpack_image_batch_with_targets,
    write_confusion_outputs,
    write_metrics_json,
    write_parameter_summary,
)
from models.mobilenetv2_plus import mobilenetv2_plus
from trials.models import create_model
from utils.configs import load_yaml, seed_everything


def unpack_batch(batch):
    return unpack_image_batch_with_targets(batch)


def build_teacher(config_path, checkpoint_path, device):
    teacher_args = argparse.Namespace()
    load_yaml(teacher_args, str(config_path))
    teacher_args.device = device
    teacher = create_model(teacher_args)

    load_checkpoint_checked(teacher, checkpoint_path, device="cpu", strict=True)
    print("Teacher loaded with strict architecture validation.")

    teacher.to(device)
    teacher.eval()
    for param in teacher.parameters():
        param.requires_grad = False
    return teacher, teacher_args


def build_student(
    num_classes,
    width_mult,
    dropout,
    pretrained,
    device,
    layer_embedding=False,
    vae_head=False,
    head_type="linear",
    lightweight_layer_embedding=False,
    lightweight_layer_embedding_layers=3,
    embedding_dim=None,
    use_vich_sampling=True,
    vich_logvar_min=-10.0,
    vich_logvar_max=10.0,
    vich_init_logvar_bias=-5.0,
):
    if vae_head and head_type == "linear":
        head_type = "vae"
    student = mobilenetv2_plus(
        num_classes=int(num_classes),
        width_mult=float(width_mult),
        dropout_rate=float(dropout),
        layer_embedding=bool(layer_embedding),
        vae_head=bool(vae_head),
        head_type=head_type,
        lightweight_layer_embedding=bool(lightweight_layer_embedding),
        lightweight_layer_embedding_layers=int(lightweight_layer_embedding_layers),
        embedding_dim=embedding_dim,
        use_vich_sampling=bool(use_vich_sampling),
        vich_logvar_min=float(vich_logvar_min),
        vich_logvar_max=float(vich_logvar_max),
        vich_init_logvar_bias=float(vich_init_logvar_bias),
    )
    if pretrained and float(width_mult) == 1.0:
        student.load_pretrained_weights()
    elif pretrained:
        print("Skipping ImageNet pretrained load because width_mult is not 1.0.")
    student.to(device)
    return student


def build_data_args(config_path, args):
    data_args = argparse.Namespace()
    load_yaml(data_args, str(config_path))

    data_args.batch_size = int(args.batch_size)
    data_args.num_workers = int(args.workers)
    data_args.cache_img = bool(args.cache_img)
    data_args.train_shuffle = True
    data_args.device = args.device

    if args.num_classes is not None:
        data_args.num_classes = int(args.num_classes)
        data_args.affectnet_plus_label_mode = int(args.num_classes)

    if args.train_root is not None:
        data_args.train_root = args.train_root
    if args.val_root is not None:
        data_args.val_root = args.val_root
    if args.metadata is not None:
        data_args.metadata = args.metadata
    if args.train_frac is not None:
        data_args.train_frac = float(args.train_frac)
    if args.val_frac is not None:
        data_args.val_frac = float(args.val_frac)

    data_args.sample_numbers = (
        int(args.sample_numbers)
        if args.sample_numbers is not None
        else int(getattr(data_args, "sample_numbers", 0))
    )
    data_args.affectnet_plus_cache_index = bool(args.cache_index)
    data_args.affectnet_plus_cache_dir = args.cache_dir
    data_args.affectnet_plus_refresh_cache = bool(args.refresh_cache)
    data_args.affectnet_plus_use_soft_label = bool(args.use_soft_label)
    data_args.train_size = int(args.img_size)
    data_args.val_size = int(args.img_size)
    resize_size = int(args.resize_size)
    data_args.train_resize_size = resize_size if resize_size > 0 else int(args.img_size)
    data_args.unified_resolution_crop = bool(args.unified_resolution_crop)
    data_args.aug_color_jitter = float(args.color_jitter)
    data_args.aug_random_erasing_p = float(args.random_erasing_p)
    return data_args


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

    Only meaningful with --no-train-augment: the cache was built from a
    deterministic, augmentation-free pass, so it must only be matched
    against equally deterministic training images.
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


def train_one_epoch(
    teacher,
    student,
    loader,
    criterion,
    optimizer,
    device,
    epoch,
    mixup_alpha,
    num_classes,
    supervision,
    teacher_input_size,
    model_ema=None,
    max_batches=0,
    show_progress=True,
    use_amp=False,
    scaler=None,
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
    vae_kl_losses = AverageMeter()
    accs = AverageMeter()
    g2g_meter = AverageMeter()
    ctkd_t_meter = AverageMeter()
    alpha_mean_meter = AverageMeter()
    effective_t_mean_meter = AverageMeter()
    alpha_min = alpha_max = None
    effective_t_min = effective_t_max = None
    needs_raw_teacher_logits = criterion.logit_std_enable or criterion.adaptive_T_enable or criterion.ctkd_enable

    pbar = tqdm(
        loader,
        desc=f"epoch {epoch},kd-train",
        dynamic_ncols=True,
        leave=False,
        disable=not show_progress,
        file=sys.__stdout__,
    )
    for batch_id, batch in enumerate(pbar):
        if max_batches and batch_id >= max_batches:
            break
        _idxs, images, labels, label_em, paths = batch
        soft_targets = label_em if torch.is_tensor(label_em) and label_em.numel() > 0 else None
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        if soft_targets is not None:
            soft_targets = normalize_probability_targets(
                soft_targets.to(device, non_blocking=True)
            )

        if supervision == "soft":
            if soft_targets is None:
                raise RuntimeError("Soft supervision requested, but this batch has no vote distribution.")
            supervised_targets = soft_targets
        elif supervision == "auto" and soft_targets is not None:
            supervised_targets = soft_targets
        else:
            supervised_targets = labels

        teacher_mu = teacher_logvar = None
        original_teacher_logits = None
        teacher_probabilities = None
        if teacher_cache is not None:
            original_teacher_logits, teacher_mu, teacher_logvar = lookup_teacher_cache(teacher_cache, paths, device)
            # Post-hoc teacher calibration: divide the raw teacher logits by a fixed scale BEFORE
            # any softmax, so the distribution actually distilled is softmax(z / (T * tau_KD)).
            # Mirrors train_rafdb_kd.py:471-485 exactly so the two datasets' dose-response
            # experiments are the same manipulation. Orthogonal to gate/g2g (those read mu/logvar).
            if teacher_temperature_scale != 1.0:
                original_teacher_logits = original_teacher_logits / teacher_temperature_scale
            teacher_probabilities = teacher_probabilities_from_logits(original_teacher_logits, criterion.temperature)
        elif teacher is not None:
            with torch.no_grad(), torch.cuda.amp.autocast(enabled=amp_enabled):
                teacher_images = _prepare_teacher_images(images, teacher_input_size)
                teacher_output = teacher(teacher_images)
                original_teacher_logits = extract_logits(teacher_output)
                teacher_mu, teacher_logvar = extract_mu_logvar(teacher_output)
                if teacher_temperature_scale != 1.0:
                    original_teacher_logits = original_teacher_logits / teacher_temperature_scale
                teacher_probabilities = teacher_probabilities_from_logits(
                    original_teacher_logits,
                    criterion.temperature,
                )
        has_teacher = teacher_probabilities is not None

        with torch.cuda.amp.autocast(enabled=amp_enabled):
            if mixup_alpha > 0:
                mixed_images, mix_index, lam = mixup_batch(images, mixup_alpha, device)
                if supervised_targets.ndim == 1:
                    supervised_distribution = labels_to_distribution(
                        supervised_targets,
                        num_classes,
                        criterion.label_smoothing,
                    )
                else:
                    supervised_distribution = supervised_targets
                mixed_supervised_targets = mix_targets(supervised_distribution, mix_index, lam)
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
                loss, hard_loss, soft_loss, vae_kl_loss = criterion(student_output, **criterion_kwargs)
                dominant_labels = labels if lam >= 0.5 else labels[mix_index]
            else:
                student_output = student(images)
                student_logits = extract_logits(student_output)

                criterion_kwargs = {"labels": supervised_targets}
                if has_teacher:
                    if needs_raw_teacher_logits:
                        criterion_kwargs["teacher_logits"] = original_teacher_logits
                    else:
                        criterion_kwargs["teacher_probabilities"] = teacher_probabilities
                    if teacher_mu is not None:
                        criterion_kwargs["teacher_mu"] = teacher_mu
                        criterion_kwargs["teacher_logvar"] = teacher_logvar
                loss, hard_loss, soft_loss, vae_kl_loss = criterion(student_output, **criterion_kwargs)
                dominant_labels = labels

        optimizer.zero_grad(set_to_none=True)
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
        batch_size = labels.size(0)
        losses.update(loss.item(), batch_size)
        hard_losses.update(hard_loss.item(), batch_size)
        soft_losses.update(soft_loss.item(), batch_size)
        vae_kl_losses.update(vae_kl_loss.item(), batch_size)
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

        if show_progress:
            pbar.set_postfix(
                loss=f"{losses.avg:.4f}",
                hard=f"{hard_losses.avg:.4f}",
                soft=f"{soft_losses.avg:.4f}",
                aux_kl=f"{vae_kl_losses.avg:.4f}",
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

    return losses.avg, hard_losses.avg, soft_losses.avg, vae_kl_losses.avg, accs.avg, diagnostics


@torch.no_grad()
def validate(student, loader, device, epoch, max_batches=0, show_progress=True, use_amp=False):
    student.eval()
    amp_enabled = bool(use_amp and device.type == "cuda")
    losses = AverageMeter()
    accs = AverageMeter()

    pbar = tqdm(
        loader,
        desc=f"epoch {epoch},kd-valid",
        dynamic_ncols=True,
        leave=False,
        disable=not show_progress,
        file=sys.__stdout__,
    )
    for batch_id, batch in enumerate(pbar):
        if max_batches and batch_id >= max_batches:
            break
        images, labels, _soft_targets = unpack_batch(batch)
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        with torch.cuda.amp.autocast(enabled=amp_enabled):
            logits = extract_logits(student(images))
            loss = F.cross_entropy(logits, labels)
        preds = logits.argmax(dim=1)
        acc = (preds == labels).float().mean() * 100.0
        batch_size = labels.size(0)
        losses.update(loss.item(), batch_size)
        accs.update(acc.item(), batch_size)
        if show_progress:
            pbar.set_postfix(loss=f"{losses.avg:.4f}", acc=f"{accs.avg:.2f}%")

    return losses.avg, accs.avg


def iter_images(loader, device):
    for batch in loader:
        images, _labels, _soft_targets = unpack_batch(batch)
        yield images.to(device, non_blocking=True)


def main(args):
    # SwanLab is hard-disabled: --use-swanlab is still accepted for CLI/launcher
    # compatibility but has no effect, so it can never turn on unexpectedly.
    args.use_swanlab = False
    seed_everything(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    args.device = torch.device("cuda:0" if torch.cuda.is_available() and not args.cpu else "cpu")
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
                "miscalibration injection rather than a swept variable."
            )
        print(
            f"WARNING: --teacher-temperature-scale {args.teacher_temperature_scale} combined with a "
            "temperature mechanism via --allow-tempscale-with-mechanism. Effective KD softmax is "
            "softmax(z / (T_prescale * T_mechanism)) -- the temperatures COMPOSE MULTIPLICATIVELY, so "
            "this is only interpretable with T_prescale FIXED across the compared arms."
        )

    run_name = args.name
    if run_name is None:
        run_name = f"AffectNetPlus_{args.num_classes or 'cfg'}cls_kd_mbv2plus"
    run_time = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    save_dir = Path(args.save_root) / run_name / run_time
    save_dir.mkdir(parents=True, exist_ok=True)
    setup_run_logging(save_dir)

    print(f"KD run: {run_name}")
    print(f"Save dir: {save_dir}")
    print(f"Device: {args.device}")

    teacher, teacher_args = build_teacher(args.teacher_config, args.teacher_ckpt, args.device)
    if args.num_classes is None:
        args.num_classes = int(teacher_args.num_classes)
    dataset_name = args.dataset_name or str(teacher_args.dataset_name)
    tracker = SwanLabTracker(
        enabled=args.use_swanlab,
        project=args.swanlab_project,
        experiment_name=run_name,
        config=vars(args),
        logdir=args.swanlab_logdir,
        mode=args.swanlab_mode,
        tags=[dataset_name, "KD", "MobileNetV2Plus", "LightLE", "VICH"],
    )

    student = build_student(
        num_classes=args.num_classes,
        width_mult=args.width_mult,
        dropout=args.dropout,
        pretrained=not args.no_student_pretrained,
        device=args.device,
        layer_embedding=args.student_layer_embedding,
        vae_head=args.student_vae_head,
        head_type=args.student_head_type,
        lightweight_layer_embedding=args.student_lightweight_layer_embedding,
        lightweight_layer_embedding_layers=args.student_layer_embedding_layers,
        embedding_dim=args.student_embedding_dim,
        use_vich_sampling=args.use_vich_sampling,
        vich_logvar_min=args.vich_logvar_min,
        vich_logvar_max=args.vich_logvar_max,
        vich_init_logvar_bias=args.vich_init_logvar_bias,
    )
    student.input_resolution = int(args.img_size)

    data_args = build_data_args(args.teacher_config, args)
    train_loader, val_loader = build_dataloader(data_args)
    if train_loader is None or val_loader is None:
        raise RuntimeError("Both train and validation loaders are required for KD training.")
    if args.expected_train_samples and len(train_loader.dataset) != args.expected_train_samples:
        raise RuntimeError(
            f"Train sample mismatch: expected {args.expected_train_samples}, got {len(train_loader.dataset)}."
        )
    if args.expected_val_samples and len(val_loader.dataset) != args.expected_val_samples:
        raise RuntimeError(
            f"Validation sample mismatch: expected {args.expected_val_samples}, got {len(val_loader.dataset)}."
        )

    if args.no_train_augment or args.teacher_cache:
        if not hasattr(train_loader.dataset, "transform"):
            raise RuntimeError(
                "--no-train-augment/--teacher-cache require a dataset exposing a '.transform' "
                "attribute to force determinism; this dataset backend doesn't expose one."
            )
        train_loader.dataset.transform = get_data_transforms(data_args)["valid"]
        print("Training augmentation disabled: train loader forced onto the deterministic 'valid' transform.")
    teacher_cache = load_teacher_cache(args.teacher_cache) if args.teacher_cache else None

    print(
        f"Train Samples: {len(train_loader.dataset)}, "
        f"batchs={len(train_loader)}, sample_numbers={data_args.sample_numbers}"
    )
    print(f"Validation Samples: {len(val_loader.dataset)}, batchs={len(val_loader)}")
    smoke_images, _smoke_labels, smoke_soft_targets = unpack_batch(next(iter(train_loader)))
    smoke_images = smoke_images[: min(2, smoke_images.shape[0])].to(args.device)
    if args.supervision == "soft":
        if smoke_soft_targets is None:
            raise RuntimeError("FERPlus soft supervision is enabled but label_em is missing.")
        smoke_soft_targets = normalize_probability_targets(
            smoke_soft_targets[: smoke_images.shape[0]].to(args.device)
        )
    else:
        smoke_soft_targets = None
    run_kd_smoke_test(
        student,
        teacher,
        smoke_images,
        args.num_classes,
        teacher_images=_prepare_teacher_images(smoke_images, args.teacher_input_size),
        soft_targets=smoke_soft_targets,
    )
    flops = measure_flops(student, args.device, int(data_args.train_size))
    write_parameter_summary(
        student,
        save_dir,
        num_classes=args.num_classes,
        head_type=args.student_head_type,
        layer_embedding_layers=args.student_layer_embedding_layers,
        flops=flops,
    )

    criterion = DistillationLoss(
        alpha=args.alpha,
        temperature=args.temperature,
        label_smoothing=args.label_smoothing,
        vae_kl_beta=args.student_vae_kl_beta,
        beta_vich=args.beta_vich,
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
    criterion.to(args.device)
    trainable_parameters = list(student.parameters())
    if args.ctkd_enable:
        trainable_parameters.extend(criterion.ctkd.parameters())
        print(f"CTKD enabled: learnable temperature in [{args.ctkd_t_min}, {args.ctkd_t_max}].")
    optimizer = optim.AdamW(trainable_parameters, lr=args.lr, weight_decay=args.weight_decay)
    amp_enabled = bool(args.use_amp and args.device.type == "cuda")
    scaler = torch.cuda.amp.GradScaler(enabled=amp_enabled)
    print(f"AMP enabled: {amp_enabled}")
    if args.scheduler_name == "cosine":
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
    model_ema = ModelEMA(student, decay=args.ema_decay, device=args.device) if args.ema else None

    shutil.copyfile(args.teacher_config, save_dir / Path(args.teacher_config).name)
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
        if int(data_args.sample_numbers) > 0:
            train_loader.dataset.class_balance_resample(data_args.sample_numbers)

        criterion.set_epoch(epoch, args.epochs)
        train_loss, hard_loss, soft_loss, aux_kl_loss, train_acc, phase0_diag = train_one_epoch(
            teacher,
            student,
            train_loader,
            criterion,
            optimizer,
            args.device,
            epoch,
            args.mixup,
            args.num_classes,
            args.supervision,
            args.teacher_input_size,
            model_ema,
            args.max_train_batches,
            args.progress,
            amp_enabled,
            scaler,
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
            args.device,
            epoch,
            args.max_val_batches,
            args.progress,
            amp_enabled,
        )
        elapsed = time.time() - epoch_start
        print(
            f"Epoch {epoch} ({elapsed:.1f}s): "
            f"Train Loss={train_loss:.4f} Hard={hard_loss:.4f} Soft={soft_loss:.4f} AuxKL={aux_kl_loss:.4f} "
            f"Train Acc={train_acc:.2f}% | Val Loss={val_loss:.4f} Acc={val_acc:.2f}%"
        )

        save_checkpoint(
            save_dir / "last_student.pth",
            student,
            val_acc,
            epoch=epoch,
            extra={"best_acc": best_acc, "best_epoch": best_epoch},
        )
        save_checkpoint(
            save_dir / "last_checkpoint.pth",
            student,
            val_acc,
            epoch=epoch,
            extra={"best_acc": best_acc, "best_epoch": best_epoch},
        )
        epoch_metrics = {
            "epoch": epoch,
            "train_loss": train_loss,
            "hard_loss": hard_loss,
            "soft_loss": soft_loss,
            "aux_kl_loss": aux_kl_loss,
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
            save_checkpoint(
                save_dir / "best_student.pth",
                student,
                best_acc,
                epoch=epoch,
                extra={"teacher_ckpt": str(args.teacher_ckpt)},
            )
            save_checkpoint(
                save_dir / "best_checkpoint.pth",
                student,
                best_acc,
                epoch=epoch,
                extra={"teacher_ckpt": str(args.teacher_ckpt)},
            )
            print(f"Saved best student ({best_acc:.2f}%) at epoch {epoch}")

    if args.swa:
        print("Updating SWA BatchNorm statistics...")
        update_bn(iter_images(train_loader, args.device), swa_model, device=args.device)
        swa_loss, swa_acc = validate(
            swa_model,
            val_loader,
            args.device,
            args.epochs,
            args.max_val_batches,
            args.progress,
            amp_enabled,
        )
        print(f"SWA Final Result: Loss={swa_loss:.4f} Acc={swa_acc:.2f}%")
        swa_ckpt_path = save_dir / "swa_student.pth"
        save_checkpoint(
            swa_ckpt_path,
            swa_model,
            swa_acc,
            extra={"teacher_ckpt": str(args.teacher_ckpt)},
        )
        swa_metrics = evaluate_detailed(
            swa_model,
            val_loader,
            args.device,
            num_classes=args.num_classes,
            max_batches=args.max_val_batches,
        )
        write_confusion_outputs(swa_metrics, save_dir, "confusion_matrix_swa")
        write_metrics_json(
            save_dir / "metrics_swa.json",
            dataset_name,
            args.num_classes,
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
            args.device,
            num_classes=args.num_classes,
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
            dataset_name,
            args.num_classes,
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
        best_ckpt = load_checkpoint_checked(student, best_ckpt_path, device=args.device, strict=True)
        best_metrics = evaluate_detailed(
            student,
            val_loader,
            args.device,
            num_classes=args.num_classes,
            max_batches=args.max_val_batches,
        )
        write_confusion_outputs(best_metrics, save_dir, "confusion_matrix")
        write_metrics_json(
            save_dir / "metrics_best.json",
            dataset_name,
            args.num_classes,
            best_metrics,
            student,
            best_ckpt_path,
            best_ckpt.get("epoch", best_epoch),
            args.beta_vich,
            flops,
        )
    if last_ckpt_path.exists():
        last_ckpt = load_checkpoint_checked(student, last_ckpt_path, device=args.device, strict=True)
        last_metrics = evaluate_detailed(
            student,
            val_loader,
            args.device,
            num_classes=args.num_classes,
            max_batches=args.max_val_batches,
        )
        write_metrics_json(
            save_dir / "metrics_last.json",
            dataset_name,
            args.num_classes,
            last_metrics,
            student,
            last_ckpt_path,
            last_ckpt.get("epoch", args.epochs),
            args.beta_vich,
            flops,
        )

    print(f"Training complete. Best Acc: {best_acc:.2f}% at epoch {best_epoch}")
    tracker.finish()


def parse_args():
    parser = argparse.ArgumentParser("AffectNet+ POSTER-Var to MobileNetV2Plus KD")
    parser.add_argument("--teacher-config", required=True, type=Path)
    parser.add_argument("--teacher-ckpt", required=True, type=Path)
    parser.add_argument("--num-classes", type=int, default=None, choices=[7, 8])
    parser.add_argument("--dataset-name", type=str, default=None)
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--save-root", type=Path, default=Path("kd_logs"))
    parser.add_argument("--train-root", type=str, default=None)
    parser.add_argument("--val-root", type=str, default=None)
    parser.add_argument("--metadata", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=48)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--sample-numbers", type=int, default=None)
    parser.add_argument("--train-frac", type=float, default=None)
    parser.add_argument("--val-frac", type=float, default=None)
    parser.add_argument("--max-train-batches", type=int, default=0)
    parser.add_argument("--max-val-batches", type=int, default=0)
    parser.add_argument("--expected-train-samples", type=int, default=0)
    parser.add_argument("--expected-val-samples", type=int, default=0)
    parser.add_argument("--cache-img", action="store_true")
    parser.add_argument("--cache-index", action="store_true")
    parser.add_argument("--cache-dir", type=str, default="D:/Veriseti/poster-var/dataset_cache")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--use-soft-label", action="store_true")
    parser.add_argument("--supervision", choices=["hard", "soft", "auto"], default="hard")
    parser.add_argument("--img-size", type=int, choices=[112, 224, 256], default=224)
    parser.add_argument("--resize-size", type=int, default=256)
    parser.add_argument("--teacher-input-size", type=int, default=224)
    parser.add_argument("--unified-resolution-crop", action="store_true")
    parser.add_argument("--color-jitter", type=float, default=0.2)
    parser.add_argument("--random-erasing-p", type=float, default=0.5)
    parser.add_argument("--width-mult", type=float, default=1.0)
    parser.add_argument("--dropout", type=float, default=0.5)
    parser.add_argument("--student-layer-embedding", action="store_true")
    parser.add_argument("--student-lightweight-layer-embedding", action="store_true")
    parser.add_argument("--student-layer-embedding-layers", type=int, default=3)
    parser.add_argument("--student-vae-head", action="store_true")
    parser.add_argument("--student-head-type", type=str, default="linear", choices=["linear", "vae", "le_vae", "vich"])
    parser.add_argument("--student-vae-kl-beta", type=float, default=0.001)
    parser.add_argument("--student-embedding-dim", type=int, default=None)
    parser.add_argument("--beta-vich", type=float, default=1e-4)
    parser.add_argument("--no-vich-sampling", action="store_false", dest="use_vich_sampling")
    parser.set_defaults(use_vich_sampling=True)
    parser.add_argument("--vich-logvar-min", type=float, default=-10.0)
    parser.add_argument("--vich-logvar-max", type=float, default=10.0)
    parser.add_argument("--vich-init-logvar-bias", type=float, default=-5.0)
    parser.add_argument("--no-student-pretrained", action="store_true")
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--alpha", type=float, default=0.2)
    parser.add_argument("--temperature", type=float, default=6.0)
    parser.add_argument("--label-smoothing", type=float, default=0.2)
    parser.add_argument("--mixup", type=float, default=0.2)
    # --- Phase 0: Component A (uncertainty gate) ---
    parser.add_argument("--gate-enable", action="store_true")
    parser.add_argument(
        "--gate-uncertainty-source",
        choices=["mean_logvar", "target_logvar", "top2_logvar", "entropy"],
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
    # --- teacher-side post-hoc calibration (dose-response experiments) ---
    parser.add_argument(
        "--teacher-temperature-scale",
        type=float,
        default=1.0,
        help=(
            "Post-hoc temperature-scale the teacher logits (original_teacher_logits /= T) before "
            "computing soft targets. 1.0 = off (default). Distil from a re-calibrated teacher "
            "without changing its architecture, recipe or accuracy. Same manipulation as "
            "train_rafdb_kd.py's flag of the same name. Incompatible with --logit-std-enable/"
            "--adaptive-t-enable/--ctkd-enable unless --allow-tempscale-with-mechanism is passed."
        ),
    )
    parser.add_argument(
        "--allow-tempscale-with-mechanism",
        action="store_true",
        help=(
            "Opt out of the --teacher-temperature-scale x mechanism mutual-exclusion guard. Only "
            "legitimate when the pre-scale is FIXED across all compared arms and the mechanism flag "
            "is the single manipulated variable; SWEEPING the pre-scale with a temperature mechanism "
            "on is degenerate (the temperatures compose multiplicatively)."
        ),
    )
    parser.add_argument("--scheduler-name", choices=["cosine", "cosine_warm_restarts"], default="cosine_warm_restarts")
    parser.add_argument("--min-lr", type=float, default=1e-6)
    parser.add_argument("--scheduler-t0", type=int, default=10)
    parser.add_argument("--scheduler-t-mult", type=int, default=2)
    parser.add_argument("--swa", action="store_true")
    parser.add_argument("--swa-start", type=int, default=90)
    parser.add_argument("--swa-lr", type=float, default=1e-4)
    parser.add_argument("--ema", action="store_true")
    parser.add_argument("--ema-decay", type=float, default=0.999)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--use-amp", action="store_true", help="Enable CUDA mixed precision training for student KD.")
    parser.add_argument("--use-swanlab", action="store_true")
    parser.add_argument("--swanlab-project", type=str, default="Unified-FER-KD")
    parser.add_argument("--swanlab-mode", choices=["offline", "cloud"], default="offline")
    parser.add_argument("--swanlab-logdir", type=Path, default=Path("swanlog"))
    parser.add_argument("--no-progress", action="store_false", dest="progress", help="Disable live batch progress bars and print only epoch summaries.")
    parser.set_defaults(progress=True)
    parser.add_argument("--cpu", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
