"""FERPlus teacher-side grid on a SIGNED axis, for the two-dataset overlay and the T*_JSD arm.

WHY SIGNED AND NOT ECE. ECE is an absolute value, so it cannot distinguish over-confidence from
under-confidence. That is fatal for the cross-dataset figure, because the whole point of pairing
RAF-DB with FERPlus is that their teachers sit on OPPOSITE sides of calibration: Stage1 is
natively over-confident (needs softening, T*>1) and this FERPlus teacher is natively
under-confident (needs sharpening, T*<1). On an ECE axis both arms pile up on the same positive
half-line and the direction-independence of the law is invisible. On a signed axis
(mean confidence - accuracy) RAF-DB's native point sits at x>0 and FERPlus's at x<0, and the two
curves become two halves of one V centred on x=0.

Everything here is closed-form from the cached teacher logits
(diagnostics/ferplus_jsd/ferplus_val_logits.pt), so no forward pass is needed. The human-vote
JSD column is included because the T=0.74 arm is chosen by it, not by ECE.

Outputs -> diagnostics/ferplus_jsd/ferplus_teacher_signed_grid.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402
from ferplus_human_vote_jsd import EMOTIONS, entropy, jsd  # noqa: E402
from utils.configs import load_yaml  # noqa: E402

JSD_DIR = ROOT / "diagnostics" / "ferplus_jsd"
CACHE = JSD_DIR / "ferplus_val_logits.pt"
OUT = JSD_DIR / "ferplus_teacher_signed_grid.json"

# The four arms of the FERPlus dose-response, incl. the T*_JSD arm added after B-015 closed.
DEFAULT_TS = [0.26, 0.5063, 0.74, 1.0]
ROLES = {
    0.26:   "over-sharpened (sign flipped to OVER-confident)",
    0.5063: "T*_NLL / T*_ECE region -- calibrated against HARD labels",
    0.74:   "T*_JSD -- aligned with the 10-rater HUMAN distribution",
    1.0:    "native (under-confident, soft-vote-trained)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml")
    ap.add_argument("--extra-T", type=float, nargs="*", default=[])
    args = ap.parse_args()

    if not CACHE.exists():
        raise SystemExit(f"missing {CACHE} -- run diagnostics/ferplus_human_vote_jsd.py first")
    blob = torch.load(CACHE, map_location="cpu", weights_only=False)
    logits, labels, indices, paths = (blob["logits"], blob["labels"],
                                      blob["indices"], blob["paths"])
    acc = float((logits.argmax(1) == labels).float().mean() * 100)
    print(f"cached teacher logits: n={labels.shape[0]}, own accuracy {acc:.2f}%")

    # human vote distributions, normalised by each row's OWN sum (see B-008)
    cfg = argparse.Namespace()
    load_yaml(cfg, str(ROOT / args.config))
    df = pd.read_csv(ROOT / cfg.metadata)
    df = df[df["fold"].isin(cfg.val_folds)].reset_index(drop=True)
    by_path = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows_idx = [by_path[Path(p).name] for p in paths]
    votes = torch.tensor(df.loc[rows_idx, EMOTIONS].to_numpy(dtype=np.float64),
                         dtype=torch.float64)
    vsum = votes.sum(dim=1)
    keep = vsum > 0
    p_human = (votes[keep] / vsum[keep].unsqueeze(1)).float()
    z, y = logits[keep].float(), labels[keep]
    h_human = entropy(p_human)
    print(f"human vote rows used: {int(keep.sum())}, mean human entropy {float(h_human.mean()):.4f} nat")

    Ts = sorted(set(DEFAULT_TS + list(args.extra_T)))
    out = {"teacher_acc": acc, "n_val": int(keep.sum()),
           "human_mean_entropy": float(h_human.mean()), "grid": []}
    hdr = (f"{'T':<8}{'role':<52}{'ECE':<9}{'signed gap':<13}{'NLL':<9}"
           f"{'JSD':<9}{'mean conf':<11}{'entropy'}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for T in Ts:
        probs = F.softmax(z / T, dim=1)
        conf, preds = probs.max(dim=1)
        acc_t = float((preds == y).float().mean())
        rec = {
            "T": T,
            "role": ROLES.get(T, "extra grid point"),
            "teacher_ece": confidence_ece(z, y, T),
            # signed miscalibration: >0 over-confident, <0 under-confident. This is the figure's x.
            "signed_gap": float(conf.mean()) - acc_t,
            "mean_confidence": float(conf.mean()),
            "accuracy_frac": acc_t,
            "nll": float(F.cross_entropy(z / T, y.long())),
            "mean_jsd_vs_human": float(jsd(p_human, probs).mean()),
            "mean_entropy": float(entropy(probs).mean()),
            "log_T_over_Tstar_nll": math.log(T / 0.5063),
        }
        out["grid"].append(rec)
        print(f"{T:<8g}{rec['role']:<52}{rec['teacher_ece']:<9.4f}{rec['signed_gap']:<+13.4f}"
              f"{rec['nll']:<9.4f}{rec['mean_jsd_vs_human']:<9.4f}"
              f"{rec['mean_confidence']:<11.4f}{rec['mean_entropy']:.4f}")

    # The two objectives disagree -- state it with the numbers that will go in the paper.
    g = {r["T"]: r for r in out["grid"]}
    if 0.5063 in g and 0.74 in g:
        a, b = g[0.5063], g[0.74]
        print(f"\nThe two objectives pull apart:")
        print(f"  hard-label optimum T=0.5063 : ECE {a['teacher_ece']:.4f}  "
              f"JSD {a['mean_jsd_vs_human']:.4f}  entropy {a['mean_entropy']:.4f}")
        print(f"  human-vote optimum T=0.74   : ECE {b['teacher_ece']:.4f}  "
              f"JSD {b['mean_jsd_vs_human']:.4f}  entropy {b['mean_entropy']:.4f}")
        print(f"  moving to the human-aligned T costs "
              f"{b['teacher_ece'] - a['teacher_ece']:+.4f} ECE and buys "
              f"{b['mean_jsd_vs_human'] - a['mean_jsd_vs_human']:+.4f} JSD")
        print(f"  human mean entropy {float(h_human.mean()):.4f} vs teacher "
              f"{a['mean_entropy']:.4f} @T*_ECE and {b['mean_entropy']:.4f} @T*_JSD")

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
