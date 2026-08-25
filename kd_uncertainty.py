"""Uncertainty-gated KD (Phase 0, Component A): per-sample alpha from teacher
uncertainty.

All uncertainty sources operate on `teacher_probabilities` (softmax(logits/T),
already computed by the training loop for the KD soft-loss term) rather than
raw teacher logits, so the gate works regardless of whether raw logits are
being threaded through for the Component D baselines (logit standardization /
adaptive-T / CTKD) -- the gate and those baselines are independent axes.
"""
import torch
import torch.nn as nn


def mean_logvar(teacher_logvar):
    """u_i = mean_c(logvar_t[i, c])."""
    return teacher_logvar.mean(dim=1)


def target_logvar(teacher_logvar, labels, teacher_probabilities):
    """u_i = logvar_t[i, y_i].

    y_i is the hard label when `labels` is a 1-D class-index tensor; when
    `labels` is a soft distribution (e.g. FERPlus vote shares, ndim==2 --
    "no hard label"), y_i falls back to the teacher's own predicted class
    (argmax of `teacher_probabilities`), per the spec's "hard label yoksa
    argmax teacher" rule.
    """
    if labels.ndim == 1:
        index = labels.long()
    else:
        index = teacher_probabilities.argmax(dim=1)
    return teacher_logvar.gather(1, index.view(-1, 1)).squeeze(1)


def top2_logvar(teacher_probabilities, teacher_logvar):
    """Mean logvar of the teacher's top-2 predicted classes (by probability)."""
    top2_indices = teacher_probabilities.topk(2, dim=1).indices
    gathered = teacher_logvar.gather(1, top2_indices)
    return gathered.mean(dim=1)


def entropy_from_probabilities(probabilities, eps=1e-12):
    """H(p) = -sum_c(p_c * log(p_c)), for p = softmax(teacher_logits / T).

    Needs no VICH/VAE head -- the baseline uncertainty source, usable with
    a plain linear teacher head.
    """
    return -(probabilities * torch.log(probabilities.clamp_min(eps))).sum(dim=1)


def oracle_error(teacher_probabilities, labels):
    """u_i = 1.0 if the teacher's own top-1 prediction is wrong, else 0.0.

    A synthetic, perfect-information uncertainty signal (by construction
    equivalent to knowing the teacher's error in advance) -- derived only
    from teacher_probabilities and labels, no mu/logvar needed, so it works
    with any head type. Used to upper-bound how much per-sample gating could
    help if the uncertainty proxy were flawless, isolating "does per-sample
    gating help at all on this dataset" from "is logvar/entropy a good
    uncertainty proxy" -- diagnostic-only, not a real deployable signal
    (it requires the ground-truth label, which gating is meant to reduce
    reliance on, not consume directly).
    """
    target_index = labels.long() if labels.ndim == 1 else labels.argmax(dim=1)
    predicted = teacher_probabilities.argmax(dim=1)
    return (predicted != target_index).float()


_SOURCES = {"mean_logvar", "target_logvar", "top2_logvar", "entropy", "oracle_error"}


def resolve_uncertainty(source, teacher_probabilities, teacher_mu, teacher_logvar, labels):
    """Dispatch to the requested uncertainty source, raising an actionable
    error if a non-entropy source is requested without teacher mu/logvar."""
    if source == "entropy":
        return entropy_from_probabilities(teacher_probabilities)
    if source == "oracle_error":
        return oracle_error(teacher_probabilities, labels)
    if teacher_mu is None or teacher_logvar is None:
        raise RuntimeError(
            f"gate_uncertainty_source={source!r} requires the teacher to expose "
            "(mu, logvar) (VICH/VAE head); got a plain-logits teacher. Use "
            "gate_uncertainty_source='entropy' (needs no mu/logvar) or a VICH/VAE "
            "teacher head."
        )
    if source == "mean_logvar":
        return mean_logvar(teacher_logvar)
    if source == "target_logvar":
        return target_logvar(teacher_logvar, labels, teacher_probabilities)
    if source == "top2_logvar":
        return top2_logvar(teacher_probabilities, teacher_logvar)
    raise ValueError(f"Unsupported gate_uncertainty_source: {source!r}")


class UncertaintyNormalizer(nn.Module):
    """Normalizes a per-sample uncertainty signal: u_hat_i = (u_i - mean)/(std+eps).

    mode="batch": always uses the current batch's mean/std -- no persistent
    state, identical behavior in train and eval.

    mode="running": maintains an EMA of mean/var (momentum=0.99 by default),
    updated only while `self.training` is True; eval-time normalization uses
    the frozen running stats and never updates them (matches the spec's
    "running modunda ... eval sirasinda guncelleme yapma").
    """

    def __init__(self, mode="batch", momentum=0.99, eps=1e-6):
        super().__init__()
        if mode not in {"batch", "running"}:
            raise ValueError(f"Unsupported normalization mode: {mode!r}")
        self.mode = str(mode)
        self.momentum = float(momentum)
        self.eps = float(eps)
        self.register_buffer("running_mean", torch.tensor(0.0))
        self.register_buffer("running_var", torch.tensor(1.0))
        self.register_buffer("initialized", torch.tensor(False))

    def forward(self, u):
        u = u.float()
        if self.mode == "batch":
            mean = u.mean()
            var = u.var(unbiased=False)
            return (u - mean) / (var.sqrt() + self.eps)

        if self.training:
            with torch.no_grad():
                batch_mean = u.mean()
                batch_var = u.var(unbiased=False)
                if not bool(self.initialized):
                    self.running_mean.copy_(batch_mean)
                    self.running_var.copy_(batch_var)
                    self.initialized.fill_(True)
                else:
                    self.running_mean.mul_(self.momentum).add_(batch_mean * (1.0 - self.momentum))
                    self.running_var.mul_(self.momentum).add_(batch_var * (1.0 - self.momentum))

        return (u - self.running_mean) / (self.running_var.sqrt() + self.eps)


def gate_alpha(u_hat, alpha_lo, alpha_hi, k, tau):
    """alpha_i = alpha_lo + (alpha_hi - alpha_lo) * sigmoid(k * (u_hat_i - tau)).

    Higher teacher uncertainty -> higher alpha_i (lean on the hard label
    more); lower uncertainty -> lower alpha_i (KD dominates).
    """
    return alpha_lo + (alpha_hi - alpha_lo) * torch.sigmoid(k * (u_hat - tau))
