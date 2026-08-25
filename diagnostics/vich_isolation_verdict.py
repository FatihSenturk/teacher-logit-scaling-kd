"""VICH head-isolation GO/NO-GO (RAF-DB, VAE9182 teacher, 3 seeds).

Single manipulated variable: the STUDENT head. Both arms use the identical teacher
(VAE9182), identical backbone (MobileNetV2Plus w/ ECA+GeM+LightLE), identical recipe
(400e, SWA@200, plain KD, tau=6, alpha=0.3), identical seeds {42,1,43}.
    arm "vich"        --student-head-type vich    (VICH variational head)
    arm "plus_linear" --student-head-type linear  (plain linear classifier)

The question this closes: VICH is inherited from the POSTERv2 teacher-side work, where
it was reported as NOT improving a large model. Does it earn its place on a 2.25M-param
student? Reported on BOTH axes, because the answer differs between them:
    accuracy  -> is VICH an accuracy lever?   (pre-registered null expectation)
    ECE       -> is VICH a calibration lever? (the axis the paper's thesis lives on)

Paired per-seed deltas, not just mean-vs-mean: seed sd (~0.15pp acc) is larger than the
effect being measured, so an unpaired comparison cannot resolve it.

Read-only, CPU. Outputs -> diagnostics/vich_isolation/
"""
import glob
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from teacher_temperature_scaling_fit import build_val_images, confidence_ece  # noqa: E402
from student_halfb_eval import eval_logits, student_from_run  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

SEEDS = (42, 1, 43)
ARMS = {
    # arm -> {seed: run_name}
    "vich": {
        42: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200",
        1:  "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1",
        43: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43",
    },
    "plus_linear": {
        42: "RAFDB_vae9182_pluslinear_T6_224_400e_swa200_seed42",
        1:  "RAFDB_vae9182_pluslinear_T6_224_400e_swa200_seed1",
        43: "RAFDB_vae9182_pluslinear_T6_224_400e_swa200_seed43",
    },
}
OUT_DIR = ROOT / "diagnostics" / "vich_isolation"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def run_dir(name):
    d = sorted(glob.glob(str(ROOT / "results/unified_students" / name / "*")))
    return d[-1] if d and Path(d[-1], "best_checkpoint.pth").exists() else None


def main():
    images, labels = build_val_images()
    print(f"fold-3 val n={images.shape[0]}\n")

    per_seed = {arm: {} for arm in ARMS}
    for arm, mapping in ARMS.items():
        for seed in SEEDS:
            d = run_dir(mapping[seed])
            if d is None:
                print(f"  MISSING {arm} seed{seed}: {mapping[seed]}")
                continue
            logits = eval_logits(student_from_run(d), images)
            per_seed[arm][seed] = {
                "acc": float((logits.argmax(1) == labels).float().mean() * 100.0),
                "ece": confidence_ece(logits, labels, 1.0),
                "run_dir": d,
            }

    print(f"{'seed':<6}{'vich acc':<11}{'linear acc':<12}{'d_acc':<10}"
          f"{'vich ECE':<11}{'linear ECE':<12}{'d_ece':<10}")
    d_accs, d_eces = [], []
    for seed in SEEDS:
        if seed not in per_seed["vich"] or seed not in per_seed["plus_linear"]:
            continue
        v, l = per_seed["vich"][seed], per_seed["plus_linear"][seed]
        da, de = l["acc"] - v["acc"], l["ece"] - v["ece"]
        d_accs.append(da)
        d_eces.append(de)
        print(f"{seed:<6}{v['acc']:<11.3f}{l['acc']:<12.3f}{da:<+10.3f}"
              f"{v['ece']:<11.4f}{l['ece']:<12.4f}{de:<+10.4f}")

    summary = {}
    for arm in ARMS:
        accs = [per_seed[arm][s]["acc"] for s in SEEDS if s in per_seed[arm]]
        eces = [per_seed[arm][s]["ece"] for s in SEEDS if s in per_seed[arm]]
        summary[arm] = {"acc_mean": st.mean(accs), "acc_sd": sample_sd(accs),
                        "ece_mean": st.mean(eces), "ece_sd": sample_sd(eces), "n": len(accs)}
        print(f"\n{arm:<12} acc={st.mean(accs):.3f}+/-{sample_sd(accs):.3f}   "
              f"ECE={st.mean(eces):.4f}+/-{sample_sd(eces):.4f}   n={len(accs)}")

    # Paired deltas are the decision statistic. Sign consistency across all 3 seeds is
    # the bar we set for calling a lever real at n=3 (a mean alone cannot carry it).
    print("\n--- paired delta (plus_linear - vich); NEGATIVE d_ece means VICH calibrates better ---")
    print(f"  d_acc = {st.mean(d_accs):+.3f} +/- {sample_sd(d_accs):.3f}   "
          f"signs {[('+' if x > 0 else '-') for x in d_accs]}")
    print(f"  d_ece = {st.mean(d_eces):+.4f} +/- {sample_sd(d_eces):.4f}   "
          f"signs {[('+' if x > 0 else '-') for x in d_eces]}")
    rel = st.mean(d_eces) / summary["plus_linear"]["ece_mean"] * 100.0
    print(f"  VICH removes {rel:.1f}% of the linear-head student's ECE (relative).")

    payload = {"sd_convention": SD_CONVENTION,
               "per_seed": per_seed, "summary": summary,
               "paired_delta_linear_minus_vich": {
                   "d_acc_mean": st.mean(d_accs), "d_acc_sd": sample_sd(d_accs), "d_acc_all": d_accs,
                   "d_ece_mean": st.mean(d_eces), "d_ece_sd": sample_sd(d_eces), "d_ece_all": d_eces,
                   "ece_relative_reduction_pct": rel}}
    (OUT_DIR / "vich_isolation_verdict.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'vich_isolation_verdict.json'}")


if __name__ == "__main__":
    main()
