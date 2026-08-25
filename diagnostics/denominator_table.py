"""One denominator convention for every ratio in 5.4, and the table that fixes it.

THE PROBLEM. 5.4 currently quotes ratios against at least three different denominators without
saying so: the paired delta's own sd (the "0.82 pp" the text calls "the seed spread of its own
control", which it is not), the mean baseline seed sd pooled over the three teachers (what T5a's
3.2x / 22x / 6.9x are built on), and -- for the gate rows -- each teacher's own control arm sd.
Three conventions in one subsection is how "74x" survived long enough to reach the draft while
reproducing under none of them.

THE CONVENTION ADOPTED: **the treatment's own control ARM seed sd**, per teacher, at the SAME
class weighting the treatment ran under, @swa. Rationale:
  - It is a property of the control, not of the contrast, so it does not shrink when a mechanism
    happens to be reproducible, and it is the same yardstick the pre-registered P2/P5 decision
    rules use ("|d| >= 2x the control's seed sd").
  - It is defined for n=1 treatment rows, where a paired-delta sd does not exist at all. Half of
    T5's gate rows are n=1, so a paired-sd convention cannot cover the table it is meant to serve.
  - It is per teacher, so a teacher whose students are intrinsically noisier is not judged against
    another teacher's noise floor -- which matters here, because stage1/primary students sit at
    ECE 0.0745/0.0755 against VAE9182's 0.0278.

WHAT THIS SCRIPT EMITS: the full denominator table (acc sd AND ECE sd, per teacher, per class
weighting, with n), every T5 row re-expressed in those units, and an explicit consistency check
against the pooled denominator T5a currently uses -- so the two can be reconciled in the text
rather than silently coexisting.

Read-only, zero GPU. Outputs -> diagnostics/paper_tables/denominator_table.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from paper_tables import A_AUDIT_MECH, CKPTS, TEACHERS, is_ablation_control, load_audit, load_runs  # noqa: E402
from t5_pairing_diff import build  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
CK = "swa"


def control_arms(runs, audit, ck=CK):
    """(teacher, class_weight_mode) -> the control ARM's own seed spread on both axes."""
    arms = {}
    for key, r in runs.items():
        if r["teacher"] not in TEACHERS or not is_ablation_control(r):
            continue
        a = audit.get(key + (ck,))
        if not a:
            continue
        k = (r["teacher"], r["class_weight_mode"])
        arms.setdefault(k, {"acc": [], "ece": [], "seeds": []})
        arms[k]["acc"].append(a["acc"])
        arms[k]["ece"].append(a["ece"])
        arms[k]["seeds"].append(int(r["seed"]))
    out = {}
    for k, v in arms.items():
        if len(v["acc"]) < 2:
            continue
        out[k] = {"n": len(v["acc"]), "seeds": sorted(v["seeds"]),
                  "acc_mean": st.mean(v["acc"]), "acc_sd": sample_sd(v["acc"]),
                  "ece_mean": st.mean(v["ece"]), "ece_sd": sample_sd(v["ece"])}
    return out


def main():
    runs = load_runs()
    audit = load_audit(A_AUDIT_MECH)
    arms = control_arms(runs, audit)
    cells, _, _ = build(runs, audit, "new")

    L = ["# Denominator table — every ratio in 5.4 on one convention", "",
         f"Producer: `diagnostics/denominator_table.py` · @{CK} · {SD_CONVENTION}", "",
         "**Adopted convention: the seed sd of the treatment's OWN CONTROL ARM**, per teacher, in "
         "**the same class-weighting mode the treatment ran in**. Rationale: (a) it is a property "
         "of the control, not of the contrast — it does not shrink when a mechanism turns out to "
         "be reproducible; (b) it is the same auxiliary quantity the pre-registered P2/P5 decision "
         "rules use; (c) it is **defined even on n=1 rows** — half of T5's gate rows are n=1 and a "
         "paired sd does not exist there at all; (d) it is per teacher, so a teacher whose "
         "students are inherently noisy is not judged against someone else's noise floor.", "",
         "## Control arms (the denominators)", "",
         "| teacher | class weighting | acc mean ± **sd** | ECE mean ± **sd** | n | seeds |",
         "|---|---|---|---|---|---|"]
    for (t, cw), v in sorted(arms.items()):
        L.append(f"| {t} | `{cw}` | {v['acc_mean']:.3f} ± **{v['acc_sd']:.3f}** | "
                 f"{v['ece_mean']:.4f} ± **{v['ece_sd']:.4f}** | {v['n']} | {v['seeds']} |")

    L += ["", "> Gate rows take the `none` arm as denominator and every other mechanism takes the "
              "`effective_number` arm — because each treatment is differenced against the control "
              "in its own mode "
              "(`METHODS_DATA.md` §5A.2).", "",
          "## Every T5 row, in units of its own control arm's sd (@swa)", "",
          "| teacher | mechanism | cw | Δacc | acc sd | **Δacc / sd** | ΔECE | ECE sd | "
          "**ΔECE / sd** | n |", "|---|---|---|---|---|---|---|---|---|---|"]
    rows_json = {}
    for (t, mech), rec in sorted(cells.items()):
        c = rec["by_ckpt"].get(CK)
        cw = rec["class_weight_mode"]
        arm = arms.get((t, cw))
        if not c or not arm:
            continue
        ra = abs(c["d_acc_mean"]) / arm["acc_sd"] if arm["acc_sd"] else float("nan")
        re_ = abs(c["d_ece_mean"]) / arm["ece_sd"] if arm["ece_sd"] else float("nan")
        L.append(f"| {t} | {mech} | `{cw}` | {c['d_acc_mean']:+.3f} | {arm['acc_sd']:.3f} | "
                 f"**{ra:.2f}×** | {c['d_ece_mean']:+.4f} | {arm['ece_sd']:.4f} | "
                 f"**{re_:.1f}×** | {c['n']} |")
        rows_json[f"{t}/{mech}"] = {
            "class_weight_mode": cw, "n": c["n"],
            "d_acc_mean": c["d_acc_mean"], "d_ece_mean": c["d_ece_mean"],
            "control_acc_sd": arm["acc_sd"], "control_ece_sd": arm["ece_sd"],
            "d_acc_over_control_sd": ra, "d_ece_over_control_sd": re_}

    # --- reconcile with the pooled denominator T5a currently uses
    eff = [v for (t, cw), v in arms.items() if cw == "effective_number"]
    pooled_acc = st.mean([v["acc_sd"] for v in eff])
    pooled_ece = st.mean([v["ece_sd"] for v in eff])
    ls = {t: rows_json[f"{t}/logit_std"] for t in TEACHERS if f"{t}/logit_std" in rows_json}
    L += ["", "## Reconciliation with the pooled denominator T5a currently uses", "",
          "T5a currently uses the **mean** seed sd of the three teachers' `effective_number` "
          f"baseline cells (acc **{pooled_acc:.3f}** pp, ECE **{pooled_ece:.4f}**). The two "
          "conventions separate on the `logit_std` rows as follows:", "",
          "| teacher | ΔECE | pooled denominator | ratio | own arm's denominator | ratio |",
          "|---|---|---|---|---|---|"]
    for t, v in ls.items():
        L.append(f"| {t} | {v['d_ece_mean']:+.4f} | {pooled_ece:.4f} | "
                 f"{abs(v['d_ece_mean'])/pooled_ece:.0f}× | {v['control_ece_sd']:.4f} | "
                 f"**{v['d_ece_over_control_sd']:.0f}×** |")
    L += ["", "> **Which one the text uses.** The pooled denominator is appropriate for T5a's "
              "*across-teachers* claim (\"in all three teachers the calibration effect exceeds the "
              "accuracy effect in noise units\"), because that needs one common scale. **Any "
              "sentence about a single cell** must use that cell's own arm's denominator. Which "
              "denominator is in use has to be stated in the sentence — 5.4 as it currently stands "
              "does not state it, and that is exactly why \"74×\" does not hold under any "
              "convention.", "",
          "> **Number withdrawn:** \"its control's seed spread (0.82 pp)\". 0.818 pp is the "
          "**paired Δacc sd** of `vae9182/logit_std`; the same cell's control arm's own accuracy "
          f"seed sd is **{arms[('vae9182','effective_number')]['acc_sd']:.3f} pp**. The number was "
          "right, its label was wrong.", ""]

    (OUT_DIR / "denominator_table.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "denominator_table.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION, "checkpoint": CK,
        "convention": "each treatment is divided by ITS OWN control arm's seed sd, per teacher, "
                      "at the same class_weight_mode",
        "control_arms": {f"{t}/{cw}": v for (t, cw), v in sorted(arms.items())},
        "rows": rows_json,
        "pooled_denominator_used_by_T5a": {"acc_sd": pooled_acc, "ece_sd": pooled_ece,
                                           "over": "effective_number control arms, 3 teachers"},
    }, indent=2), encoding="utf-8")

    print(f"{'teacher':<9}{'cw':<18}{'acc sd':>9}{'ECE sd':>10}{'n':>4}  seeds")
    for (t, cw), v in sorted(arms.items()):
        print(f"{t:<9}{cw:<18}{v['acc_sd']:>9.3f}{v['ece_sd']:>10.4f}{v['n']:>4}  {v['seeds']}")
    print(f"\npooled (T5a): acc sd {pooled_acc:.3f} pp, ECE sd {pooled_ece:.4f}")
    print(f"\nlogit_std under the two conventions:")
    for t, v in ls.items():
        print(f"  {t:<9} dECE {v['d_ece_mean']:+.4f}  pooled {abs(v['d_ece_mean'])/pooled_ece:.0f}x"
              f"   own-arm {v['d_ece_over_control_sd']:.0f}x")
    print(f"\nWrote {OUT_DIR / 'denominator_table.md'}")


if __name__ == "__main__":
    main()
