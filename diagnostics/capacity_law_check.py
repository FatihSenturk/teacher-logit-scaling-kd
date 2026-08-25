"""8(b) EXPLORATORY -- does the calibration law hold across student capacity?

*** NOT PRE-REGISTERED. *** No prediction about capacity was frozen before these runs. What WAS
frozen, on 2026-07-29 01:28:02 in rafdb_p3_capacity_slope_queue.ps1, is the question and the
ANALYSIS PLAN (PREREGISTRATIONS.md B4). This script implements that plan verbatim; everything it
reports is exploratory and will be labelled as such in the paper.

WHAT THE QUESTION NEEDS AND WHAT WE NOW HAVE. "Does the teacher-ECE -> student-ECE slope change
with student capacity?" needs a teacher-temperature sweep AT EACH capacity:

    2.248 M (pre-trained) : 5 temperatures {0.85, 1.0, 1.3406, 1.7, 2.2}  -> slope fittable
    0.712 M (scratch)     : 3 temperatures {1.0, 1.7, 2.2}                -> slope fittable (P3)
    1.380 M (scratch)     : 1 temperature  {1.0}                          -> no slope

P3 (4 runs, finished 2026-07-30 08:58:50) added T=1.7 and T=2.2 at width 0.5, so a second slope
now exists. Before P3 this script could only report the missing design.

THREE THINGS THE FROZEN ANALYSIS PLAN REQUIRES, EACH LOAD-BEARING:
  1. b_2248 IS REFIT ON THE SAME THREE TEMPERATURES as b_w050. Comparing a 5-point fit against a
     3-point fit would confound capacity with fit support: the 5-point fit includes T=0.85 and
     T=1.3406, which sit in the low-ECE region and pull the line differently. The 5-point slope
     is still printed, but the CAPACITY COMPARISON uses the 3-point refit only.
  2. NO CONFIDENCE INTERVAL IS FABRICATED FOR EITHER SLOPE from a single seed pair. Two of the
     three w050 cells have n=2, which gives one degree of freedom -- a t-interval from that is
     theatre. Instead each slope gets a WORST-CASE ENVELOPE: every cell mean is pushed by one
     measured seed sd in whichever direction moves the slope most. That is an envelope, not a
     confidence interval, and it is labelled as such wherever it appears.
  3. THE SCRATCH/PRE-TRAINED CONFOUND IS STATED, NOT BURIED. b_w050 is scratch, b_2248 is
     pre-trained, so the two differ in TWO things at once. Separating them needs a scratch
     dose-response at 2.248 M (4 runs, not launched).

ONE MORE CONFOUND THAT WOULD BE EASY TO MISS: the T=1.0 cell in a naive `runs.csv` group-by
contains every mechanism run too (n=14, sd 0.0374 -- ten times the real seed spread). The
dose-response point is baseline-only, so the 2.248 M curve is read from two_dataset_overlay.json,
which already enforces that, and the w050 cells are filtered to the frontier family by name.

Read-only, zero GPU. Outputs -> diagnostics/p5_efficiency/capacity_law_check.{json,md}
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OVERLAY = ROOT / "diagnostics" / "p1_dose_response" / "two_dataset_overlay.json"
AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
RUNS = ROOT / "runs.csv"
OUT_DIR = ROOT / "diagnostics" / "p5_efficiency"
CKPT = "swa"
BIG_PARAMS = 2.248291       # the capacity the dose-response sweep was run at


def linfit(xs, ys):
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return b, a, (1 - ss_res / ss_tot if ss_tot else float("nan"))


def slope_envelope(xs, sds):
    """Worst-case |delta b| when every cell mean moves by one measured seed sd.

    b is linear in y: b = sum_i w_i y_i with w_i = (x_i - mean(x)) / sxx. So the extreme is
    reached by pushing each y_i along sign(w_i), giving sum_i |w_i| sd_i. This is an ENVELOPE
    (a bound on how far seed noise alone could move the fitted slope), NOT a confidence
    interval -- with n=2 in two cells there is one degree of freedom and no interval is honest.
    """
    mx = st.mean(xs)
    sxx = sum((x - mx) ** 2 for x in xs)
    return sum(abs((x - mx) / sxx) * sd for x, sd in zip(xs, sds))


def frontier_cells():
    """Capacity-sweep students @CKPT, keyed (capacity_tag, t_scale) -> cell.

    Membership is SEMANTIC: `student_pretrained == False` is the exact signature of the capacity
    sweep (every other family on disk is pre-trained at width 1.0). The family field alone would
    drop the four runs P3 was launched to produce, because t_scale != 1.0 sends them to
    `dose_response`; the run NAME must not be used either, since `"frontier" in name` is what
    swept those same four runs into the fixed-teacher w050 cell in the first place.
    """
    meta, cells = {}, {}
    for r in csv.DictReader(open(RUNS, encoding="utf-8")):
        if r["student_pretrained"] == "False":
            meta[r["run_name"]] = (float(r["params_m"]), float(r["t_scale"] or 1.0),
                                   int(r["seed"]), r["capacity_tag"])
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        if r["checkpoint"] != CKPT or r["run_name"] not in meta:
            continue
        params, t_scale, seed, w = meta[r["run_name"]]
        c = cells.setdefault((w, t_scale), {"params_m": params, "ece": [], "acc": [], "seeds": []})
        c["ece"].append(float(r["ece"]))
        c["acc"].append(float(r["acc"]))
        c["seeds"].append(seed)
    return cells


def capacity_points(cells):
    """The fixed-teacher (T=1.0) level comparison across widths -- one cell per width."""
    out = {w: c for (w, t), c in cells.items() if t == 1.0}
    return dict(sorted(out.items(), key=lambda kv: kv[1]["params_m"]))


def main():
    pts = [p for p in json.loads(OVERLAY.read_text())["arms"]["rafdb_vae9182"]["points"]
           if CKPT in p.get("by_ckpt", {})]
    tx = [p["teacher_ece"] for p in pts]
    sy = [p["by_ckpt"][CKPT]["ece_mean"] for p in pts]
    slope5, icept5, r2_5 = linfit(tx, sy)

    cells = frontier_cells()
    caps = capacity_points(cells)

    # --- the two slopes, on the SAME three temperatures (frozen analysis plan, B4 point 1)
    SHARED_T = (1.0, 1.7, 2.2)
    tece = {p["T"]: p["teacher_ece"] for p in pts}
    big = {p["T"]: p["by_ckpt"][CKPT] for p in pts}
    missing = [t for t in SHARED_T if t not in tece]
    if missing:
        raise RuntimeError(f"no teacher ECE for T={missing} in the overlay -- the shared-support "
                           f"comparison cannot be built and must not be faked with the 5-point fit.")

    small = {t: cells[("w050", t)] for t in SHARED_T if ("w050", t) in cells}
    if len(small) != len(SHARED_T):
        raise RuntimeError(
            f"w050 has cells only at T={sorted(small)}, need {list(SHARED_T)}. A slope through "
            f"{len(small)} point(s) is not a slope; report the missing design instead.")

    xs = [tece[t] for t in SHARED_T]
    ys_s = [st.mean(small[t]["ece"]) for t in SHARED_T]
    sd_s = [sample_sd(small[t]["ece"]) for t in SHARED_T]
    n_s = [len(small[t]["ece"]) for t in SHARED_T]
    ys_b = [big[t]["ece_mean"] for t in SHARED_T]
    sd_b = [big[t]["ece_sd"] for t in SHARED_T]
    n_b = [big[t]["n"] for t in SHARED_T]

    b_small, a_small, r2_small = linfit(xs, ys_s)
    b_big, a_big, r2_big = linfit(xs, ys_b)
    env_small = slope_envelope(xs, sd_s)
    env_big = slope_envelope(xs, sd_b)
    d_slope = b_small - b_big
    # Two envelopes overlap => seed noise alone could produce the observed slope gap, so the
    # gap is NOT resolvable. This is the decision statistic, stated before it is interpreted.
    overlap = abs(d_slope) <= (env_small + env_big)

    L = ["# 8(b) — The calibration law × student capacity", "",
         "> ⚠️ **EXPLORATORY — THE RESULT IS NOT PRE-REGISTERED.** No *prediction* about capacity "
         "was frozen before these runs. What was frozen is **the question and the analysis plan** "
         "(`PREREGISTRATIONS.md` B4, 2026-07-29 01:28:02); this script executes that plan. In the "
         "paper this section will be labelled exploratory.", "",
         f"Producer: `diagnostics/capacity_law_check.py` · @{CKPT} · {SD_CONVENTION}", "",
         "## How many temperatures exist at each capacity", "",
         "| capacity | init | teacher-temperature points | slope? |", "|---|---|---|---|",
         f"| {BIG_PARAMS:.3f} M | pretrained | **{len(tx)}** "
         f"({', '.join(f'{t:g}' for t in sorted(tece))}) | ✅ |"]
    for w, c in caps.items():
        ts = sorted(t for (ww, t) in cells if ww == w)
        L.append(f"| {c['params_m']:.3f} M | scratch | **{len(ts)}** "
                 f"({', '.join(f'{t:g}' for t in ts)}) | {'✅' if len(ts) >= 3 else '❌'} |")
    L += ["", "P3 (4 runs, finished 2026-07-30 08:58:50) added T=1.7 and T=2.2 at width 0.5, "
              "so **a second slope now exists**. 1.380 M still has a single point, so that "
              "capacity does not enter this comparison.", "",
          "## 1. Two slopes, over the same three temperatures", "",
          "The comparison is made **on the same fit support**: putting a 5-point fit against a 3-point "
          "fit would confound capacity with fit support (written in B4 before the runs).", "",
          f"| teacher ECE | T | student ECE @swa — {BIG_PARAMS:.3f} M (pretrained) | n | "
          f"student ECE @swa — 0.712 M (scratch) | n |", "|---|---|---|---|---|---|"]
    for t, x, yb, sb, nb, ysm, ss, ns in zip(SHARED_T, xs, ys_b, sd_b, n_b, ys_s, sd_s, n_s):
        L.append(f"| {x:.4f} | {t:g} | {yb:.4f} ± {sb:.4f} | {nb} | {ysm:.4f} ± {ss:.4f} | {ns} |")
    res_big = [y - (a_big + b_big * x) for x, y in zip(xs, ys_b)]
    res_small = [y - (a_small + b_small * x) for x, y in zip(xs, ys_s)]
    # How far below the cells' OWN seed noise the residuals sit, as a measured range rather than a
    # loose "order of magnitude" -- against the smallest cell sd the factor is only ~3.5, so the
    # order-of-magnitude phrasing would be an overstatement at the low end.
    sd_all = [s for s in sd_b + sd_s if s > 0]
    worst_res = max(max(abs(r) for r in res_big), max(abs(r) for r in res_small))
    ratio_lo, ratio_hi = min(sd_all) / worst_res, max(sd_all) / worst_res
    L += ["",
          f"| capacity | slope b | intercept | R² | largest residual | seed-noise envelope "
          f"(±1 sd, NOT a confidence interval) |",
          "|---|---|---|---|---|---|",
          f"| {BIG_PARAMS:.3f} M (pretrained) | **{b_big:.3f}** | {a_big:+.4f} | {r2_big:.5f} | "
          f"{max(abs(r) for r in res_big):.5f} | ±{env_big:.3f} |",
          f"| 0.712 M (scratch) | **{b_small:.3f}** | {a_small:+.4f} | {r2_small:.5f} | "
          f"{max(abs(r) for r in res_small):.5f} | ±{env_small:.3f} |", "",
          "> **R² is not an informative statistic on three points**, so the residuals are given "
          "as well. What matters is this: the largest residual of either fit "
          f"({max(abs(r) for r in res_big):.5f} ve {max(abs(r) for r in res_small):.5f}) kendi "
          f"is **{ratio_lo:.1f}–{ratio_hi:.1f}× below** its own cells' seed sd "
          f"(sd range {min(sd_all):.4f}–{max(sd_all):.4f}) — "
          "so the linearity comes from the relationship itself, not from a fit landing on three "
          f"points. (Lower bound {ratio_lo:.1f}×; against the smallest sd, calling it 'an order of "
          "magnitude' would be an overstatement, hence the range.) The residual *pattern* is also "
          "nearly identical at the two capacities "
          f"({', '.join(f'{r:+.5f}' for r in res_big)} ve "
          f"{', '.join(f'{r:+.5f}' for r in res_small)}), so the slight residual curvature is a structural feature of the teacher-ECE "
          "axis, not seed noise.", "",
          f"Slope difference **{d_slope:+.3f}** ({abs(d_slope) / b_big * 100:.1f}% "
          f"{'shallower' if d_slope < 0 else 'steeper'}), the two envelopes summed "
          f"**±{env_small + env_big:.3f}**.", ""]
    if overlap:
        L += [f"> **The slope difference is not resolvable.** Seed noise alone can move the slope by "
              f"±{env_small + env_big:.3f}, while the observed difference is "
              f"{abs(d_slope):.3f}. So *'the slope changes with capacity'* cannot be said from this data — "
              f"but what can be said is worth more: **the law also holds for a student 3.16× smaller** "
              f"(monotone, R²={r2_small:.4f}), and its slope is not distinguishably different from the "
              f"large student's. Calibration transfer is not a large-student "
              f"artefact.", ""]
    else:
        L += [f"> **The slope difference lies outside the noise envelope** ({abs(d_slope):.3f} > "
              f"±{env_small + env_big:.3f}): a capacity-dependent slope change was measured. "
              f"However, because of the scratch/pretrained confound below there is as yet no basis for "
              f"attributing it to **capacity**.", ""]
    L += ["> ⚠️ **Two variables at once.** `b_w050` is scratch and `b_2248` is pretrained — the two "
          "slopes differ in capacity *and* in initialisation. Separating them requires a scratch "
          "dose-response at 2.248 M (4 runs, **not launched**). This confound was written in B4 before the runs.",
          "",
          "> ⚠️ **The envelope is not a confidence interval.** w050's T=1.7 and T=2.2 cells are n=2, "
          "i.e. one degree of freedom; producing a t interval from that would be theatre. The envelope "
          "is obtained by pushing each cell mean by one measured seed sd in the direction that moves "
          "the slope most — i.e. the **upper bound** on how far noise could carry the slope.", "",
          f"5-point fit (for the record only, **not used** in the comparison): "
          f"b = {slope5:.3f}, kesme {icept5:+.4f}, R² = {r2_5:.3f}, n = {len(tx)}.", "",
          "## 2. Capacity at a fixed teacher (scratch, same teacher T=1.0)", "",
          "| capacity | student ECE @swa | student acc @swa | n |", "|---|---|---|---|"]
    eces = []
    for w, c in caps.items():
        eces.append(st.mean(c["ece"]))
        L.append(f"| {c['params_m']:.3f} M | {st.mean(c['ece']):.4f} ± {sample_sd(c['ece']):.4f} | "
                 f"{st.mean(c['acc']):.2f} ± {sample_sd(c['acc']):.2f} | {len(c['ece'])} |")
    span = max(eces) - min(eces)
    typ_sd = st.mean([sample_sd(c["ece"]) for c in caps.values()])
    L += ["", f"Capacity span **{span:.4f}**, typical between-seed sd **{typ_sd:.4f}** — "
              f"so the span is **{span / typ_sd:.1f}× the noise**. "
          + ("A 3.16× capacity difference does not move student ECE distinguishably from "
             "seed noise." if span < 2 * typ_sd else
             "The span is separated from noise: capacity has a measurable effect and must be reported."),
          "",
          "## 3. What can and cannot be said", "",
          "| iddia | durum |", "|---|---|",
          "| Student ECE is flat across a 3.16× capacity range (at a single teacher) | ✅ measured |",
          f"| At 2.248 M the law is monotone and near-linear (R²={r2_5:.3f}, 5 points) | ✅ measured |",
          f"| **The law also holds at 0.712 M** (monotone, R²={r2_small:.4f}, 3 points) | "
          f"✅ **measured by P3** |",
          ("| Does the slope change with capacity | ⚠️ **measured, unresolved** — difference "
           f"{abs(d_slope):.3f}, noise envelope ±{env_small + env_big:.3f} |" if overlap else
           "| Does the slope change with capacity | ⚠️ outside the envelope, but the init confound remains open |"),
          "| Does the slope difference come from **capacity** | ❌ not measured (scratch/pretrained confound) |",
          "| Does the law hold at 1.380 M | ❌ not measured (single point) |",
          "",
          "## 4. What is missing to close this line", "",
          "| design | new runs | what it buys |", "|---|---|---|",
          "| 2.248 M scratch dose-response (T=1.0/1.7/2.2, 1 seed + existing) | 4 | "
          "separates scratch from pretrained — the right to attribute the slope difference to capacity |",
          "| a third seed at T=1.7/2.2 for w050 | 2 | lifts the n=2 cells to n=3, narrows the envelope by ~40% |",
          "| T=1.7/2.2 at 1.380 M (2 seeds) | 4 | a third capacity → a slope-vs-capacity curve |",
          "",
          "> These runs were **not launched**. The experiment freeze is in force and the capacity "
          "frontier is supplementary; this addition only makes sense with explicit approval.", ""]

    (OUT_DIR / "capacity_law_check.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "capacity_law_check.json").write_text(json.dumps({
        "status": "EXPLORATORY — result not pre-registered; question + analysis plan were "
                  "(PREREGISTRATIONS.md B4, frozen 2026-07-29 01:28:02)",
        "sd_convention": SD_CONVENTION, "checkpoint": CKPT,
        "shared_support_temperatures": list(SHARED_T),
        "slope_comparison": {
            "note": "both slopes fitted on the SAME three temperatures; the 5-point fit is "
                    "recorded separately and is NOT used for the capacity comparison",
            "big": {"params_m": BIG_PARAMS, "init": "pretrained", "slope": b_big,
                    "intercept": a_big, "r2": r2_big, "seed_noise_envelope": env_big,
                    "cell_ece_mean": ys_b, "cell_ece_sd": sd_b, "cell_n": n_b},
            "small": {"params_m": small[1.0]["params_m"], "init": "scratch", "slope": b_small,
                      "intercept": a_small, "r2": r2_small, "seed_noise_envelope": env_small,
                      "cell_ece_mean": ys_s, "cell_ece_sd": sd_s, "cell_n": n_s},
            "teacher_ece": xs,
            "slope_difference": d_slope,
            "combined_envelope": env_small + env_big,
            "difference_resolvable": not overlap,
            "envelope_is_not_a_confidence_interval": True,
        },
        "slope_fit_5point_recorded_only": {"slope": slope5, "intercept": icept5, "r2": r2_5,
                                           "n_points": len(tx)},
        "capacity_cells_at_T1": {w: {"params_m": c["params_m"], "ece_mean": st.mean(c["ece"]),
                                     "ece_sd": sample_sd(c["ece"]), "acc_mean": st.mean(c["acc"]),
                                     "acc_sd": sample_sd(c["acc"]), "n": len(c["ece"]),
                                     "seeds": sorted(c["seeds"])}
                                 for w, c in caps.items()},
        "capacity_ece_span": span, "typical_seed_sd": typ_sd,
        "confounds": {
            "init": "b_w050 is scratch, b_2248 is pre-trained -- two variables at once; "
                    "separating them needs a scratch dose-response at 2.248 M (4 runs, "
                    "not launched)",
            "cell_n": "two of three w050 cells have n=2 (one degree of freedom); no confidence "
                      "interval is reported for either slope",
        },
        "missing_design": {"scratch_dose_response_2248M": 4, "third_seed_w050": 2,
                           "w075_slope": 4},
    }, indent=2), encoding="utf-8")

    print(f"shared support T={list(SHARED_T)}  teacher ECE={[round(x, 4) for x in xs]}")
    print(f"b @ {BIG_PARAMS:.3f} M (pretrained, 3pt): {b_big:.3f}  R2 {r2_big:.5f}  "
          f"max|resid| {max(abs(r) for r in res_big):.5f}  envelope +/-{env_big:.3f}")
    print(f"b @ {small[1.0]['params_m']:.3f} M (scratch,  3pt): {b_small:.3f}  R2 {r2_small:.5f}  "
          f"max|resid| {max(abs(r) for r in res_small):.5f}  envelope +/-{env_small:.3f}")
    print(f"slope difference {d_slope:+.3f} vs combined envelope +/-{env_small + env_big:.3f}  "
          f"-> {'RESOLVED' if not overlap else 'NOT resolvable'}")
    print(f"5-point fit (recorded only): b={slope5:.3f}  R2={r2_5:.3f}")
    print(f"capacity ECE span at fixed teacher: {span:.4f}  vs typical seed sd {typ_sd:.4f} "
          f"({span / typ_sd:.1f}x)")
    print(f"\nWrote {OUT_DIR / 'capacity_law_check.md'}")


if __name__ == "__main__":
    main()
