"""Baseline KD methods (Phase 0, Component D): logit standardization,
entropy-adaptive temperature, and CTKD (curriculum temperature via a
gradient-reversal layer). All default off, independent flags.
"""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


def standardize_logits_per_sample(logits, eps=1e-6):
    """z_hat = (z - mean_c(z)) / (std_c(z) + eps), per Sun et al. CVPR 2024.

    Applied to raw logits before any temperature division, for both teacher
    and student, in the KD term only -- the supervised term is untouched.
    """
    mean = logits.mean(dim=1, keepdim=True)
    std = logits.std(dim=1, keepdim=True, unbiased=False)
    return (logits - mean) / (std + eps)


def entropy_adaptive_temperature(teacher_logits, t_base, gamma):
    """Per-sample T_i = t_base * (1 + gamma*(H_i/logC - mean(H/logC))), clamped
    to [1.0, 2*t_base] (ATD-style baseline; the spec's "entropy + temperature"
    counterpart to the uncertainty gate's alpha-only modulation).

    H_i is computed at T=1 (not at t_base), to avoid a circular definition of
    the temperature used to compute the very entropy that then reshapes it.
    """
    num_classes = teacher_logits.shape[1]
    probs = F.softmax(teacher_logits, dim=1)
    log_probs = F.log_softmax(teacher_logits, dim=1)
    entropy = -(probs * log_probs).sum(dim=1)
    normalized_entropy = entropy / math.log(num_classes)
    h_bar = normalized_entropy.mean()
    t_i = float(t_base) * (1.0 + float(gamma) * (normalized_entropy - h_bar))
    return torch.clamp(t_i, min=1.0, max=2.0 * float(t_base))


class GradientReversalFunction(torch.autograd.Function):
    """Identity on the forward pass; negates (and scales by `lambda_`) the
    gradient on the backward pass."""

    @staticmethod
    def forward(ctx, x, lambda_):
        ctx.lambda_ = float(lambda_)
        return x.view_as(x)

    @staticmethod
    def backward(ctx, grad_output):
        return -ctx.lambda_ * grad_output, None


class CTKDTemperature(nn.Module):
    """Single global learnable KD temperature routed through a gradient
    reversal layer (Li et al. AAAI 2023, simplified to one global scalar
    rather than a per-sample MLP, per the Phase 0 spec's "global öğrenilebilir
    sıcaklık parametresi").

    T = t_min + (t_max - t_min) * sigmoid(GRL(theta, lambda)). `lambda` ramps
    0 -> grl_lambda_max via a cosine schedule over training epochs (via
    set_epoch, called once per epoch by the training loop): early in
    training, gradient from the KD loss barely perturbs theta; later,
    the reversed gradient pushes theta in the direction that makes the KD
    task *harder* -- the curriculum.
    """

    def __init__(self, t_min=1.0, t_max=8.0, grl_lambda_max=1.0):
        super().__init__()
        self.t_min = float(t_min)
        self.t_max = float(t_max)
        self.grl_lambda_max = float(grl_lambda_max)
        # theta=0 -> sigmoid(0)=0.5 -> T starts at the midpoint of [t_min, t_max].
        self.theta = nn.Parameter(torch.zeros(1))
        self._current_epoch = 0
        self._total_epochs = 0

    def set_epoch(self, epoch, total_epochs):
        self._current_epoch = int(epoch)
        self._total_epochs = int(total_epochs)

    def current_lambda(self):
        if self._total_epochs <= 0:
            return 0.0
        progress = min(1.0, max(0.0, self._current_epoch / self._total_epochs))
        return self.grl_lambda_max * (1.0 - math.cos(math.pi * progress)) / 2.0

    def forward(self):
        reversed_theta = GradientReversalFunction.apply(self.theta, self.current_lambda())
        temperature = self.t_min + (self.t_max - self.t_min) * torch.sigmoid(reversed_theta)
        return temperature.squeeze(0)
