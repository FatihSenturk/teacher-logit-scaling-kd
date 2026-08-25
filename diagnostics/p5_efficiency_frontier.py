"""P5: teacher->student compression accounting, and an honest statement of what is NOT a frontier.

TWO FINDINGS ABOUT THE DATA ITSELF, both of which change what can be reported:

1. THE "FRONTIER" IS CURRENTLY A SINGLE POINT. Every student run in the campaign uses the
   identical architecture (2.248291 M params, 0.328584384 GMACs) -- verified across all runs by
   c4_efficiency_table.py, which finds exactly one distinct value of each. An efficiency FRONTIER
   requires varying capacity, so it cannot be plotted from the current run set. What CAN be
   reported honestly is the teacher->student COMPRESSION RATIO plus accuracy retention. A real
   frontier needs the deferred width-sweep (width_mult in {0.5, 0.75, 1.0}) and/or the
   vanilla_mnv2 control; this script prints exactly which runs are missing.

2. THE EXISTING LATENCY MEASUREMENTS ARE NOT COMPARABLE AND MUST NOT BE TABULATED. The three
   teacher latency CSVs measure the SAME architecture (58.34 M params, 8.4827 GMACs) and report
   249.8 / 89.2 / 47.5 ms -- a 5.3x spread. Identical FLOPs cannot produce a 5.3x latency spread;
   the spread is machine contention at measurement time (the campaign's KD queues were running).
   Latency therefore needs ONE re-measurement pass on an idle machine, all models back to back.
   This script refuses to emit a latency column until that exists.

Outputs -> diagnostics/p5_efficiency/
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))
from stats_convention import SD_CONVENTION  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "p5_efficiency"
OUT_DIR.mkdir(parents=True, exist_ok=True)
C4 = ROOT / "diagnostics" / "c4_efficiency_table"
_SV = json.loads((ROOT / "diagnostics" / "seed_variance" / "seed_variance_table.json").read_text())
# See the same note in p4_teacher_selection_recipe.py: the cells moved under "cells" when the
# sd-convention stamp was added on 2026-07-28. Both shapes load.
SEED_VAR = _SV.get("cells", _SV)

# Exact, contention-free structural numbers (params/FLOPs/size are deterministic).
TEACHER = {"name": "POSTERv2 (VAE head, VAE9182)", "params_m": 58.334272,
           "flops_g": 8.482723136, "size_mb": 555.0154619216919, "acc": 91.8187744458931}
STUDENT = {"name": "MobileNetV2Plus + VICH head", "params_m": 2.248291,
           "flops_g": 0.328584384, "size_mb": 8.82592487335205}


def latency_validity():
    """Cross-check the teacher latency measurements against their identical FLOPs."""
    rows = []
    for f in sorted(C4.glob("*latency*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            rows.append({"file": f.name, "model": r["Model"], "params_m": float(r["Params (M)"]),
                         "flops_g": float(r["FLOPs (G)"]), "latency_ms": float(r["Latency (ms)"])})
    teach = [r for r in rows if "Teacher" in r["model"]]
    lat = [r["latency_ms"] for r in teach]
    flops = {round(r["flops_g"], 6) for r in teach}
    spread = max(lat) / min(lat) if lat else float("nan")
    return {"teacher_rows": teach, "distinct_teacher_flops": sorted(flops),
            "latency_spread_ratio": spread,
            "comparable": spread < 1.25 or len(flops) > 1,
            "verdict": ("usable" if (spread < 1.25 or len(flops) > 1) else
                        f"NOT COMPARABLE: identical FLOPs {sorted(flops)} but {spread:.1f}x latency "
                        f"spread -> measurement contention, needs an idle-machine re-run")}


def frontier_coverage():
    """Which capacity points exist? A frontier needs >1."""
    seen = {}
    for run_name_dir in (ROOT / "results" / "unified_students").iterdir():
        if not run_name_dir.is_dir():
            continue
        for ts in run_name_dir.iterdir():
            mb, ra = ts / "metrics_best.json", ts / "run_args.json"
            if not (mb.exists() and ra.exists()):
                continue
            m, a = json.loads(mb.read_text()), json.loads(ra.read_text())
            key = (a.get("student_arch", "plus"), a.get("width_mult"), round(m.get("params_m", 0), 6))
            seen.setdefault(key, 0)
            seen[key] += 1
    return seen


def main():
    lat = latency_validity()
    cov = frontier_coverage()
    base = SEED_VAR["T-C baseline"]

    print("=== P5 step 1: teacher -> student compression (exact, deterministic) ===")
    pr = TEACHER["params_m"] / STUDENT["params_m"]
    fr = TEACHER["flops_g"] / STUDENT["flops_g"]
    sr = TEACHER["size_mb"] / STUDENT["size_mb"]
    print(f"  params : {TEACHER['params_m']:.3f} M -> {STUDENT['params_m']:.3f} M   = {pr:.1f}x smaller")
    print(f"  FLOPs  : {TEACHER['flops_g']:.4f} G -> {STUDENT['flops_g']:.4f} G   = {fr:.1f}x fewer")
    print(f"  size   : {TEACHER['size_mb']:.1f} MB -> {STUDENT['size_mb']:.2f} MB  = {sr:.1f}x smaller")
    print(f"  accuracy: teacher {TEACHER['acc']:.2f}% -> student {base['acc_mean']:.3f}"
          f" +/- {base['acc_sd']:.3f}% (n={base['n']})")
    print(f"            retention {100 * base['acc_mean'] / TEACHER['acc']:.2f}% "
          f"(gives up {TEACHER['acc'] - base['acc_mean']:.2f} pp for {fr:.1f}x fewer FLOPs)")

    print("\n=== P5 step 2: latency measurement validity ===")
    for r in lat["teacher_rows"]:
        print(f"  {r['file']:<38} {r['flops_g']:.4f} G  ->  {r['latency_ms']:7.1f} ms")
    print(f"  VERDICT: {lat['verdict']}")

    # Counting DISTINCT params values is not the right test: the head swap (vich vs linear)
    # changes params by ~0.4%, which technically yields >1 value while spanning no capacity
    # range at all. A frontier needs meaningful SPREAD, so require max/min >= MIN_SPREAD.
    MIN_SPREAD = 1.15
    all_params = [k[2] for k in cov]
    spread = max(all_params) / min(all_params)
    plottable = spread >= MIN_SPREAD

    print("\n=== P5 step 3: is there a frontier to plot? ===")
    print(f"  distinct student params values: {len(cov)}   "
          f"span {min(all_params):.6f}-{max(all_params):.6f} M = {spread:.3f}x "
          f"(need >= {MIN_SPREAD}x)")
    for (arch, wm, params), n in sorted(cov.items(), key=lambda kv: kv[0][2]):
        print(f"    arch={arch:<13} width_mult={wm}  params={params:.6f} M   ({n} run(s))")
    if not plottable:
        print(f"  => NOT a frontier: all points within {100 * (spread - 1):.1f}% of each other "
              f"(head-size differences, not capacity). Cannot plot an accuracy-vs-cost curve.")
        print("     Missing runs required to make it one:")
        print("       - vanilla_mnv2 control  (--student-arch vanilla_mnv2, isolates the Plus stack)")
        print("       - width sweep           (--width-mult 0.5 / 0.75, isolates capacity)")
        print("     Until then report the compression ratio above, NOT a frontier.")

    payload = {"compression": {"params_ratio": pr, "flops_ratio": fr, "size_ratio": sr,
                               "teacher": TEACHER, "student": STUDENT,
                               "student_acc_mean": base["acc_mean"], "student_acc_sd": base["acc_sd"],
                               "retention_pct": 100 * base["acc_mean"] / TEACHER["acc"]},
               "latency_validity": lat,
               "frontier_coverage": {f"{k[0]}|wm={k[1]}|params={k[2]}": v for k, v in cov.items()},
               "params_spread_ratio": spread, "min_spread_for_frontier": MIN_SPREAD,
               "is_frontier_plottable": plottable,
               "sd_convention": SD_CONVENTION}
    (OUT_DIR / "p5_efficiency.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'p5_efficiency.json'}")


if __name__ == "__main__":
    main()
