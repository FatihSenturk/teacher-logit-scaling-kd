"""Tests for Component B (Gaussian-to-Gaussian class-space distillation).

Run directly: python tests/test_g2g.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import torch.distributions as dist

import kd_g2g
from kd_common import DistillationLoss


def _make_gaussians(seed=7, batch=6, num_classes=5):
    generator = torch.Generator().manual_seed(seed)
    mu_t = torch.randn(batch, num_classes, generator=generator)
    logvar_t = torch.randn(batch, num_classes, generator=generator) * 0.5
    mu_s = torch.randn(batch, num_classes, generator=generator)
    logvar_s = torch.randn(batch, num_classes, generator=generator) * 0.5
    return mu_t, logvar_t, mu_s, logvar_s


class TestG2GKL(unittest.TestCase):
    def test_kl_matches_torch_distributions_direction_teacher_to_student(self):
        mu_t, logvar_t, mu_s, logvar_s = _make_gaussians()
        got = kd_g2g.g2g_kl(mu_t, logvar_t, mu_s, logvar_s)

        std_t = torch.exp(0.5 * logvar_t)
        std_s = torch.exp(0.5 * logvar_s)
        p_teacher = dist.Normal(mu_t, std_t)
        q_student = dist.Normal(mu_s, std_s)
        expected = dist.kl_divergence(p_teacher, q_student).sum(dim=1)

        self.assertTrue(torch.allclose(got, expected, atol=1e-5))

    def test_kl_direction_is_not_symmetric(self):
        # Sanity: KL(t||s) != KL(s||t) in general, confirming we didn't
        # accidentally implement the reversed direction and have it look right
        # only because the test fixture happens to be symmetric.
        mu_t, logvar_t, mu_s, logvar_s = _make_gaussians()
        forward_kl = kd_g2g.g2g_kl(mu_t, logvar_t, mu_s, logvar_s)
        reversed_kl = kd_g2g.g2g_kl(mu_s, logvar_s, mu_t, logvar_t)
        self.assertFalse(torch.allclose(forward_kl, reversed_kl))

    def test_extreme_logvar_stays_finite_with_clamp(self):
        mu_t = torch.zeros(2, 3)
        mu_s = torch.zeros(2, 3)
        logvar_t = torch.full((2, 3), 50.0)
        logvar_s = torch.full((2, 3), -50.0)
        got = kd_g2g.g2g_kl(mu_t, logvar_t, mu_s, logvar_s, clamp=True)
        self.assertTrue(torch.isfinite(got).all())
        # Must match the clamped reference exactly (clamp really is applied).
        clamped_t = kd_g2g.clamp_logvar(logvar_t)
        clamped_s = kd_g2g.clamp_logvar(logvar_s)
        expected = kd_g2g.g2g_kl(mu_t, clamped_t, mu_s, clamped_s, clamp=False)
        self.assertTrue(torch.allclose(got, expected))

    def test_unclamped_extreme_logvar_can_overflow(self):
        # Documents *why* clamping is mandatory: without it, this combination
        # overflows float32 to +inf.
        mu_t = torch.zeros(1, 1)
        mu_s = torch.zeros(1, 1)
        logvar_t = torch.tensor([[50.0]])
        logvar_s = torch.tensor([[-50.0]])
        got = kd_g2g.g2g_kl(mu_t, logvar_t, mu_s, logvar_s, clamp=False)
        self.assertFalse(torch.isfinite(got).all())


class TestG2GW2(unittest.TestCase):
    def test_w2_hand_computed_example(self):
        mu_t = torch.tensor([[0.0, 1.0]])
        logvar_t = torch.tensor([[0.0, 0.0]])  # var=1 -> std=1
        mu_s = torch.tensor([[1.0, 1.0]])
        logvar_s = torch.tensor([[2.0 * torch.log(torch.tensor(2.0)), 0.0]])  # std=2 in dim0
        # dim0: (0-1)^2 + (1-2)^2 = 1 + 1 = 2
        # dim1: (1-1)^2 + (1-1)^2 = 0
        expected = torch.tensor([2.0])
        got = kd_g2g.g2g_w2(mu_t, logvar_t, mu_s, logvar_s)
        self.assertTrue(torch.allclose(got, expected, atol=1e-5))

    def test_w2_extreme_logvar_stays_finite_with_clamp(self):
        mu_t = torch.zeros(2, 3)
        mu_s = torch.zeros(2, 3)
        logvar_t = torch.full((2, 3), 50.0)
        logvar_s = torch.full((2, 3), -50.0)
        got = kd_g2g.g2g_w2(mu_t, logvar_t, mu_s, logvar_s, clamp=True)
        self.assertTrue(torch.isfinite(got).all())


class TestValidateShapes(unittest.TestCase):
    def test_missing_teacher_raises(self):
        mu_s = torch.randn(2, 3)
        logvar_s = torch.randn(2, 3)
        with self.assertRaises(RuntimeError) as ctx:
            kd_g2g.validate_g2g_shapes(None, None, mu_s, logvar_s)
        self.assertIn("teacher", str(ctx.exception))

    def test_missing_student_raises(self):
        mu_t = torch.randn(2, 3)
        logvar_t = torch.randn(2, 3)
        with self.assertRaises(RuntimeError) as ctx:
            kd_g2g.validate_g2g_shapes(mu_t, logvar_t, None, None)
        self.assertIn("student", str(ctx.exception))

    def test_shape_mismatch_raises(self):
        mu_t = torch.randn(2, 3)
        logvar_t = torch.randn(2, 3)
        mu_s = torch.randn(2, 4)
        logvar_s = torch.randn(2, 4)
        with self.assertRaises(RuntimeError):
            kd_g2g.validate_g2g_shapes(mu_t, logvar_t, mu_s, logvar_s)


class TestWarmup(unittest.TestCase):
    def test_no_warmup_returns_one(self):
        self.assertEqual(kd_g2g.g2g_warmup_factor(current_epoch=5, warmup_epochs=0), 1.0)

    def test_warmup_at_start_mid_end_and_beyond(self):
        self.assertEqual(kd_g2g.g2g_warmup_factor(0, 10), 0.0)
        self.assertAlmostEqual(kd_g2g.g2g_warmup_factor(5, 10), 0.5)
        self.assertEqual(kd_g2g.g2g_warmup_factor(10, 10), 1.0)
        self.assertEqual(kd_g2g.g2g_warmup_factor(20, 10), 1.0)


class TestDistillationLossIntegration(unittest.TestCase):
    def test_g2g_disabled_by_default_no_change(self):
        criterion = DistillationLoss(alpha=0.2, temperature=6.0)
        self.assertFalse(criterion.g2g_enable)
        self.assertIsNone(criterion.last_g2g_term)

    def test_g2g_enabled_adds_term_and_stashes_diagnostic(self):
        batch, num_classes = 4, 7
        generator = torch.Generator().manual_seed(3)
        student_logits = torch.randn(batch, num_classes, generator=generator)
        student_mu = torch.randn(batch, num_classes, generator=generator)
        student_logvar = torch.randn(batch, num_classes, generator=generator) * 0.1 - 1.0
        student_output = {
            "logits": student_logits,
            "mu": student_mu,
            "logvar": student_logvar,
            "kl_loss": torch.tensor(0.0),
        }
        teacher_logits = torch.randn(batch, num_classes, generator=generator)
        teacher_mu = torch.randn(batch, num_classes, generator=generator)
        teacher_logvar = torch.randn(batch, num_classes, generator=generator) * 0.1 - 1.0
        labels = torch.randint(0, num_classes, (batch,), generator=generator)

        criterion_off = DistillationLoss(alpha=0.2, temperature=6.0, beta_vich=1e-4)
        loss_off, *_ = criterion_off(
            student_output, teacher_logits=teacher_logits, labels=labels,
            teacher_mu=teacher_mu, teacher_logvar=teacher_logvar,
        )

        criterion_on = DistillationLoss(
            alpha=0.2, temperature=6.0, beta_vich=1e-4,
            g2g_enable=True, g2g_weight=0.5, g2g_mode="kl",
        )
        loss_on, *_ = criterion_on(
            student_output, teacher_logits=teacher_logits, labels=labels,
            teacher_mu=teacher_mu, teacher_logvar=teacher_logvar,
        )

        self.assertIsNotNone(criterion_on.last_g2g_term)
        self.assertFalse(torch.allclose(loss_off, loss_on))
        expected_term = kd_g2g.g2g_term(teacher_mu, teacher_logvar, student_mu, student_logvar, mode="kl").mean()
        self.assertTrue(torch.allclose(loss_on, loss_off + 0.5 * expected_term, atol=1e-5))

    def test_g2g_enabled_without_teacher_mu_raises(self):
        batch, num_classes = 4, 7
        student_output = {
            "logits": torch.randn(batch, num_classes),
            "mu": torch.randn(batch, num_classes),
            "logvar": torch.randn(batch, num_classes),
            "kl_loss": torch.tensor(0.0),
        }
        labels = torch.randint(0, num_classes, (batch,))
        criterion = DistillationLoss(alpha=0.2, temperature=6.0, g2g_enable=True, g2g_weight=0.5)
        with self.assertRaises(RuntimeError):
            criterion(student_output, teacher_logits=torch.randn(batch, num_classes), labels=labels)


if __name__ == "__main__":
    unittest.main()
