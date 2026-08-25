"""Teacher-side ECE across the dose-response temperature grid (zero-GPU).

The P1 experiments scale the teacher's logits by `--teacher-temperature-scale T`
(train_rafdb_kd.py: original_teacher_logits / T, applied BEFORE the KD softmax at
tau_KD). So the object actually being distilled at grid point T is the distribution
softmax(z_teacher / T), and its calibration is exactly confidence_ece(z, y, T).

That makes the whole teacher-side x-axis ANALYTIC: forward each teacher over the
fold-3 val set ONCE, cache the logits, then every T point is a closed-form re-read
of the same tensor. No GPU, no re-forward per grid point.

Why this matters for the paper: "T" is an arbitrary knob with no cross-teacher
meaning (T=1.34 is the optimum for Stage1 and a mis-setting for VAE9182). Teacher
ECE is the physically meaningful axis, and it is the axis on which the two teachers'
dose-response curves become comparable/overlayable.

NB: teacher ECE here is measured at the scaling temperature T, NOT at T * tau_KD.
tau_KD=6 is a fixed property of the KD loss shared by every run in both curves, so
it cancels in any between-run comparison; T is the only manipulated variable.

Outputs -> diagnostics/teacher_ece_grid/
    teacher_val_logits_<teacher>.pt   cached logits+labels (reusable)
    teacher_ece_grid.json             ECE/NLL/acc at every grid + fine-sweep T
"""
import json
import sys
from pathlib import Path

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "diagnostics"))

from kd_common import extract_logits  # noqa: E402
from teacher_temperature_scaling_fit import (  # noqa: E402
    TEACHERS, build_one_teacher, build_val_images, confidence_ece, fit_temperature, nll,
)

OUT_DIR = PROJECT_ROOT / "diagnostics" / "teacher_ece_grid"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# The exact temperature-scale values used by the two dose-response launchers
# (rafdb_p1_temperature_doseresponse_queue.ps1 and rafdb_p1_vae9182_flatcontrol_queue.ps1).
EXPERIMENT_TS = [0.85, 1.00, 1.3406, 1.70, 2.20]
FINE_TS = [round(0.60 + 0.05 * i, 2) for i in range(int((3.00 - 0.60) / 0.05) + 1)]


def cached_logits(name, images, labels):
    """Forward a teacher once over the val set; reuse the cache on later calls."""
    cache = OUT_DIR / f"teacher_val_logits_{name}.pt"
    if cache.exists():
        blob = torch.load(cache, map_location="cpu", weights_only=False)
        if blob["labels"].shape == labels.shape and torch.equal(blob["labels"], labels):
            print(f"[{name}] reusing cached logits {cache.name}")
            return blob["logits"]
        print(f"[{name}] cache label mismatch -> recomputing")
    teacher = build_one_teacher(TEACHERS[name])
    teacher.eval()
    chunks = []
    with torch.no_grad():
        for i in range(0, images.shape[0], 128):
            chunks.append(extract_logits(teacher(images[i:i + 128])).float())
            print(f"[{name}] {min(i + 128, images.shape[0])}/{images.shape[0]}", flush=True)
    logits = torch.cat(chunks, dim=0)
    torch.save({"logits": logits, "labels": labels}, cache)
    print(f"[{name}] wrote {cache}")
    return logits


def main():
    images, labels = build_val_images()
    print(f"fold-3 val n={images.shape[0]}\n")

    out = {}
    for name in ("stage1", "vae9182", "primary"):
        logits = cached_logits(name, images, labels)
        acc = float((logits.argmax(1) == labels).float().mean() * 100.0)
        t_star = fit_temperature(logits, labels)
        ece_t1 = confidence_ece(logits, labels, 1.0)
        ece_tstar = confidence_ece(logits, labels, t_star)

        grid = {f"{T:g}": {"teacher_ece": confidence_ece(logits, labels, T),
                           "teacher_nll": nll(logits, labels, T)}
                for T in EXPERIMENT_TS}
        fine = {f"{T:g}": confidence_ece(logits, labels, T) for T in FINE_TS}

        # Anchor check: ECE(T=1) must reproduce the head-compat audit value.
        anchor = TEACHERS[name]["audit_ece_t1"]
        ok = abs(ece_t1 - anchor) <= 0.003

        out[name] = {
            "own_acc_pct": acc, "T_star": t_star,
            "ece_T1": ece_t1, "ece_Tstar": ece_tstar,
            # Teacher-side headroom: how much miscalibration post-hoc scaling can remove.
            "teacher_headroom_dECE": ece_t1 - ece_tstar,
            "audit_anchor": anchor, "anchor_ok": ok,
            "experiment_grid": grid, "fine_sweep": fine,
        }
        flag = "OK" if ok else "** ANCHOR MISMATCH **"
        print(f"\n[{name}] acc={acc:.2f}%  T*={t_star:.4f}  "
              f"ECE(T=1)={ece_t1:.4f} (audit {anchor:.4f} {flag})  ECE(T*)={ece_tstar:.4f}  "
              f"teacher headroom dECE={ece_t1 - ece_tstar:+.4f}")
        print("    grid: " + "  ".join(
            f"T={T:g}->{grid[f'{T:g}']['teacher_ece']:.4f}" for T in EXPERIMENT_TS))

    (OUT_DIR / "teacher_ece_grid.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'teacher_ece_grid.json'}")


if __name__ == "__main__":
    main()
