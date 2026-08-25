"""Items 1+2: selection-independent metrics for every run, at THREE checkpoints.

THE PROBLEM THIS EXISTS TO EXPOSE (verified in code, not assumed):
  train_rafdb_kd.py:895-900  -> the "best" checkpoint is selected by `if val_acc > best_acc`,
                                i.e. by top-1 ACCURACY on the val_loader.
  train_rafdb_kd.py:960-977  -> metrics_best.json is then produced by re-loading that same
                                checkpoint and evaluating on the SAME val_loader.
  train_rafdb_kd.py:1049-1050 + :67-73 -> that val_loader is fold 3 of the metadata CSV, which
                                is RAF-DB's official TEST split (3068 images). There is no
                                third partition.
  => SELECTION AND REPORTING USE THE SAME IMAGES. Every "best" number, including every ECE this
     campaign has reported, is therefore optimistically biased by epoch selection, and the bias
     is on ACCURACY (the selection criterion) while ECE rides along uncontrolled.

WHY THIS MATTERS SPECIFICALLY FOR A CALIBRATION PAPER: "the ECE at the accuracy-selected epoch"
is not a clean calibration measurement. Accuracy-based early stopping can pick an epoch whose
calibration is atypical. A calibration claim needs numbers from a rule that never looked at the
eval set.

TWO SELECTION-INDEPENDENT CHECKPOINTS ALREADY EXIST in every run directory:
  last_checkpoint.pth  -- epoch `args.epochs`, a fixed rule, no peeking (train_rafdb_kd.py:877-878)
  swa_student.pth      -- SWA average over epochs [swa_start, epochs], fixed rule (:902-908)
So the audit needs no retraining; it only needs to be measured.

METRIC DEFINITIONS (stated explicitly for Methods):
  ECE   : 15 bins, EQUAL-WIDTH on [0,1] (not equal-mass), binned on TOP-1 softmax confidence
          max_k p_k; bin term |acc(bin) - mean_conf(bin)| weighted by |bin|/N; first bin closed
          on the left. This is Guo et al. (2017) ECE. Implementation:
          diagnostics/teacher_temperature_scaling_fit.py::confidence_ece
  NLL   : mean negative log-likelihood, F.cross_entropy(logits, labels) at T=1.
  Brier : multi-class Brier score, mean_i sum_k (p_ik - y_ik)^2, y one-hot (range [0,2]).
  macroF1: unweighted mean per-class F1 over the 7 classes.
All on the same fold-3 images (n=3068), eval mode, VICH sampling off.

Usage:  python diagnostics/selection_audit_table.py [--device cuda] [--limit N]
Caches per (run, checkpoint) into <run_dir>/selection_audit.json so re-runs are free.
Outputs -> diagnostics/selection_audit/selection_audit.csv
"""
import argparse
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from kd_common import clean_state_dict, extract_logits  # noqa: E402
from train_rafdb_kd import build_student  # noqa: E402
from teacher_temperature_scaling_fit import build_val_images, confidence_ece  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "selection_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
STUDENTS = ROOT / "results" / "unified_students"

# checkpoint tag -> (filename, is_selection_independent, how the epoch is chosen)
VARIANTS = {
    "best": ("best_checkpoint.pth", False, "argmax val_acc over epochs (PEEKS at eval set)"),
    "last": ("last_checkpoint.pth", True, "final epoch, fixed rule"),
    "swa":  ("swa_student.pth", True, "SWA average over [swa_start, epochs], fixed rule"),
}


def load_student(run_dir, ckpt_name, device):
    args = SimpleNamespace(**json.loads((run_dir / "run_args.json").read_text()))
    args.student_pretrained = False
    args.use_vich_sampling = False
    student = build_student(args, device)
    ckpt = torch.load(run_dir / ckpt_name, map_location=device, weights_only=False)
    sd = ckpt["model_state_dict"]
    # swa_student.pth comes from torch.optim.swa_utils.AveragedModel: keys are prefixed
    # "module." and it carries an extra "n_averaged" buffer that the bare student lacks.
    sd = {k: v for k, v in sd.items() if k != "n_averaged"}
    if sd and all(k.startswith("module.") for k in sd):
        sd = {k[len("module."):]: v for k, v in sd.items()}
    student.load_state_dict(clean_state_dict(sd), strict=True)
    student.eval()
    return student, ckpt.get("epoch")


@torch.no_grad()
def measure(student, images, labels, device, batch=256):
    chunks = []
    for i in range(0, images.shape[0], batch):
        chunks.append(extract_logits(student(images[i:i + batch].to(device))).float().cpu())
    logits = torch.cat(chunks)
    probs = F.softmax(logits, dim=1)
    preds = logits.argmax(1)
    n, k = labels.shape[0], probs.shape[1]
    onehot = F.one_hot(labels.long(), num_classes=k).float()

    f1s = []
    for c in range(k):
        tp = float(((preds == c) & (labels == c)).sum())
        fp = float(((preds == c) & (labels != c)).sum())
        fn = float(((preds != c) & (labels == c)).sum())
        f1s.append(0.0 if (2 * tp + fp + fn) == 0 else 2 * tp / (2 * tp + fp + fn))

    return {
        "acc": float((preds == labels).float().mean() * 100.0),
        "ece": confidence_ece(logits, labels, 1.0),
        "nll": float(F.cross_entropy(logits, labels.long())),
        "brier": float(((probs - onehot) ** 2).sum(dim=1).mean()),
        "macro_f1": 100.0 * sum(f1s) / k,
        "n_val": n,
    }


# ---------------------------------------------------------------------------------------------
# INCLUSION SET FROZEN 2026-07-31. The audit is a property of the SELECTION PROCEDURE, not of any
# experiment, so it grew with every campaign phase: 116 -> 125 -> 131 runs. Each growth spurt
# forced an edit to the abstract, for no scientific gain -- the estimate moved 0.781 -> 0.769 ->
# 0.766 pp, i.e. it sat inside 0.015 pp the whole time. The set is therefore frozen, and its
# stability across the three inclusion sets is reported instead (see
# diagnostics/selection_audit/README.md), which is a stronger statement than any single N.
#
# WHY THE BOUNDARY IS 31 JUL 06:00 AND NOT MIDNIGHT ON THE 30th. The freeze was specified as
# "N = 131, cutoff 30 July". Those two are not consistent: P4's sequential queue crossed midnight,
# so its sixth control is stamped 2026-07-31-02-06-02, and a literal 30-July cutoff yields 130 --
# dropping one of the six controls the freeze exists to include. 06:00 on the 31st is after P4's
# last launch (02:06) and before P5's first (12:2x), so it separates the two campaigns exactly and
# reproduces the intended N = 131.
AUDIT_CUTOFF = "2026-07-31-06-00-00"
AUDIT_FROZEN_N = 131


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="ignore per-run cache")
    ap.add_argument("--ignore-cutoff", action="store_true",
                    help="audit runs launched after AUDIT_CUTOFF too. For inspecting new runs "
                         "only -- the number quoted in the paper is the frozen one.")
    args = ap.parse_args()
    device = torch.device(args.device)
    print(f"device={device}")

    images, labels = build_val_images()
    print(f"fold-3 val n={images.shape[0]} (RAF-DB official test split)\n")

    # results/unified_students also holds AffectNet+/FERPlus students. Those were trained on a
    # different dataset with a different arg schema (train_affectnetplus_kd.py), so scoring them
    # on RAF-DB fold-3 would be meaningless AND build_student() from train_rafdb_kd would fail on
    # missing args. Filter on each run's own recorded dataset -- authoritative, not name-guessing.
    run_dirs, skipped, after_cutoff = [], 0, 0
    for rn in sorted(STUDENTS.iterdir()):
        if not rn.is_dir():
            continue
        for ts in sorted(rn.iterdir()):
            if not ((ts / "run_args.json").exists() and (ts / "metrics_best.json").exists()):
                continue
            ds = json.loads((ts / "metrics_best.json").read_text()).get("dataset", "")
            if str(ds).upper().replace("-", "") != "RAFDB":
                skipped += 1
                continue
            # The directory name is the launch timestamp, stamped by train_rafdb_kd.py and not
            # back-datable, so it is the right key for the freeze.
            if ts.name > AUDIT_CUTOFF and not args.ignore_cutoff:
                after_cutoff += 1
                continue
            run_dirs.append(ts)
    print(f"skipped {skipped} non-RAF-DB student runs (different dataset -> not comparable here)")
    if after_cutoff:
        print(f"excluded {after_cutoff} run(s) launched after the frozen cutoff {AUDIT_CUTOFF} "
              f"(pass --ignore-cutoff to inspect them; the paper quotes the frozen set)")
    if not args.ignore_cutoff and not args.limit and len(run_dirs) != AUDIT_FROZEN_N:
        raise RuntimeError(
            f"the frozen inclusion set should hold {AUDIT_FROZEN_N} runs but {len(run_dirs)} "
            f"matched. The abstract quotes N={AUDIT_FROZEN_N}; either a run directory was removed "
            f"or the cutoff no longer separates the campaigns. Resolve before regenerating.")
    if args.limit:
        run_dirs = run_dirs[: args.limit]
    print(f"{len(run_dirs)} finished runs\n")

    rows = []
    for i, rd in enumerate(run_dirs, 1):
        cache_p = rd / "selection_audit.json"
        cache = json.loads(cache_p.read_text()) if (cache_p.exists() and not args.force) else {}
        ra = json.loads((rd / "run_args.json").read_text())
        changed = False
        for tag, (fname, indep, rule) in VARIANTS.items():
            if not (rd / fname).exists():
                continue
            if tag not in cache:
                try:
                    student, ep = load_student(rd, fname, device)
                    m = measure(student, images, labels, device)
                    m["ckpt_epoch"] = ep
                    cache[tag] = m
                    changed = True
                    del student
                except Exception as exc:                      # keep going; record the reason
                    cache[tag] = {"error": f"{type(exc).__name__}: {exc}"}
                    changed = True
            m = cache[tag]
            if "error" in m:
                print(f"  [{i}/{len(run_dirs)}] {rd.parent.name} [{tag}] ERROR {m['error'][:90]}")
                continue
            rows.append({"run_name": rd.parent.name, "timestamp": rd.name, "checkpoint": tag,
                         "selection_independent": indep, "selection_rule": rule,
                         "seed": ra.get("seed"), "epochs": ra.get("epochs"),
                         "swa_start": ra.get("swa_start") if ra.get("swa") else "",
                         "t_scale": ra.get("teacher_temperature_scale", 1.0),
                         "student_head": ra.get("student_head_type"),
                         "ckpt_epoch": m.get("ckpt_epoch"),
                         "acc": m["acc"], "ece": m["ece"], "nll": m["nll"],
                         "brier": m["brier"], "macro_f1": m["macro_f1"], "n_val": m["n_val"],
                         "run_dir": str(rd)})
        if changed:
            cache_p.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        have = [t for t in VARIANTS if t in cache and "error" not in cache[t]]
        print(f"  [{i}/{len(run_dirs)}] {rd.parent.name:<62} {have}")

    if not rows:
        print("\nNo measurements produced -- nothing written. Check the ERROR lines above.")
        return
    # THE FROZEN FILE AND THE SUPERSET ARE DIFFERENT FILES. Until P5 every campaign fell inside
    # the cutoff, so --ignore-cutoff had never actually written anything, and it wrote to the same
    # path. P5 is the first campaign outside the freeze: running --ignore-cutoff would have
    # rewritten selection_audit.csv with 137 runs, and T8 -- which pools every row of that file --
    # would have quoted N=137 while the abstract says 131. Nothing would have errored. So the
    # superset gets its own name, and the frozen file is only ever written by a frozen run.
    out = OUT_DIR / ("selection_audit_unfrozen.csv" if args.ignore_cutoff
                     else "selection_audit.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {out}  ({len(rows)} run x checkpoint measurements)")

    # Selection-optimism gap: how much does peeking buy, on each axis?
    import statistics as st
    from stats_convention import SD_CONVENTION, sample_sd
    print(f"\n[sd convention: {SD_CONVENTION}]")
    by_run = {}
    for r in rows:
        by_run.setdefault((r["run_name"], r["timestamp"]), {})[r["checkpoint"]] = r
    for indep in ("last", "swa"):
        d_acc = [v["best"]["acc"] - v[indep]["acc"] for v in by_run.values()
                 if "best" in v and indep in v]
        d_ece = [v["best"]["ece"] - v[indep]["ece"] for v in by_run.values()
                 if "best" in v and indep in v]
        if not d_acc:
            continue
        print(f"\n=== selection optimism: best - {indep}  (n={len(d_acc)} runs) ===")
        print(f"  d_acc = {st.mean(d_acc):+.3f} +/- {sample_sd(d_acc):.3f} pp   "
              f"(positive = 'best' flatters accuracy)")
        print(f"  d_ece = {st.mean(d_ece):+.4f} +/- {sample_sd(d_ece):.4f}      "
              f"(sign tells whether peeking also flattered calibration)")


if __name__ == "__main__":
    main()
