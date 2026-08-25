"""B-015 verdict: does the B-007 calibration law hold on a SECOND dataset (FERPlus)?

Scored against the pre-registration written into BULGULAR.md and
ferplus_dose_response_queue.ps1 BEFORE any FERPlus student existed:

  PREDICTION 1  student-ECE argmin at T*=0.5063 (the teacher's own calibrating temperature)
  PREDICTION 2  student ECE monotone in teacher ECE (equivalently in |signed teacher gap|)
  PREDICTION 3  the T=1.0 end is worst (largest |teacher gap|)
  FALSIFIED IF  the argmin is not at T*, or the ordering does not follow teacher ECE
                -> in that case the law's scope is restricted to RAF-DB, honestly.

WHY THIS IS A STRONG TEST AND NOT A REPLICATION OF THE SAME REGIME.
Stage1 (RAF-DB) is natively OVER-confident: it needs SOFTENING (T*=1.349 > 1). The FERPlus VICH
teacher was trained on soft 10-rater vote targets and is natively UNDER-confident: it needs
SHARPENING (T*=0.5063 < 1). So the required correction runs the OPPOSITE direction, on a
different dataset, with a different class count (8 vs 7). A law that survives that is not an
artefact of one teacher's pathology.

THE DECISIVE EVIDENCE IS WITHIN-SEED, NOT POOLED. Each of the 3 seeds ran all 3 temperatures,
so for a fixed seed the initial weights, data order and augmentation draws are IDENTICAL and the
ONLY difference is the teacher pre-scale. 3 seeds x 3 checkpoints = 9 independent monotonicity
tests that contain no seed confound at all. Pooled correlations are reported too, but they are
the weaker statement.

STATISTICS. Sample sd (n-1), not pstdev -- see the methodological correction in BULGULAR.
Spearman is computed exactly on 3 distinct x-values (no ties), so rho in {-1, -0.5, +0.5, +1}.
Reading a p-value off n=3 would be meaningless, so significance is carried by the within-seed
replication count (how many of the 9 curves are monotone), not by a test on 3 points.

Read-only, zero GPU. Outputs -> diagnostics/selection_audit/b015_verdict.json
"""
import csv
import json
import statistics as st
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))
from stats_convention import SD_CONVENTION  # noqa: E402

CSV = ROOT / "diagnostics" / "selection_audit" / "ferplus_selection_audit.csv"
OUT = ROOT / "diagnostics" / "selection_audit" / "b015_verdict.json"

# Closed-form teacher-side quantities, from cached teacher logits (diagnostics/ferplus_jsd/).
# Fixed BEFORE the students ran; not re-derived here.
TEACHER = {
    "0.5063": {"ece": 0.0156, "signed_gap": -0.0117, "role": "T*_NLL (calibrated)"},
    "0.26":   {"ece": 0.0393, "signed_gap": +0.0393, "role": "over-sharpened (sign flipped)"},
    "1.0":    {"ece": 0.1282, "signed_gap": -0.1277, "role": "native (under-confident)"},
}
T_STAR = "0.5063"
CHECKPOINTS = ("best", "last", "swa")

# Arms that exist in the audit CSV but are NOT part of the frozen B-015 grid, and why.
# This is a pre-registration guard, not tidiness. B-015's three predictions were frozen on
# 2026-07-26 13:27:26 over exactly {1.0, 0.5063, 0.26} (ferplus_dose_response_queue.ps1:38-41).
# T=0.74 is a LATER, SEPARATE pre-registration (B-017, frozen 2026-07-27 12:56:29). Folding its
# runs into this verdict would silently turn a 3-point pre-registered test into a 4-point
# post-hoc one -- the exact failure mode this campaign audits everywhere else. The earlier
# version of this script had no such list and simply crashed when the 0.74 rows appeared;
# crashing was luckier than the alternative, which would have been quietly absorbing them.
NOT_IN_B015 = {
    "0.74": "B-017 arm (T*_JSD), pre-registered separately on 2026-07-27; see PREREGISTRATIONS.md A4",
}
# RAF-DB's fitted law, for the cross-dataset comparison (diagnostics/p4_teacher_selection_recipe.py)
RAFDB_FIT = {"intercept": 0.0244, "slope": 0.7653}


def tkey(v):
    """Map a t_scale to its B-015 arm key, or None if the arm is deliberately out of scope.

    Returning None (rather than raising) only for the explicitly enumerated NOT_IN_B015 arms
    keeps the original guard intact: a t_scale that is neither a B-015 arm nor a known
    out-of-scope arm still raises, so a genuinely unexpected value can never be dropped silently.
    """
    v = float(v)
    for k in TEACHER:
        if abs(v - float(k)) < 1e-9:
            return k
    for k in NOT_IN_B015:
        if abs(v - float(k)) < 1e-9:
            return None
    raise KeyError(f"unexpected t_scale {v}")


def spearman3(xs, ys):
    """Spearman with TIE-CORRECTED (midrank) ranking.

    The tie handling is load-bearing here, not a nicety. In the pooled view there are 9 runs but
    only 3 distinct teacher-ECE values, so x is 3 groups of 3 ties. An untied ranking (assigning
    1,2,3 arbitrarily within a tie group) invents an ordering that does not exist in the data and
    deflates rho -- the first version of this script reported +0.867 for data whose groups do not
    overlap at all, and that artefact was very nearly written up as a failed prediction.

    NOTE: even with correct midranks, rho cannot reach 1.0 when x is tied, so the pooled rho is
    reported for completeness only. The primary pooled statistics are spearman on the 3 group
    MEANS (no ties) and the group-separation test, both computed in main().
    """
    def rank(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and a[order[j + 1]] == a[order[i]]:
                j += 1
            mid = (i + j) / 2.0 + 1.0          # midrank shared by the whole tie group
            for k in range(i, j + 1):
                r[order[k]] = mid
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


def linfit(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, my - slope * mx


def pearson(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return num / den if den else float("nan")


def main():
    all_rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    rows, excluded = [], {}
    for r in all_rows:
        k = tkey(r["t_scale"])
        if k is None:
            excluded[str(float(r["t_scale"]))] = excluded.get(str(float(r["t_scale"])), 0) + 1
            continue
        r["T"] = k
        rows.append(r)
    if excluded:
        print("  Excluded from the B-015 verdict (out of the frozen grid):")
        for t, c in sorted(excluded.items()):
            reason = next(v for k, v in NOT_IN_B015.items() if abs(float(k) - float(t)) < 1e-9)
            print(f"    T={t}: {c} row(s) -- {reason}")
    for r in rows:
        r["ece"] = float(r["ece"])
        r["acc"] = float(r["acc"])
        r["nll"] = float(r["nll"])
        r["brier"] = float(r["brier"])
    seeds = sorted({r["seed"] for r in rows})
    out = {"n_runs": len({(r["run_name"]) for r in rows}), "seeds": seeds,
           "teacher": TEACHER, "T_star": T_STAR}
    print(f"{out['n_runs']} runs x {len(CHECKPOINTS)} checkpoints, seeds {seeds}\n")

    # ---------- PREDICTION 2 & 3, within-seed: the decisive test ----------
    print("=" * 78)
    print("WITHIN-SEED MONOTONICITY (decisive: zero seed confound)")
    print("=" * 78)
    within = []
    for seed in seeds:
        for ck in CHECKPOINTS:
            pts = [(r["T"], r["ece"]) for r in rows if r["seed"] == seed and r["checkpoint"] == ck]
            if len(pts) != 3:
                continue
            pts.sort(key=lambda p: TEACHER[p[0]]["ece"])           # order by TEACHER ECE
            eces = [p[1] for p in pts]
            mono = all(eces[i] < eces[i + 1] for i in range(len(eces) - 1))
            argmin_T = min(pts, key=lambda p: p[1])[0]
            within.append({"seed": seed, "checkpoint": ck, "monotone": mono,
                           "argmin_T": argmin_T, "argmin_at_T_star": argmin_T == T_STAR,
                           "curve": {p[0]: p[1] for p in pts}})
            arrow = "  ".join(f"{p[0]}:{p[1]:.4f}" for p in pts)
            print(f"  seed {seed:>2} @{ck:<4}  (teacher ECE ascending)  {arrow}"
                  f"   monotone={'YES' if mono else 'NO '}  argmin=T{argmin_T}")
    n_mono = sum(w["monotone"] for w in within)
    n_argmin = sum(w["argmin_at_T_star"] for w in within)
    print(f"\n  monotone in teacher ECE:      {n_mono}/{len(within)} within-seed curves")
    print(f"  argmin exactly at T*={T_STAR}:  {n_argmin}/{len(within)} within-seed curves")
    out["within_seed"] = {"curves": within, "n_monotone": n_mono,
                          "n_argmin_at_T_star": n_argmin, "n_total": len(within)}

    # ---------- pooled view, per checkpoint ----------
    print("\n" + "=" * 78)
    print("POOLED PER-CHECKPOINT (3 seeds per point; sample sd, n-1)")
    print("=" * 78)
    out["pooled"] = {}
    for ck in CHECKPOINTS:
        agg = {}
        for k in TEACHER:
            e = [r["ece"] for r in rows if r["checkpoint"] == ck and r["T"] == k]
            a = [r["acc"] for r in rows if r["checkpoint"] == ck and r["T"] == k]
            agg[k] = {"n": len(e), "ece_mean": st.mean(e),
                      "ece_sd": st.stdev(e) if len(e) > 1 else 0.0,
                      "acc_mean": st.mean(a),
                      "acc_sd": st.stdev(a) if len(a) > 1 else 0.0}
        xs = [TEACHER[r["T"]]["ece"] for r in rows if r["checkpoint"] == ck]
        ys = [r["ece"] for r in rows if r["checkpoint"] == ck]
        xs_abs = [abs(TEACHER[r["T"]]["signed_gap"]) for r in rows if r["checkpoint"] == ck]
        rho = spearman3(xs, ys)
        rho_abs = spearman3(xs_abs, ys)
        pear = pearson(xs, ys)
        slope, icept = linfit(xs, ys)
        argmin_T = min(agg, key=lambda k: agg[k]["ece_mean"])

        # PRIMARY pooled statistics, both tie-free:
        # (a) Spearman on the 3 group means -- 3 distinct x, so rho can actually reach +-1.
        ks = sorted(TEACHER, key=lambda k: TEACHER[k]["ece"])
        rho_means = spearman3([TEACHER[k]["ece"] for k in ks], [agg[k]["ece_mean"] for k in ks])
        # (b) SEPARATION: is every individual run of the lower-teacher-ECE arm strictly below
        #     every run of the next arm? This is stronger than any correlation -- it says the
        #     groups do not overlap at all, so no seed assignment could reorder them.
        sep, sep_detail = True, []
        for k1, k2 in zip(ks, ks[1:]):
            lo = [r["ece"] for r in rows if r["checkpoint"] == ck and r["T"] == k1]
            hi = [r["ece"] for r in rows if r["checkpoint"] == ck and r["T"] == k2]
            ok = max(lo) < min(hi)
            sep &= ok
            sep_detail.append({"pair": f"{k1}<{k2}", "max_lower": max(lo), "min_upper": min(hi),
                               "separated": ok})
        acc_range = max(v["acc_mean"] for v in agg.values()) - min(v["acc_mean"] for v in agg.values())
        out["pooled"][ck] = {"by_T": agg, "spearman_teacherECE_tied_runs": rho,
                             "spearman_abs_signed_gap_tied_runs": rho_abs,
                             "spearman_on_group_means": rho_means,
                             "groups_fully_separated": sep, "separation_detail": sep_detail,
                             "pearson_teacherECE": pear,
                             "fit_slope": slope, "fit_intercept": icept,
                             "argmin_T": argmin_T, "argmin_at_T_star": argmin_T == T_STAR,
                             "acc_range_pp": acc_range}
        print(f"\n  @{ck}")
        for k in sorted(TEACHER, key=lambda k: TEACHER[k]["ece"]):
            v = agg[k]
            print(f"    T={k:<7} teacher_ECE={TEACHER[k]['ece']:.4f}  "
                  f"student_ECE={v['ece_mean']:.4f} +/- {v['ece_sd']:.4f}  "
                  f"acc={v['acc_mean']:.3f} +/- {v['acc_sd']:.3f}   {TEACHER[k]['role']}")
        print(f"    Spearman on group MEANS (tie-free, primary) = {rho_means:+.3f}")
        print(f"    Groups fully separated (no overlap between arms) = "
              f"{'YES' if sep else 'NO'}")
        for s in sep_detail:
            print(f"       {s['pair']}: max(lower)={s['max_lower']:.4f} < "
                  f"min(upper)={s['min_upper']:.4f}  -> {'OK' if s['separated'] else 'OVERLAP'}")
        print(f"    Spearman over all 9 runs (x has 3-way ties, midranks; cannot reach 1.0) = "
              f"{rho:+.3f}  [|signed gap| version {rho_abs:+.3f}]")
        print(f"    Pearson = {pear:+.3f}   fit: student_ECE = {icept:+.4f} + {slope:.4f} x teacher_ECE")
        print(f"    argmin at T={argmin_T} ({'MATCHES' if argmin_T == T_STAR else 'DOES NOT MATCH'} "
              f"pre-registered T*={T_STAR})   accuracy range across arms = {acc_range:.3f} pp")

    # ---------- effect sizes, every pair ----------
    print("\n" + "=" * 78)
    print("EFFECT SIZES (pooled sample sd -> Cohen d)")
    print("=" * 78)
    out["effect_sizes"] = {}
    for ck in CHECKPOINTS:
        out["effect_sizes"][ck] = {}
        for k1, k2 in combinations(sorted(TEACHER, key=lambda k: TEACHER[k]["ece"]), 2):
            a = [r["ece"] for r in rows if r["checkpoint"] == ck and r["T"] == k1]
            b = [r["ece"] for r in rows if r["checkpoint"] == ck and r["T"] == k2]
            if len(a) < 2 or len(b) < 2:
                continue
            gap = st.mean(b) - st.mean(a)
            sp = (((len(a) - 1) * st.stdev(a) ** 2 + (len(b) - 1) * st.stdev(b) ** 2)
                  / (len(a) + len(b) - 2)) ** 0.5
            d = gap / sp if sp else float("inf")
            out["effect_sizes"][ck][f"{k1}_vs_{k2}"] = {"gap": gap, "pooled_sd": sp, "cohen_d": d}
            print(f"  @{ck:<4} T={k1:<7} -> T={k2:<7}  d_ECE={gap:+.4f}  "
                  f"pooled_sd={sp:.4f}  Cohen d={d:+7.1f}")

    # ---------- cross-dataset: same law, different regime? ----------
    print("\n" + "=" * 78)
    print("CROSS-DATASET COMPARISON vs the RAF-DB fit")
    print("=" * 78)
    fb = out["pooled"]["best"]
    print(f"  RAF-DB  : student_ECE = {RAFDB_FIT['intercept']:+.4f} + "
          f"{RAFDB_FIT['slope']:.4f} x teacher_ECE   (Pearson +0.992, 3 teachers)")
    print(f"  FERPlus : student_ECE = {fb['fit_intercept']:+.4f} + "
          f"{fb['fit_slope']:.4f} x teacher_ECE   (Pearson {fb['pearson_teacherECE']:+.3f}, @best)")
    print("  The SIGN and the ordering replicate; the coefficients do not, and should not be")
    print("  expected to -- different dataset, different class count (8 vs 7), and the FERPlus")
    print("  teacher needs SHARPENING (T*<1) where Stage1 needs SOFTENING (T*>1). The law being")
    print("  tested is the monotone relation, not a shared regression line.")
    out["cross_dataset"] = {"rafdb_fit": RAFDB_FIT,
                            "ferplus_fit_best": {"intercept": fb["fit_intercept"],
                                                 "slope": fb["fit_slope"],
                                                 "pearson": fb["pearson_teacherECE"]}}

    # ---------- VERDICT ----------
    print("\n" + "=" * 78)
    print("VERDICT vs PRE-REGISTRATION")
    print("=" * 78)
    p1 = all(out["pooled"][ck]["argmin_at_T_star"] for ck in CHECKPOINTS)
    p1w = n_argmin == len(within)
    # Pooled monotonicity is judged on the tie-free group-mean Spearman AND on full group
    # separation -- never on the tied 9-run rho, which cannot reach 1.0 by construction.
    rho_m = {ck: out["pooled"][ck]["spearman_on_group_means"] for ck in CHECKPOINTS}
    p2 = all(v > 0.99 for v in rho_m.values())
    p2sep = all(out["pooled"][ck]["groups_fully_separated"] for ck in CHECKPOINTS)
    p2w = n_mono == len(within)
    worst = {ck: max(out["pooled"][ck]["by_T"],
                     key=lambda k: out["pooled"][ck]["by_T"][k]["ece_mean"]) for ck in CHECKPOINTS}
    p3 = all(v == "1.0" for v in worst.values())
    print(f"  P1  argmin at T*={T_STAR}          pooled: {'PASS' if p1 else 'FAIL'}   "
          f"within-seed: {'PASS' if p1w else 'FAIL'} ({n_argmin}/{len(within)})")
    print(f"  P2  monotone in teacher ECE     pooled (group-mean Spearman "
          f"{'/'.join(f'{v:+.3f}' for v in rho_m.values())}): {'PASS' if p2 else 'FAIL'}   "
          f"within-seed: {'PASS' if p2w else 'FAIL'} ({n_mono}/{len(within)})")
    print(f"      group separation (no arm overlaps the next): "
          f"{'PASS' if p2sep else 'FAIL'}")
    print(f"  P3  T=1.0 end is worst          {'PASS' if p3 else 'FAIL'}   "
          f"(worst arm per checkpoint: {worst})")
    verdict = ("CONFIRMED" if (p1 and p1w and p2 and p2sep and p2w and p3)
               else "FALSIFIED_OR_PARTIAL")
    out["verdict"] = {"P1_argmin_at_T_star": {"pooled": p1, "within_seed": p1w},
                      "P2_monotone_in_teacher_ece": {"pooled_group_means": p2,
                                                     "group_separation": p2sep,
                                                     "within_seed": p2w,
                                                     "group_mean_spearman": rho_m},
                      "P3_T1_worst": p3, "overall": verdict}
    print(f"\n  >>> B-015 = {verdict}")
    if verdict == "CONFIRMED":
        print("  >>> The B-007 calibration-conditioned law is NOT RAF-DB-specific. It holds on a")
        print("  >>> second dataset whose teacher carries the OPPOSITE pathology, at all three")
        print("  >>> checkpoints, and within every individual seed.")
    else:
        print("  >>> Scope restricted to RAF-DB as pre-registered. See failing predictions above.")

    # honest scope limits, recorded with the verdict rather than left to the write-up
    out["scope_limits"] = [
        "3 temperature points per dataset, not a dense sweep: monotonicity is established on an "
        "ordering of 3, so a non-monotone excursion BETWEEN grid points cannot be ruled out.",
        "One teacher per dataset. The law is now cross-dataset and cross-pathology, but not "
        "cross-architecture: every teacher here is POSTERv2.",
        "Accuracy is NOT flat across the arms and is NOT monotone in teacher ECE; only the "
        "worst-calibrated arm is reliably worst in accuracy too. The claim is about calibration.",
        "Teacher pre-scaling changes teacher calibration only; it cannot speak to teachers that "
        "differ by training recipe rather than by a post-hoc temperature.",
    ]
    print("\n  Recorded scope limits:")
    for s in out["scope_limits"]:
        print(f"    - {s}")

    out["sd_convention"] = SD_CONVENTION
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
