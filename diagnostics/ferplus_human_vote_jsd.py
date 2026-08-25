"""FERPlus human-vote alignment: does teacher calibration align it with human raters?

WHY THIS EXISTS (the FER-specific leg of the calibration thesis).
The temperature-scaling result says a teacher's softmax can be made better calibrated
against its own hard labels. That is a statistical statement, true of any classifier.
FER has something almost no other vision task has: FERPlus ships the raw 10-rater vote
distribution per image, i.e. a measured ground-truth *distribution*, not just an argmax.

So we can ask a question that is not available on ImageNet-style benchmarks:
    Is the temperature that best CALIBRATES the teacher also the temperature that best
    matches the HUMAN DISAGREEMENT distribution?
If T*_NLL (fit against hard labels) coincides with T*_JSD (fit against rater votes),
then "calibrating the teacher" is not a statistical nicety -- it is literally aligning
the teacher with the human label-generating process, and soft-label KD in FER inherits
a concrete meaning: the student is being taught human ambiguity, correctly scaled.

This analysis is inference-only, needs no GPU, and stands regardless of how any KD
run turns out -- it is a property of the teacher and the dataset.

VOTE NORMALIZATION (a real correctness point, not a detail):
The training config sets votes_sum: 10 and divides every row by a FIXED 10. But in
configs/FERPlus_majority_metadata.csv the 8 emotion votes do NOT always sum to 10
(the FERPlus 'unknown'/'NF' votes were dropped upstream): sums of 10/9/8/7/6 all occur.
Dividing those rows by 10 yields a sub-normalized vector that is not a distribution and
would silently corrupt any divergence. Here every row is normalized by its OWN vote sum,
and the discrepancy is counted and reported.

Outputs -> diagnostics/ferplus_jsd/
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dataset_utils.builder import build_dataloader  # noqa: E402
from kd_common import extract_logits, load_checkpoint_checked  # noqa: E402
from trials.models import create_model  # noqa: E402
from utils.configs import load_yaml  # noqa: E402

EMOTIONS = ["neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear", "contempt"]
OUT_DIR = PROJECT_ROOT / "diagnostics" / "ferplus_jsd"
OUT_DIR.mkdir(parents=True, exist_ok=True)
EPS = 1e-12


def jsd(p, q):
    """Jensen-Shannon divergence in NATS, per sample. Symmetric, bounded [0, ln2]."""
    m = 0.5 * (p + q)
    def kl(a, b):
        return (a * (torch.log(a + EPS) - torch.log(b + EPS))).sum(dim=1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def entropy(p):
    return -(p * torch.log(p + EPS)).sum(dim=1)


def spearman(x, y):
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml")
    ap.add_argument("--checkpoint", default="checkpoints/teacher_ferplus_vich_best.pt")
    ap.add_argument("--expected-acc", type=float, default=91.34,
                    help="known own-accuracy of this teacher; guards against a config/ckpt mispairing")
    ap.add_argument("--acc-tol", type=float, default=0.5)
    # `parse_known_args` -- deponun standart kuralı (bkz. bootstrap_cis.py): Level-1 kapısı
    # üreticileri `runpy` ile çağırıyor ve betiğin YOLU argv'de kalıyor; `parse_args` orada
    # SystemExit atıp kapıyı "başka hata"ya düşürüyor, yani kapı Level-1 sorusunu HİÇ soramıyor.
    # 17 Ağu 2026'da bu betik ihraç bandına girdiği gün tam bunu yaşadı: artefakt kayda geçince
    # üreticisi ilk kez kapıya girdi ve argümansız çağrılamadığı ortaya çıktı.
    args, _unknown = ap.parse_known_args()

    cfg = argparse.Namespace()
    load_yaml(cfg, str(PROJECT_ROOT / args.config))
    cfg.device = torch.device("cpu")   # inference-only; the GPU is reserved for KD runs
    cfg.num_workers = 0
    cfg.batch_size = 32
    cfg.cache_img = False
    cfg.train_root = None              # val split only

    # The forward pass is the only expensive part (~15 min on CPU) and every temperature
    # is a closed-form re-read of the same logits, so cache them: re-sweeping a wider or
    # finer T grid must never cost another forward.
    cache = OUT_DIR / "ferplus_val_logits.pt"
    dataset = None
    if cache.exists():
        blob = torch.load(cache, map_location="cpu", weights_only=False)
        logits, labels, indices, paths_in_loader = (
            blob["logits"], blob["labels"], blob["indices"], blob["paths"])
        print(f"Reusing cached teacher logits ({cache.name}), n={labels.shape[0]}")
    else:
        model = create_model(cfg).to(cfg.device)
        load_checkpoint_checked(model, str(PROJECT_ROOT / args.checkpoint), device=cfg.device, strict=True)
        model.eval()

        _train, val_loader = build_dataloader(cfg)
        dataset = val_loader.dataset
        print(f"FERPlus val (folds {cfg.val_folds}): n={len(dataset)}")

        logits_all, labels_all, idx_all = [], [], []
        with torch.no_grad():
            for batch in val_loader:
                index, img, label, _label_em, _path = batch
                logits_all.append(extract_logits(model(img)).float())
                labels_all.append(label)
                idx_all.append(index)
                print(f"  {sum(x.shape[0] for x in labels_all)}/{len(dataset)}", flush=True)
        logits = torch.cat(logits_all)
        labels = torch.cat(labels_all)
        indices = torch.cat(idx_all).numpy()
        paths_in_loader = [Path(dataset.data_infos[i]["path"]).name for i in indices]
        torch.save({"logits": logits, "labels": labels, "indices": indices,
                    "paths": paths_in_loader}, cache)
        print(f"Cached teacher logits -> {cache}")

    acc = float((logits.argmax(1) == labels).float().mean() * 100)
    print(f"\nTeacher own-accuracy: {acc:.2f}%  (expected ~{args.expected_acc})")
    if abs(acc - args.expected_acc) > args.acc_tol:
        raise SystemExit(f"ABORT: accuracy {acc:.2f}% is off the known {args.expected_acc}% by more "
                         f"than {args.acc_tol} -- config/checkpoint pairing is probably wrong.")

    # --- human vote distributions, normalized by each row's OWN sum ---
    df = pd.read_csv(PROJECT_ROOT / cfg.metadata)
    df = df[df["fold"].isin(cfg.val_folds)].reset_index(drop=True)
    df_by_path = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows = [df_by_path[Path(p).name] for p in paths_in_loader]
    votes = torch.tensor(df.loc[rows, EMOTIONS].to_numpy(dtype=np.float64), dtype=torch.float64)

    vote_sums = votes.sum(dim=1)
    n_not10 = int((vote_sums != 10).sum())
    print(f"Vote rows whose 8 emotion votes do NOT sum to 10: {n_not10}/{len(vote_sums)} "
          f"({100 * n_not10 / len(vote_sums):.1f}%) -- normalizing by each row's own sum.")
    keep = vote_sums > 0
    p_human = (votes[keep] / vote_sums[keep].unsqueeze(1)).float()
    z = logits[keep].double().float()
    y = labels[keep]

    # --- temperature sweep: calibration (NLL/ECE vs hard labels) vs human alignment (JSD vs votes) ---
    sys.path.insert(0, str(PROJECT_ROOT / "diagnostics"))
    from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402

    # Range must be wide enough that no optimum lands on a boundary. The first pass used
    # [0.50, 4.00] and BOTH T*_NLL and T*_ECE clamped at 0.50 -- a boundary artifact, not
    # an optimum. This teacher is trained on soft vote targets and is therefore
    # UNDER-confident (it needs sharpening, T<1), so the grid must reach well below 0.5.
    Ts = [round(0.10 + 0.02 * i, 2) for i in range(int((4.00 - 0.10) / 0.02) + 1)]
    sweep = []
    for T in Ts:
        q = F.softmax(z / T, dim=1)
        sweep.append({
            "T": T,
            "mean_jsd": float(jsd(p_human, q).mean()),
            "nll": float(F.cross_entropy(z / T, y)),
            "ece": confidence_ece(z, y, T),
        })
    t_jsd = min(sweep, key=lambda r: r["mean_jsd"])
    t_nll = min(sweep, key=lambda r: r["nll"])
    t_ece = min(sweep, key=lambda r: r["ece"])
    at1 = next(r for r in sweep if r["T"] == 1.0)

    lo, hi = Ts[0], Ts[-1]
    boundary = {k: v["T"] for k, v in (("JSD", t_jsd), ("NLL", t_nll), ("ECE", t_ece))
                if v["T"] in (lo, hi)}
    if boundary:
        print(f"\n** WARNING: optimum on a grid boundary [{lo}, {hi}] for {boundary} -- "
              f"these are NOT resolved optima; widen the grid before reporting them. **")

    print("\n--- temperature optima on the SAME teacher, SAME split ---")
    print(f"  T*_JSD (best match to 10-rater votes) = {t_jsd['T']:.2f}   mean JSD {t_jsd['mean_jsd']:.4f}")
    print(f"  T*_NLL (best calibrated vs hard label)= {t_nll['T']:.2f}   NLL {t_nll['nll']:.4f}")
    print(f"  T*_ECE (min 15-bin ECE)               = {t_ece['T']:.2f}   ECE {t_ece['ece']:.4f}")
    print(f"  at T=1.0: JSD {at1['mean_jsd']:.4f}  NLL {at1['nll']:.4f}  ECE {at1['ece']:.4f}")
    print(f"  JSD improvement from scaling: {at1['mean_jsd'] - t_jsd['mean_jsd']:+.4f} "
          f"({100 * (at1['mean_jsd'] - t_jsd['mean_jsd']) / at1['mean_jsd']:+.1f}%)")
    # Report the gap; do NOT assert a conclusion. On this teacher the three criteria do
    # NOT coincide (T*_ECE 0.46 < T*_NLL 0.50 < T*_JSD 0.74 < 1.0): calibrating against
    # ARGMAX labels overshoots, sharpening well past what the rater votes actually support.
    # That is the finding -- hard-label calibration and human-distribution alignment are
    # related but distinct objectives, and only FER datasets with raw votes can show it.
    print(f"\n  >>> T*_ECE {t_ece['T']:.2f} | T*_NLL {t_nll['T']:.2f} | T*_JSD {t_jsd['T']:.2f} | T=1 reference")
    print(f"  >>> |T*_JSD - T*_NLL| = {abs(t_jsd['T'] - t_nll['T']):.2f}, "
          f"|T*_JSD - T*_ECE| = {abs(t_jsd['T'] - t_ece['T']):.2f}")
    print(f"  >>> All optima are BELOW 1.0: this soft-target teacher is over-smooth "
          f"(under-confident) w.r.t. both hard labels and human raters.")

    # --- per-sample: does the teacher know where humans disagree? ---
    q1 = F.softmax(z, dim=1)
    qbest = F.softmax(z / t_jsd["T"], dim=1)
    h_human = entropy(p_human).numpy()
    corr = {}
    for tag, q in (("T1", q1), ("T_jsd", qbest)):
        h_t = entropy(q).numpy()
        corr[tag] = {"pearson": float(np.corrcoef(h_human, h_t)[0, 1]),
                     "spearman": spearman(h_human, h_t),
                     "teacher_mean_entropy": float(h_t.mean())}
        print(f"  human-entropy vs teacher-entropy @{tag}: "
              f"pearson {corr[tag]['pearson']:.3f}  spearman {corr[tag]['spearman']:.3f}  "
              f"(teacher mean H {h_t.mean():.3f} vs human mean H {h_human.mean():.3f})")

    payload = {
        "teacher_acc": acc, "n_val": int(keep.sum()),
        "vote_rows_not_summing_to_10": n_not10,
        "T_star_jsd": t_jsd, "T_star_nll": t_nll, "T_star_ece": t_ece, "at_T1": at1,
        "abs_T_jsd_minus_T_nll": abs(t_jsd["T"] - t_nll["T"]),
        "entropy_correlation": corr,
        "human_mean_entropy": float(h_human.mean()),
        "sweep": sweep,
    }
    (OUT_DIR / "ferplus_jsd.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    np.save(OUT_DIR / "per_sample_human_entropy.npy", h_human)
    print(f"\nWrote {OUT_DIR / 'ferplus_jsd.json'}")


if __name__ == "__main__":
    main()
