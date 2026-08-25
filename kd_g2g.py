"""Gaussian-to-Gaussian class-space distillation (Phase 0, Component B).

Distills the teacher's class-space diagonal Gaussian N(mu_t, exp(logvar_t))
into the student's N(mu_s, exp(logvar_s)) -- per-class independent. Pure,
stateless functions: G2G carries no learnable parameters or running state
(unlike the gate's EMA normalizer or CTKD's learnable temperature), so no
nn.Module is needed here.
"""
import torch


def clamp_logvar(logvar, min_value=-10.0, max_value=10.0):
    return torch.clamp(logvar, min=min_value, max=max_value)


def g2g_kl(mu_t, logvar_t, mu_s, logvar_s, clamp=True, clamp_min=-10.0, clamp_max=10.0):
    """Per-sample KL(N(mu_t, var_t) || N(mu_s, var_s)), summed over classes.

    KL_i = sum_c[ 0.5*(logvar_s - logvar_t)
                + (exp(logvar_t) + (mu_t - mu_s)^2) / (2*exp(logvar_s))
                - 0.5 ]

    Direction: this is KL(teacher || student) -- the teacher is the
    reference distribution p, the student is the approximation q, matching
    `torch.distributions.kl_divergence(Normal(mu_t, std_t), Normal(mu_s, std_s))`
    with that exact (p, q) argument order (verified in tests/test_g2g.py).
    """
    if clamp:
        logvar_t = clamp_logvar(logvar_t, clamp_min, clamp_max)
        logvar_s = clamp_logvar(logvar_s, clamp_min, clamp_max)
    term = (
        0.5 * (logvar_s - logvar_t)
        + (torch.exp(logvar_t) + (mu_t - mu_s).pow(2)) / (2.0 * torch.exp(logvar_s))
        - 0.5
    )
    return term.sum(dim=1)


def g2g_w2(mu_t, logvar_t, mu_s, logvar_s, clamp=True, clamp_min=-10.0, clamp_max=10.0):
    """Per-sample squared 2-Wasserstein distance between the two diagonal Gaussians.

    W2sq_i = sum_c[ (mu_t - mu_s)^2 + (exp(0.5*logvar_t) - exp(0.5*logvar_s))^2 ]
    """
    if clamp:
        logvar_t = clamp_logvar(logvar_t, clamp_min, clamp_max)
        logvar_s = clamp_logvar(logvar_s, clamp_min, clamp_max)
    term = (mu_t - mu_s).pow(2) + (torch.exp(0.5 * logvar_t) - torch.exp(0.5 * logvar_s)).pow(2)
    return term.sum(dim=1)


def g2g_term(mu_t, logvar_t, mu_s, logvar_s, mode="kl", clamp=True, clamp_min=-10.0, clamp_max=10.0):
    """Per-sample G2G term for the requested mode ("kl" or "w2")."""
    if mode == "kl":
        return g2g_kl(mu_t, logvar_t, mu_s, logvar_s, clamp=clamp, clamp_min=clamp_min, clamp_max=clamp_max)
    if mode == "w2":
        return g2g_w2(mu_t, logvar_t, mu_s, logvar_s, clamp=clamp, clamp_min=clamp_min, clamp_max=clamp_max)
    raise ValueError(f"Unsupported G2G mode: {mode!r}")


def validate_g2g_shapes(teacher_mu, teacher_logvar, student_mu, student_logvar):
    """Raise a clear, actionable error naming which side lacks mu/logvar,
    instead of letting G2G silently no-op (per the Phase 0 spec's explicit
    "fail loudly, don't silently disable" requirement)."""
    missing = []
    if teacher_mu is None or teacher_logvar is None:
        missing.append("teacher")
    if student_mu is None or student_logvar is None:
        missing.append("student")
    if missing:
        raise RuntimeError(
            "g2g_enable=True requires both teacher and student heads to expose "
            "(mu, logvar) in class space (VICH or VAE-style heads only, not a "
            f"plain linear head). Missing mu/logvar on: {', '.join(missing)}. "
            "Use a VICH/VAE head on that side, or disable G2G."
        )
    if teacher_mu.shape != student_mu.shape:
        raise RuntimeError(
            f"G2G requires matching class-space shapes: teacher mu {tuple(teacher_mu.shape)} "
            f"!= student mu {tuple(student_mu.shape)}."
        )


def g2g_warmup_factor(current_epoch, warmup_epochs):
    """Linear 0->1 ramp of the G2G weight over the first `warmup_epochs` epochs.

    Returns 1.0 (no warmup) if `warmup_epochs <= 0`; clamped to [0, 1] so any
    epoch at or beyond the warmup window uses the full weight.
    """
    warmup_epochs = int(warmup_epochs)
    if warmup_epochs <= 0:
        return 1.0
    return max(0.0, min(1.0, float(current_epoch) / float(warmup_epochs)))
