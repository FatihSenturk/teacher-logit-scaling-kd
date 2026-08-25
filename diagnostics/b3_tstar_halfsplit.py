"""Phase B3 prep: fit Stage1's teacher temperature T* on a HELD-OUT half of the
fold-3 val set, so the causal KD run (B3) never tunes T* on the data the student
is scored on. Resolves the pre-registered "never val" leakage concern for P1.

Protocol:
  * fold-3 val (n=3068) -> stratified 50/50 split, FIXED seed (reproducible).
  * fit T* on half-A only (NLL-optimal, Stage1 teacher).
  * report ECE on half-A AND half-B at T=1 and T* (T* should generalize to
    half-B; if it doesn't, the "overconfidence" is not a stable scalar).
  * save the split (seed + half-B indices) to JSON so the post-hoc student
    evaluation reports B3's accuracy/ECE on the SAME half-B (leak-free).

The full-val T* (diagnostics/teacher_temperature_scaling_fit.py -> 1.349) stays
the diagnostic number for CL-3's "teacher is overconfident" finding; THIS half-A
T* is the one the B3 causal run must use.

Read-only on training code. CPU.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "diagnostics"))

from kd_common import extract_logits  # noqa: E402
from train_rafdb_kd import build_teacher  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece, fit_temperature, build_val_images  # noqa: E402

OUT_DIR = PROJECT_ROOT / "diagnostics" / "teacher_temperature_scaling"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = torch.device("cpu")

STAGE1_CKPT = PROJECT_ROOT / "results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/best.pt"
SPLIT_SEED = 1234  # fixed so the post-hoc student eval reproduces the same half-B


def build_stage1_teacher():
    args = SimpleNamespace(
        teacher_vae_head=False, teacher_layer_embedding=True, teacher_votes_sum=0,
        teacher_vich_head=True, teacher_vich_use_sampling=True,
        teacher_vich_logvar_min=-10.0, teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=0.0,
    )
    return build_teacher(STAGE1_CKPT, DEVICE, args)


def main():
    all_images, all_labels = build_val_images()
    n = all_images.shape[0]
    idx = np.arange(n)
    half_a, half_b = train_test_split(
        idx, test_size=0.5, random_state=SPLIT_SEED, stratify=all_labels.numpy()
    )
    half_a.sort()
    half_b.sort()
    print(f"fold-3 val n={n}  ->  half-A {len(half_a)}  half-B {len(half_b)}  (stratified, seed {SPLIT_SEED})")

    teacher = build_stage1_teacher()
    teacher.eval()
    with torch.no_grad():
        chunks = []
        for i in range(0, n, 128):
            chunks.append(extract_logits(teacher(all_images[i:i + 128])).float())
    logits = torch.cat(chunks, dim=0)

    la = torch.from_numpy(half_a)
    lb = torch.from_numpy(half_b)
    logits_a, labels_a = logits[la], all_labels[la]
    logits_b, labels_b = logits[lb], all_labels[lb]

    t_star = fit_temperature(logits_a, labels_a)

    def acc(lg, lb_):
        return float((lg.argmax(1) == lb_).float().mean() * 100.0)

    result = {
        "split_seed": SPLIT_SEED,
        "n_total": int(n), "n_half_a": int(len(half_a)), "n_half_b": int(len(half_b)),
        "half_b_indices": half_b.tolist(),
        "T_star_fit_on_half_a": t_star,
        "half_a": {
            "acc": acc(logits_a, labels_a),
            "ece_T1": confidence_ece(logits_a, labels_a, 1.0),
            "ece_Tstar": confidence_ece(logits_a, labels_a, t_star),
        },
        "half_b": {  # T* never saw this -- the honest generalization check
            "acc": acc(logits_b, labels_b),
            "ece_T1": confidence_ece(logits_b, labels_b, 1.0),
            "ece_Tstar": confidence_ece(logits_b, labels_b, t_star),
        },
        "full_val_T_star_reference": 1.3494,
    }
    print(json.dumps({k: v for k, v in result.items() if k != "half_b_indices"}, indent=2))
    print(f"\n>>> USE THIS FOR B3:  --teacher-temperature-scale {t_star:.4f}")
    print(f">>> ECE half-B: T=1 {result['half_b']['ece_T1']:.4f} -> T* {result['half_b']['ece_Tstar']:.4f} "
          f"(T* fit on half-A generalizes: {'YES' if result['half_b']['ece_Tstar'] < result['half_b']['ece_T1'] else 'NO'})")

    out = OUT_DIR / "b3_tstar_halfsplit.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
