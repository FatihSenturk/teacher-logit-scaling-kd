"""Audit: could a non-RAF-DB student ever have been scored on RAF-DB's val set and had that
wrong ECE cached to its own calibration.json?

WHY THIS EXISTS. `build_runs_ledger.py` originally globbed everything under
results/unified_students, including students trained by `train_affectnetplus_kd.py` on FERPlus and
AffectNet+. Scoring one of those on RAF-DB fold-3 would produce a meaningless ECE AND write it to
that run's calibration.json, where it would look exactly like a legitimate cached value forever
after. The glob was fixed (`is_rafdb`), but a fix does not undo writes that already happened, so
the historical question has to be answered from the artifacts on disk, not from the current code.

THREE INDEPENDENT CHECKS, all machine-verified:

  1. LOCATION   -- does any non-RAF-DB run directory contain a calibration.json at all?
  2. FINGERPRINT-- every cache records n_val. RAF-DB fold-3 val is 3068; FERPlus val is 3153.
                   The sizes differ, so n_val identifies which dataset a cache was computed on.
                   A RAF-DB cache reading 3153 (or vice versa) is proof of cross-contamination.
  3. FEASIBILITY-- `student_from_run` builds the student via train_rafdb_kd.build_student, which
                   reads `student_feature_adapter_dim` from run_args.json. train_affectnetplus_kd.py
                   never writes that flag, so construction raises BEFORE any forward pass or write.
                   If no non-RAF-DB run carries the flag, poisoning was not merely absent -- it was
                   structurally impossible, which is the stronger claim and the one worth printing.

Read-only, zero GPU, no model construction. Outputs -> diagnostics/calibration_cache_audit.json
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

STUDENTS = ROOT / "results" / "unified_students"
OUT = ROOT / "diagnostics" / "calibration_cache_audit.json"

RAFDB_N_VAL = 3068          # fold-3 official test split
FERPLUS_N_VAL = 3153        # different size -> n_val is a discriminating fingerprint
REQUIRED_FLAG = "student_feature_adapter_dim"


def norm(ds):
    return str(ds).upper().replace("-", "").replace("_", "")


def scan():
    runs = []
    for rn in sorted(STUDENTS.iterdir()):
        if not rn.is_dir():
            continue
        for rd in sorted(rn.iterdir()):
            if not rd.is_dir():
                continue
            mb, ra, cj = rd / "metrics_best.json", rd / "run_args.json", rd / "calibration.json"
            ds = "UNFINISHED"
            if mb.exists():
                try:
                    ds = str(json.loads(mb.read_text()).get("dataset", "?"))
                except Exception:
                    ds = "UNREADABLE"
            cal = json.loads(cj.read_text()) if cj.exists() else None
            args = json.loads(ra.read_text()) if ra.exists() else {}
            runs.append({
                "run_name": rn.name,
                "timestamp": rd.name,
                "dataset": ds,
                "is_rafdb": norm(ds) == "RAFDB",
                "has_cache": cal is not None,
                "n_val": cal.get("n_val") if cal else None,
                "method": cal.get("method") if cal else None,
                "cache_mtime": (cj.stat().st_mtime if cj.exists() else None),
                "has_required_flag": REQUIRED_FLAG in args,
            })
    return runs


def main():
    runs = scan()
    finished = [r for r in runs if r["dataset"] not in ("UNFINISHED", "UNREADABLE")]
    nonraf = [r for r in finished if not r["is_rafdb"]]

    # 1. LOCATION
    misplaced = [r for r in nonraf if r["has_cache"]]

    # 2. FINGERPRINT
    wrong_n = [r for r in runs if r["has_cache"]
               and ((r["is_rafdb"] and r["n_val"] != RAFDB_N_VAL)
                    or (not r["is_rafdb"] and r["n_val"] == RAFDB_N_VAL))]

    # 3. FEASIBILITY
    could = [r for r in nonraf if r["has_required_flag"]]

    clean = not misplaced and not wrong_n and not could

    print(f"run directories scanned: {len(runs)}  "
          f"(finished {len(finished)}, unfinished {len(runs) - len(finished)})")
    print()
    print(f"{'dataset':<18}{'dirs':>6}{'with cache':>12}{'carries flag':>14}")
    for ds, n in sorted(Counter(r["dataset"] for r in runs).items()):
        sub = [r for r in runs if r["dataset"] == ds]
        print(f"{ds:<18}{n:>6}{sum(1 for r in sub if r['has_cache']):>12}"
              f"{sum(1 for r in sub if r['has_required_flag']):>14}")
    print()
    print(f"1. LOCATION    non-RAF-DB dirs carrying a calibration.json : {len(misplaced)}")
    for r in misplaced:
        print(f"     POISONED {r['dataset']:<14} {r['run_name']}  n_val={r['n_val']}")
    print(f"2. FINGERPRINT caches whose n_val contradicts their dataset: {len(wrong_n)}")
    for r in wrong_n:
        print(f"     MISMATCH {r['dataset']:<14} {r['run_name']}  n_val={r['n_val']}")
    print(f"3. FEASIBILITY non-RAF-DB runs that COULD have been scored : {len(could)}")
    for r in could:
        print(f"     AT RISK  {r['dataset']:<14} {r['run_name']}")
    print()
    if clean:
        print("VERDICT: NO calibration cache was poisoned, and none could have been --")
        print(f"         all {len(nonraf)} finished non-RAF-DB runs lack `{REQUIRED_FLAG}`, so")
        print("         build_student() raises before any forward pass or cache write.")
        print("         No T1-T10 row is affected. Nothing to recompute.")
    else:
        print("VERDICT: CONTAMINATION FOUND -- delete the listed caches and rebuild the ledger.")

    payload = {
        "verdict": "clean" if clean else "contaminated",
        "rafdb_n_val": RAFDB_N_VAL, "ferplus_n_val": FERPLUS_N_VAL,
        "required_flag": REQUIRED_FLAG,
        "dirs_scanned": len(runs), "finished": len(finished),
        "non_rafdb_finished": len(nonraf),
        "check_1_misplaced_caches": [r["run_name"] for r in misplaced],
        "check_2_n_val_mismatch": [r["run_name"] for r in wrong_n],
        "check_3_structurally_at_risk": [r["run_name"] for r in could],
        "distinct_methods": sorted({r["method"] for r in runs if r["method"]}),
        "distinct_n_val": sorted({r["n_val"] for r in runs if r["n_val"] is not None}),
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
