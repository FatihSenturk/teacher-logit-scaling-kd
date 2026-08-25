"""A1: the selection-optimism number that appears in the ABSTRACT, recomputed and versioned.

WHY THIS SCRIPT EXISTS. The abstract and 5.10 both quote a single scalar -- "accuracy-selected
checkpoints are inflated by +0.78 pp over N runs". That number is a property of the SELECTION
PROCEDURE, not of any experimental condition, so it grows every time the campaign adds runs. A
number in an abstract cannot be left to a stale hand-transcription, and it cannot be quoted
without stating which run set and which checkpoint pair produced it.

THE COMPARISON IS best - last, NOT best - swa. Both are reported below because they answer
different questions and the abstract must not silently mix them:
    best - last : the full optimism of accuracy-based early stopping against a fixed-epoch rule.
                  Available for every run (n = all).
    best - swa  : optimism against the SWA average, which is itself a smoothing of the late
                  epochs and therefore a HARDER baseline to beat. Only runs with SWA have it.
The abstract's +0.78 pp is the best-last figure.

WHETHER THE 2026-07-29/31 RUNS BELONG IN IT. They do: the audit measures how much an
accuracy-selected checkpoint flatters itself, which is a property of the selection rule applied to
any run of this pipeline, not of the manipulation under test (Methods 4). Excluding them would make
the number depend on which experiments happened to be in flight. Both figures are printed so the
effect of including them is visible rather than asserted.

The "recent" set is P2 (5) + P3 (4) + P4 (6) = 15 runs, i.e. everything added after the 116-run
state the paper's current text quotes. NOTE that the P4 controls also match the
"baseline_noclassweight" marker, so they are correctly counted here -- an earlier version of this
docstring called the set "P2/P3, 9 runs", which stopped being true the moment P4 landed.

Read-only, zero GPU. Outputs -> diagnostics/selection_audit/selection_optimism_headline.json
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
OUT = ROOT / "diagnostics" / "selection_audit" / "selection_optimism_headline.json"

# The 15 runs P2, P3 and P4 added on 2026-07-29..31, identified by name so the split is
# auditable. P4's six controls match the "baseline_noclassweight" marker.
NEW_MARKERS = ("baseline_noclassweight", "frontier_w050_tempscale")
NEW_EXACT = ("RAFDB_vae9182_gate_oracle_error_b070_T6_224_400e_swa200_seed1",
             "RAFDB_vae9182_gate_oracle_error_b070_T6_224_400e_swa200_seed43")


def is_new(name):
    return any(m in name for m in NEW_MARKERS) or name in NEW_EXACT


def load():
    by_run = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        by_run.setdefault(r["run_name"], {})[r["checkpoint"]] = (float(r["acc"]), float(r["ece"]))
    return by_run


def stats(by_run, pair, include_new):
    a, b = pair
    d_acc, d_ece, used = [], [], []
    for name, cks in sorted(by_run.items()):
        if not include_new and is_new(name):
            continue
        if a not in cks or b not in cks:
            continue
        d_acc.append(cks[a][0] - cks[b][0])
        d_ece.append(cks[a][1] - cks[b][1])
        used.append(name)
    return {"n": len(d_acc),
            "d_acc_mean": st.mean(d_acc), "d_acc_sd": sample_sd(d_acc),
            "d_ece_mean": st.mean(d_ece), "d_ece_sd": sample_sd(d_ece),
            "d_acc_positive_share": sum(1 for v in d_acc if v > 0) / len(d_acc),
            "runs": used}


# The three inclusion sets this campaign actually passed through, keyed by the launch-timestamp
# boundary that produces each. Reported together because the useful claim is not any single N --
# it is that the estimate does not depend on which of them you pick.
STABILITY_SETS = [
    # Boundaries sit in the GAPS between campaigns, not on calendar midnights: P1's six logit_std
    # runs launched 01:24-09:47 on the 29th, so a midnight-of-the-29th cutoff would cut P1 in
    # half and report n=110 rather than the 116 this set actually held. Likewise P4's queue ran
    # past midnight, so its boundary is 06:00 on the 31st, not the 30th.
    ("2026-07-29-14-00-00", "before P2 (the set the paper's current text quotes)"),
    ("2026-07-30-06-00-00", "after P2+P3"),
    ("2026-07-31-06-00-00", "after P4 -- FROZEN, this is the number to quote"),
]


def load_timestamps():
    """run_name -> launch timestamp, from the ledger (which takes it from the run directory)."""
    out = {}
    for r in csv.DictReader(open(ROOT / "runs.csv", encoding="utf-8")):
        out[r["run_name"]] = r["timestamp"]
    return out


def stability_series(by_run):
    ts = load_timestamps()
    rows = []
    for cutoff, label in STABILITY_SETS:
        d_acc = [cks["best"][0] - cks["last"][0] for n, cks in by_run.items()
                 if "best" in cks and "last" in cks and ts.get(n, "") <= cutoff]
        rows.append({"cutoff": cutoff, "label": label, "n": len(d_acc),
                     "d_acc_mean": st.mean(d_acc), "d_acc_sd": sample_sd(d_acc)})
    span = max(r["d_acc_mean"] for r in rows) - min(r["d_acc_mean"] for r in rows)
    return rows, span


def main():
    by_run = load()
    if any(not n.startswith("RAFDB") for n in by_run):
        raise RuntimeError("the audit contains non-RAF-DB runs; the abstract says 'RAF-DB runs' "
                           "and the scope claim would be false.")

    out = {"sd_convention": SD_CONVENTION,
           "scope": "RAF-DB student runs only (the audit evaluates the RAF-DB fold-3 val split, "
                    "so no other dataset can enter it)",
           "abstract_figure": "best - last, d_acc_mean +/- d_acc_sd",
           "variants": {}}
    for pair in (("best", "last"), ("best", "swa")):
        for inc in (True, False):
            key = f"{pair[0]}-{pair[1]}/{'with' if inc else 'without'}_recent"
            s = stats(by_run, pair, inc)
            s.pop("runs")
            out["variants"][key] = s

    w = out["variants"]["best-last/with_recent"]
    wo = out["variants"]["best-last/without_recent"]
    out["headline"] = {
        "n": w["n"], "d_acc_mean": w["d_acc_mean"], "d_acc_sd": w["d_acc_sd"],
        "d_ece_mean": w["d_ece_mean"], "d_ece_sd": w["d_ece_sd"],
        "previous_n": wo["n"], "previous_d_acc_mean": wo["d_acc_mean"],
        "shift_from_adding_recent_pp": w["d_acc_mean"] - wo["d_acc_mean"],
    }
    series, span = stability_series(by_run)
    out["stability_across_inclusion_sets"] = {
        "note": "the audit's inclusion set was frozen at the last entry; these are the three sets "
                "the campaign passed through, and the estimate is stable across all of them",
        "series": series, "span_pp": span,
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"scope: RAF-DB only, {len(by_run)} runs in the audit "
          f"({sum(1 for n in by_run if is_new(n))} of them added since the 116-run state)\n")
    print(f"{'comparison':<14}{'run set':<16}{'n':>5}{'d_acc (pp)':>18}{'d_ECE':>20}"
          f"{'d_acc > 0':>11}")
    for k, s in out["variants"].items():
        pair, inc = k.split("/")
        print(f"{pair:<14}{('with recent' if inc.startswith('with_') else 'without recent'):<16}"
              f"{s['n']:>5}{f'{s[chr(100)+chr(95)+chr(97)+chr(99)+chr(99)+chr(95)+chr(109)+chr(101)+chr(97)+chr(110)]:+.3f} +/- {s['d_acc_sd']:.3f}':>18}"
              f"{f'{s['d_ece_mean']:+.4f} +/- {s['d_ece_sd']:.4f}':>20}"
              f"{s['d_acc_positive_share'] * 100:>10.0f}%")
    h = out["headline"]
    print(f"\nABSTRACT: 'an audit of {h['n']} runs ... inflated by "
          f"{h['d_acc_mean']:+.2f} +/- {h['d_acc_sd']:.2f} pp'")
    print(f"  was     : {h['previous_n']} runs, {h['previous_d_acc_mean']:+.2f} pp")
    print(f"  shift from adding the {h['n'] - h['previous_n']} runs since: "
          f"{h['shift_from_adding_recent_pp']:+.3f} pp")
    print(f"\n--- stability across the three inclusion sets the campaign passed through ---")
    for r in series:
        print(f"  n={r['n']:<5} {r['d_acc_mean']:+.3f} +/- {r['d_acc_sd']:.3f} pp   {r['label']}")
    print(f"  span across all three: {span:.3f} pp")
    print(f"  -> one line for the text: "
          + " / ".join(f"n={r['n']}: {r['d_acc_mean']:+.3f}" for r in series)
          + f" pp (span {span:.3f} pp)")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
