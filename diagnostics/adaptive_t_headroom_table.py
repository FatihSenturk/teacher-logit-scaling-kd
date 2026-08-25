"""B-007 -> B-010: does a mechanism's benefit scale with the teacher's headroom?

Two blocks, one shared val-set load.

BLOCK A (P3, observational across teachers): adaptive_t vs. its matched baseline, paired by
seed, for all 3 teachers. Each teacher has a different amount of removable miscalibration
(teacher headroom: stage1 0.0220, primary 0.0206, vae9182 0.0017). If the headroom law governs
mechanisms and not just post-hoc scaling, adaptive_t's ECE benefit should be large on the two
miscalibrated teachers and ~absent on the well-calibrated one.

BLOCK B (B-010, causal within ONE teacher): the same mechanism on VAE9182 whose logits are
pre-scaled by a FIXED T0=0.7311, chosen so the pre-scaled teacher's ECE = 0.0378 = Stage1's
native level. Same teacher, same architecture, same recipe, same seeds as its own control --
the ONLY difference from native VAE9182 is injected miscalibration. This removes the
head/augmentation/seed confounds that Block A cannot.

Pre-registered prediction (BULGULAR B-010, written before any of these runs finished): native
adaptive_t on VAE9182 is a WEAK ECE lever (-0.0034, 3/3 seeds). Under injected miscalibration it
should grow toward what the miscalibrated teachers show. Kill-switch: needs to clear -0.0034 in
BOTH seeds.

Read-only. CPU. Caches per-run ECE into <run_dir>/calibration.json.
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

OUT_DIR = ROOT / "diagnostics" / "adaptive_t_headroom"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TEACHER_GRID = json.loads((ROOT / "diagnostics" / "teacher_ece_grid" / "teacher_ece_grid.json").read_text())
SEEDS = (42, 1, 43)

BLOCK_A = {
    "stage1": {
        "baseline": {42: "RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200",
                     1: "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1",
                     43: "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43"},
        "adaptive_t": {42: "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200",
                       1: "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200_seed1",
                       43: "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200_seed43"},
    },
    "primary": {
        "baseline": {42: "RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200",
                     1: "RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1",
                     43: "RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43"},
        "adaptive_t": {42: "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200",
                       1: "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200_seed1",
                       43: "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200_seed43"},
    },
    "vae9182": {
        "baseline": {42: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200",
                     1: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1",
                     43: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43"},
        "adaptive_t": {42: "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200",
                       1: "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200_seed1",
                       43: "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200_seed43"},
    },
}
BLOCK_B = {
    "off": {s: f"RAFDB_vae9182_miscalT0731_adaptivetoff_b070_T6_224_400e_swa200_seed{s}" for s in (42, 1)},
    "on":  {s: f"RAFDB_vae9182_miscalT0731_adaptiveton_b070_T6_224_400e_swa200_seed{s}" for s in (42, 1)},
}
MISCAL_T0 = 0.7311

_VAL = None


def stats(run_name):
    global _VAL
    dirs = [d for d in sorted(glob.glob(str(ROOT / "results/unified_students" / run_name / "*")))
            if Path(d, "best_checkpoint.pth").exists() and Path(d, "metrics_best.json").exists()]
    if not dirs:
        return None
    d = Path(dirs[-1])
    cal = d / "calibration.json"
    if cal.exists():
        c = json.loads(cal.read_text())
        return c["acc_recomputed"], c["ece"]
    if _VAL is None:
        _VAL = build_val_images()
    images, labels = _VAL
    lg = eval_logits(student_from_run(d), images)
    acc = float((lg.argmax(1) == labels).float().mean() * 100.0)
    ece = confidence_ece(lg, labels, 1.0)
    cal.write_text(json.dumps({"ece": ece, "acc_recomputed": acc, "n_val": int(labels.shape[0]),
                               "method": "15-bin confidence ECE, fold-3 val, best_checkpoint.pth"},
                              indent=2), encoding="utf-8")
    return acc, ece


def paired(arm_a, arm_b, seeds):
    """Per-seed (arm_b - arm_a) deltas; only seeds where BOTH arms exist."""
    rows, d_acc, d_ece = [], [], []
    for s in seeds:
        a = stats(arm_a[s]) if s in arm_a else None
        b = stats(arm_b[s]) if s in arm_b else None
        if a is None or b is None:
            rows.append({"seed": s, "missing": True,
                         "which": ("control" if a is None else "") + ("|treat" if b is None else "")})
            continue
        rows.append({"seed": s, "ctrl_acc": a[0], "ctrl_ece": a[1],
                     "treat_acc": b[0], "treat_ece": b[1],
                     "d_acc": b[0] - a[0], "d_ece": b[1] - a[1]})
        d_acc.append(b[0] - a[0])
        d_ece.append(b[1] - a[1])
    out = {"per_seed": rows, "n": len(d_ece)}
    if d_ece:
        out.update({"d_acc_mean": st.mean(d_acc), "d_acc_sd": sample_sd(d_acc), "d_acc_all": d_acc,
                    "d_ece_mean": st.mean(d_ece), "d_ece_sd": sample_sd(d_ece), "d_ece_all": d_ece,
                    "d_ece_signs": ["-" if x < 0 else "+" for x in d_ece],
                    "all_negative_ece": all(x < 0 for x in d_ece)})
    return out


def headroom(teacher, prescale=1.0):
    """Removable miscalibration from the operating point. With a pre-scale T0 the reachable
    set is unchanged (scalings compose), so the floor is the same but the starting ECE is not."""
    g = TEACHER_GRID[teacher]
    fine = {float(k): v for k, v in g["fine_sweep"].items()}
    start = confidence_ece_at(teacher, prescale) if prescale != 1.0 else g["ece_T1"]
    return start - min(fine.values()), start


def confidence_ece_at(teacher, T):
    import torch
    b = torch.load(ROOT / "diagnostics" / "teacher_ece_grid" / f"teacher_val_logits_{teacher}.pt",
                   map_location="cpu", weights_only=False)
    return confidence_ece(b["logits"], b["labels"], T)


def main():
    print("=== BLOCK A: adaptive_t vs baseline, paired by seed, per teacher ===")
    print("(negative d_ece = adaptive_t calibrates better)\n")
    block_a = {}
    for teacher, arms in BLOCK_A.items():
        hr, start = headroom(teacher)
        res = paired(arms["baseline"], arms["adaptive_t"], SEEDS)
        res["teacher_headroom"] = hr
        res["teacher_ece_T1"] = start
        block_a[teacher] = res
        print(f"[{teacher}]  teacher ECE {start:.4f}, headroom {hr:.4f}")
        for r in res["per_seed"]:
            if r.get("missing"):
                print(f"    seed {r['seed']:<3} MISSING ({r['which']})")
            else:
                print(f"    seed {r['seed']:<3} ECE {r['ctrl_ece']:.4f} -> {r['treat_ece']:.4f}"
                      f"   d_ece {r['d_ece']:+.4f}   d_acc {r['d_acc']:+.3f}")
        if res["n"]:
            print(f"    => d_ece {res['d_ece_mean']:+.4f} +/- {res['d_ece_sd']:.4f}  "
                  f"signs {res['d_ece_signs']}   d_acc {res['d_acc_mean']:+.3f} +/- {res['d_acc_sd']:.3f}"
                  f"   n={res['n']}")
        print()

    print("=== BLOCK B: B-010 causal test -- VAE9182 pre-scaled to Stage1's ECE ===")
    hr_pre, start_pre = headroom("vae9182", MISCAL_T0)
    print(f"pre-scaled teacher (T0={MISCAL_T0}): ECE {start_pre:.4f}, headroom {hr_pre:.4f}"
          f"   [native VAE9182: ECE {TEACHER_GRID['vae9182']['ece_T1']:.4f}, headroom "
          f"{headroom('vae9182')[0]:.4f}]")
    block_b = paired(BLOCK_B["off"], BLOCK_B["on"], (42, 1))
    block_b["teacher_headroom"] = hr_pre
    block_b["teacher_ece_at_T0"] = start_pre
    for r in block_b["per_seed"]:
        if r.get("missing"):
            print(f"    seed {r['seed']:<3} MISSING ({r['which']}) -- still training")
        else:
            print(f"    seed {r['seed']:<3} ECE {r['ctrl_ece']:.4f} -> {r['treat_ece']:.4f}"
                  f"   d_ece {r['d_ece']:+.4f}   d_acc {r['d_acc']:+.3f}")
    if block_b["n"]:
        print(f"    => d_ece {block_b['d_ece_mean']:+.4f} +/- {block_b['d_ece_sd']:.4f}  "
              f"signs {block_b['d_ece_signs']}   n={block_b['n']}")

    native = block_a["vae9182"]
    print("\n=== VERDICT vs pre-registered kill-switch ===")
    print(f"  native VAE9182 adaptive_t d_ece   : {native.get('d_ece_mean', float('nan')):+.4f} "
          f"(headroom {native['teacher_headroom']:.4f})")
    if block_b["n"] < 2:
        print(f"  PARTIAL: only {block_b['n']}/2 seed(s) done -- kill-switch NOT yet evaluable. "
              f"Do not call it either way.")
    else:
        print(f"  miscalibrated  adaptive_t d_ece   : {block_b['d_ece_mean']:+.4f} "
              f"+/- {block_b['d_ece_sd']:.4f}  signs {block_b['d_ece_signs']} (headroom {hr_pre:.4f})")
        # Two criteria, BOTH required. The pre-registered bar was -0.0034 (the value B-004
        # reported for native adaptive_t). B-013 then showed that value does not survive the
        # clean contrast, so an "improve on the native number" test is no longer meaningful:
        # native is now +0.0026, i.e. a positive (worse) number, and "less bad than a bad
        # baseline" would let a WORSENING effect count as a pass. Hence criterion 1 is the
        # absolute pre-registered bar, and criterion 2 is this campaign's standing disqualifier
        # (sign consistency across seeds -- the same rule that killed G2G in B-003).
        PREREG_BAR = -0.0034
        beats_bar = all(x < PREREG_BAR for x in block_b["d_ece_all"])
        consistent = (all(x < 0 for x in block_b["d_ece_all"])
                      or all(x > 0 for x in block_b["d_ece_all"]))
        print(f"    criterion 1 -- every seed below the PRE-REGISTERED bar {PREREG_BAR:+.4f}: {beats_bar}")
        print(f"    criterion 2 -- sign consistent across seeds: {consistent}  {block_b['d_ece_signs']}")
        if beats_bar and consistent:
            print("  -> PASS: effect is real and directionally stable; spend the 3rd seed.")
        elif consistent:
            print("  -> WEAK: stable direction but below the pre-registered magnitude. Judgement call.")
        else:
            print("  -> NULL: signs disagree across seeds and sd exceeds |mean|. By this campaign's "
                  "own standard this is noise. STOP -- do not spend the 3rd seed.")
        block_b["verdict"] = ("PASS" if (beats_bar and consistent)
                             else "WEAK" if consistent else "NULL")
        block_b["prereg_bar"] = PREREG_BAR

    payload = {"sd_convention": SD_CONVENTION,
               "block_a_adaptive_t_by_teacher": block_a,
               "block_b_miscalibration_causal": block_b,
               "miscal_T0": MISCAL_T0}
    (OUT_DIR / "adaptive_t_headroom.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'adaptive_t_headroom.json'}")


if __name__ == "__main__":
    main()
