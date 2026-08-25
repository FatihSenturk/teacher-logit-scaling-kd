"""Phase C3: measure the bridge teacher's calibration and apply the
pre-registered head-vs-recipe decision rule.

The bridge teacher (Phase C2) is a VAE head trained with Primary's EXACT recipe
(configs/RAFDB_posterv2_vae_recipe_seed1.yaml), so the ONLY difference from the
Primary VICH teacher is head architecture. This script forwards it over the
fold-3 val set once (CPU), computes own top-1 accuracy, 15-bin confidence ECE at
T=1, and the NLL-optimal T*, then decides:

  ECE(T=1) ~ 0.015 band  AND  T* ~ 1.0   -> HEAD attribution
      (the VAE head is intrinsically well-calibrated / not over-confident,
       regardless of the VICH recipe -> VAE9182's ECE edge is the head)
  ECE(T=1) ~ 0.038 band  AND  T* ~ 1.3   -> RECIPE/AUGMENTATION attribution
      (the head flip did NOT fix calibration under the VICH recipe -> the edge
       was the QCS-rafdb augmentation stack / seed, not the head)
  anything clearly between the bands -> AMBIGUOUS (itself a reportable result)

Reference points (real, from this study):
  VAE9182 teacher (VAE head, QCS recipe):  ECE 0.0136,  T* 0.983
  Primary teacher (VICH head, VICH recipe): ECE 0.0396,  T* 1.261
  Stage1  teacher (VICH head, VICH recipe): ECE 0.0378,  T* 1.349

Read-only. Usage:
  python diagnostics/bridge_teacher_check.py --ckpt results/teacher_logs/RAFDB/POSTERv2/<TS>/best.pt
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "diagnostics"))

from kd_common import extract_logits  # noqa: E402
from train_rafdb_kd import build_teacher  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece, fit_temperature, build_val_images  # noqa: E402

OUT_DIR = PROJECT_ROOT / "diagnostics" / "bridge_teacher"
OUT_DIR.mkdir(parents=True, exist_ok=True)
DEVICE = torch.device("cpu")

# Pre-registered bands (midpoints of the two hypotheses, half-width 0.010).
HEAD_CENTER, RECIPE_CENTER, BAND = 0.015, 0.038, 0.010


def build_bridge_teacher(ckpt):
    # VAE head, matching configs/RAFDB_posterv2_vae_recipe_seed1.yaml.
    args = SimpleNamespace(
        teacher_vae_head=True, teacher_layer_embedding=True, teacher_votes_sum=0,
        teacher_vich_head=False, teacher_vich_use_sampling=True,
        teacher_vich_logvar_min=-10.0, teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=0.0,
    )
    return build_teacher(Path(ckpt), DEVICE, args)


def classify(ece_t1, t_star):
    near_head = abs(ece_t1 - HEAD_CENTER) <= BAND
    near_recipe = abs(ece_t1 - RECIPE_CENTER) <= BAND
    if near_head and not near_recipe:
        return "HEAD (VAE head is intrinsically well-calibrated under the VICH recipe)"
    if near_recipe and not near_head:
        return "RECIPE/AUGMENTATION (head flip did not fix calibration; QCS recipe/seed drove VAE9182's edge)"
    return ("AMBIGUOUS (ECE landed outside both pre-registered bands -- report as-is; "
            f"head band {HEAD_CENTER}+/-{BAND}, recipe band {RECIPE_CENTER}+/-{BAND})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True, help="path to the bridge teacher checkpoint (best.pt)")
    args = ap.parse_args()

    ckpt = Path(args.ckpt)
    if not ckpt.exists():
        raise FileNotFoundError(f"Bridge checkpoint not found: {ckpt}")

    all_images, all_labels = build_val_images()
    print(f"Val set: {all_images.shape[0]} images")

    teacher = build_bridge_teacher(ckpt)
    teacher.eval()
    with torch.no_grad():
        chunks = []
        for i in range(0, all_images.shape[0], 128):
            out = teacher(all_images[i:i + 128])
            chunks.append(extract_logits(out).float())
    logits = torch.cat(chunks, dim=0)

    preds = logits.argmax(dim=1)
    own_acc = float((preds == all_labels).float().mean() * 100.0)
    ece_t1 = confidence_ece(logits, all_labels, T=1.0)
    t_star = fit_temperature(logits, all_labels)
    ece_ts = confidence_ece(logits, all_labels, T=t_star)
    verdict = classify(ece_t1, t_star)

    result = {
        "ckpt": str(ckpt),
        "own_acc_pct": own_acc,
        "ece_T1": ece_t1,
        "T_star": t_star,
        "ece_Tstar": ece_ts,
        "reference": {
            "VAE9182_head": {"ece_T1": 0.0136, "T_star": 0.983},
            "Primary_recipe": {"ece_T1": 0.0396, "T_star": 1.261},
            "Stage1_recipe": {"ece_T1": 0.0378, "T_star": 1.349},
        },
        "decision_bands": {"head_center": HEAD_CENTER, "recipe_center": RECIPE_CENTER, "half_width": BAND},
        "verdict": verdict,
    }
    print(json.dumps(result, indent=2))
    print(f"\n>>> own_acc={own_acc:.2f}%  ECE(T=1)={ece_t1:.4f}  T*={t_star:.4f}  ECE(T*)={ece_ts:.4f}")
    print(f">>> PRE-REGISTERED VERDICT: {verdict}")

    out_path = OUT_DIR / "bridge_teacher_check.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
