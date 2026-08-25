"""Regression net: with all Phase 0 flags at their off/default values,
DistillationLoss must produce numerically identical output to the
pre-Phase-0 formula. This is the test that must stay green through every
later step (G2G, gate, baselines, train-script integration) -- it is re-run
as the final check after all of them.

Run directly: python tests/test_kd_backward_compat.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import torch
import torch.nn as nn
import torch.nn.functional as F

from kd_common import DistillationLoss, extract_mu_logvar


def _make_fixture(seed=42, batch=8, num_classes=7):
    generator = torch.Generator().manual_seed(seed)
    student_logits = torch.randn(batch, num_classes, generator=generator)
    student_mu = torch.randn(batch, num_classes, generator=generator)
    student_logvar = torch.randn(batch, num_classes, generator=generator) * 0.1 - 1.0
    teacher_logits = torch.randn(batch, num_classes, generator=generator)
    labels = torch.randint(0, num_classes, (batch,), generator=generator)
    return student_logits, student_mu, student_logvar, teacher_logits, labels


class TestBackwardCompat(unittest.TestCase):
    def test_matches_reference_formula_hard_and_soft(self):
        """Independent reimplementation of the pre-Phase-0 formula, not a
        call into any refactored code path -- this is the real bit-identical
        guarantee, robust to internal refactors in later steps."""
        student_logits, student_mu, student_logvar, teacher_logits, labels = _make_fixture()
        student_output = (student_logits, student_mu, student_logvar)
        alpha, temperature, label_smoothing = 0.3, 4.0, 0.1
        vae_kl_beta, beta_vich = 0.001, 1e-4

        hard_ref = F.cross_entropy(student_logits, labels.long(), label_smoothing=label_smoothing)
        teacher_probs = F.softmax(teacher_logits / temperature, dim=1)
        soft_student = F.log_softmax(student_logits / temperature, dim=1)
        soft_ref = nn.KLDivLoss(reduction="batchmean")(soft_student, teacher_probs) * (temperature ** 2)
        aux_kl_ref = -0.5 * torch.sum(
            1.0 + student_logvar - student_mu.pow(2) - student_logvar.exp(), dim=1
        ).mean()
        loss_ref = alpha * hard_ref + (1.0 - alpha) * soft_ref + vae_kl_beta * aux_kl_ref

        criterion = DistillationLoss(
            alpha=alpha,
            temperature=temperature,
            label_smoothing=label_smoothing,
            vae_kl_beta=vae_kl_beta,
            beta_vich=beta_vich,
        )
        loss, hard_loss, soft_loss, aux_kl = criterion(
            student_output, labels=labels, teacher_probabilities=teacher_probs
        )

        self.assertTrue(torch.allclose(loss, loss_ref, atol=1e-6))
        self.assertTrue(torch.allclose(hard_loss, hard_ref, atol=1e-6))
        self.assertTrue(torch.allclose(soft_loss, soft_ref, atol=1e-6))
        self.assertTrue(torch.allclose(aux_kl, aux_kl_ref, atol=1e-6))

    def test_hard_only_no_teacher(self):
        student_logits, student_mu, student_logvar, _teacher_logits, labels = _make_fixture()
        kl_loss = -0.5 * torch.sum(
            1.0 + student_logvar - student_mu.pow(2) - student_logvar.exp(), dim=1
        ).mean()
        student_output = {"logits": student_logits, "mu": student_mu, "logvar": student_logvar, "kl_loss": kl_loss}
        beta_vich = 1e-4
        criterion = DistillationLoss(alpha=0.2, temperature=6.0, label_smoothing=0.0, beta_vich=beta_vich)
        loss, hard_loss, soft_loss, aux_kl = criterion(student_output, labels=labels)
        hard_ref = F.cross_entropy(student_logits, labels.long())
        self.assertTrue(torch.allclose(hard_loss, hard_ref, atol=1e-6))
        self.assertTrue(torch.allclose(soft_loss, torch.zeros_like(soft_loss)))
        self.assertTrue(torch.allclose(aux_kl, kl_loss))
        self.assertTrue(torch.allclose(loss, hard_ref + beta_vich * kl_loss, atol=1e-6))

    def test_new_kwargs_at_default_match_implicit_default(self):
        student_logits, student_mu, student_logvar, teacher_logits, labels = _make_fixture()
        student_output = (student_logits, student_mu, student_logvar)
        teacher_probs = torch.softmax(teacher_logits / 6.0, dim=1)

        implicit = DistillationLoss(alpha=0.2, temperature=6.0, label_smoothing=0.2, vae_kl_beta=0.001, beta_vich=1e-4)
        explicit = DistillationLoss(
            alpha=0.2, temperature=6.0, label_smoothing=0.2, vae_kl_beta=0.001, beta_vich=1e-4,
            gate_enable=False, g2g_enable=False, logit_std_enable=False,
            adaptive_T_enable=False, ctkd_enable=False,
        )
        out_implicit = implicit(student_output, labels=labels, teacher_probabilities=teacher_probs)
        out_explicit = explicit(student_output, labels=labels, teacher_probabilities=teacher_probs)
        for a, b in zip(out_implicit, out_explicit):
            self.assertTrue(torch.allclose(a, b, atol=1e-7, rtol=1e-6))

    def test_vich_dict_student_path_unchanged(self):
        student_logits, student_mu, student_logvar, teacher_logits, labels = _make_fixture()
        kl_loss = -0.5 * torch.sum(
            1.0 + student_logvar - student_mu.pow(2) - student_logvar.exp(), dim=1
        ).mean()
        student_output = {"logits": student_logits, "mu": student_mu, "logvar": student_logvar, "kl_loss": kl_loss}
        criterion = DistillationLoss(alpha=0.2, temperature=6.0, label_smoothing=0.0, beta_vich=1e-4)
        _loss, _hard, _soft, aux_kl = criterion(student_output, teacher_logits=teacher_logits, labels=labels)
        self.assertTrue(torch.allclose(aux_kl, kl_loss))

    def test_vae_tuple_student_path_unchanged(self):
        student_logits, student_mu, student_logvar, teacher_logits, labels = _make_fixture()
        student_output = (student_logits, student_mu, student_logvar)
        criterion = DistillationLoss(alpha=0.2, temperature=6.0, label_smoothing=0.0, vae_kl_beta=0.001)
        _loss, _hard, _soft, aux_kl = criterion(student_output, teacher_logits=teacher_logits, labels=labels)
        expected_kl = -0.5 * torch.sum(
            1.0 + student_logvar - student_mu.pow(2) - student_logvar.exp(), dim=1
        ).mean()
        self.assertTrue(torch.allclose(aux_kl, expected_kl))

    def test_train_rafdb_kd_positional_call_shape(self):
        """Mirrors train_rafdb_kd.py's exact call shape:
        DistillationLoss(args.alpha, args.temperature, args.label_smoothing,
                          args.student_vae_kl_beta, args.beta_vich, class_weights=class_weights)
        Guards against a future signature edit accidentally reordering the
        first five positional parameters.
        """
        criterion = DistillationLoss(0.2, 6.0, 0.2, 0.001, 1e-4, class_weights=None)
        self.assertEqual(criterion.alpha, 0.2)
        self.assertEqual(criterion.temperature, 6.0)
        self.assertEqual(criterion.label_smoothing, 0.2)
        self.assertEqual(criterion.vae_kl_beta, 0.001)
        self.assertEqual(criterion.beta_vich, 1e-4)

    def test_extract_mu_logvar_dict_shape(self):
        mu = torch.randn(2, 3)
        logvar = torch.randn(2, 3)
        output = {"logits": torch.randn(2, 3), "mu": mu, "logvar": logvar, "kl_loss": torch.tensor(0.0)}
        got_mu, got_logvar = extract_mu_logvar(output)
        self.assertIs(got_mu, mu)
        self.assertIs(got_logvar, logvar)

    def test_extract_mu_logvar_tuple_shape(self):
        logits = torch.randn(2, 3)
        mu = torch.randn(2, 3)
        logvar = torch.randn(2, 3)
        got_mu, got_logvar = extract_mu_logvar((logits, mu, logvar))
        self.assertIs(got_mu, mu)
        self.assertIs(got_logvar, logvar)

    def test_extract_mu_logvar_bare_tensor_shape(self):
        logits = torch.randn(2, 3)
        got_mu, got_logvar = extract_mu_logvar(logits)
        self.assertIsNone(got_mu)
        self.assertIsNone(got_logvar)

    def test_mutual_exclusion_adaptive_t_and_ctkd(self):
        with self.assertRaises(ValueError):
            DistillationLoss(adaptive_T_enable=True, ctkd_enable=True)

    def test_mutual_exclusion_gate_and_class_weights(self):
        weights = torch.ones(7)
        with self.assertRaises(ValueError):
            DistillationLoss(gate_enable=True, class_weights=weights)

    def test_gate_and_adaptive_t_warns_not_raises(self):
        try:
            DistillationLoss(gate_enable=True, adaptive_T_enable=True)
        except ValueError:
            self.fail("gate_enable + adaptive_T_enable must warn, not raise")

    def test_invalid_choice_kwargs_raise(self):
        with self.assertRaises(ValueError):
            DistillationLoss(gate_uncertainty_source="bogus")
        with self.assertRaises(ValueError):
            DistillationLoss(gate_norm="bogus")
        with self.assertRaises(ValueError):
            DistillationLoss(g2g_mode="bogus")


if __name__ == "__main__":
    unittest.main()
