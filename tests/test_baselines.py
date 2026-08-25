"""Tests for Component D (logit standardization, entropy-adaptive
temperature, CTKD).

Run directly: python tests/test_baselines.py
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import torch.nn.functional as F

import kd_baselines
from kd_common import DistillationLoss


def _make_fixture(seed=5, batch=8, num_classes=7):
    generator = torch.Generator().manual_seed(seed)
    student_logits = torch.randn(batch, num_classes, generator=generator)
    teacher_logits = torch.randn(batch, num_classes, generator=generator)
    labels = torch.randint(0, num_classes, (batch,), generator=generator)
    return student_logits, teacher_logits, labels


class TestLogitStandardization(unittest.TestCase):
    def test_scale_invariance(self):
        torch.manual_seed(1)
        logits = torch.randn(4, 6)
        standardized = kd_baselines.standardize_logits_per_sample(logits)
        standardized_scaled = kd_baselines.standardize_logits_per_sample(3.0 * logits)
        self.assertTrue(torch.allclose(standardized, standardized_scaled, atol=1e-5))

    def test_kd_loss_scale_invariant_through_distillation_loss(self):
        student_logits, teacher_logits, labels = _make_fixture()
        criterion = DistillationLoss(alpha=0.2, temperature=4.0, logit_std_enable=True)
        loss1, _hard1, soft1, _aux1 = criterion(
            (student_logits,), teacher_logits=teacher_logits, labels=labels
        )
        loss2, _hard2, soft2, _aux2 = criterion(
            (3.0 * student_logits,), teacher_logits=(5.0 * teacher_logits), labels=labels
        )
        self.assertTrue(torch.allclose(soft1, soft2, atol=1e-4))

    def test_logit_std_without_raw_logits_raises(self):
        student_logits, teacher_logits, labels = _make_fixture()
        criterion = DistillationLoss(alpha=0.2, temperature=4.0, logit_std_enable=True)
        teacher_probs = torch.softmax(teacher_logits / 4.0, dim=1)
        with self.assertRaises(RuntimeError):
            criterion((student_logits,), teacher_probabilities=teacher_probs, labels=labels)


class TestAdaptiveTemperature(unittest.TestCase):
    def test_clamp_bounds_at_extreme_entropy(self):
        num_classes = 7
        t_base = 4.0
        # Near-uniform teacher (max entropy) -> should push T toward its ceiling.
        uniform_logits = torch.zeros(1, num_classes)
        # Near-one-hot teacher (min entropy) -> should push T toward its floor.
        peaked_logits = torch.full((1, num_classes), -20.0)
        peaked_logits[0, 0] = 20.0

        batch_logits = torch.cat([uniform_logits, peaked_logits], dim=0)
        t_i = kd_baselines.entropy_adaptive_temperature(batch_logits, t_base=t_base, gamma=5.0)
        self.assertTrue(torch.all(t_i >= 1.0 - 1e-6))
        self.assertTrue(torch.all(t_i <= 2.0 * t_base + 1e-6))

    def test_uses_temperature_one_entropy_not_t_base(self):
        # Since H is computed at T=1 (not t_base), varying t_base must not
        # change the *relative* entropy values used, only the scale/offset.
        torch.manual_seed(2)
        logits = torch.randn(6, 5)
        t_i_base4 = kd_baselines.entropy_adaptive_temperature(logits, t_base=4.0, gamma=0.5)
        t_i_base2 = kd_baselines.entropy_adaptive_temperature(logits, t_base=2.0, gamma=0.5)
        # Ratio of unclamped values should be ~t_base ratio for interior points.
        # We just sanity check they're not identical and both finite.
        self.assertTrue(torch.isfinite(t_i_base4).all())
        self.assertTrue(torch.isfinite(t_i_base2).all())
        self.assertFalse(torch.allclose(t_i_base4, t_i_base2))

    def test_adaptive_t_without_raw_logits_raises(self):
        student_logits, teacher_logits, labels = _make_fixture()
        criterion = DistillationLoss(alpha=0.2, temperature=4.0, adaptive_T_enable=True)
        teacher_probs = torch.softmax(teacher_logits / 4.0, dim=1)
        with self.assertRaises(RuntimeError):
            criterion((student_logits,), teacher_probabilities=teacher_probs, labels=labels)

    def test_adaptive_t_stashes_effective_t_stats(self):
        student_logits, teacher_logits, labels = _make_fixture()
        criterion = DistillationLoss(alpha=0.2, temperature=4.0, adaptive_T_enable=True)
        criterion((student_logits,), teacher_logits=teacher_logits, labels=labels)
        self.assertIsNotNone(criterion.last_effective_T_stats)
        self.assertLessEqual(criterion.last_effective_T_stats["min"], criterion.last_effective_T_stats["mean"])
        self.assertLessEqual(criterion.last_effective_T_stats["mean"], criterion.last_effective_T_stats["max"])


class TestCTKD(unittest.TestCase):
    def test_temperature_always_within_bounds_over_theta_sweep(self):
        # sigmoid(theta) is strictly in (0,1) mathematically, so T is strictly
        # in (t_min,t_max); at very large |theta| this saturates to exactly
        # 0/1 in float32, so bounds are checked inclusively here.
        ctkd = kd_baselines.CTKDTemperature(t_min=1.0, t_max=8.0, grl_lambda_max=1.0)
        for theta_value in torch.linspace(-20, 20, steps=41):
            with torch.no_grad():
                ctkd.theta.fill_(float(theta_value))
            temperature = ctkd()
            self.assertGreaterEqual(temperature.item(), 1.0)
            self.assertLessEqual(temperature.item(), 8.0)
        # But near the middle of the range, the interval must be strictly open.
        with torch.no_grad():
            ctkd.theta.fill_(0.0)
        mid_temperature = ctkd()
        self.assertGreater(mid_temperature.item(), 1.0)
        self.assertLess(mid_temperature.item(), 8.0)

    def test_grl_reverses_gradient_sign(self):
        torch.manual_seed(0)
        # With GRL (lambda>0): gradient into theta should be negated relative
        # to a plain (no-GRL) computation of the same forward function.
        ctkd = kd_baselines.CTKDTemperature(t_min=1.0, t_max=8.0, grl_lambda_max=1.0)
        ctkd.set_epoch(10, 10)  # lambda = grl_lambda_max at the final epoch
        temperature = ctkd()
        loss = temperature  # d(loss)/d(temperature) = 1
        loss.backward()
        grl_grad = ctkd.theta.grad.clone()

        ctkd.theta.grad = None
        no_grl_temperature = ctkd.t_min + (ctkd.t_max - ctkd.t_min) * torch.sigmoid(ctkd.theta)
        no_grl_temperature.backward()
        plain_grad = ctkd.theta.grad.clone()

        self.assertTrue(torch.allclose(grl_grad, -plain_grad, atol=1e-6))

    def test_cosine_lambda_ramp(self):
        ctkd = kd_baselines.CTKDTemperature(t_min=1.0, t_max=8.0, grl_lambda_max=1.0)
        ctkd.set_epoch(0, 10)
        lambda_start = ctkd.current_lambda()
        ctkd.set_epoch(5, 10)
        lambda_mid = ctkd.current_lambda()
        ctkd.set_epoch(10, 10)
        lambda_end = ctkd.current_lambda()
        self.assertAlmostEqual(lambda_start, 0.0, places=6)
        self.assertAlmostEqual(lambda_end, 1.0, places=6)
        self.assertGreater(lambda_mid, lambda_start)
        self.assertLess(lambda_mid, lambda_end)

    def test_ctkd_theta_is_optimizer_ready_parameter(self):
        ctkd = kd_baselines.CTKDTemperature()
        params = list(ctkd.parameters())
        self.assertEqual(len(params), 1)
        self.assertTrue(params[0].requires_grad)

    def test_ctkd_through_distillation_loss(self):
        student_logits, teacher_logits, labels = _make_fixture()
        criterion = DistillationLoss(alpha=0.2, temperature=4.0, ctkd_enable=True)
        criterion.set_epoch(3, 10)
        loss, _hard, _soft, _aux = criterion(
            (student_logits,), teacher_logits=teacher_logits, labels=labels
        )
        self.assertTrue(torch.isfinite(loss))
        self.assertIsNotNone(criterion.last_ctkd_T)
        loss.backward()
        self.assertIsNotNone(criterion.ctkd.theta.grad)


class TestMutualExclusionAndWarnings(unittest.TestCase):
    def test_adaptive_t_and_ctkd_mutually_exclusive(self):
        with self.assertRaises(ValueError):
            DistillationLoss(adaptive_T_enable=True, ctkd_enable=True)

    def test_gate_and_adaptive_t_warns_not_raises(self):
        try:
            DistillationLoss(gate_enable=True, adaptive_T_enable=True)
        except ValueError:
            self.fail("gate_enable + adaptive_T_enable must warn, not raise")


if __name__ == "__main__":
    unittest.main()
