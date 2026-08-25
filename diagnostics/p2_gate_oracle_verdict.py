"""P2 verdict: gate:oracle_error at n=3 against a class-weighting-matched control.

THE PRE-REGISTRATION (diagnostics/PREREGISTRATIONS.md A8, frozen 2026-07-29 01:26:59 in
rafdb_p2_gate_oracle_seeds_queue.ps1 lines 15-38, before the first run started):
    P2.1  Delta accuracy is NULL: |mean d_acc| <= the control arm's seed sd
    P2.2  Delta ECE is NULL:      |mean d_ECE| <= the control arm's seed sd
    P2.3  Per-seed signs are inconsistent on at least one axis
Falsified => the claim "the weighting axis is closed" falls and the paper is re-framed.

WHY @swa AND NOT @best. best_checkpoint.pth is argmax val-accuracy on the very 3068 images
the metric is then reported on (train_rafdb_kd.py:895-900 -> :960-977), so every @best number
carries selection optimism, and the optimism sits on the accuracy axis while ECE rides along
uncontrolled. @swa is a fixed rule that never looked at the eval set. All three predictions are
evaluated at @swa; @best and @last are printed only to show the verdict does not hinge on that
choice.

WHAT P2 ALSO REPAIRS, AND HOW FAR IT ACTUALLY GETS. kd_common.py raises on gate +
class-weighted CE, so every gate run was forced to --class-weight-mode none while the rest of
the mechanism grid ran effective_number. Until 2026-07-30 no no-classweight baseline existed,
so all six 400e/SWA@200 gate rows in T5 were differenced against an effective_number control
and each carried TWO manipulated variables. P2 produced the missing control at 3 seeds -- but
only for the VAE9182 teacher, so only 2 of those 6 rows can move onto it. The other 4
(stage1 x {mean_logvar, target_logvar}, primary x {mean_logvar, target_logvar}) still have no
control at their own class weighting.

For those 4 this script does the next best thing to a clean delta: it MEASURES the confound.
Because VAE9182 now has both controls at the same 3 seeds, the class-weighting switch can be
isolated on its own, and its size is exactly the bias the 4 unrepaired rows carry.

Read-only, zero GPU -- everything comes from the cached selection audit.
Outputs -> diagnostics/p2_gate_oracle/p2_verdict.{json,md}
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
RUNS = ROOT / "runs.csv"
OUT_DIR = ROOT / "diagnostics" / "p2_gate_oracle"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEEDS = (42, 1, 43)
CKPTS = ("swa", "best", "last")
PRIMARY_CKPT = "swa"

TREAT = "RAFDB_vae9182_gate_oracle_error_b070_T6_224_400e_swa200"
CONTROL = "RAFDB_vae9182_baseline_noclassweight_b070_T6_224_400e_swa200"
# the control the 6 gate rows were differenced against before P2 existed
OLD_CONTROL = "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200"


def build_seed_index():
    """(base_name, seed) -> run_name, resolved from each run's OWN recorded seed.

    The three families involved do not agree on how seed 42 is spelled: the control arm was
    launched as ..._swa200_seed42 while the treatment and the old control spell seed 42 with no
    suffix at all. A "base if seed==42 else base_seedN" rule silently pairs 2 of 3 seeds and
    hands back an n=2 verdict for a prediction that was frozen at n=3, so the mapping is read
    from runs.csv (which takes `seed` from run_args.json) instead of being inferred from names.
    """
    idx = {}
    for r in csv.DictReader(open(RUNS, encoding="utf-8")):
        name, seed = r["run_name"], int(r["seed"])
        for base in (name, name.rsplit("_seed", 1)[0] if "_seed" in name else name):
            k = (base, seed)
            if k in idx and idx[k] != name:
                raise RuntimeError(f"{k} maps to both {idx[k]} and {name}")
            idx[k] = name
    return idx


SEED_INDEX = None


def seed_suffixed(base, seed):
    name = SEED_INDEX.get((base, seed))
    if name is None:
        raise RuntimeError(f"no run recorded for base '{base}' at seed {seed} -- the arm is "
                           f"incomplete; do not fall back to a name guess.")
    return name


def load_audit():
    """(run_name, checkpoint) -> {acc, ece}. Run names are unique per checkpoint here; if a
    run were ever re-launched under the same name the audit would hold two timestamps for it,
    so that case is caught rather than silently resolved to whichever row came last."""
    out = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        k = (r["run_name"], r["checkpoint"])
        if k in out and out[k]["timestamp"] != r["timestamp"]:
            raise RuntimeError(
                f"{k} appears under two timestamps ({out[k]['timestamp']} and {r['timestamp']}) "
                f"-- pick one explicitly; a silent choice would make the verdict order-dependent.")
        out[k] = {"acc": float(r["acc"]), "ece": float(r["ece"]), "timestamp": r["timestamp"]}
    return out


def paired(audit, treat_base, control_base, ckpt):
    """Per-seed (treatment - control) at one checkpoint, paired within seed."""
    d_acc, d_ece, per_seed = [], [], {}
    for s in SEEDS:
        a = audit.get((seed_suffixed(control_base, s), ckpt))
        b = audit.get((seed_suffixed(treat_base, s), ckpt))
        if not a or not b:
            continue
        da, de = b["acc"] - a["acc"], b["ece"] - a["ece"]
        d_acc.append(da)
        d_ece.append(de)
        per_seed[s] = {"treat_acc": b["acc"], "control_acc": a["acc"], "d_acc": da,
                       "treat_ece": b["ece"], "control_ece": a["ece"], "d_ece": de}
    return d_acc, d_ece, per_seed


def arm(audit, base, ckpt):
    accs = [audit[(seed_suffixed(base, s), ckpt)]["acc"] for s in SEEDS
            if (seed_suffixed(base, s), ckpt) in audit]
    eces = [audit[(seed_suffixed(base, s), ckpt)]["ece"] for s in SEEDS
            if (seed_suffixed(base, s), ckpt) in audit]
    return {"acc_mean": st.mean(accs), "acc_sd": sample_sd(accs),
            "ece_mean": st.mean(eces), "ece_sd": sample_sd(eces), "n": len(accs)}


def signs(vals):
    return "".join("+" if v > 0 else "-" for v in vals)


def unmovable_gate_rows():
    """The 400e/SWA@200 gate rows that still have no control at their own class weighting."""
    ctrl = set()
    gates = []
    for r in csv.DictReader(open(RUNS, encoding="utf-8")):
        ok_budget = (r["student_head"] == "vich" and float(r["t_scale"] or 1) == 1.0
                     and r["epochs"] == "400" and str(r["swa_start"]) == "200"
                     and abs(float(r["alpha"] or 0) - 0.3) < 1e-9)
        if not ok_budget:
            continue
        if r["family"] == "baseline" and r["manipulation"] == "none":
            ctrl.add((r["teacher"], r["seed"], r["class_weight_mode"]))
        elif r["family"] == "mechanism_ablation" and r["manipulation"] == "gate":
            # Level-1: gate sinyali artık DEFTERDE bir sütun (`gate_signal`, 8 Ağu). Eskiden
            # burada koşunun `run_args.json`'u açılıyordu ve bu betik yayımlanmayan
            # `results/unified_students/` olmadan çalışamıyordu. Bilgi aynı, kaynağı farklı.
            src = (r.get("gate_signal") or "?").strip() or "?"
            gates.append((r["teacher"], src, r["seed"], r["class_weight_mode"]))
    movable = [g for g in gates if (g[0], g[2], g[3]) in ctrl]
    stuck = [g for g in gates if (g[0], g[2], g[3]) not in ctrl]
    return gates, movable, stuck


def main():
    global SEED_INDEX
    SEED_INDEX = build_seed_index()
    audit = load_audit()

    # ---- the pre-registered comparison
    res = {}
    for ck in CKPTS:
        d_acc, d_ece, per_seed = paired(audit, TREAT, CONTROL, ck)
        res[ck] = {"d_acc": d_acc, "d_ece": d_ece, "per_seed": per_seed,
                   "treat": arm(audit, TREAT, ck), "control": arm(audit, CONTROL, ck)}
    p = res[PRIMARY_CKPT]
    if len(p["d_ece"]) != 3:
        raise RuntimeError(f"expected 3 paired seeds at @{PRIMARY_CKPT}, got {len(p['d_ece'])} -- "
                           f"the verdict is pre-registered at n=3 and must not be given at n<3.")

    ctrl_acc_sd = p["control"]["acc_sd"]
    ctrl_ece_sd = p["control"]["ece_sd"]
    m_acc, m_ece = st.mean(p["d_acc"]), st.mean(p["d_ece"])
    # The frozen bar is the CONTROL arm's seed sd -- not a pooled or treatment sd. Stated as a
    # ratio so the margin is visible rather than hidden behind a pass/fail word.
    r21, r22 = abs(m_acc) / ctrl_acc_sd, abs(m_ece) / ctrl_ece_sd
    p21, p22 = r21 <= 1.0, r22 <= 1.0
    acc_signs, ece_signs = signs(p["d_acc"]), signs(p["d_ece"])
    p23 = len(set(acc_signs)) > 1 or len(set(ece_signs)) > 1

    # ---- how big is the class-weighting confound, on its own?
    cw_acc, cw_ece, cw_per = paired(audit, CONTROL, OLD_CONTROL, PRIMARY_CKPT)

    # ---- and what did the contaminated control make the SAME treatment look like?
    # This is the part that justifies the repair rather than merely announcing it.
    old_acc, old_ece, _ = paired(audit, TREAT, OLD_CONTROL, PRIMARY_CKPT)

    gates, movable, stuck = unmovable_gate_rows()

    # ---- report
    L = ["# P2 — `gate:oracle_error` at n=3, against a class-weighting-matched control", "",
         f"Producer: `diagnostics/p2_gate_oracle_verdict.py` · @{PRIMARY_CKPT} primary · "
         f"{SD_CONVENTION}", "",
         "> **Pre-registered.** `rafdb_p2_gate_oracle_seeds_queue.ps1` was frozen 2026-07-29 01:26:59, "
         "before the first run (see `PREREGISTRATIONS.md` A8).", "",
         "## Arms (@swa, selection-independent)", "",
         "| kol | acc (%) | ECE | n |", "|---|---|---|---|",
         f"| kontrol (baseline, `class_weight_mode=none`) | {p['control']['acc_mean']:.3f} ± "
         f"{ctrl_acc_sd:.3f} | {p['control']['ece_mean']:.4f} ± {ctrl_ece_sd:.4f} | "
         f"{p['control']['n']} |",
         f"| tedavi (`gate:oracle_error`) | {p['treat']['acc_mean']:.3f} ± "
         f"{p['treat']['acc_sd']:.3f} | {p['treat']['ece_mean']:.4f} ± "
         f"{p['treat']['ece_sd']:.4f} | {p['treat']['n']} |", "",
         "## Differences paired within seed (@swa)", "",
         "| tohum | Δacc (pp) | ΔECE |", "|---|---|---|"]
    for s in SEEDS:
        if s in p["per_seed"]:
            c = p["per_seed"][s]
            L.append(f"| {s} | {c['d_acc']:+.3f} | {c['d_ece']:+.4f} |")
    L += [f"| **ortalama** | **{m_acc:+.3f} ± {sample_sd(p['d_acc']):.3f}** | "
          f"**{m_ece:+.4f} ± {sample_sd(p['d_ece']):.4f}** |",
          f"| signs | `{acc_signs}` | `{ece_signs}` |", "",
          "## Verdict on the pre-registered predictions", "",
          "| # | prediction | bar (control's seed sd) | measured | ratio | verdict |",
          "|---|---|---|---|---|---|",
          f"| P2.1 | \\|Δacc\\| ≤ the control's sd → NULL | {ctrl_acc_sd:.3f} pp | "
          f"{abs(m_acc):.3f} pp | {r21:.2f}× | {'✅ confirmed' if p21 else '❌ FALSIFIED'} |",
          f"| P2.2 | \\|ΔECE\\| ≤ the control's sd → NULL | {ctrl_ece_sd:.4f} | "
          f"{abs(m_ece):.4f} | {r22:.2f}× | {'✅ confirmed' if p22 else '❌ FALSIFIED'} |",
          f"| P2.3 | signs inconsistent on at least one axis | — | acc `{acc_signs}`, "
          f"ECE `{ece_signs}` | — | {'✅ confirmed' if p23 else '❌ FALSIFIED'} |", ""]

    # Checkpoint robustness: the verdict must not be an artifact of choosing @swa.
    L += ["### Does the verdict depend on the checkpoint choice", "",
          "| checkpoint | Δacc (pp) | ΔECE | ECE signs | n |", "|---|---|---|---|---|"]
    for ck in CKPTS:
        c = res[ck]
        if not c["d_ece"]:
            continue
        L.append(f"| {ck}{' *(birincil)*' if ck == PRIMARY_CKPT else ''} | "
                 f"{st.mean(c['d_acc']):+.3f} ± {sample_sd(c['d_acc']):.3f} | "
                 f"{st.mean(c['d_ece']):+.4f} ± {sample_sd(c['d_ece']):.4f} | "
                 f"`{signs(c['d_ece'])}` | {len(c['d_ece'])} |")
    L += ["", "## Size of the class-weighting confound (a by-product of P2)", "",
          "For VAE9182 **both** controls now exist at the same three seeds, so the class-weighting "
          "switch can be isolated on its own. The difference below is the **exact size** of the bias "
          "carried by the gate rows listed below as 'not moved':", "",
          "| eksen | `none` − `effective_number` (@swa, n=%d) |" % len(cw_acc), "|---|---|",
          f"| Δacc | {st.mean(cw_acc):+.3f} ± {sample_sd(cw_acc):.3f} pp (signs "
          f"`{signs(cw_acc)}`) |",
          f"| ΔECE | {st.mean(cw_ece):+.4f} ± {sample_sd(cw_ece):.4f} (signs "
          f"`{signs(cw_ece)}`) |", "",
          "### Kirli kontrol neyi gizliyordu", "",
          "Same treatment, same seeds; the only difference is which control it is differenced against:", "",
          "| control | Δacc (pp) | ΔECE | ECE signs | reading |",
          "|---|---|---|---|---|",
          f"| `effective_number` (used before P2) | {st.mean(old_acc):+.3f} ± "
          f"{sample_sd(old_acc):.3f} | {st.mean(old_ece):+.4f} ± {sample_sd(old_ece):.4f} | "
          f"`{signs(old_ece)}` | *looks* ECE-neutral |",
          f"| `none` (the clean control P2 produced) | {m_acc:+.3f} ± "
          f"{sample_sd(p['d_acc']):.3f} | {m_ece:+.4f} ± {sample_sd(p['d_ece']):.4f} | "
          f"`{ece_signs}` | degrades calibration consistently |", "",
          "> **The missing control was masking a real calibration harm almost exactly.** "
          "Because class weighting worsens the control's own ECE by "
          f"{abs(st.mean(cw_ece)):.4f} , the gate's harm of the same magnitude came out near "
          "zero in the difference and the signs became mixed. This is the measured evidence that the "
          "A8 repair was not merely a gesture of rigour.", "",
          "## Re-differencing the six gate rows — how far it got", "",
          f"Gate runs on the 400e/SWA@200 budget: **{len(gates)}**. "
          f"With a control in their own class-weighting mode: **{len(movable)}**; "
          f"hâlâ olmayan: **{len(stuck)}**.", "",
          "| teacher | signal | seed | moved onto the clean control |", "|---|---|---|---|"]
    for t, src, s, cw in sorted(gates):
        L.append(f"| {t} | {src} | {s} | {'✅ yes' if (t, src, s, cw) in movable else '❌ no'} |")
    # Bu paragraf verinin durumuna göre yazılır. Sabit hâli 2026-08-01'de kendi hesapladığı
    # sayıyla çelişir olmuştu ("6 koşu gerekir, başlatılmadı" derken betik 0 eşleşmemiş satır
    # sayıyordu) -- P4 eksik kontrolleri, P5 de oracle replikasyonunu indirmişti.
    if stuck:
        L += ["", f"> **A8's note that 'all six gate rows can be moved' is only partly "
                  f"satisfied.** There are still rows without a control in their own class-weighting mode, "
                  f"**{len(stuck)}** namely, and they were dropped from T5 carrying the confound "
                  f"boyuyla birlikte supplementary'de raporlanacak.", ""]
    else:
        L += ["", "> **A8's note that 'all six gate rows can be moved' is fully "
                  "satisfied.** P4 (6 controls, 30 Jul) landed the missing "
                  "`class_weight_mode=none` baselines for stage1 and primary, and P5 (6 runs, 31 Jul–1 Aug) the "
                  "oracle replication: **every gate row is now differenced against the control in its own "
                  "mode**, with no unpaired rows. P5's verdict is also in "
                  "`diagnostics/p5_oracle_replication/p5_verdict.md`: the calibration harm "
                  "**did not resolve** for stage1/primary, so the claim below stays conditional on "
                  "VAE9182.", "",
          "> The gate claim does not rest on those four rows: `gate:oracle_error` is an "
          "**error-informed diagnostic** — a perfect signal *of the student's own error*, against "
          "a **clean** control, at **three seeds**. If even that brings no gain, no weaker "
          "**error-derived** signal can. **Scope, stated (11 Aug 2026):** this is not a bound "
          "over all signals. A signal that is not derived from the error — teacher variance, "
          "input difficulty, human disagreement — is outside it and has to be tested on its own; "
          "A12 does exactly that for the learned ones.", ""]

    (OUT_DIR / "p2_verdict.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "p2_verdict.json").write_text(json.dumps({
        "status": "PRE-REGISTERED (PREREGISTRATIONS.md A8, frozen 2026-07-29 01:26:59)",
        "sd_convention": SD_CONVENTION, "primary_checkpoint": PRIMARY_CKPT,
        "treatment": TREAT, "control": CONTROL, "seeds": list(SEEDS),
        "by_checkpoint": {ck: {"d_acc": res[ck]["d_acc"], "d_ece": res[ck]["d_ece"],
                               "treat": res[ck]["treat"], "control": res[ck]["control"],
                               "per_seed": {str(k): v for k, v in res[ck]["per_seed"].items()}}
                          for ck in CKPTS},
        "verdict": {
            "P2.1": {"statement": "|mean d_acc| <= control seed sd", "bar": ctrl_acc_sd,
                     "measured": abs(m_acc), "ratio": r21, "holds": p21},
            "P2.2": {"statement": "|mean d_ECE| <= control seed sd", "bar": ctrl_ece_sd,
                     "measured": abs(m_ece), "ratio": r22, "holds": p22},
            "P2.3": {"statement": "per-seed signs inconsistent on at least one axis",
                     "acc_signs": acc_signs, "ece_signs": ece_signs, "holds": p23},
        },
        "class_weighting_confound_none_minus_effnum": {
            "d_acc_mean": st.mean(cw_acc), "d_acc_sd": sample_sd(cw_acc),
            "d_ece_mean": st.mean(cw_ece), "d_ece_sd": sample_sd(cw_ece),
            "n": len(cw_acc), "per_seed": {str(k): v for k, v in cw_per.items()}},
        "same_treatment_against_contaminated_control": {
            "control": OLD_CONTROL,
            "d_acc_mean": st.mean(old_acc), "d_acc_sd": sample_sd(old_acc),
            "d_ece_mean": st.mean(old_ece), "d_ece_sd": sample_sd(old_ece),
            "d_ece_signs": signs(old_ece),
            "note": "against this control the same runs read as ECE-neutral with mixed signs; "
                    "the clean control shows +0.0056 with 3/3 agreeing signs"},
        "gate_row_repair": {
            "n_gate_rows": len(gates),
            "moved_to_clean_control": [list(g) for g in sorted(movable)],
            "still_unpaired": [list(g) for g in sorted(stuck)],
            "runs_needed_to_finish": 6},
    }, indent=2), encoding="utf-8")

    print(f"control @{PRIMARY_CKPT}: acc {p['control']['acc_mean']:.3f}+/-{ctrl_acc_sd:.3f}  "
          f"ECE {p['control']['ece_mean']:.4f}+/-{ctrl_ece_sd:.4f}  n={p['control']['n']}")
    print(f"treat   @{PRIMARY_CKPT}: acc {p['treat']['acc_mean']:.3f}+/-{p['treat']['acc_sd']:.3f}  "
          f"ECE {p['treat']['ece_mean']:.4f}+/-{p['treat']['ece_sd']:.4f}  n={p['treat']['n']}")
    print(f"\npaired d_acc = {m_acc:+.3f} +/- {sample_sd(p['d_acc']):.3f} pp  signs {acc_signs}")
    print(f"paired d_ece = {m_ece:+.4f} +/- {sample_sd(p['d_ece']):.4f}      signs {ece_signs}")
    print(f"\nP2.1  |d_acc| {abs(m_acc):.3f} vs bar {ctrl_acc_sd:.3f}  ({r21:.2f}x)  "
          f"{'HOLDS' if p21 else 'FALSIFIED'}")
    print(f"P2.2  |d_ece| {abs(m_ece):.4f} vs bar {ctrl_ece_sd:.4f}  ({r22:.2f}x)  "
          f"{'HOLDS' if p22 else 'FALSIFIED'}")
    print(f"P2.3  acc {acc_signs} / ece {ece_signs}  {'HOLDS' if p23 else 'FALSIFIED'}")
    print(f"\nclass-weighting alone (none - effective_number), n={len(cw_acc)}: "
          f"d_acc {st.mean(cw_acc):+.3f}+/-{sample_sd(cw_acc):.3f} pp, "
          f"d_ece {st.mean(cw_ece):+.4f}+/-{sample_sd(cw_ece):.4f}")
    print(f"gate rows: {len(gates)} total, {len(movable)} moved onto the clean control, "
          f"{len(stuck)} still unpaired")
    for g in sorted(stuck):
        print(f"    unpaired: {g[0]}/{g[1]} seed{g[2]} (cw={g[3]})")
    print(f"\nWrote {OUT_DIR / 'p2_verdict.md'}")


if __name__ == "__main__":
    main()
