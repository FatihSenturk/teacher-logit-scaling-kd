"""A2: measured cell-level diff of T5/T5a under the OLD vs the NEW control-pairing rule.

WHY A MEASUREMENT AND NOT AN ARGUMENT. The defect being audited is nondeterministic in principle:
before 2026-07-30, `controls[(teacher, seed)] = key` accepted any run passing
is_ablation_control(), and once P2 put a second legal control on disk (class_weight_mode=none
alongside effective_number) the surviving control for every VAE9182 cell was whichever the dict
happened to yield LAST. "Probably unaffected" is not a defensible answer for numbers that appear
in 5.4 and, downstream, in the abstract. So both rules are re-executed here over the same
artifacts and every T5/T5a cell is differenced.

  OLD rule: key = (teacher, seed)                -> ambiguous once two controls exist
  NEW rule: key = (teacher, seed, class_weight_mode)

The OLD rule is reproduced faithfully, including its overwrite semantics and the iteration order
that decided the winner (runs.csv row order, which is the order build_runs_ledger walked the
results directory). The point is not to rehabilitate the old rule but to show exactly which cells
it moved.

ALSO RE-ANCHORS THE THREE NOISE-UNIT RATIOS quoted in 5.4. The prose says the accuracy change is
"smaller than the seed spread of its own control (0.82 pp)" while the calibration change is "74
times that spread". Those two denominators are not the same statistic, and one of them is not the
control's spread at all, so every candidate denominator is computed and printed side by side
rather than assumed.

Read-only, zero GPU. Outputs -> diagnostics/paper_tables/t5_pairing_diff.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from paper_tables import (CKPTS, TEACHERS, A_AUDIT_MECH, gate_variant, is_ablation_control,  # noqa: E402
                          load_audit, load_runs)

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
LOGIT_STD_CELL = ("vae9182", "logit_std")


def is_treatment(r):
    """Same budget/alpha gate T5 applies, lifted verbatim so the two rules differ ONLY in the
    control key -- otherwise the diff would also absorb a filter change."""
    return (r["family"] == "mechanism_ablation" and r["student_head"] == "vich"
            and float(r["t_scale"] or 1) == 1.0 and r["epochs"] == "400"
            and str(r["swa_start"]) == "200"
            and abs(float(r["alpha"] or 0) - 0.3) < 1e-9)


def build(runs, audit, rule):
    """rule='old' -> (teacher, seed); rule='new' -> (teacher, seed, class_weight_mode)."""
    controls, treats, shadowed = {}, {}, []
    for key, r in runs.items():
        if r["teacher"] not in TEACHERS:
            continue
        if is_ablation_control(r):
            k = ((r["teacher"], r["seed"]) if rule == "old"
                 else (r["teacher"], r["seed"], r["class_weight_mode"]))
            if k in controls:
                # The old rule silently overwrote here. Record what it discarded.
                shadowed.append({"key": list(map(str, k)), "kept": key[0],
                                 "discarded": controls[k][0]})
            controls[k] = key
        elif is_treatment(r):
            mech = r["manipulation"]
            if mech == "gate":
                mech = gate_variant(r)
            tk = ((r["teacher"], mech) if rule == "old"
                  else (r["teacher"], mech, r["class_weight_mode"]))
            treats.setdefault(tk, {})[r["seed"]] = key

    cells = {}
    for tk, by_seed in treats.items():
        t, mech = tk[0], tk[1]
        cw = tk[2] if rule == "new" else None
        rec = {"teacher": t, "mechanism": mech, "class_weight_mode": cw, "by_ckpt": {}}
        for ck in CKPTS:
            d_acc, d_ece, ctrl_names, seeds = [], [], [], []
            for seed, tkey in sorted(by_seed.items()):
                ckey = ((t, seed) if rule == "old" else (t, seed, cw))
                if ckey not in controls:
                    continue
                a = audit.get(controls[ckey] + (ck,))
                b = audit.get(tkey + (ck,))
                if not a or not b:
                    continue
                d_acc.append(b["acc"] - a["acc"])
                d_ece.append(b["ece"] - a["ece"])
                ctrl_names.append(controls[ckey][0])
                seeds.append(seed)
            if not d_ece:
                continue
            rec["by_ckpt"][ck] = {
                "d_acc_mean": st.mean(d_acc), "d_acc_sd": sample_sd(d_acc),
                "d_ece_mean": st.mean(d_ece), "d_ece_sd": sample_sd(d_ece),
                "n": len(d_ece),
                "d_ece_signs": "".join("+" if v > 0 else "-" for v in d_ece),
                "controls_used": sorted(set(ctrl_names)),
                # TOHUM BAŞINA FARKLAR (14 Ağu, B5). Özet istatistikler bağımlılık
                # sorusunu cevaplayamaz: "paylaşılan kontrol bağımsızlık varsayımını
                # deliyor mu" ancak hücrelerin tohum-tohum vektörleri karşılaştırılarak
                # ölçülebilir. Ortalama ve sd o vektörden türer, tersi değil.
                "d_acc_list": list(d_acc), "d_ece_list": list(d_ece),
                "seeds": list(seeds),
            }
        if rec["by_ckpt"]:
            cells[(t, mech)] = rec
    return cells, shadowed, controls


def arm_seed_sd(runs, audit, teacher, cw, ck="swa"):
    """The control ARM's own seed spread -- distinct from the paired delta's spread."""
    accs, eces = [], []
    for key, r in runs.items():
        if (r["teacher"] == teacher and is_ablation_control(r)
                and (cw is None or r["class_weight_mode"] == cw)):
            a = audit.get(key + (ck,))
            if a:
                accs.append(a["acc"])
                eces.append(a["ece"])
    if len(accs) < 2:
        return None
    return {"n": len(accs), "acc_mean": st.mean(accs), "acc_sd": sample_sd(accs),
            "ece_mean": st.mean(eces), "ece_sd": sample_sd(eces)}


def main():
    runs = load_runs()
    audit = load_audit(A_AUDIT_MECH)
    old, shadowed, _ = build(runs, audit, "old")
    new, _, _ = build(runs, audit, "new")

    keys = sorted(set(old) | set(new))
    rows, unchanged = [], []
    for k in keys:
        o = old.get(k, {}).get("by_ckpt", {}).get("swa")
        n = new.get(k, {}).get("by_ckpt", {}).get("swa")
        label = f"{k[0]}/{k[1]}"
        if o and n:
            same = (abs(o["d_acc_mean"] - n["d_acc_mean"]) < 5e-4
                    and abs(o["d_ece_mean"] - n["d_ece_mean"]) < 5e-6
                    and o["n"] == n["n"])
            (unchanged if same else rows).append((label, o, n))
        else:
            rows.append((label, o, n))

    L = ["# A2 — Cell-level diff of the T5/T5a pairing-rule change", "",
         f"Producer: `diagnostics/t5_pairing_diff.py` · @swa · {SD_CONVENTION}", "",
         "Old rule `(teacher, seed)`, new rule `(teacher, seed, class_weight_mode)`. "
         "The treatment filter is byte-identical in both, so the difference below comes **from the "
         "control pairing alone**.", "",
         f"**{len(unchanged)} cells unchanged**, **{len(rows)} cells changed.**", ""]

    if shadowed:
        L += ["## Controls the old rule silently discarded", "",
              "On each row below the old rule saw two legal controls under the same key and "
              "**kept whichever came later** (the winner depended on `runs.csv` row order):", "",
              "| key (teacher, seed) | kept | discarded |", "|---|---|---|"]
        for s in shadowed:
            L.append(f"| {', '.join(s['key'])} | `{s['kept']}` | `{s['discarded']}` |")
        L.append("")

    L += ["## Cells that changed (@swa)", "",
          "| cell | Δacc old | Δacc new | diff | ΔECE old | ΔECE new | diff | n old→new | "
          "control used (new) |", "|---|---|---|---|---|---|---|---|---|"]
    for label, o, n in rows:
        def g(d, k, f):
            return "—" if not d else f"{d[k]:{f}}"
        dacc = ("—" if not (o and n) else f"{n['d_acc_mean'] - o['d_acc_mean']:+.3f}")
        dece = ("—" if not (o and n) else f"{n['d_ece_mean'] - o['d_ece_mean']:+.4f}")
        ctrl = ("dropped" if not n else ", ".join(f"`{c}`" for c in n["controls_used"]))
        L.append(f"| {label} | {g(o, 'd_acc_mean', '+.2f')} | {g(n, 'd_acc_mean', '+.2f')} | "
                 f"{dacc} | {g(o, 'd_ece_mean', '+.4f')} | {g(n, 'd_ece_mean', '+.4f')} | "
                 f"{dece} | {g(o, 'n', 'd')}→{g(n, 'n', 'd')} | {ctrl} |")
    L += ["", "## Cells that did not change", "",
          ", ".join(f"`{lab}`" for lab, _, _ in unchanged) + ".", "",
          "> All of these are `class_weight_mode=effective_number` treatments; the old rule kept the "
          "control appearing **last** in `runs.csv` order, and that happened to be the "
          "`effective_number` baseline (`baseline_noclassweight` sorts before "
          "`betaKD` alphabetically), so the result came out the same. **That was a coincidence, not a guarantee** — "
          "a change in run name would have changed the winner; the rule is now semantic.", ""]

    # ---- the three numbers 5.4 quotes, with every candidate denominator made explicit
    lk = LOGIT_STD_CELL
    o_ls = old.get(lk, {}).get("by_ckpt", {}).get("swa")
    n_ls = new.get(lk, {}).get("by_ckpt", {}).get("swa")
    eff = arm_seed_sd(runs, audit, "vae9182", "effective_number")
    non = arm_seed_sd(runs, audit, "vae9182", "none")
    L += ["## The numbers 5.4 quotes — re-anchored", "",
          f"`{lk[0]}/{lk[1]}` @swa, eski kural: Δacc **{o_ls['d_acc_mean']:+.2f} ± "
          f"{o_ls['d_acc_sd']:.2f}** pp, ΔECE **{o_ls['d_ece_mean']:+.4f} ± "
          f"{o_ls['d_ece_sd']:.4f}** (n={o_ls['n']})  ",
          f"same cell, new rule: Δacc **{n_ls['d_acc_mean']:+.2f} ± {n_ls['d_acc_sd']:.2f}** "
          f"pp, ΔECE **{n_ls['d_ece_mean']:+.4f} ± {n_ls['d_ece_sd']:.4f}** (n={n_ls['n']})", "",
          "**The two denominators in the text are not the same statistic.** On the accuracy side 5.4 says "
          "\"its control's seed spread (0.82 pp)\", but 0.82 pp is **not the control's spread; it is "
          "the sd of the paired Δacc**. Candidate denominators:", "",
          "| denominator | value | Δacc as a multiple | ΔECE as a multiple |",
          "|---|---|---|---|"]
    cands = [("paired Δacc sd (the 0.82 in the text)", n_ls["d_acc_sd"], "acc"),
             ("paired ΔECE sd", n_ls["d_ece_sd"], "ece")]
    if eff:
        cands += [("kontrol kolunun kendi acc tohum sd'si (`effective_number`)", eff["acc_sd"], "acc"),
                  ("kontrol kolunun kendi ECE tohum sd'si (`effective_number`)", eff["ece_sd"], "ece")]
    if non:
        cands += [("kontrol kolunun kendi ECE tohum sd'si (`none`)", non["ece_sd"], "ece")]
    for name, val, axis in cands:
        ra = f"{abs(n_ls['d_acc_mean']) / val:.1f}×" if axis == "acc" else "—"
        re_ = f"{abs(n_ls['d_ece_mean']) / val:.1f}×" if axis == "ece" else "—"
        L.append(f"| {name} | {val:.4f} | {ra} | {re_} |")
    L += ["", "> **The correct sentence for the text:** the accuracy change "
              f"({n_ls['d_acc_mean']:+.2f} pp) is smaller than its own paired sd "
              f"({n_ls['d_acc_sd']:.2f} pp) — statistically invisible; the calibration "
              f"change ({n_ls['d_ece_mean']:+.4f}) is this many times its own paired sd: "
              f"({n_ls['d_ece_sd']:.4f}) **{abs(n_ls['d_ece_mean']) / n_ls['d_ece_sd']:.0f} "
              f"**. If the control's own ECE seed sd is preferred instead, the ratio becomes "
              f"{abs(n_ls['d_ece_mean']) / eff['ece_sd']:.0f}×. **74× does not come out under "
              "any denominator** — that number must be updated.", ""]

    (OUT_DIR / "t5_pairing_diff.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "t5_pairing_diff.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION,
        "n_unchanged": len(unchanged), "n_changed": len(rows),
        "unchanged_cells": [lab for lab, _, _ in unchanged],
        "changed_cells": [{"cell": lab, "old": o, "new": n} for lab, o, n in rows],
        "shadowed_controls_under_old_rule": shadowed,
        "logit_std_vae9182": {"old": o_ls, "new": n_ls},
        "vae9182_control_arm_seed_sd": {"effective_number": eff, "none": non},
    }, indent=2), encoding="utf-8")

    print(f"unchanged cells: {len(unchanged)}   changed cells: {len(rows)}")
    for lab, o, n in rows:
        f = lambda d, k, fmt: "—" if not d else format(d[k], fmt)
        print(f"  {lab:<28} d_acc {f(o,'d_acc_mean','+.2f')} -> {f(n,'d_acc_mean','+.2f')}   "
              f"d_ece {f(o,'d_ece_mean','+.4f')} -> {f(n,'d_ece_mean','+.4f')}   "
              f"n {f(o,'n','d')} -> {f(n,'n','d')}")
    print(f"\nvae9182/logit_std @swa unchanged: "
          f"{abs(o_ls['d_acc_mean'] - n_ls['d_acc_mean']) < 5e-4 and abs(o_ls['d_ece_mean'] - n_ls['d_ece_mean']) < 5e-6}")
    print(f"  d_acc {n_ls['d_acc_mean']:+.3f} +/- {n_ls['d_acc_sd']:.3f} pp")
    print(f"  d_ece {n_ls['d_ece_mean']:+.4f} +/- {n_ls['d_ece_sd']:.4f}")
    print(f"  vae9182 control arm (effective_number): acc sd {eff['acc_sd']:.3f} pp, "
          f"ECE sd {eff['ece_sd']:.4f}, n={eff['n']}")
    print(f"  ratio d_ece / paired sd      = {abs(n_ls['d_ece_mean'])/n_ls['d_ece_sd']:.1f}x")
    print(f"  ratio d_ece / control ECE sd = {abs(n_ls['d_ece_mean'])/eff['ece_sd']:.1f}x")
    print(f"\nWrote {OUT_DIR / 't5_pairing_diff.md'}")


if __name__ == "__main__":
    main()
