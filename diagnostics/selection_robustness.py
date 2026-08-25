"""Does every conclusion survive when measured at a SELECTION-INDEPENDENT checkpoint?

The audit (selection_audit_table.py) established that `best` peeks at the eval set: it is chosen
by argmax val_acc on the very 3068 images every number is reported on, buying +0.792 +/- 0.464 pp
of accuracy versus the final epoch. That is LARGER than most effects this paper discusses, so
every claim has to be re-derived from a checkpoint chosen by a fixed rule.

This script re-derives the two load-bearing result families at all three checkpoints and reports
whether the conclusion CHANGES:
  1. B-007 dose-response: student ECE vs teacher ECE per teacher, monotonicity + Spearman.
  2. Mechanism ablations: adaptive_t / gate / g2g_kl vs matched baseline, paired by seed, per teacher.

A conclusion that only holds at `best` is not a result. A conclusion that holds at `swa` and
`last` too is robust to selection.

Read-only; consumes diagnostics/selection_audit/selection_audit.csv (no model forwards).
Outputs -> diagnostics/selection_audit/selection_robustness.json
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# `sys.path` eklemesi ŞART -- gerekçe `selection_gain_estimator.py`'dekiyle aynı: import
# ROOT'tan önce ve yol eklemesi olmadan yapılıyordu, betik yalnız CWD `diagnostics/` iken
# çalışıyordu ve Level-1 kapısı ona soruyu hiç sormuyordu.
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
TEACHER_GRID = json.loads((ROOT / "diagnostics" / "teacher_ece_grid" / "teacher_ece_grid.json").read_text())
OUT = ROOT / "diagnostics" / "selection_audit" / "selection_robustness.json"
CKPTS = ("best", "swa", "last")
SEEDS = (42, 1, 43)

# T -> {seed: run_name}, reused verbatim from p1_two_teacher_overlay.py so the two analyses
# cannot silently diverge on which run is which point.
DOSE = {
    "stage1": {
        0.85:   {s: f"RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        1.00:   {42: "RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200",
                 1: "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1",
                 43: "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43"},
        1.3406: {42: "RAFDB_stage1_tempscale_T1341_halfA_baseline_b070_T6_224_400e_swa200",
                 1: "RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed1",
                 43: "RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed43"},
        1.70:   {s: f"RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        2.20:   {s: f"RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
    },
    "vae9182": {
        0.85:   {s: f"RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        1.00:   {42: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200",
                 1: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1",
                 43: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43"},
        1.3406: {s: f"RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        1.70:   {s: f"RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        2.20:   {s: f"RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
    },
}
MECH = {
    "stage1": {
        "baseline": DOSE["stage1"][1.00],
        "adaptive_t": {42: "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200",
                       1: "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200_seed1",
                       43: "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200_seed43"},
        "g2g_kl": {42: "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200",
                   1: "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200_seed1",
                   43: "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200_seed43"},
    },
    "primary": {
        "baseline": {42: "RAFDB_vichteacher_primary_9201_betaKD_b070_T6_224_best_400e_swa200",
                     1: "RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1",
                     43: "RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed43"},
        "adaptive_t": {42: "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200",
                       1: "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200_seed1",
                       43: "RAFDB_primary_adaptive_t_b070_T6_224_400e_swa200_seed43"},
        "g2g_kl": {42: "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200",
                   1: "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200_seed1",
                   43: "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200_seed43"},
    },
    "vae9182": {
        "baseline": DOSE["vae9182"][1.00],
        "adaptive_t": {42: "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200",
                       1: "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200_seed1",
                       43: "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200_seed43"},
        "g2g_kl": {42: "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200",
                   1: "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200_seed1",
                   43: "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200_seed43"},
    },
}


def load_audit():
    """(run_name, checkpoint) -> metrics. Keeps the newest timestamp per run_name."""
    best_ts, table = {}, {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        key = r["run_name"]
        if key not in best_ts or r["timestamp"] > best_ts[key]:
            best_ts[key] = r["timestamp"]
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        if r["timestamp"] != best_ts[r["run_name"]]:
            continue
        table[(r["run_name"], r["checkpoint"])] = {
            "acc": float(r["acc"]), "ece": float(r["ece"]), "nll": float(r["nll"]),
            "brier": float(r["brier"]), "macro_f1": float(r["macro_f1"])}
    return table


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    dx, dy = [a - mx for a in x], [b - my for b in y]
    den = (sum(a * a for a in dx) * sum(b * b for b in dy)) ** 0.5
    return sum(a * b for a, b in zip(dx, dy)) / den if den else float("nan")


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(o):
            r[i] = pos + 1
        return r
    return pearson(rank(x), rank(y))


def agg(table, mapping, ck, field):
    vals = [table[(mapping[s], ck)][field] for s in mapping if (mapping[s], ck) in table]
    return (st.mean(vals), sample_sd(vals), len(vals)) if vals else (None, None, 0)


def main():
    table = load_audit()
    out = {"sd_convention": SD_CONVENTION, "dose_response": {}, "mechanisms": {}}

    print("=" * 96)
    print("1) B-007 DOSE-RESPONSE at each checkpoint  (does the law depend on peeking?)")
    print("=" * 96)
    for teacher, by_T in DOSE.items():
        grid = TEACHER_GRID[teacher]["experiment_grid"]
        out["dose_response"][teacher] = {}
        print(f"\n[{teacher}]  teacher headroom "
              f"{TEACHER_GRID[teacher]['ece_T1'] - min(TEACHER_GRID[teacher]['fine_sweep'].values()):.4f}")
        print(f"  {'T':<9}{'teacherECE':<12}" + "".join(f"{'ECE@' + c:<22}" for c in CKPTS))
        for T in sorted(by_T):
            line = f"  {T:<9g}{grid[f'{T:g}']['teacher_ece']:<12.4f}"
            for ck in CKPTS:
                m, sd, n = agg(table, by_T[T], ck, "ece")
                line += (f"{m:.4f}+/-{sd:.4f}(n{n})".ljust(22) if m is not None
                         else "-".ljust(22))
            print(line)
        for ck in CKPTS:
            xs, ys, accs = [], [], []
            for T in sorted(by_T):
                m, _sd, n = agg(table, by_T[T], ck, "ece")
                a, _asd, _ = agg(table, by_T[T], ck, "acc")
                if m is None:
                    continue
                xs.append(grid[f"{T:g}"]["teacher_ece"])
                ys.append(m)
                accs.append(a)
            if len(xs) < 3:
                continue
            base = next((i for i, T in enumerate(sorted(by_T)) if T == 1.00), None)
            realized = (ys[base] - min(ys)) if base is not None else None
            best_T = sorted(by_T)[ys.index(min(ys))]
            out["dose_response"][teacher][ck] = {
                "pearson": pearson(xs, ys), "spearman": spearman(xs, ys),
                "student_realized_dECE": realized, "student_best_T": best_T,
                "acc_U_depth_pp": max(accs) - min(accs), "n_points": len(xs)}
            print(f"    @{ck:<5} spearman {spearman(xs, ys):+.3f}  pearson {pearson(xs, ys):+.3f}  "
                  f"realized dECE {realized:+.4f}  argmin T={best_T:g}  accU {max(accs)-min(accs):.3f}pp")

    print("\n" + "=" * 96)
    print("2) MECHANISM ABLATIONS, paired by seed, at each checkpoint")
    print("   (negative d_ece = mechanism calibrates better; signs must agree across seeds)")
    print("=" * 96)
    for teacher, arms in MECH.items():
        out["mechanisms"][teacher] = {}
        print(f"\n[{teacher}]")
        for mech in ("adaptive_t", "g2g_kl"):
            out["mechanisms"][teacher][mech] = {}
            for ck in CKPTS:
                d_acc, d_ece = [], []
                for s in SEEDS:
                    kb = (arms["baseline"].get(s), ck)
                    km = (arms[mech].get(s), ck)
                    if kb not in table or km not in table:
                        continue
                    d_acc.append(table[km]["acc"] - table[kb]["acc"])
                    d_ece.append(table[km]["ece"] - table[kb]["ece"])
                if not d_ece:
                    print(f"  {mech:<11} @{ck:<5} (no matched pairs)")
                    continue
                signs = "".join("-" if v < 0 else "+" for v in d_ece)
                consistent = len(set(signs)) == 1
                out["mechanisms"][teacher][mech][ck] = {
                    "d_acc_mean": st.mean(d_acc), "d_acc_sd": sample_sd(d_acc),
                    "d_ece_mean": st.mean(d_ece), "d_ece_sd": sample_sd(d_ece),
                    "d_ece_signs": signs, "sign_consistent": consistent, "n": len(d_ece)}
                verdict = ("IMPROVES" if consistent and d_ece[0] < 0
                           else "WORSENS" if consistent else "NULL(signs disagree)")
                print(f"  {mech:<11} @{ck:<5} d_ece {st.mean(d_ece):+.4f}+/-{sample_sd(d_ece):.4f} "
                      f"[{signs}]  d_acc {st.mean(d_acc):+.3f}+/-{sample_sd(d_acc):.3f}  n={len(d_ece)}  -> {verdict}")

    # ---- did any conclusion flip between best and the selection-independent checkpoints? ----
    print("\n" + "=" * 96)
    print("3) CONCLUSION STABILITY: best vs swa/last")
    print("=" * 96)
    flips = []
    for teacher, d in out["dose_response"].items():
        if "best" in d and "swa" in d:
            if d["best"]["student_best_T"] != d["swa"]["student_best_T"]:
                flips.append(f"dose_response[{teacher}] argmin T: best={d['best']['student_best_T']:g} "
                             f"vs swa={d['swa']['student_best_T']:g}")
    # Compare EVERY checkpoint pair, not just best-vs-swa: the sharpest contradictions in this
    # data are between the two selection-INDEPENDENT checkpoints (swa vs last), which a
    # best-vs-swa-only check silently misses.
    def verdict_of(c):
        if not c["sign_consistent"]:
            return "NULL"
        return "IMPROVES" if c["d_ece_mean"] < 0 else "WORSENS"

    for teacher, ms in out["mechanisms"].items():
        for mech, cks in ms.items():
            verdicts = {ck: verdict_of(c) for ck, c in cks.items()}
            if len(set(verdicts.values())) > 1:
                detail = "  ".join(f"{ck}={verdicts[ck]}[{cks[ck]['d_ece_signs']}]"
                                   f"({cks[ck]['d_ece_mean']:+.4f})" for ck in CKPTS if ck in cks)
                flips.append(f"mechanism[{teacher}/{mech}]: {detail}")
    if flips:
        print("  CONCLUSIONS THAT CHANGE WITH CHECKPOINT CHOICE:")
        for f in flips:
            print(f"    - {f}")
        print("\n  => Any effect in this list is SMALLER than the checkpoint-choice artifact.")
        print("     3/3 seed sign-consistency is NOT sufficient evidence for it: the same")
        print("     comparison can be 3/3 consistent in BOTH directions depending only on which")
        print("     checkpoint of the SAME runs is read. Report these as null/unresolved.")
    else:
        print("  No qualitative conclusion changes across checkpoints.")
    out["conclusions_that_change"] = flips

    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
