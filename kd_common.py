import copy
import csv
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

import kd_baselines
import kd_g2g
import kd_uncertainty


class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

    def isatty(self):
        return any(getattr(stream, "isatty", lambda: False)() for stream in self.streams)


def setup_run_logging(save_dir):
    log_path = Path(save_dir) / "train.log"
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = TeeStream(sys.__stdout__, log_file)
    sys.stderr = TeeStream(sys.__stderr__, log_file)
    print(f"Logging to: {log_path}")
    return log_path


class AverageMeter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0.0
        self.sum = 0.0
        self.count = 0
        self.avg = 0.0

    def update(self, value, n=1):
        self.val = float(value)
        self.sum += float(value) * int(n)
        self.count += int(n)
        self.avg = self.sum / max(1, self.count)


class MinMeanMaxMeter:
    """Tracks running min/mean/max of a scalar-or-per-sample quantity across batches.

    Used for epoch-level diagnostics (e.g. gate alpha_i, effective temperature)
    where a single running average would hide the spread the Phase 0 spec asks
    to log.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.min = float("inf")
        self.max = float("-inf")
        self.sum = 0.0
        self.count = 0

    def update(self, values):
        if torch.is_tensor(values):
            values = values.detach().flatten().tolist()
        elif not isinstance(values, (list, tuple)):
            values = [values]
        for value in values:
            value = float(value)
            self.min = min(self.min, value)
            self.max = max(self.max, value)
            self.sum += value
            self.count += 1

    @property
    def mean(self):
        return self.sum / max(1, self.count)

    def as_dict(self, prefix=""):
        if self.count == 0:
            return {f"{prefix}min": None, f"{prefix}mean": None, f"{prefix}max": None}
        return {f"{prefix}min": self.min, f"{prefix}mean": self.mean, f"{prefix}max": self.max}


class DistillationLoss(nn.Module):
    """Shared hard/soft supervision, teacher KD, and probabilistic-head loss."""

    _GATE_SOURCES = {"mean_logvar", "target_logvar", "top2_logvar", "entropy", "oracle_error"}
    _GATE_NORMS = {"batch", "running"}
    _G2G_MODES = {"kl", "w2"}

    def __init__(
        self,
        alpha=0.2,
        temperature=6.0,
        label_smoothing=0.2,
        vae_kl_beta=0.001,
        beta_vich=1e-4,
        class_weights=None,
        gate_enable=False,
        gate_uncertainty_source="mean_logvar",
        gate_norm="batch",
        gate_alpha_lo=0.1,
        gate_alpha_hi=0.7,
        gate_k=2.0,
        gate_tau=0.0,
        g2g_enable=False,
        g2g_weight=0.0,
        g2g_mode="kl",
        g2g_warmup_epochs=0,
        logit_std_enable=False,
        adaptive_T_enable=False,
        adaptive_T_gamma=0.5,
        ctkd_enable=False,
        ctkd_t_min=1.0,
        ctkd_t_max=8.0,
        ctkd_grl_lambda_max=1.0,
    ):
        super().__init__()
        self.alpha = float(alpha)
        self.temperature = float(temperature)
        self.vae_kl_beta = float(vae_kl_beta)
        self.beta_vich = float(beta_vich)
        self.label_smoothing = float(label_smoothing)
        self.kl_div_loss = nn.KLDivLoss(reduction="batchmean")
        if class_weights is None:
            self.register_buffer("class_weights", None)
        else:
            self.register_buffer("class_weights", class_weights.float())

        # --- Phase 0 additions: all default off/neutral, bit-identical when unused. ---
        self.gate_enable = bool(gate_enable)
        if gate_uncertainty_source not in self._GATE_SOURCES:
            raise ValueError(f"Unsupported gate_uncertainty_source: {gate_uncertainty_source!r}")
        self.gate_uncertainty_source = str(gate_uncertainty_source)
        if gate_norm not in self._GATE_NORMS:
            raise ValueError(f"Unsupported gate_norm: {gate_norm!r}")
        self.gate_norm = str(gate_norm)
        self.gate_alpha_lo = float(gate_alpha_lo)
        self.gate_alpha_hi = float(gate_alpha_hi)
        self.gate_k = float(gate_k)
        self.gate_tau = float(gate_tau)

        self.g2g_enable = bool(g2g_enable)
        self.g2g_weight = float(g2g_weight)
        if g2g_mode not in self._G2G_MODES:
            raise ValueError(f"Unsupported g2g_mode: {g2g_mode!r}")
        self.g2g_mode = str(g2g_mode)
        self.g2g_warmup_epochs = int(g2g_warmup_epochs)

        self.logit_std_enable = bool(logit_std_enable)

        self.adaptive_T_enable = bool(adaptive_T_enable)
        self.adaptive_T_gamma = float(adaptive_T_gamma)

        self.ctkd_enable = bool(ctkd_enable)
        self.ctkd_t_min = float(ctkd_t_min)
        self.ctkd_t_max = float(ctkd_t_max)
        self.ctkd_grl_lambda_max = float(ctkd_grl_lambda_max)

        if self.adaptive_T_enable and self.ctkd_enable:
            raise ValueError(
                "adaptive_T_enable and ctkd_enable cannot both be set: both mechanisms "
                "own 'the effective temperature' and have no defined combination semantics."
            )
        if self.gate_enable and self.class_weights is not None:
            raise ValueError(
                "gate_enable with class_weights is not supported: class-weighted CE is "
                "not exactly per-sample decomposable (F.cross_entropy normalizes by "
                "sum(weight) across the batch, not mean_i(weight_i * loss_i)), so the "
                "gate's per-sample blend cannot reproduce it. Disable one of them."
            )
        if self.gate_enable and self.adaptive_T_enable:
            print(
                "Warning: gate_enable and adaptive_T_enable are both on. These are "
                "alternative ablations of the same idea (reacting to teacher "
                "uncertainty) on different axes (alpha vs. temperature); this "
                "combination is untested and not part of the planned ablation grid."
            )

        self.gate_normalizer = (
            kd_uncertainty.UncertaintyNormalizer(mode=self.gate_norm) if self.gate_enable else None
        )
        self.ctkd = (
            kd_baselines.CTKDTemperature(
                t_min=self.ctkd_t_min, t_max=self.ctkd_t_max, grl_lambda_max=self.ctkd_grl_lambda_max
            )
            if self.ctkd_enable
            else None
        )

        self._current_epoch = 0
        self._total_epochs = 0

        # Per-forward() diagnostics for epoch-level logging; kept as plain floats
        # (never tensors) so callers can log them without extra .item() calls and
        # without risking graph retention. None until the corresponding mechanism runs.
        self.last_alpha_stats = None
        self.last_g2g_term = None
        self.last_effective_T_stats = None
        self.last_ctkd_T = None

    def set_epoch(self, epoch, total_epochs):
        """Advance epoch-scheduled state (G2G warmup weight, CTKD's GRL ramp).

        Called once per epoch from the training loop, not per-batch, so
        forward()'s signature never needs an epoch argument.
        """
        self._current_epoch = int(epoch)
        self._total_epochs = int(total_epochs)
        if self.ctkd is not None:
            self.ctkd.set_epoch(self._current_epoch, self._total_epochs)

    def supervised_loss(self, logits, targets):
        if targets.ndim == 1:
            return F.cross_entropy(
                logits,
                targets.long(),
                weight=self.class_weights,
                label_smoothing=self.label_smoothing,
            )

        if targets.ndim != 2 or targets.shape != logits.shape:
            raise ValueError(
                f"Supervised targets must be [B] or {tuple(logits.shape)}, got {tuple(targets.shape)}."
            )
        targets = normalize_probability_targets(targets)
        log_probs = F.log_softmax(logits, dim=1)
        if self.class_weights is None:
            return -(targets * log_probs).sum(dim=1).mean()
        weights = self.class_weights.view(1, -1)
        weighted_loss = -(targets * log_probs * weights).sum(dim=1)
        normalizer = (targets * weights).sum(dim=1).clamp_min(1e-12)
        return (weighted_loss / normalizer).mean()

    def supervised_loss_per_sample(self, logits, targets):
        """Per-sample supervised loss, for the gate's per-sample alpha blend.

        The soft-target (distribution) branch is an exact per-sample decomposition
        of `supervised_loss`'s soft-target branch (same formula, final `.mean()`
        simply omitted). The hard-label branch is only exact when `class_weights`
        is None: `F.cross_entropy(weight=..., reduction="mean")` normalizes by
        `sum(weight_i)` across the whole batch, not `mean_i(weight_i * loss_i)`, so
        it has no exact per-sample decomposition when class weights are set. That
        combination is rejected at construction time (see __init__), so this method
        never actually has to handle it, but it still asserts the precondition here
        rather than silently returning a subtly-wrong value.
        """
        if targets.ndim == 1:
            if self.class_weights is not None:
                raise RuntimeError(
                    "supervised_loss_per_sample does not support class_weights "
                    "for hard-label targets; this should be unreachable because "
                    "gate_enable + class_weights is rejected at construction."
                )
            return F.cross_entropy(
                logits,
                targets.long(),
                reduction="none",
                label_smoothing=self.label_smoothing,
            )

        if targets.ndim != 2 or targets.shape != logits.shape:
            raise ValueError(
                f"Supervised targets must be [B] or {tuple(logits.shape)}, got {tuple(targets.shape)}."
            )
        targets = normalize_probability_targets(targets)
        log_probs = F.log_softmax(logits, dim=1)
        if self.class_weights is None:
            return -(targets * log_probs).sum(dim=1)
        weights = self.class_weights.view(1, -1)
        weighted_loss = -(targets * log_probs * weights).sum(dim=1)
        normalizer = (targets * weights).sum(dim=1).clamp_min(1e-12)
        return weighted_loss / normalizer

    def _resolve_effective_temperature(self, teacher_logits):
        """Resolve the temperature used for the KD soft-loss term: CTKD's
        learned global scalar, adaptive-T's per-sample tensor ([B, 1], for
        broadcasting against [B, C] logits), or the fixed `self.temperature`.

        Only called from the non-gated branch of forward() -- when the gate
        is enabled, T stays fixed by design (see the Phase 0 spec's "gate
        only changes the L_sup/L_KD balance; T stays fixed" rule), so this
        method is never invoked and last_effective_T_stats/last_ctkd_T are
        left at the None they were reset to at the top of forward().
        """
        if self.ctkd_enable:
            temperature = self.ctkd()
            self.last_ctkd_T = float(temperature.detach().cpu())
            self.last_effective_T_stats = {
                "min": self.last_ctkd_T, "mean": self.last_ctkd_T, "max": self.last_ctkd_T,
            }
            return temperature
        if self.adaptive_T_enable:
            if teacher_logits is None:
                raise RuntimeError(
                    "adaptive_T_enable=True requires raw teacher_logits (not "
                    "precomputed teacher_probabilities); pass teacher_logits= instead."
                )
            per_sample_T = kd_baselines.entropy_adaptive_temperature(
                teacher_logits, self.temperature, self.adaptive_T_gamma
            )
            self.last_effective_T_stats = {
                "min": float(per_sample_T.min().detach().cpu()),
                "mean": float(per_sample_T.mean().detach().cpu()),
                "max": float(per_sample_T.max().detach().cpu()),
            }
            return per_sample_T.view(-1, 1)
        return self.temperature

    def _soft_targets_and_student_log_probs(self, student_logits, teacher_logits, teacher_probabilities, temperature):
        """Returns (student_log_probs, teacher_probs) at the given temperature,
        applying per-sample logit standardization first if enabled (requires
        raw `teacher_logits`, since standardization must happen before any
        softmax -- a precomputed `teacher_probabilities` cannot be
        standardized after the fact).
        """
        if self.logit_std_enable:
            if teacher_logits is None:
                raise RuntimeError(
                    "logit_std_enable=True requires raw teacher_logits (not "
                    "precomputed teacher_probabilities); pass teacher_logits= instead."
                )
            student_logits = kd_baselines.standardize_logits_per_sample(student_logits)
            teacher_logits = kd_baselines.standardize_logits_per_sample(teacher_logits)
            teacher_probabilities = None  # force recompute from the standardized logits

        soft_student = F.log_softmax(student_logits / temperature, dim=1)
        if teacher_probabilities is None:
            if teacher_logits is None:
                raise RuntimeError("Soft KD loss requires teacher_logits or teacher_probabilities.")
            teacher_probabilities = F.softmax(teacher_logits / temperature, dim=1)
        soft_teacher = normalize_probability_targets(teacher_probabilities)
        return soft_student, soft_teacher

    def forward(
        self,
        student_output,
        teacher_logits=None,
        labels=None,
        teacher_probabilities=None,
        teacher_mu=None,
        teacher_logvar=None,
    ):
        student_logits = extract_logits(student_output)
        if labels is None:
            raise ValueError("Supervised labels/targets are required.")
        hard_loss = self.supervised_loss(student_logits, labels)
        soft_loss = hard_loss.new_tensor(0.0)
        has_teacher = teacher_probabilities is not None or teacher_logits is not None
        self.last_effective_T_stats = None
        self.last_ctkd_T = None
        if has_teacher and self.alpha < 1.0:
            # Gate keeps T fixed by design (see _resolve_effective_temperature's
            # docstring); only the non-gated path can modulate T via adaptive-T/CTKD.
            effective_T = self.temperature if self.gate_enable else self._resolve_effective_temperature(teacher_logits)
            soft_student, soft_teacher = self._soft_targets_and_student_log_probs(
                student_logits, teacher_logits, teacher_probabilities, effective_T
            )
            per_sample_kd = F.kl_div(soft_student, soft_teacher, reduction="none").sum(dim=1)
            t_squared = effective_T ** 2
            if torch.is_tensor(t_squared) and t_squared.numel() > 1:
                soft_loss = (per_sample_kd * t_squared.view(-1)).mean()
            else:
                soft_loss = per_sample_kd.mean() * t_squared

        aux_kl = hard_loss.new_tensor(0.0)
        aux_beta = 0.0
        if isinstance(student_output, dict) and student_output.get("kl_loss") is not None:
            aux_kl = student_output["kl_loss"]
            aux_beta = self.beta_vich
        elif isinstance(student_output, (tuple, list)) and len(student_output) >= 3:
            mu, logvar = student_output[1], student_output[2]
            aux_kl = -0.5 * torch.sum(
                1.0 + logvar - mu.pow(2) - logvar.exp(),
                dim=1,
            ).mean()
            aux_beta = self.vae_kl_beta

        if not has_teacher:
            loss = hard_loss + aux_beta * aux_kl
            self.last_alpha_stats = None
        elif self.gate_enable:
            # Per-sample alpha blend: cannot reuse the scalar-reduced hard_loss/
            # soft_loss above (they're already .mean()-reduced), so recompute
            # both per-sample here. Independent of `self.alpha < 1.0`/self.alpha
            # entirely -- the gate fully replaces the fixed alpha blend.
            hard_per_sample = self.supervised_loss_per_sample(student_logits, labels)
            soft_student_per, gate_teacher_probabilities = self._soft_targets_and_student_log_probs(
                student_logits, teacher_logits, teacher_probabilities, self.temperature
            )
            soft_per_sample = (
                F.kl_div(soft_student_per, gate_teacher_probabilities, reduction="none").sum(dim=1)
                * (self.temperature ** 2)
            )

            uncertainty = kd_uncertainty.resolve_uncertainty(
                self.gate_uncertainty_source,
                gate_teacher_probabilities,
                teacher_mu,
                teacher_logvar,
                labels,
            )
            u_hat = self.gate_normalizer(uncertainty)
            alpha_i = kd_uncertainty.gate_alpha(
                u_hat, self.gate_alpha_lo, self.gate_alpha_hi, self.gate_k, self.gate_tau
            )

            blended = alpha_i * hard_per_sample + (1.0 - alpha_i) * soft_per_sample
            loss = blended.mean() + aux_beta * aux_kl
            self.last_alpha_stats = {
                "min": float(alpha_i.min().detach().cpu()),
                "mean": float(alpha_i.mean().detach().cpu()),
                "max": float(alpha_i.max().detach().cpu()),
            }
        else:
            loss = self.alpha * hard_loss + (1.0 - self.alpha) * soft_loss + aux_beta * aux_kl
            self.last_alpha_stats = None

        if self.g2g_enable:
            student_mu, student_logvar = extract_mu_logvar(student_output)
            kd_g2g.validate_g2g_shapes(teacher_mu, teacher_logvar, student_mu, student_logvar)
            teacher_mu = teacher_mu.detach()
            teacher_logvar = teacher_logvar.detach()
            per_sample_g2g = kd_g2g.g2g_term(
                teacher_mu, teacher_logvar, student_mu, student_logvar, mode=self.g2g_mode
            )
            warmup = kd_g2g.g2g_warmup_factor(self._current_epoch, self.g2g_warmup_epochs)
            g2g_mean = per_sample_g2g.mean()
            loss = loss + self.g2g_weight * warmup * g2g_mean
            self.last_g2g_term = float(g2g_mean.detach().cpu())
        else:
            self.last_g2g_term = None

        return loss, hard_loss, soft_loss, aux_kl


class ModelEMA:
    """Exponential moving average with an evaluation-ready model copy."""

    def __init__(self, model, decay=0.999, device=None):
        self.decay = float(decay)
        self.module = copy.deepcopy(model).eval()
        if device is not None:
            self.module.to(device)
        for parameter in self.module.parameters():
            parameter.requires_grad_(False)

    @torch.no_grad()
    def update(self, model):
        model_state = model.state_dict()
        for name, ema_value in self.module.state_dict().items():
            source = model_state[name].detach()
            if source.device != ema_value.device:
                source = source.to(ema_value.device)
            if torch.is_floating_point(ema_value):
                ema_value.mul_(self.decay).add_(source, alpha=1.0 - self.decay)
            else:
                ema_value.copy_(source)


def normalize_probability_targets(targets, eps=1e-12):
    targets = targets.float().clamp_min(0.0)
    denominator = targets.sum(dim=1, keepdim=True).clamp_min(float(eps))
    return targets / denominator


def labels_to_distribution(labels, num_classes, label_smoothing=0.0):
    distribution = F.one_hot(labels.long(), num_classes=int(num_classes)).float()
    smoothing = float(label_smoothing)
    if smoothing > 0:
        distribution = distribution * (1.0 - smoothing) + smoothing / int(num_classes)
    return distribution


def teacher_probabilities_from_logits(logits, temperature):
    return F.softmax(logits / float(temperature), dim=1)


@torch.no_grad()
def run_kd_smoke_test(
    student,
    teacher,
    student_images,
    num_classes,
    teacher_images=None,
    soft_targets=None,
):
    student_was_training = student.training
    teacher_was_training = teacher.training if teacher is not None else False
    student.eval()
    if teacher is not None:
        teacher.eval()

    student_logits_1 = extract_logits(student(student_images))
    student_logits_2 = extract_logits(student(student_images))
    expected_shape = (student_images.shape[0], int(num_classes))
    if tuple(student_logits_1.shape) != expected_shape:
        raise RuntimeError(
            f"Student smoke shape mismatch: expected {expected_shape}, got {tuple(student_logits_1.shape)}."
        )
    if not torch.allclose(student_logits_1, student_logits_2, atol=1e-7, rtol=1e-6):
        max_diff = (student_logits_1 - student_logits_2).abs().max().item()
        raise RuntimeError(f"Student eval output is not deterministic; max difference={max_diff}.")

    if teacher is not None:
        teacher_input = student_images if teacher_images is None else teacher_images
        teacher_logits = extract_logits(teacher(teacher_input))
        if tuple(teacher_logits.shape) != expected_shape:
            raise RuntimeError(
                f"Teacher smoke shape mismatch: expected {expected_shape}, got {tuple(teacher_logits.shape)}."
            )

    if soft_targets is not None:
        if tuple(soft_targets.shape) != expected_shape:
            raise RuntimeError(
                f"Soft-target shape mismatch: expected {expected_shape}, got {tuple(soft_targets.shape)}."
            )
        row_sums = soft_targets.float().sum(dim=1)
        if not torch.allclose(row_sums, torch.ones_like(row_sums), atol=1e-4, rtol=1e-4):
            raise RuntimeError(
                f"Soft-target rows must sum to 1; observed range "
                f"[{row_sums.min().item():.6f}, {row_sums.max().item():.6f}]."
            )

    student.train(student_was_training)
    if teacher is not None:
        teacher.train(teacher_was_training)
    print(
        f"Smoke test passed: student/teacher logits={expected_shape}, "
        f"deterministic_eval=True, soft_targets={soft_targets is not None}."
    )


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def extract_logits(output):
    if isinstance(output, dict):
        return output["logits"]
    if isinstance(output, (tuple, list)):
        return output[0]
    return output


def extract_mu_logvar(output):
    """Extract (mu, logvar) from a VICH-dict or VAE/VICH-tuple model output.

    Student VICH heads (models/mobilenetv2_plus.py::VICHHead) return a dict
    {"logits","mu","logvar","kl_loss"}. Teacher and student VAE-style heads
    (trails/posterv2/vit_vae_model.py::VaeClassifier/VICHClassifier,
    models/mobilenetv2_plus.py::VAEClassifier) return a plain 3-tuple
    (logits, mu, logvar). A bare logits tensor (linear head) has neither,
    so this returns (None, None) rather than raising -- callers that require
    mu/logvar (gate's non-entropy sources, G2G) must check for None themselves
    and raise a mechanism-specific, actionable error.
    """
    if isinstance(output, dict):
        return output.get("mu"), output.get("logvar")
    if isinstance(output, (tuple, list)) and len(output) >= 3:
        return output[1], output[2]
    return None, None


def clean_state_dict(state_dict):
    cleaned = {}
    for key, value in state_dict.items():
        if key.endswith("total_ops") or key.endswith("total_params"):
            continue
        if key.startswith("module."):
            key = key[7:]
        cleaned[key] = value
    return cleaned


def load_checkpoint_checked(model, checkpoint_path, device="cpu", strict=True):
    checkpoint = torch.load(str(checkpoint_path), map_location=device, weights_only=False)
    state_dict = checkpoint.get("model", checkpoint.get("model_state_dict", checkpoint.get("state_dict", checkpoint)))
    state_dict = clean_state_dict(state_dict)
    incompatible = model.load_state_dict(state_dict, strict=strict)
    if not strict and (incompatible.missing_keys or incompatible.unexpected_keys):
        raise RuntimeError(
            "Checkpoint architecture mismatch: "
            f"missing={incompatible.missing_keys}, unexpected={incompatible.unexpected_keys}"
        )
    return checkpoint


def unpack_image_batch(batch):
    images, labels, _soft_targets = unpack_image_batch_with_targets(batch)
    return images, labels


def unpack_image_batch_with_targets(batch):
    if len(batch) == 5:
        _idxs, images, labels, label_em, _paths = batch
        soft_targets = label_em if torch.is_tensor(label_em) and label_em.numel() > 0 else None
        return images, labels, soft_targets
    if len(batch) == 3:
        _idxs, images, labels = batch
        return images, labels, None
    if len(batch) == 2:
        images, labels = batch
        return images, labels, None
    raise ValueError(f"Unsupported batch format with {len(batch)} elements.")


def mixup_data(images, labels, alpha, device):
    mixed_images, index, lam = mixup_batch(images, alpha, device)
    return mixed_images, labels, labels[index], lam


def mixup_batch(images, alpha, device):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    index = torch.randperm(images.size(0), device=device)
    mixed_images = lam * images + (1.0 - lam) * images[index]
    return mixed_images, index, float(lam)


def mix_targets(targets, index, lam):
    return float(lam) * targets + (1.0 - float(lam)) * targets[index]


@torch.no_grad()
def evaluate_detailed(model, loader, device, num_classes, max_batches=0):
    model.eval()
    y_true, y_pred = [], []
    losses = AverageMeter()
    for batch_id, batch in enumerate(loader):
        if max_batches and batch_id >= max_batches:
            break
        images, labels = unpack_image_batch(batch)
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        logits = extract_logits(model(images))
        loss = F.cross_entropy(logits, labels)
        preds = logits.argmax(dim=1)
        losses.update(loss.item(), images.size(0))
        y_true.extend(labels.detach().cpu().tolist())
        y_pred.extend(preds.detach().cpu().tolist())

    labels_range = list(range(int(num_classes)))
    cm = confusion_matrix(y_true, y_pred, labels=labels_range)
    return {
        "accuracy": accuracy_score(y_true, y_pred) * 100.0,
        "precision": precision_score(y_true, y_pred, average="macro", zero_division=0) * 100.0,
        "recall": recall_score(y_true, y_pred, average="macro", zero_division=0) * 100.0,
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0) * 100.0,
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0) * 100.0,
        "loss": losses.avg,
        "n": len(y_true),
        "confusion_matrix": cm,
    }


def write_confusion_outputs(metrics, save_dir, prefix="confusion_matrix"):
    cm = metrics["confusion_matrix"]
    save_dir = Path(save_dir)
    np.savetxt(save_dir / f"{prefix}.csv", cm, delimiter=",", fmt="%d")
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
        fig.colorbar(im, ax=ax)
        ax.set_title("Confusion Matrix")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        ticks = np.arange(cm.shape[0])
        ax.set_xticks(ticks)
        ax.set_yticks(ticks)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=8)
        fig.tight_layout()
        fig.savefig(save_dir / f"{prefix}.png", dpi=150)
        plt.close(fig)
    except Exception as exc:
        print(f"Confusion matrix PNG skipped: {exc}")


class LogitsOnlyWrapper(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model

    def forward(self, x):
        return extract_logits(self.model(x))


def count_params(model):
    return sum(parameter.numel() for parameter in model.parameters())


def count_trainable_params(model):
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def state_dict_size_mb(model):
    total_bytes = sum(tensor.numel() * tensor.element_size() for tensor in model.state_dict().values())
    return total_bytes / (1024 * 1024)


def measure_flops(model, device, image_size):
    try:
        from thop import profile

        flops_model = copy.deepcopy(model).to(device)
        dummy = torch.randn(1, 3, int(image_size), int(image_size), device=device)
        flops_model.eval()
        with torch.no_grad():
            macs, _params = profile(LogitsOnlyWrapper(flops_model), inputs=(dummy,), verbose=False)
        del flops_model
        return macs
    except Exception as exc:
        print(f"FLOPs measurement skipped: {exc}")
        return None


def write_parameter_summary(student, save_dir, num_classes, head_type, layer_embedding_layers, flops=None):
    total_params = count_params(student)
    trainable_params = count_trainable_params(student)
    head_params = student.head_parameter_count() if hasattr(student, "head_parameter_count") else 0
    le_params = student.layer_embedding_parameter_count() if hasattr(student, "layer_embedding_parameter_count") else 0
    level_embed_params = (
        student.level_embedding_parameter_count()
        if hasattr(student, "level_embedding_parameter_count")
        else le_params
    )
    fusion_norm_params = (
        student.fusion_norm_parameter_count()
        if hasattr(student, "fusion_norm_parameter_count")
        else 0
    )
    fusion_weight_params = (
        student.fusion_weight_parameter_count()
        if hasattr(student, "fusion_weight_parameter_count")
        else 0
    )
    adapter_params = student.adapter_parameter_count() if hasattr(student, "adapter_parameter_count") else 0
    feature_dim = getattr(student, "classifier_in_features", None)
    pre_adapter_dim = getattr(student, "pre_adapter_features", feature_dim)
    backbone_params = total_params - head_params - le_params - adapter_params
    expected_vich = 2 * (int(feature_dim) * int(num_classes) + int(num_classes)) if head_type == "vich" else None
    expected_level_embeddings = int(layer_embedding_layers) * int(pre_adapter_dim) if le_params else 0
    expected_lightle_total = (
        expected_level_embeddings + 2 * int(pre_adapter_dim) + int(layer_embedding_layers)
        if getattr(student, "lightweight_layer_embedding", False) and le_params
        else expected_level_embeddings
    )
    heavy_projections = [
        name
        for name, module in student.named_modules()
        if isinstance(module, nn.Linear)
        and module.in_features == int(pre_adapter_dim)
        and module.out_features == int(pre_adapter_dim)
    ]

    lines = [
        "model: MobileNetV2Plus",
        f"classes: {num_classes}",
        f"head_type: {head_type}",
        f"total_params: {total_params}",
        f"trainable_params: {trainable_params}",
        f"backbone_params_approx: {backbone_params}",
        f"adapter_params: {adapter_params}",
        f"head_params: {head_params}",
        f"layer_embedding_params: {le_params}",
        f"level_embedding_params: {level_embed_params}",
        f"fusion_norm_params: {fusion_norm_params}",
        f"fusion_weight_params: {fusion_weight_params}",
        f"lightle_taps: {getattr(student, 'layer_embedding_indices', ())}",
        f"heavy_square_projections: {heavy_projections}",
        f"feature_dim: {feature_dim}",
        f"total_params_m: {total_params / 1e6:.6f}",
        f"model_size_mb_state_dict: {state_dict_size_mb(student):.4f}",
        f"flops_g: {'' if flops is None else flops / 1e9}",
    ]
    if head_type == "vich":
        lines.extend([
            f"expected_vich_head_params: {expected_vich}",
            f"actual_vich_head_params: {head_params}",
            f"expected_level_embedding_params: {expected_level_embeddings}",
            f"expected_lightle_total_params: {expected_lightle_total}",
        ])
        if head_params != expected_vich:
            raise RuntimeError(
                f"VICH head is not lightweight: expected {expected_vich}, got {head_params}."
            )
        if getattr(student, "lightweight_layer_embedding", False) and le_params != expected_lightle_total:
            raise RuntimeError(
                f"LightLE parameter mismatch: expected {expected_lightle_total}, got {le_params}."
            )
        if getattr(student, "lightweight_layer_embedding", False) and total_params >= 2_300_000:
            raise RuntimeError(
                f"Unified lightweight student exceeds the 2.3M limit: {total_params} parameters."
            )
        if getattr(student, "lightweight_layer_embedding", False) and heavy_projections:
            raise RuntimeError(
                f"LightLE contains forbidden square projections: {heavy_projections}."
            )
    text = "\n".join(lines) + "\n"
    print("\nParameter sanity check:\n" + text)
    save_dir = Path(save_dir)
    for filename in ("parameter_count.txt", "model_summary.txt"):
        (save_dir / filename).write_text(text, encoding="utf-8")
    return {
        "total_params": total_params,
        "head_params": head_params,
        "layer_embedding_params": le_params,
        "feature_dim": feature_dim,
        "flops": flops,
    }


def save_checkpoint(path, model, acc, epoch=None, extra=None):
    payload = {"model_state_dict": model.state_dict(), "acc": float(acc)}
    if epoch is not None:
        payload["epoch"] = int(epoch)
    if extra:
        payload.update(extra)
    torch.save(payload, path)


def write_metrics_json(path, dataset, num_classes, metrics, student, checkpoint_path, epoch, beta_vich, flops):
    checkpoint_path = Path(checkpoint_path)
    payload = {
        "dataset": dataset,
        "classes": int(num_classes),
        "model": "MobileNetV2Plus",
        "head": getattr(student, "head_type", "unknown").upper(),
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "params_m": count_params(student) / 1e6,
        "flops_g": None if flops is None else flops / 1e9,
        "size_mb": checkpoint_path.stat().st_size / (1024 * 1024) if checkpoint_path.exists() else None,
        "best_epoch": epoch,
        "beta_vich": float(beta_vich),
        "feature_dim": getattr(student, "classifier_in_features", None),
        "vich_head_params": student.head_parameter_count() if hasattr(student, "head_parameter_count") else None,
        "input_resolution": getattr(student, "input_resolution", None),
        "checkpoint": str(checkpoint_path),
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def create_training_log(path):
    fields = [
        "epoch",
        "train_loss",
        "hard_loss",
        "soft_loss",
        "aux_kl_loss",
        "feature_loss",
        "train_acc",
        "val_loss",
        "val_acc",
        "elapsed_sec",
        "lr",
        # Phase 0 diagnostics: always present, blank when the corresponding
        # mechanism (gate / G2G / adaptive-T / CTKD) is disabled for the run.
        "alpha_min",
        "alpha_mean",
        "alpha_max",
        "g2g_term",
        "effective_T_min",
        "effective_T_mean",
        "effective_T_max",
        "ctkd_T",
    ]
    with open(path, "w", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=fields).writeheader()
    return fields


def append_training_log(path, fields, values):
    with open(path, "a", newline="", encoding="utf-8") as file:
        csv.DictWriter(file, fieldnames=fields).writerow(values)


class SwanLabTracker:
    def __init__(self, enabled, project, experiment_name, config, logdir, mode="offline", tags=None):
        self.enabled = bool(enabled)
        self.swanlab = None
        if self.enabled:
            import swanlab

            self.swanlab = swanlab
            swanlab.init(
                project=project,
                experiment_name=experiment_name,
                config={key: tracker_safe_value(value) for key, value in config.items()},
                logdir=str(logdir),
                mode=mode,
                tags=tags,
            )

    def log(self, values):
        if self.enabled:
            self.swanlab.log(values)

    def finish(self):
        if self.enabled:
            self.swanlab.finish()


def tracker_safe_value(value):
    if isinstance(value, dict):
        return {str(key): tracker_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [tracker_safe_value(item) for item in value]
    if isinstance(value, (Path, torch.device, os.PathLike)):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
