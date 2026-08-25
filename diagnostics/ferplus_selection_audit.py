"""FERPlus counterpart of selection_audit_table.py: ECE/NLL/Brier at best/last/swa.

WHY THIS SCRIPT IS REQUIRED AND NOT OPTIONAL.
The brief for the FERPlus dose-response said best+swa+last metrics (acc, ECE, NLL, Brier,
macro-F1) must be logged FROM THE START, so they would not have to be reconstructed the way
RAF-DB's were. That did not happen, and the reason is in the shared writer, not in the launcher:
    kd_common.py:855-877  write_metrics_json  -> stores accuracy/precision/recall/macro_f1/
                                                 weighted_f1/params/flops/size ONLY
    kd_common.py:652-680  evaluate_detailed   -> never accumulates probabilities, so no
                                                 probability-based metric CAN be derived there
There is no `ece`, `nll` or `brier` anywhere in kd_common.py. So metrics_{best,last,swa}.json
carry accuracy and macro-F1 but no calibration metric at all.

Nothing is lost, because all three checkpoints ARE written:
    train_affectnetplus_kd.py:763  swa_student.pth   (SWA average over [swa_start, epochs])
    ...                            best_student.pth / last_student.pth
so the calibration metrics are recoverable by re-scoring those checkpoints. This script does
that, for all 9 runs uniformly, with the SAME metric definitions used for RAF-DB's 290
measurements -- which is the property that makes the two datasets comparable in B-015. Patching
write_metrics_json instead would only have covered runs 3-9 (runs 1-2 had already imported the
module) and would still have needed this pass for runs 1-2, i.e. two metric schemas on disk for
no gain.

THE VAL PIPELINE MUST BE THE STUDENT'S OWN, NOT THE TEACHER CONFIG'S.
diagnostics/ferplus_human_vote_jsd.py scores the TEACHER and so builds loaders straight from
configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml, taking val_size from the YAML. The students were
trained through train_affectnetplus_kd.py:535 -> build_data_args(teacher_config, args), which
OVERRIDES val_size/train_size with --img-size 224 and val_root with --val-root. Reusing the
teacher's loader here would silently evaluate at the wrong resolution. So this script rebuilds
the loader through build_data_args() from each run's own recorded run_args.json.

That gives a free correctness check: the recomputed `best` accuracy must reproduce that run's
metrics_best.json accuracy. Any drift means the pipeline was not faithfully reconstructed, and
the script says so per run rather than quietly reporting wrong ECE.

METRIC DEFINITIONS -- identical to diagnostics/selection_audit_table.py, restated:
  ECE   : 15 bins, EQUAL-WIDTH on [0,1], binned on top-1 softmax confidence max_k p_k; bin term
          |acc(bin) - mean_conf(bin)| weighted by |bin|/N (Guo et al. 2017). Implementation
          reused from diagnostics/teacher_temperature_scaling_fit.py::confidence_ece.
  NLL   : mean F.cross_entropy(logits, labels) at T=1.
  Brier : multi-class, mean_i sum_k (p_ik - y_ik)^2, y one-hot (range [0,2]).
  macroF1: unweighted mean per-class F1 over the 8 FERPlus classes.
All on the FERPlus val fold, eval mode, VICH sampling off, hard argmax labels.

Defaults to CPU: the FERPlus dose-response queue owns the GPU, and 27 checkpoints x ~3.1k
images is a few minutes of CPU work. Pass --device cuda only when the queue is idle.

Usage:  python diagnostics/ferplus_selection_audit.py [--device cpu] [--limit N] [--force]
Caches per (run, checkpoint) into <run_dir>/selection_audit.json so re-runs are free.
Outputs -> diagnostics/selection_audit/ferplus_selection_audit.csv
"""
import argparse
import csv
import json
import statistics as st
import sys
from pathlib import Path
from types import SimpleNamespace

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from dataset_utils.builder import build_dataloader  # noqa: E402
from kd_common import clean_state_dict, extract_logits, unpack_image_batch_with_targets  # noqa: E402
from train_affectnetplus_kd import build_data_args, build_student  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "selection_audit"
OUT_DIR.mkdir(parents=True, exist_ok=True)
STUDENTS = ROOT / "results" / "unified_students"

# checkpoint tag -> (filename, is_selection_independent, how the epoch is chosen)
VARIANTS = {
    "best": ("best_student.pth", False, "argmax val_acc over epochs (PEEKS at eval set)"),
    "last": ("last_student.pth", True, "final epoch, fixed rule"),
    "swa":  ("swa_student.pth", True, "SWA average over [swa_start, epochs], fixed rule"),
}


def build_val_images(run_args):
    """Materialise the val split exactly as the run itself saw it.

    train_root is forced to None so build_dataloader skips indexing FERPlus's 28k-image train
    split, which this audit never touches (the JSD script uses the same trick).
    """
    a = SimpleNamespace(**run_args)
    a.device = torch.device("cpu")
    a.workers = 0
    a.cache_img = False
    data_args = build_data_args(ROOT / a.teacher_config if not Path(a.teacher_config).is_absolute()
                               else Path(a.teacher_config), a)
    data_args.train_root = None
    data_args.train_shuffle = False
    _train, val_loader = build_dataloader(data_args)
    if val_loader is None:
        raise RuntimeError("build_dataloader returned no val loader")
    imgs, labs = [], []
    for batch in val_loader:
        images, labels, _soft = unpack_image_batch_with_targets(batch)
        imgs.append(images)
        labs.append(labels)
    images = torch.cat(imgs)
    labels = torch.cat(labs)
    return images, labels, int(data_args.val_size)


def load_student(run_dir, ckpt_name, run_args, device):
    a = SimpleNamespace(**run_args)
    student = build_student(
        num_classes=a.num_classes,
        width_mult=a.width_mult,
        dropout=a.dropout,
        pretrained=False,                 # weights come from the checkpoint
        device=device,
        layer_embedding=a.student_layer_embedding,
        vae_head=a.student_vae_head,
        head_type=a.student_head_type,
        lightweight_layer_embedding=a.student_lightweight_layer_embedding,
        lightweight_layer_embedding_layers=a.student_layer_embedding_layers,
        embedding_dim=a.student_embedding_dim,
        use_vich_sampling=False,          # deterministic eval
        vich_logvar_min=a.vich_logvar_min,
        vich_logvar_max=a.vich_logvar_max,
        vich_init_logvar_bias=a.vich_init_logvar_bias,
    )
    ckpt = torch.load(run_dir / ckpt_name, map_location=device, weights_only=False)
    sd = ckpt["model_state_dict"]
    # swa_student.pth comes from torch.optim.swa_utils.AveragedModel: keys are prefixed "module."
    # and it carries an extra "n_averaged" buffer the bare student does not have.
    sd = {k: v for k, v in sd.items() if k != "n_averaged"}
    if sd and all(k.startswith("module.") for k in sd):
        sd = {k[len("module."):]: v for k, v in sd.items()}
    student.load_state_dict(clean_state_dict(sd), strict=True)
    student.eval()
    return student, ckpt.get("epoch")


@torch.no_grad()
def measure(student, images, labels, device, batch=64):
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu",
                    help="cpu by default: the dose-response queue owns the GPU")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="ignore per-run cache")
    ap.add_argument("--acc-tol", type=float, default=0.05,
                    help="max allowed drift (pp) between recomputed and logged best accuracy")
    args = ap.parse_args()
    device = torch.device(args.device)
    print(f"device={device}")

    run_dirs = []
    for rn in sorted(STUDENTS.iterdir()):
        if not rn.is_dir():
            continue
        for ts in sorted(rn.iterdir()):
            if not ((ts / "run_args.json").exists() and (ts / "metrics_best.json").exists()):
                continue
            ds = json.loads((ts / "metrics_best.json").read_text()).get("dataset", "")
            if str(ds).upper().replace("-", "").replace("+", "") != "FERPLUS":
                continue
            if "tempscale" not in ts.parent.name:
                continue
            run_dirs.append(ts)
    if args.limit:
        run_dirs = run_dirs[: args.limit]
    print(f"{len(run_dirs)} finished FERPlus tempscale runs\n")
    if not run_dirs:
        print("Nothing to audit yet.")
        return

    images, labels, val_size = build_val_images(
        json.loads((run_dirs[0] / "run_args.json").read_text()))
    print(f"FERPlus val n={images.shape[0]} at {val_size}px "
          f"(student's own pipeline, not the teacher config's)\n")

    rows, mismatches = [], []
    for i, rd in enumerate(run_dirs, 1):
        cache_p = rd / "selection_audit.json"
        cache = json.loads(cache_p.read_text()) if (cache_p.exists() and not args.force) else {}
        ra = json.loads((rd / "run_args.json").read_text())
        logged_best = json.loads((rd / "metrics_best.json").read_text()).get("accuracy")
        changed = False
        for tag, (fname, indep, rule) in VARIANTS.items():
            if not (rd / fname).exists():
                continue
            if tag not in cache:
                try:
                    student, ep = load_student(rd, fname, ra, device)
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
                print(f"  [{i}/{len(run_dirs)}] {rd.parent.name} [{tag}] ERROR {m['error'][:110]}")
                continue
            # Faithfulness check: a reconstructed pipeline that does not reproduce the run's own
            # logged accuracy is not measuring the same thing, so its ECE cannot be trusted.
            if tag == "best" and logged_best is not None:
                drift = m["acc"] - float(logged_best)
                if abs(drift) > args.acc_tol:
                    mismatches.append((rd.parent.name, float(logged_best), m["acc"], drift))
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
        print(f"  [{i}/{len(run_dirs)}] {rd.parent.name:<58} {have}")

    if not rows:
        print("\nNo measurements produced -- nothing written. Check the ERROR lines above.")
        return

    out = OUT_DIR / "ferplus_selection_audit.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {out}  ({len(rows)} run x checkpoint measurements)")

    if mismatches:
        print(f"\n** {len(mismatches)} run(s) do NOT reproduce their logged best accuracy "
              f"(tol {args.acc_tol} pp) -- the val pipeline is not faithfully reconstructed, "
              f"so treat their ECE as UNVERIFIED: **")
        for name, logged, recomputed, drift in mismatches:
            print(f"     {name:<58} logged {logged:.3f} vs recomputed {recomputed:.3f} "
                  f"({drift:+.3f} pp)")
    else:
        print("\nAll runs reproduce their logged best accuracy within tolerance "
              f"({args.acc_tol} pp) -- val pipeline faithfully reconstructed.")

    # --- dose-response view: teacher pre-scale T vs student ECE, per checkpoint ---
    print("\n=== B-015 dose-response: student ECE by teacher pre-scale T ===")
    print("  (pre-registered: argmin at T*=0.5063, monotone in teacher ECE; T=1.0 worst)")
    # Closed-form from the cached FERPlus teacher logits; see
    # diagnostics/ferplus_teacher_signed_grid.py (the authoritative producer of these four).
    teacher_ece = {"1.0": 0.1282, "0.74": 0.0665, "0.5063": 0.0156, "0.26": 0.0393}
    for tag in VARIANTS:
        sub = [r for r in rows if r["checkpoint"] == tag]
        if not sub:
            continue
        print(f"\n  -- checkpoint: {tag}")
        by_t = {}
        for r in sub:
            by_t.setdefault(str(round(float(r["t_scale"]), 4)), []).append(r)
        for t in sorted(by_t, key=float):
            g = by_t[t]
            eces = [r["ece"] for r in g]
            accs = [r["acc"] for r in g]
            t_ece = teacher_ece.get(t, teacher_ece.get(str(float(t))))
            sd = sample_sd(eces)
            print(f"     T={t:<7} n={len(g)}  teacher_ECE={t_ece if t_ece else '?'}  "
                  f"student_ECE={st.mean(eces):.4f} +/- {sd:.4f}  "
                  f"acc={st.mean(accs):.3f}  seeds={sorted(r['seed'] for r in g)}")
        if len(by_t) > 1:
            argmin = min(by_t, key=lambda t: st.mean([r["ece"] for r in by_t[t]]))
            print(f"     argmin student ECE at T={argmin}"
                  f"   (pre-registered prediction: T=0.5063)")

    # --- selection optimism, same two contrasts as RAF-DB ---
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
        print(f"  d_ece = {st.mean(d_ece):+.4f} +/- {sample_sd(d_ece):.4f}")
    print(f"\n[sd convention: {SD_CONVENTION}]")


if __name__ == "__main__":
    main()
