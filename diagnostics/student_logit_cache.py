"""Per-sample student logit cache -- the substrate the calibration FIGURES need.

WHY THIS FILE EXISTS. Everything this campaign has measured so far is a SCALAR per run:
selection_audit.json holds acc/ECE/NLL/Brier per checkpoint, calibration.json holds one ECE.
A reliability diagram, a confidence histogram and a per-class confidence gap all need the
per-sample distribution those scalars were reduced from -- and it was discarded. Re-forwarding
a student inside each figure script would make every figure edit slow and, worse, would let two
figures disagree if a checkpoint were ever touched between them. So: forward once, write
<run_dir>/logits_<ckpt>.npz, and let every figure be a pure file read.

THE CORRECTNESS GATE (the reason this is not merely a convenience). A cached logit file that
silently disagreed with the audited scalar would poison every figure downstream while looking
completely normal. So each write RE-DERIVES accuracy and 15-bin ECE from the logits just
produced and compares them to that run's own selection_audit.json. A deviation beyond --tol is
a hard error and the .npz is NOT written. That makes the cache falsifiable against an artifact
produced by a different script, on a different day, through a different code path.

The labels are stored alongside the logits in every file rather than once globally, so a cache
entry can be validated on its own without trusting a second file to still describe the same
val set. All entries are checked against each other for label identity on load.

WHY --device DEFAULTS TO cuda, EVEN THOUGH THIS IS AN ANALYSIS SCRIPT. The gate above was
written expecting CPU to reproduce the audit and it did not: on
RAFDB_stage1_tempscale_T085_...seed1 @swa, CPU gives accuracy identical to six decimals but
ECE 0.0816781 against the audit's 0.0813682 (+3.1e-4), while CUDA reproduces the audit to the
last bit (delta exactly 0.00e+00). The cause is not a checkpoint difference: predictions are
identical, and CPU is fully deterministic here (batch 128 vs 256 gives max|logit diff| = 0).
It is that ECE is a BINNED statistic -- 2 of 3068 samples sit within 1e-4 of a 15-bin edge, and
a ~1e-6 float difference moves them between bins whose occupancy is small enough that the
weighted term shifts by ~3e-4. So ECE carries a device-dependent numerical floor of ~3e-4,
which is 0.07x the RAF-DB seed sd (0.0043) and changes no conclusion -- but it does mean a
figure built on CPU logits would print an ECE that disagrees in the fourth decimal with the
table beside it. Building the cache on the same device the audit used removes that entirely.
Pass --device cpu to trade bit-identity for zero GPU contention.

Usage:
  python diagnostics/student_logit_cache.py --arm stage1              # 5 T x 3 seeds, @swa
  python diagnostics/student_logit_cache.py --arm stage1 --ckpt best last
  python diagnostics/student_logit_cache.py --arm stage1 --force      # ignore existing cache
"""
import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from kd_common import clean_state_dict, extract_logits  # noqa: E402
from train_rafdb_kd import build_student  # noqa: E402
from teacher_temperature_scaling_fit import build_val_images, confidence_ece  # noqa: E402
from p1_two_teacher_overlay import CURVES  # noqa: E402  single source of run -> (teacher, T)

STUDENTS = ROOT / "results" / "unified_students"

# Same filenames and semantics as diagnostics/selection_audit_table.py::VARIANTS. Kept as a
# literal rather than imported because that module runs a full measurement pass on import-time
# arguments; the mapping is three lines and is asserted against the audit JSON on every write.
CKPT_FILE = {"best": "best_checkpoint.pth", "last": "last_checkpoint.pth",
             "swa": "swa_student.pth"}

_VAL = None


def val_images():
    global _VAL
    if _VAL is None:
        _VAL = build_val_images()
    return _VAL


def run_dir_of(run_name):
    """The single timestamp directory of a finished run. Ambiguity is an error, not a guess."""
    parent = STUDENTS / run_name
    if not parent.is_dir():
        raise FileNotFoundError(f"no such run: {parent}")
    cands = [d for d in sorted(parent.iterdir())
             if d.is_dir() and (d / "metrics_best.json").exists()]
    if len(cands) != 1:
        raise RuntimeError(f"{run_name}: expected exactly 1 finished run dir, found {len(cands)}")
    return cands[0]


def load_student(run_dir, ckpt, device):
    args = SimpleNamespace(**json.loads((run_dir / "run_args.json").read_text()))
    args.student_pretrained = False      # deterministic eval build: never re-pull ImageNet
    args.use_vich_sampling = False       # VICH head must be deterministic at eval
    student = build_student(args, device)
    blob = torch.load(run_dir / CKPT_FILE[ckpt], map_location=device, weights_only=False)
    sd = {k: v for k, v in blob["model_state_dict"].items() if k != "n_averaged"}
    if sd and all(k.startswith("module.") for k in sd):
        # swa_student.pth comes from torch.optim.swa_utils.AveragedModel, which prefixes every
        # key with "module." and adds an n_averaged buffer the bare student does not have.
        sd = {k[len("module."):]: v for k, v in sd.items()}
    student.load_state_dict(clean_state_dict(sd), strict=True)
    student.eval()
    return student


@torch.no_grad()
def forward_val(student, images, device, batch=256):
    # batch=256 matches selection_audit_table.measure(), so the validation below compares two
    # numerically identical reductions rather than two that differ by accumulation order.
    out = []
    for i in range(0, images.shape[0], batch):
        out.append(extract_logits(student(images[i:i + batch].to(device))).float().cpu())
    return torch.cat(out, dim=0)


def cache_path(run_dir, ckpt):
    return run_dir / f"logits_{ckpt}.npz"


def build_one(run_name, ckpt, device, tol, force):
    run_dir = run_dir_of(run_name)
    p = cache_path(run_dir, ckpt)
    if p.exists() and not force:
        return "cached", p, None

    audit_p = run_dir / "selection_audit.json"
    if not audit_p.exists():
        raise FileNotFoundError(
            f"{run_name}: no selection_audit.json -- there is nothing to validate the cache "
            f"against. Run diagnostics/selection_audit_table.py first.")
    audit = json.loads(audit_p.read_text())[ckpt]

    images, labels = val_images()
    t0 = time.time()
    logits = forward_val(load_student(run_dir, ckpt, device), images, device)
    dt = time.time() - t0

    acc = float((logits.argmax(1) == labels).float().mean() * 100.0)
    ece = confidence_ece(logits, labels, 1.0)
    d_acc, d_ece = abs(acc - audit["acc"]), abs(ece - audit["ece"])
    if d_acc > tol["acc"] or d_ece > tol["ece"]:
        raise RuntimeError(
            f"{run_name} @{ckpt}: cached logits disagree with selection_audit.json -- "
            f"acc {acc:.4f} vs {audit['acc']:.4f} (d={d_acc:.4f}), "
            f"ECE {ece:.6f} vs {audit['ece']:.6f} (d={d_ece:.6f}). "
            f"NOT writing the cache; the checkpoint or the eval pipeline has changed.")
    if int(labels.shape[0]) != int(audit["n_val"]):
        raise RuntimeError(f"{run_name} @{ckpt}: n_val {labels.shape[0]} != audit {audit['n_val']}")

    np.savez_compressed(
        p,
        logits=logits.numpy().astype(np.float32),
        labels=labels.numpy().astype(np.int64),
        meta=np.array(json.dumps({
            "run_name": run_name, "run_dir": str(run_dir), "checkpoint": ckpt,
            "n_val": int(labels.shape[0]), "acc_recomputed": acc, "ece_recomputed": ece,
            "audit_acc": audit["acc"], "audit_ece": audit["ece"],
            "d_acc": d_acc, "d_ece": d_ece,
            "ece_method": "15-bin equal-width confidence ECE, fold-3 val, T=1",
            "device": str(device), "seconds": round(dt, 1),
        })))
    return "computed", p, dt


def load_cache(run_name, ckpt):
    """(logits, labels, meta) for one run. Raises if the cache is missing -- never recomputes
    silently, so a figure script cannot quietly start doing forward passes."""
    p = cache_path(run_dir_of(run_name), ckpt)
    if not p.exists():
        raise FileNotFoundError(
            f"no logit cache for {run_name} @{ckpt}. Build it: "
            f"python diagnostics/student_logit_cache.py --arm <arm> --ckpt {ckpt}")
    z = np.load(p, allow_pickle=False)
    return z["logits"], z["labels"], json.loads(str(z["meta"]))


def load_arm(arm, ckpt="swa"):
    """{T: {seed: (logits, labels)}} for a whole dose-response arm, with label identity checked
    across every entry -- if two runs were somehow scored on different images, every pooled
    statistic downstream would be meaningless and it would not be visible in the figure."""
    out, ref = {}, None
    for T, seeds in CURVES[arm].items():
        out[float(T)] = {}
        for seed, run_name in seeds.items():
            lg, lb, _ = load_cache(run_name, ckpt)
            if ref is None:
                ref = lb
            elif not np.array_equal(ref, lb):
                raise RuntimeError(f"{run_name} @{ckpt}: label vector differs from the other "
                                   f"cache entries -- these runs were not scored on one val set")
            out[float(T)][int(seed)] = lg
    return out, ref


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", nargs="+", default=["stage1"], choices=sorted(CURVES.keys()))
    ap.add_argument("--ckpt", nargs="+", default=["swa"], choices=sorted(CKPT_FILE.keys()))
    ap.add_argument("--device", default="cuda",
                    help="cuda reproduces selection_audit.json bit-exactly (see module docstring); "
                         "cpu is ~3e-4 off in ECE but contends with nothing.")
    ap.add_argument("--threads", type=int, default=2,
                    help="torch CPU threads. Deliberately low: this is meant to run alongside "
                         "a training job that already owns 12 dataloader workers.")
    ap.add_argument("--tol-acc", type=float, default=1e-3, help="pp")
    ap.add_argument("--tol-ece", type=float, default=1e-4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.device == "cpu":
        torch.set_num_threads(args.threads)
    device = torch.device(args.device)
    tol = {"acc": args.tol_acc, "ece": args.tol_ece}

    jobs = [(rn, ck) for arm in args.arm for seeds in CURVES[arm].values()
            for rn in seeds.values() for ck in args.ckpt]
    print(f"{len(jobs)} (run, checkpoint) pairs on {device} "
          f"[tol acc {args.tol_acc} pp, ECE {args.tol_ece}]\n")

    n_new = 0
    for i, (rn, ck) in enumerate(jobs, 1):
        status, p, dt = build_one(rn, ck, device, tol, args.force)
        n_new += status == "computed"
        t = f"{dt:5.1f}s" if dt else "   -- "
        print(f"  [{i:>2}/{len(jobs)}] {status:<8} {t}  {rn} @{ck}")

    print(f"\n{n_new} computed, {len(jobs) - n_new} already cached. "
          f"Every written file matched its run's selection_audit.json within tolerance.")


if __name__ == "__main__":
    main()
