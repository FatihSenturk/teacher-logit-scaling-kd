"""B1-B4: the complete number set needed to rewrite 5.4 (mechanism ablations) after P2.

5.4 currently claims ECE-axis NEUTRALITY for gating ("None does", "Uncertainty gating is null at
the SWA checkpoint on every teacher"). P2 falsified that on the calibration axis, so the
subsection is being rewritten and every number it will contain is emitted here, from artifacts,
at full precision -- so nothing is hand-transcribed twice.

  B1  gate variants vs the class-weighting-MATCHED control: per teacher x variant, mean +/-
      sample sd on both axes, per-seed sign pattern, n, and the per-seed values themselves.
  B2  the cancellation arithmetic: class weighting's effect on the CONTROL's own ECE, gate's
      harm against the clean control, and the old contaminated diff -- all at one precision,
      each labelled with the arm and teacher it belongs to, plus the identity check that the
      three are consistent.
  B3  T5's new skeleton: which rows stand on 3 matched seeds, which are single-seed, which were
      dropped for having no control at their own class weighting.
  B4  the same gate runs against the contaminated control, in full, since that number goes into
      the text as the evidence that control hygiene changed the result.

Read-only, zero GPU. Outputs -> diagnostics/paper_tables/section54_numbers.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from paper_tables import (A_AUDIT_MECH, CKPTS, TEACHERS, gate_variant, is_ablation_control,  # noqa: E402
                          load_audit, load_runs)
from t5_pairing_diff import build, is_treatment  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
SEEDS = (42, 1, 43)
CK = "swa"


def signs(v):
    return "".join("+" if x > 0 else "-" for x in v)


def per_seed_delta(runs, audit, treat_pred, control_pred, ck=CK):
    """Paired (treatment - control) per seed, both arms selected by predicate on the ledger row."""
    tre = {int(r["seed"]): k for k, r in runs.items() if treat_pred(r)}
    con = {int(r["seed"]): k for k, r in runs.items() if control_pred(r)}
    out = {}
    for s in SEEDS:
        if s not in tre or s not in con:
            continue
        a, b = audit.get(con[s] + (ck,)), audit.get(tre[s] + (ck,))
        if not a or not b:
            continue
        out[s] = {"d_acc": b["acc"] - a["acc"], "d_ece": b["ece"] - a["ece"],
                  "treat_run": tre[s][0], "control_run": con[s][0]}
    return out


def summarise(per):
    da = [v["d_acc"] for v in per.values()]
    de = [v["d_ece"] for v in per.values()]
    return {"n": len(da), "d_acc_mean": st.mean(da), "d_acc_sd": sample_sd(da),
            "d_ece_mean": st.mean(de), "d_ece_sd": sample_sd(de),
            "d_acc_signs": signs(da), "d_ece_signs": signs(de),
            "per_seed": {str(k): v for k, v in sorted(per.items())}}


def ctrl_pred(teacher, cw):
    return lambda r: (r["teacher"] == teacher and is_ablation_control(r)
                      and r["class_weight_mode"] == cw)


def gate_pred(teacher, src):
    return lambda r: (r["teacher"] == teacher and is_treatment(r)
                      and r["manipulation"] == "gate"
                      and gate_variant(r) == f"gate:{src}")


def main():
    runs = load_runs()
    audit = load_audit(A_AUDIT_MECH)
    new, _, controls_new = build(runs, audit, "new")

    # ---------- B1
    b1 = {}
    for (t, mech), rec in sorted(new.items()):
        if not mech.startswith("gate:"):
            continue
        src = mech.split(":", 1)[1]
        per = per_seed_delta(runs, audit, gate_pred(t, src), ctrl_pred(t, "none"))
        if per:
            b1[f"{t}/{mech}"] = summarise(per)

    # ---------- B2 (all VAE9182, where both controls exist at the same 3 seeds)
    cw_effect = summarise(per_seed_delta(
        runs, audit, ctrl_pred("vae9182", "none"), ctrl_pred("vae9182", "effective_number")))
    gate_clean = b1["vae9182/gate:oracle_error"]
    gate_dirty = summarise(per_seed_delta(
        runs, audit, gate_pred("vae9182", "oracle_error"),
        ctrl_pred("vae9182", "effective_number")))
    # identity: (gate - dirty_control) == (gate - clean_control) + (clean_control - dirty_control)
    resid = gate_dirty["d_ece_mean"] - (gate_clean["d_ece_mean"] + cw_effect["d_ece_mean"])
    if abs(resid) > 1e-9:
        raise RuntimeError(f"cancellation identity does not close (residual {resid:.2e}); one of "
                           f"the three deltas is not the paired quantity it claims to be.")

    # ---------- B3
    three, single, dropped = [], [], []
    for (t, mech), rec in sorted(new.items()):
        c = rec["by_ckpt"].get(CK)
        (three if c and c["n"] >= 3 else single).append(f"{t}/{mech}")
    for key, r in runs.items():
        if not is_treatment(r) or r["manipulation"] != "gate" or r["teacher"] not in TEACHERS:
            continue
        if (r["teacher"], int(r["seed"]), r["class_weight_mode"]) not in {
                (k[0], int(k[1]), k[2]) for k in controls_new}:
            dropped.append(f"{r['teacher']}/{gate_variant(r)} seed{r['seed']} "
                           f"(cw={r['class_weight_mode']})")

    L = ["# Number set for the 5.4 rewrite (B1–B4)", "",
         f"Producer: `diagnostics/section54_numbers.py` · @{CK} · {SD_CONVENTION} · "
         f"treatment−control, paired within seed", "",
         "## B1 — Gate variants against a class-weighting-matched control", "",
         "| teacher / variant | Δacc (pp) | acc signs | ΔECE | ECE signs | n |",
         "|---|---|---|---|---|---|"]
    for k, s in b1.items():
        acc = (f"{s['d_acc_mean']:+.3f} ± {s['d_acc_sd']:.3f}" if s["n"] > 1
               else f"{s['d_acc_mean']:+.3f} *(n=1)*")
        ece = (f"{s['d_ece_mean']:+.4f} ± {s['d_ece_sd']:.4f}" if s["n"] > 1
               else f"{s['d_ece_mean']:+.4f} *(n=1)*")
        L.append(f"| {k} | {acc} | `{s['d_acc_signs']}` | {ece} | `{s['d_ece_signs']}` | {s['n']} |")
    L += ["", "Per seed (`gate:oracle_error`, the only n=3 arm):", "",
          "| tohum | Δacc (pp) | ΔECE |", "|---|---|---|"]
    for s, v in gate_clean["per_seed"].items():
        L.append(f"| {s} | {v['d_acc']:+.3f} | {v['d_ece']:+.4f} |")
    L += ["", "> Only VAE9182's gate rows appear here: the `class_weight_mode=none` control "
              "exists for that teacher alone (see B3 and `PREREGISTRATIONS.md` A8).", "",
          "## B2 — The cancellation arithmetic (all VAE9182, same three seeds, @swa)", "",
          "| # | quantity | arm pair | ΔECE | signs | n |", "|---|---|---|---|---|---|",
          f"| (i) | effect of class weighting on the **control's own** ECE | "
          f"baseline `none` − baseline `effective_number` | **{cw_effect['d_ece_mean']:+.4f} ± "
          f"{cw_effect['d_ece_sd']:.4f}** | `{cw_effect['d_ece_signs']}` | {cw_effect['n']} |",
          f"| (ii) | the gate's **real** damage | `gate:oracle_error` − baseline `none` | "
          f"**{gate_clean['d_ece_mean']:+.4f} ± {gate_clean['d_ece_sd']:.4f}** | "
          f"`{gate_clean['d_ece_signs']}` | {gate_clean['n']} |",
          f"| (iii) | the diff reported before P2 | `gate:oracle_error` − baseline "
          f"`effective_number` | **{gate_dirty['d_ece_mean']:+.4f} ± "
          f"{gate_dirty['d_ece_sd']:.4f}** | `{gate_dirty['d_ece_signs']}` | {gate_dirty['n']} |",
          "",
          f"**The identity closes exactly:** (ii) + (i) = {gate_clean['d_ece_mean']:+.4f} "
          f"{'+' if cw_effect['d_ece_mean'] >= 0 else '−'} "
          f"{abs(cw_effect['d_ece_mean']):.4f} = {gate_dirty['d_ece_mean']:+.4f} = (iii), "
          f"residual {resid:.1e}.", "",
          "> **This is the sentence for the text.** Two independent errors were almost exactly "
          f"cancelling each other: class weighting **worsens** the control's ECE by "
          f"{abs(cw_effect['d_ece_mean']):.4f}, while the gate worsens the student's ECE by "
          f"{gate_clean['d_ece_mean']:.4f}. When the two meet in one difference, what remains is "
          f"{gate_dirty['d_ece_mean']:+.4f} — indistinguishable from zero, and the three seeds' "
          f"signs are mixed, `{gate_dirty['d_ece_signs']}`. Control hygiene here was therefore "
          "not a gesture of rigour but the result itself.", "",
          "## B3 — T5'in yeni iskeleti", "",
          f"**Rows standing on three paired seeds ({len(three)}):**", "",
          ", ".join(f"`{x}`" for x in three) + ".", "",
          f"**Tek tohum † ({len(single)}):**", "",
          ", ".join(f"`{x}`" for x in single) + ".", "",
          f"**Rows dropped for lack of a control ({len(dropped)}):**", "",
          ", ".join(f"`{x}`" for x in sorted(dropped)) + ".", "",
          "> All four dropped rows are `class_weight_mode=none` gate runs; stage1 and primary have no "
          "baseline in that mode. Differencing against the other mode's control would restore the "
          "two-variable situation P2 removed. Completing it costs 2 teachers × 3 seeds = 6 runs.", "",
          "## B4 — The same runs against the contaminated control (as it will appear in the text)", "",
          "| tohum | Δacc (pp) | ΔECE |", "|---|---|---|"]
    for s, v in gate_dirty["per_seed"].items():
        L.append(f"| {s} | {v['d_acc']:+.3f} | {v['d_ece']:+.4f} |")
    L += [f"| **ortalama** | **{gate_dirty['d_acc_mean']:+.3f} ± {gate_dirty['d_acc_sd']:.3f}** | "
          f"**{gate_dirty['d_ece_mean']:+.4f} ± {gate_dirty['d_ece_sd']:.4f}** |",
          f"| signs | `{gate_dirty['d_acc_signs']}` | `{gate_dirty['d_ece_signs']}` |", "",
          f"For comparison, the same runs against the clean control: Δacc "
          f"**{gate_clean['d_acc_mean']:+.3f} ± {gate_clean['d_acc_sd']:.3f}** pp "
          f"`{gate_clean['d_acc_signs']}`, ΔECE **{gate_clean['d_ece_mean']:+.4f} ± "
          f"{gate_clean['d_ece_sd']:.4f}** `{gate_clean['d_ece_signs']}`.", "",
          "> **Wordings that can no longer be written:** \"None does\", \"gating is null at the SWA "
          "checkpoint on every teacher\", and any sentence calling the gate \"neutral / no effect\". "
          "The correct statement: **even with a perfect signal it degrades calibration consistently across three seeds.**",
          ""]

    (OUT_DIR / "section54_numbers.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "section54_numbers.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION, "checkpoint": CK,
        "B1_gate_vs_matched_control": b1,
        "B2_cancellation": {"i_class_weighting_on_control": cw_effect,
                            "ii_gate_vs_clean_control": gate_clean,
                            "iii_gate_vs_contaminated_control": gate_dirty,
                            "identity_residual": resid},
        "B3_skeleton": {"three_seeds": three, "single_seed": single, "dropped_no_control": sorted(dropped)},
    }, indent=2), encoding="utf-8")

    print("B1 gate variants vs matched control:")
    for k, s in b1.items():
        print(f"  {k:<30} d_acc {s['d_acc_mean']:+.3f} [{s['d_acc_signs']}]   "
              f"d_ece {s['d_ece_mean']:+.4f} [{s['d_ece_signs']}]   n={s['n']}")
    print(f"\nB2 cancellation (vae9182, n=3, @swa):")
    print(f"  (i)   class weighting on control ECE : {cw_effect['d_ece_mean']:+.4f} +/- "
          f"{cw_effect['d_ece_sd']:.4f} [{cw_effect['d_ece_signs']}]")
    print(f"  (ii)  gate vs CLEAN control         : {gate_clean['d_ece_mean']:+.4f} +/- "
          f"{gate_clean['d_ece_sd']:.4f} [{gate_clean['d_ece_signs']}]")
    print(f"  (iii) gate vs CONTAMINATED control  : {gate_dirty['d_ece_mean']:+.4f} +/- "
          f"{gate_dirty['d_ece_sd']:.4f} [{gate_dirty['d_ece_signs']}]")
    print(f"  identity residual: {resid:.1e}")
    print(f"\nB3 skeleton: {len(three)} rows at n=3, {len(single)} single-seed, "
          f"{len(dropped)} dropped")
    print(f"\nWrote {OUT_DIR / 'section54_numbers.md'}")


if __name__ == "__main__":
    main()
