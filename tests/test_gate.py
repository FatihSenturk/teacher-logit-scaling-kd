"""Tests for Component A (uncertainty-gated per-sample alpha).

Run directly: python tests/test_gate.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import torch.nn.functional as F

import kd_uncertainty
from kd_common import DistillationLoss


def _make_fixture(seed=11, batch=8, num_classes=7):
    generator = torch.Generator().manual_seed(seed)
    student_logits = torch.randn(batch, num_classes, generator=generator)
    student_mu = torch.randn(batch, num_classes, generator=generator)
    student_logvar = torch.randn(batch, num_classes, generator=generator) * 0.1 - 1.0
    teacher_logits = torch.randn(batch, num_classes, generator=generator)
    teacher_mu = torch.randn(batch, num_classes, generator=generator)
    teacher_logvar = torch.randn(batch, num_classes, generator=generator) * 0.3 - 0.5
    labels = torch.randint(0, num_classes, (batch,), generator=generator)
    return (
        student_logits, student_mu, student_logvar,
        teacher_logits, teacher_mu, teacher_logvar, labels,
    )


class TestGateOff(unittest.TestCase):
    def test_gate_off_by_default(self):
        criterion = DistillationLoss(alpha=0.2, temperature=6.0)
        self.assertFalse(criterion.gate_enable)
        self.assertIsNone(criterion.gate_normalizer)
        self.assertIsNone(criterion.last_alpha_stats)


class TestGateDegenerate(unittest.TestCase):
    def test_degenerate_alpha_lo_eq_hi_matches_nongated_path(self):
        (student_logits, student_mu, student_logvar,
         teacher_logits, teacher_mu, teacher_logvar, labels) = _make_fixture()
        student_output = (student_logits, student_mu, student_logvar)
        alpha, temperature = 0.35, 5.0

        nongated = DistillationLoss(alpha=alpha, temperature=temperature)
        loss_nongated, hard_nongated, soft_nongated, _ = nongated(
            student_output, teacher_logits=teacher_logits, labels=labels
        )

        gated = DistillationLoss(
            alpha=alpha, temperature=temperature,
            gate_enable=True, gate_alpha_lo=alpha, gate_alpha_hi=alpha,
            gate_uncertainty_source="mean_logvar",
        )
        loss_gated, hard_gated, soft_gated, _ = gated(
            student_output, teacher_logits=teacher_logits, labels=labels,
            teacher_mu=teacher_mu, teacher_logvar=teacher_logvar,
        )

        self.assertTrue(torch.allclose(loss_gated, loss_nongated, atol=1e-5))
        self.assertIsNotNone(gated.last_alpha_stats)
        self.assertAlmostEqual(gated.last_alpha_stats["min"], alpha, places=5)
        self.assertAlmostEqual(gated.last_alpha_stats["max"], alpha, places=5)


class TestGateMonotonic(unittest.TestCase):
    def test_alpha_monotonic_in_u_hat(self):
        u_hat = torch.linspace(-5, 5, steps=21)
        alpha = kd_uncertainty.gate_alpha(u_hat, alpha_lo=0.1, alpha_hi=0.7, k=2.0, tau=0.0)
        diffs = alpha[1:] - alpha[:-1]
        self.assertTrue(torch.all(diffs >= 0))
        self.assertGreater(alpha.max().item(), alpha.min().item())

    def test_alpha_bounded_by_lo_hi(self):
        u_hat = torch.linspace(-50, 50, steps=101)
        alpha = kd_uncertainty.gate_alpha(u_hat, alpha_lo=0.1, alpha_hi=0.7, k=2.0, tau=0.0)
        self.assertTrue(torch.all(alpha >= 0.1 - 1e-6))
        self.assertTrue(torch.all(alpha <= 0.7 + 1e-6))


class TestUncertaintyNormalizer(unittest.TestCase):
    def test_batch_mode_uses_current_batch_stats_always(self):
        normalizer = kd_uncertainty.UncertaintyNormalizer(mode="batch")
        u1 = torch.tensor([1.0, 2.0, 3.0, 4.0])
        u2 = torch.tensor([10.0, 20.0, 30.0, 40.0])
        out1 = normalizer(u1)
        out2 = normalizer(u2)
        # Each call re-derives mean/std from its own batch -> both end up
        # with the same normalized shape regardless of scale.
        self.assertTrue(torch.allclose(out1, out2, atol=1e-4))

    def test_running_mode_updates_only_in_training(self):
        normalizer = kd_uncertainty.UncertaintyNormalizer(mode="running", momentum=0.9)
        normalizer.train()
        normalizer(torch.tensor([1.0, 2.0, 3.0]))
        mean_after_train = normalizer.running_mean.clone()

        normalizer.eval()
        normalizer(torch.tensor([100.0, 200.0, 300.0]))
        mean_after_eval = normalizer.running_mean.clone()

        self.assertTrue(torch.allclose(mean_after_train, mean_after_eval))

    def test_running_mode_diverges_from_batch_mode(self):
        running = kd_uncertainty.UncertaintyNormalizer(mode="running", momentum=0.5)
        batch = kd_uncertainty.UncertaintyNormalizer(mode="batch")
        running.train()
        running(torch.tensor([0.0, 0.0, 0.0, 0.0]))  # seeds running stats at mean=0, var=0
        out_running = running(torch.tensor([10.0, 20.0, 30.0, 40.0]))
        out_batch = batch(torch.tensor([10.0, 20.0, 30.0, 40.0]))
        self.assertFalse(torch.allclose(out_running, out_batch))


class TestResolveUncertainty(unittest.TestCase):
    def test_entropy_needs_no_mu_logvar(self):
        probs = torch.softmax(torch.randn(4, 5), dim=1)
        result = kd_uncertainty.resolve_uncertainty("entropy", probs, None, None, torch.randint(0, 5, (4,)))
        self.assertEqual(result.shape, (4,))
        self.assertTrue(torch.all(result >= 0))

    def test_non_entropy_source_without_mu_logvar_raises(self):
        probs = torch.softmax(torch.randn(4, 5), dim=1)
        labels = torch.randint(0, 5, (4,))
        for source in ("mean_logvar", "target_logvar", "top2_logvar"):
            with self.assertRaises(RuntimeError):
                kd_uncertainty.resolve_uncertainty(source, probs, None, None, labels)

    def test_target_logvar_hard_label_indexing(self):
        logvar = torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        labels = torch.tensor([0, 2])
        probs = torch.softmax(torch.randn(2, 3), dim=1)
        got = kd_uncertainty.target_logvar(logvar, labels, probs)
        self.assertTrue(torch.allclose(got, torch.tensor([1.0, 6.0])))

    def test_target_logvar_soft_label_uses_teacher_argmax(self):
        logvar = torch.tensor([[1.0, 2.0, 3.0]])
        soft_labels = torch.tensor([[0.5, 0.3, 0.2]])  # ndim==2 -> "no hard label"
        probs = torch.tensor([[0.1, 0.1, 0.8]])  # teacher argmax = class 2
        got = kd_uncertainty.target_logvar(logvar, soft_labels, probs)
        self.assertTrue(torch.allclose(got, torch.tensor([3.0])))


class TestDistillationLossGateIntegration(unittest.TestCase):
    def test_missing_teacher_mu_logvar_raises_for_non_entropy_source(self):
        (student_logits, student_mu, student_logvar,
         teacher_logits, _teacher_mu, _teacher_logvar, labels) = _make_fixture()
        student_output = (student_logits, student_mu, student_logvar)
        criterion = DistillationLoss(
            alpha=0.2, temperature=6.0, gate_enable=True, gate_uncertainty_source="mean_logvar"
        )
        with self.assertRaises(RuntimeError):
            criterion(student_output, teacher_logits=teacher_logits, labels=labels)

    def test_entropy_source_works_without_teacher_mu_logvar(self):
        (student_logits, student_mu, student_logvar,
         teacher_logits, _teacher_mu, _teacher_logvar, labels) = _make_fixture()
        student_output = (student_logits, student_mu, student_logvar)
        criterion = DistillationLoss(
            alpha=0.2, temperature=6.0, gate_enable=True, gate_uncertainty_source="entropy"
        )
        loss, _hard, _soft, _aux = criterion(student_output, teacher_logits=teacher_logits, labels=labels)
        self.assertTrue(torch.isfinite(loss))
        self.assertIsNotNone(criterion.last_alpha_stats)

    def test_gate_and_class_weights_raises_at_construction(self):
        weights = torch.ones(7)
        with self.assertRaises(ValueError):
            DistillationLoss(gate_enable=True, class_weights=weights)


if __name__ == "__main__":
    unittest.main()
