"""Phase B3 post-hoc eval: score a trained student on the T*-UNSEEN half (half-B)
of fold-3 val, so the causal comparison (B3 temp-scaled vs Stage1 baseline) never
overlaps the data T* was fit on.

Reconstructs the student exactly from the run's own run_args.json, loads
best_checkpoint.pth (strict), forwards the full fold-3 val once (deterministic:
eval mode, VICH sampling off), and reports accuracy + 15-bin confidence ECE on
BOTH the full val (sanity vs metrics_best.json) and half-B (the reported number).

half-B indices come from diagnostics/teacher_temperature_scaling/b3_tstar_halfsplit.json
(same stratified split, seed 1234, that T* was fit off).

Usage:
  python diagnostics/student_halfb_eval.py --run-dir results/unified_students/<RUN>/<TS>
  # compare two runs on the same half-B:
  python diagnostics/student_halfb_eval.py --run-dir <B3_run> --baseline-run-dir <baseline_run>
Read-only. CPU.
"""
import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "diagnostics"))

from kd_common import extract_logits, clean_state_dict  # noqa: E402
from train_rafdb_kd import build_student  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece, build_val_images  # noqa: E402

DEVICE = torch.device("cpu")
SPLIT_JSON = PROJECT_ROOT / "diagnostics" / "teacher_temperature_scaling" / "b3_tstar_halfsplit.json"


def load_half_b():
    d = json.loads(SPLIT_JSON.read_text())
    return torch.tensor(d["half_b_indices"], dtype=torch.long), d["split_seed"]


def student_from_run(run_dir):
    run_dir = Path(run_dir)
    args = SimpleNamespace(**json.loads((run_dir / "run_args.json").read_text()))
    # deterministic eval build: don't reload ImageNet, no sampling
    args.student_pretrained = False
    args.use_vich_sampling = False
    student = build_student(args, DEVICE)
    ckpt = torch.load(run_dir / "best_checkpoint.pth", map_location=DEVICE, weights_only=False)
    student.load_state_dict(clean_state_dict(ckpt["model_state_dict"]), strict=True)
    student.eval()
    return student


def eval_logits(student, images):
    with torch.no_grad():
        chunks = []
        for i in range(0, images.shape[0], 128):
            chunks.append(extract_logits(student(images[i:i + 128])).float())
    return torch.cat(chunks, dim=0)


def report(name, logits, labels, half_b):
    def acc(lg, lb):
        return float((lg.argmax(1) == lb).float().mean() * 100.0)
    full = {"acc": acc(logits, labels), "ece": confidence_ece(logits, labels, 1.0)}
    lb_logits, lb_labels = logits[half_b], labels[half_b]
    hb = {"acc": acc(lb_logits, lb_labels), "ece": confidence_ece(lb_logits, lb_labels, 1.0)}
    print(f"[{name}]")
    print(f"    full val (n={len(labels)}): acc={full['acc']:.2f}%  ECE={full['ece']:.4f}   (sanity vs metrics_best.json)")
    print(f"    half-B   (n={len(lb_labels)}): acc={hb['acc']:.2f}%  ECE={hb['ece']:.4f}   <-- reported (T*-unseen)")
    return {"full": full, "half_b": hb}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, help="student run dir (B3 temp-scaled)")
    ap.add_argument("--baseline-run-dir", default=None, help="optional matched baseline run dir")
    ap.add_argument("--label", default="B3_tempscaled")
    args = ap.parse_args()

    half_b, seed = load_half_b()
    all_images, all_labels = build_val_images()
    print(f"fold-3 val n={all_images.shape[0]}  half-B n={len(half_b)}  (split seed {seed})\n")

    out = {"split_seed": seed}
    logits = eval_logits(student_from_run(args.run_dir), all_images)
    out[args.label] = report(args.label, logits, all_labels, half_b)

    if args.baseline_run_dir:
        print()
        base_logits = eval_logits(student_from_run(args.baseline_run_dir), all_images)
        out["baseline"] = report("baseline", base_logits, all_labels, half_b)
        d_acc = out[args.label]["half_b"]["acc"] - out["baseline"]["half_b"]["acc"]
        d_ece = out[args.label]["half_b"]["ece"] - out["baseline"]["half_b"]["ece"]
        print(f"\n>>> CAUSAL DELTA on half-B (temp-scaled - baseline):  d_acc={d_acc:+.2f}pp  d_ECE={d_ece:+.4f}")
        print(">>> Reference: VAE9182 student baseline 90.06% / ECE 0.0285 (the target if calibration is causal).")
        out["causal_delta_half_b"] = {"d_acc_pp": d_acc, "d_ece": d_ece}

    out_path = PROJECT_ROOT / "diagnostics" / "teacher_temperature_scaling" / "b3_halfb_eval.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
