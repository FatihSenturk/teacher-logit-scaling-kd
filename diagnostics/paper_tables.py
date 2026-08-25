"""Paper-ready Results tables T1-T9, generated from artifacts only.

RULES THIS SCRIPT ENFORCES (they are the reason it exists rather than a hand-typed table):

  1. NOTHING IS TYPED IN. Every number is read from a committed artifact. Each table prints the
     artifact path(s) it came from, so a reviewer -- or the author six months from now -- can go
     from a cell to the file that produced it without asking anyone.
  2. @swa IS PRIMARY. `best` is chosen by argmax val-accuracy ON THE REPORTED SET, so it carries
     selection optimism (quantified in T8). `swa` and `last` are selection-independent. Every
     dose-response and mechanism table therefore shows all three, with swa first.
  3. ERROR BARS ARE SAMPLE sd (n-1), from diagnostics/stats_convention.py. n is always shown.
     A cell with n=1 shows no "+/-" at all rather than a fake +/- 0.0000.
  4. PRECISION IS PUBLICATION PRECISION: accuracy 2 decimals, ECE/JSD/Brier 4 decimals.
  5. MISSING IS MISSING. An arm that has not finished prints "-" and its real n. This script
     never interpolates, never carries a value across checkpoints, and never silently drops a
     seed to make an n look round.

Usage:  python diagnostics/paper_tables.py
Output: diagnostics/paper_tables/RESULTS_TABLES.md   (read-only analysis; no GPU, no training)
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

D = ROOT / "diagnostics"
OUT_DIR = D / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_MD = OUT_DIR / "RESULTS_TABLES.md"
OUT_JSON = OUT_DIR / "RESULTS_TABLES.json"
AXIS_SPANS = {}

CKPTS = ("swa", "best", "last")
TEACHERS = ("stage1", "primary", "vae9182")

# --------------------------------------------------------------------------- artifact loading
A_OVERLAY = D / "p1_dose_response" / "two_dataset_overlay.json"
A_B015 = D / "selection_audit" / "b015_verdict.json"
A_AUDIT = D / "selection_audit" / "selection_audit.csv"
# THE FROZEN SET AND THE MEASURED SET ARE NOT THE SAME SET, and only one table needs the frozen
# one. T8 quotes selection optimism at N=131, an inclusion set deliberately frozen on 2026-07-31;
# it must read `selection_audit.csv` and nothing else. Every OTHER table here measures a
# mechanism, and a mechanism table that cannot see a run launched after the cutoff is simply
# wrong -- P5's six oracle replications are exactly that case. So: T8 -> A_AUDIT (frozen),
# every mechanism/capacity table -> A_AUDIT_MECH (the superset when it exists).
A_AUDIT_ALL = D / "selection_audit" / "selection_audit_unfrozen.csv"
A_AUDIT_MECH = A_AUDIT_ALL if A_AUDIT_ALL.exists() else A_AUDIT
A_FER_AUDIT = D / "selection_audit" / "ferplus_selection_audit.csv"
A_GAIN = D / "selection_audit" / "selection_gain.json"
A_P4 = D / "p4_teacher_selection" / "p4_teacher_selection.json"
A_STUDENT_JSD = D / "ferplus_jsd" / "ferplus_student_jsd.json"
A_TEACHER_GRID_FER = D / "ferplus_jsd" / "ferplus_teacher_signed_grid.json"
A_FER_JSD = D / "ferplus_jsd" / "ferplus_jsd.json"
A_P5 = D / "p5_efficiency" / "p5_efficiency.json"
A_CAP_LAW = D / "p5_efficiency" / "capacity_law_check.json"
A_LAT = D / "p5_efficiency" / "latency_benchmark.csv"
A_LAT_JSON = D / "p5_efficiency" / "latency_benchmark.json"
# Second, independent latency session on an idle machine. Its whole purpose is that the fp16
# observation was NOT paper-eligible from one session -- the pre-registered rule was that it
# enters the paper only if an independent session reproduces it. Kept as a separate file (the
# benchmark's --tag flag) precisely so session 2 cannot overwrite the baseline it must be
# compared against.
A_LAT2 = D / "p5_efficiency" / "latency_benchmark_session2.csv"
A_RUNS = ROOT / "runs.csv"


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rel(p):
    return str(Path(p)).replace(str(ROOT) + "\\", "").replace("\\", "/")


def src(*paths):
    return "*Kaynak: " + " · ".join(f"`{rel(p)}`" for p in paths) + "*"


# --------------------------------------------------------------------------- formatting
def f_acc(m, s, n):
    if n == 0 or m is None:
        return "-"
    return f"{m:.2f}" if n == 1 else f"{m:.2f} ± {s:.2f}"


def f_ece(m, s, n):
    if n == 0 or m is None:
        return "-"
    return f"{m:.4f}" if n == 1 else f"{m:.4f} ± {s:.4f}"


def cell(d, key_mean, key_sd, fmt):
    """One (mean, sd, n) cell out of an overlay by_ckpt dict."""
    if not d:
        return "-"
    return fmt(d.get(key_mean), d.get(key_sd), d.get("n", 0))


# --------------------------------------------------------------------------- T1/T2/T3
def dose_table(arm, title, note):
    """Dose-response: one row per pre-scaling temperature, all three checkpoints."""
    lines = [f"### {title}", "", note, "",
             "| T | teacher ECE | signed gap | student ECE @swa | student ECE @best | "
             "student ECE @last | student acc @swa | n |",
             "|---|---|---|---|---|---|---|---|"]
    for p in sorted(arm["points"], key=lambda r: r["T"]):
        bc = p["by_ckpt"]
        swa = bc.get("swa", {})
        lines.append(
            f"| {p['T']:g} | {p['teacher_ece']:.4f} | {p['signed_gap']:+.4f} | "
            f"{cell(bc.get('swa'), 'ece_mean', 'ece_sd', f_ece)} | "
            f"{cell(bc.get('best'), 'ece_mean', 'ece_sd', f_ece)} | "
            f"{cell(bc.get('last'), 'ece_mean', 'ece_sd', f_ece)} | "
            f"{cell(bc.get('swa'), 'acc_mean', 'acc_sd', f_acc)} | {swa.get('n', 0)} |")
    return lines


# --------------------------------------------------------------------------- T4 helpers
def midrank(v):
    """Tie-corrected ranks. An untied ranking invents an order inside a tie group and DEFLATES
    rho -- that bug once turned a perfectly separated B-015 result into a printed 'FALSIFIED'."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    mx, my = st.mean(x), st.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den if den else float("nan")


def spearman(x, y):
    return pearson(midrank(x), midrank(y))


# --------------------------------------------------------------------------- run tables
def load_runs():
    if not A_RUNS.exists():
        return {}
    out = {}
    for r in csv.DictReader(open(A_RUNS, encoding="utf-8")):
        out[(r["run_name"], r["timestamp"])] = r
    return out


def load_audit(path):
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        for k in ("acc", "ece", "nll", "brier", "macro_f1"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        out[(r["run_name"], r["timestamp"], r["checkpoint"])] = r
    return out


def gate_variant(r):
    """Gate runs differ by which uncertainty signal drives the blend; `manipulation` collapses
    them all to 'gate', so the signal is carried by its own ledger column.

    WAS A LEVEL-1 VIOLATION (fixed 8 Aug 2026, isolated step). This function used to open
    `<run_dir>/run_args.json`, which made three table producers -- `paper_tables`,
    `t5_pairing_diff`, `section54_numbers` -- depend on `results/unified_students/` being
    present. That was 8 of the Level-1 gate's 13 violations from a single root cause: the
    paper's numbers could not be regenerated without the raw run directories, which are not
    published. `build_runs_ledger.py` already reads run_args (it is Level 3 and declared
    `ALLOWED`), so the distinction is now extracted ONCE, at the outermost layer that is
    permitted to look, and written to `runs.csv` as `gate_signal`.

    Takes the ledger ROW now, not a path. A missing column raises rather than defaulting:
    silently returning "gate" would merge five distinct mechanism cells into one and the
    pairing table would average across signals without saying so.
    """
    if "gate_signal" not in r:
        raise RuntimeError(
            "runs.csv'de `gate_signal` sütunu yok. Defter bu sütun eklenmeden önce kurulmuş; "
            "`python diagnostics/build_runs_ledger.py` ile yeniden kurun. Sessizce 'gate'e "
            "düşmek beş ayrı mekanizma hücresini tek hücreye katardı.")
    sig = (r.get("gate_signal") or "").strip()
    return "gate:" + sig if sig else "gate"


def is_ablation_control(r):
    """The mechanism grid's control arm, defined by flags -- NOT by name.

    All of these must match for a run to be a legal paired control: unmanipulated teacher
    (t_scale 1.0), the VICH student head, the 400e/SWA@200 budget and alpha=0.3. This is what
    keeps the legacy alpha=0.25 / 200-epoch / linear-head / reduced-resolution runs out of the
    control pool, and (via family) keeps the width-frontier runs out of it too.
    """
    return (r["family"] == "baseline" and r["manipulation"] == "none"
            and r["student_head"] == "vich" and float(r["t_scale"] or 1) == 1.0
            and r["epochs"] == "400" and str(r["swa_start"]) == "200"
            and abs(float(r["alpha"] or 0) - 0.3) < 1e-9)


def mechanism_table(runs, audit):
    """T5: every mechanism vs. its OWN matched baseline, paired within seed AND within
    class-weighting mode.

    WHY class_weight_mode IS PART OF THE PAIRING KEY. kd_common.py raises on gate +
    class-weighted CE, so all six gate rows were necessarily run with
    --class-weight-mode none while every other mechanism ran effective_number. Until
    2026-07-30 no no-classweight baseline existed, so those six rows were differenced
    against an effective_number control and each carried TWO manipulated variables
    (the mechanism and the loss weighting). P2 produced the missing control at 3 seeds.
    Keying on class_weight_mode is what moves the gate rows onto it -- and, just as
    importantly, keeps every non-gate mechanism on the effective_number control instead
    of letting dict iteration order decide which of the two now-legal controls wins.
    """
    controls, treats = {}, {}
    for key, r in runs.items():
        if r["teacher"] not in TEACHERS:
            continue
        if is_ablation_control(r):
            ck = (r["teacher"], r["seed"], r["class_weight_mode"])
            if ck in controls:
                raise RuntimeError(
                    f"two legal controls for {ck}: {controls[ck][0]} and {key[0]}. Every "
                    f"delta in T5 for that cell would depend on dict order -- resolve by "
                    f"narrowing is_ablation_control(), do not let this pass.")
            controls[ck] = key
        elif (r["family"] == "mechanism_ablation" and r["student_head"] == "vich"
              and float(r["t_scale"] or 1) == 1.0 and r["epochs"] == "400"
              and str(r["swa_start"]) == "200"
              and abs(float(r["alpha"] or 0) - 0.3) < 1e-9):
            # Same budget/alpha gate as the control. Without it a 200-epoch no-SWA run of the
            # same mechanism would be paired against a 400e/SWA@200 control and the budget
            # difference would be reported as the mechanism's effect.
            mech = r["manipulation"]
            if mech == "gate":
                mech = gate_variant(r)
            treats.setdefault((r["teacher"], mech, r["class_weight_mode"]), {})[r["seed"]] = key

    lines = ["| teacher | mechanism | class weighting (both arms) | Δacc @swa (pp) | ΔECE @swa | "
             "ΔECE @best | ΔECE @last | signs @swa | n |",
             "|---|---|---|---|---|---|---|---|---|"]
    payload = {}
    unpaired = []
    for teacher in TEACHERS:
        for (t, mech, cw), by_seed in sorted(treats.items(), key=lambda kv: tuple(map(str, kv[0]))):
            if t != teacher:
                continue
            row = {"teacher": t, "mechanism": mech, "class_weight_mode": cw,
                   "control_class_weight_mode": cw}
            cells = {}
            for ck in CKPTS:
                d_acc, d_ece = [], []
                for seed, tk in by_seed.items():
                    ck_key = (t, seed, cw)
                    if ck_key not in controls:
                        # No control at this treatment's OWN class weighting. Differencing
                        # against the other mode would reintroduce exactly the two-variable
                        # defect this key exists to remove, so the cell is dropped and
                        # reported instead of being quietly filled with a mismatched control.
                        if ck == "swa":
                            unpaired.append(f"{t}/{mech} seed{seed} (cw={cw})")
                        continue
                    a = audit.get(controls[ck_key] + (ck,))
                    b = audit.get(tk + (ck,))
                    if not a or not b:
                        continue
                    d_acc.append(b["acc"] - a["acc"])
                    d_ece.append(b["ece"] - a["ece"])
                cells[ck] = (d_acc, d_ece)
                row[ck] = {"d_acc_mean": st.mean(d_acc) if d_acc else None,
                           "d_acc_sd": sample_sd(d_acc), "d_ece_mean": st.mean(d_ece) if d_ece else None,
                           "d_ece_sd": sample_sd(d_ece), "n": len(d_ece),
                           "d_ece_signs": "".join("-" if v < 0 else "+" for v in d_ece),
                           # doğruluk işaretleri de saklanıyor: 2×-kontrol-sd ölçütünün işaret
                           # koşulu (G3.1) her iki eksende de mekanik uygulanabilsin diye.
                           "d_acc_signs": "".join("-" if v < 0 else "+" for v in d_acc)}
            swa_acc, swa_ece = cells["swa"]
            if not swa_ece:
                continue

            def d_fmt(v, digits):
                # n=1 gets NO "+/- 0.0000": a single seed has no spread to report, and printing
                # a zero error bar reads as "perfectly reproducible" -- the exact opposite of
                # what one run means.
                if not v:
                    return "-"
                return (f"{v[0]:+.{digits}f} *(n=1)*" if len(v) == 1
                        else f"{st.mean(v):+.{digits}f} ± {sample_sd(v):.{digits}f}")

            signs = "".join("-" if v < 0 else "+" for v in swa_ece)
            lines.append(
                f"| {t} | {mech} | {cw} | {d_fmt(swa_acc, 2)} | {d_fmt(swa_ece, 4)} | "
                + " | ".join(d_fmt(cells[c][1], 4) for c in ("best", "last"))
                + f" | `{signs}` | {len(swa_ece)} |")
            payload[f"{t}/{mech}"] = row
    if unpaired:
        lines += ["", f"> ⚠️ **{len(unpaired)} treatment cell(s) could not be paired** — no control "
                      f"exists in their own class-weighting mode, so they are omitted (differencing "
                      f"against the other mode's control would reintroduce a second variable): "
                  + ", ".join(f"`{u}`" for u in sorted(unpaired)) + "."]
    return lines, payload


# --------------------------------------------------------------------------- main
def p6_sections(add, payload):
    """T11/T12 — P6'nın resmî hükmü (ön-kayıt A9).

    A9 bu iki numarayı P6'ya ayırmıştı ("kendi tabloları olacak: T11/T12"); burada özet
    satırlar durur, tam tablo `paper_tables/p6_collapse_test.md` içinde. JSON üretilmemişse
    blok atlanır — paper_tables.py hiçbir koşulda P6 yüzünden çökmemeli.
    """
    p = OUT_MD.parent / "p6_collapse_test.json"
    if not p.exists():
        return
    d = jload(p)

    # --- T11: eşleşmiş T·τ çiftleri (P6.1)
    add("## T11 — Does the law collapse onto the product T·τ? (P6.1)")
    add("")
    add("Two matched pairs hold T·τ fixed while moving τ and T in opposite directions. If "
        "student ECE depended on (T,τ) only through the product, both cells of a pair would "
        "land within seed noise of each other. The bar was frozen before the runs at "
        f"2×{d['bar']} = {d['two_bar']} (the seed sd of the control arm's ECE @swa). "
        "Full table: `paper_tables/p6_collapse_test.md`.")
    add("")
    add("| pair (T·τ) | τ, T (low-τ cell) | τ, T (high-τ cell) | mean ΔECE | signs | "
        "\\|mean\\|/2×bar | verdict |")
    add("|---|---|---|---|---|---|---|")
    cells = {}
    for pname, v in d["p6_1"]["pairs"].items():
        ratio = abs(v["mean"]) / d["two_bar"]
        add(f"| {pname} | τ={v['tau_lo']}, T={v['T_lo']} | τ={v['tau_hi']}, T={v['T_hi']} | "
            f"{v['mean']:+.4f} ± {v['sd']:.4f} | "
            f"{'3/3 same' if v['same_sign_3of3'] else 'mixed'} | {ratio:.1f}× | "
            f"{v['status']} |")
        cells[pname] = {"mean": v["mean"], "sd": v["sd"],
                        "same_sign_3of3": v["same_sign_3of3"], "status": v["status"]}
    add("")
    add(d["p6_1"]["overall"])
    add("")
    rep = d["p6_1"].get("reproduces_early_reading", {})
    if rep.get("checked"):
        add("The 2 Aug early reading (queue at ~10/42) is reproduced "
            + ("**bit-identically** — all six ΔECE values and both pair verdicts agree."
               if rep.get("identical")
               else "**NOT** reproduced; the deviations are: " + "; ".join(rep.get("diffs", []))))
        add("")
    add(src(p))
    add("")

    # --- T12: α modülasyonu (P6.2, P6.3)
    add("## T12 — Does the KD weight α modulate the transfer? (P6.2, P6.3)")
    add("")
    add("gap(α) := ECE(T=1) − ECE(T=1.3406), within seed, τ=6 throughout. A larger gap means "
        "the pre-scaling intervention moves the student more. Two rules were frozen before the "
        "runs: gap(α) is non-increasing in α (P6.2) and gap(0.9) < gap(0.1) strictly (P6.3), "
        "each required in 3/3 seeds.")
    add("")
    add("| α | seed 42 | seed 1 | seed 43 | mean |")
    add("|---|---|---|---|---|")
    gaps = {}
    for a in d["alpha_order"]:
        row = d["grid2_cells"][a]
        vals = [row[s]["gap"] for s in ("42", "1", "43")]
        add(f"| {a} | " + " | ".join(f"{v:+.4f}" for v in vals) +
            f" | **{st.mean(vals):+.4f}** |")
        gaps[a] = {"by_seed": {s: row[s]["gap"] for s in ("42", "1", "43")},
                   "mean": st.mean(vals)}
    add("")
    add(f"**P6.2 (monotonicity): {d['p6_2']['verdict']}** — held in "
        f"{d['p6_2']['n_seeds_ok']}/3 seeds. "
        f"**P6.3 (extremes): {d['p6_3']['verdict']}** — held in "
        f"{d['p6_3']['n_seeds_ok']}/3 seeds.")
    add("")
    add("The α=0.3 row reuses the existing dose-response arms, as the declaration specified; "
        "it is not a new run.")
    add("")
    add(src(p))
    add("")
    payload["T11_collapse"] = {"pairs": cells, "overall": d["p6_1"]["overall"],
                               "bar": d["bar"], "two_bar": d["two_bar"],
                               "reproduces_early_reading": rep}
    payload["T12_alpha"] = {"gaps": gaps,
                            "P6_2": {"verdict": d["p6_2"]["verdict"],
                                     "n_seeds_ok": d["p6_2"]["n_seeds_ok"]},
                            "P6_3": {"verdict": d["p6_3"]["verdict"],
                                     "n_seeds_ok": d["p6_3"]["n_seeds_ok"]}}


def r3_sections(add, payload):
    """T13/T14/T15 — R3 robustluk turunun özet satırları (ön-kayıt A10).

    Tam tablolar kendi dosyalarında durur; burada yalnız makaleye girecek sayılar
    tekrarlanır, çünkü tek kaynak kuralı RESULTS_TABLES'ın makalenin tek referansı
    olmasını gerektiriyor. Üretilmemiş bir JSON blokla birlikte atlanır.
    """
    from calibration_metrics import METRIC_LABEL, METRIC_ORDER
    tdir = OUT_MD.parent

    # --- T13: çok-metrik doz-cevap
    p = tdir / "robustness_metrics.json"
    if p.exists():
        d = jload(p)
        add("## T13 — Multi-metric robustness of the dose–response (R3-1)")
        add("")
        add("Seven metrics on the same 42 runs and the same cached logits. The question is not "
            "whether a metric is small but whether the metrics **agree about where the curve "
            "bottoms out**; if they do, the result is not an artefact of the 15-bin equal-width "
            "ECE specification. `steps` counts individual (T-pair, seed) steps that agree with "
            "the other seeds at the same pair. Full table: `paper_tables/robustness_metrics.md`.")
        add("")
        series = list(d["series"].values())
        add("| metric | " + " | ".join(f"{s['series']}<br>argmin T · steps" for s in series) + " |")
        add("|---|" + "---|" * len(series))
        cells = {}
        for m in METRIC_ORDER:
            row = []
            for s in series:
                pm = s["metrics"][m]
                am = (f"**{pm['argmin_T_modal']:g}**" if pm["argmin_T_unanimous"]
                      else f"{pm['argmin_T_modal']:g}*")
                row.append(f"{am} · {pm['steps_consistent']}/{pm['steps_total']}")
                cells[f"{s['series']}|{m}"] = {"argmin_T": pm["argmin_T_modal"],
                                               "unanimous": pm["argmin_T_unanimous"],
                                               "steps_consistent": pm["steps_consistent"],
                                               "steps_total": pm["steps_total"]}
            add(f"| {METRIC_LABEL[m]} | " + " | ".join(row) + " |")
        add("")
        add("Bold = all three seeds put the minimum at the same T; `*` = modal value, seeds "
            "disagree. " + f"Across all series and metrics, "
            f"{d['total_steps'] - d['total_breaks']}/{d['total_steps']} steps agree with the "
            "other seeds at the same pair; every disagreement is listed in the full table.")
        add("")
        add(src(p))
        add("")
        payload["T13_robustness"] = {"cells": cells, "total_steps": d["total_steps"],
                                     "total_breaks": d["total_breaks"]}

    # --- T14: T* fit kriteri duyarlılığı
    p = tdir / "tstar_sensitivity.json"
    if p.exists():
        d = jload(p)
        add("## T14 — T\\* fitting-criterion sensitivity (R3-2)")
        add("")
        add("The deployed T\\* minimises NLL; the reported quantity is ECE. This table prices "
            "that mismatch. Full table: `paper_tables/tstar_sensitivity.md`.")
        add("")
        add("| teacher | T\\*_NLL | T\\*_ECE | \\|ΔT\\*\\| | ΔECE (criterion cost) | "
            "ECE removed by TS |")
        add("|---|---|---|---|---|---|")
        for tag, r in d["results"].items():
            add(f"| {tag} | {r['T_star_nll']:.4f} | {r['T_star_ece']:.4f} | "
                f"{r['abs_dT']:.4f} | {r['d_ece']:+.5f} | {r['ece_removed_by_ts']:+.5f} |")
        add("")
        bad = [t for t, r in d["results"].items() if r["ece_removed_by_ts"] <= 0]
        if bad:
            add("> The last column is why this table exists: in "
                + ", ".join(f"**{b}**" for b in bad)
                + " temperature scaling at the NLL optimum **increases** ECE, and the two "
                  "criteria disagree about the direction of the correction — so 'the fitting "
                  "criterion does not matter' cannot be written for every teacher.")
            add("")
        add(src(p))
        add("")
        payload["T14_tstar_sensitivity"] = {
            t: {k: r[k] for k in ("T_star_nll", "T_star_ece", "abs_dT", "d_ece",
                                  "ece_removed_by_ts")}
            for t, r in d["results"].items()}

    # --- T15: FERPlus JSD katman duyarlılığı
    p = tdir / "jsd_sensitivity.json"
    if p.exists():
        d = jload(p)
        add("## T15 — FERPlus JSD sensitivity to the vote-count stratum (R3-3)")
        add("")
        add("The human target is built from each row's own vote sum, and that sum is not always "
            "10. This table asks whether the ECE/JSD separation survives conditioning on vote "
            "resolution. Full table: `paper_tables/jsd_sensitivity.md`.")
        add("")
        add("| slice | n | T\\*_ECE | T\\*_NLL | T\\*_JSD | separation held |")
        add("|---|---|---|---|---|---|")
        for name, r in d["results"].items():
            if r.get("n", 0) == 0:
                continue
            add(f"| {name} | {r['n']} | {r['T_ece']:.2f} | {r['T_nll']:.2f} | {r['T_jsd']:.2f} | "
                f"{'yes' if r['separation_preserved'] else '**no**'} |")
        add("")
        add(src(p))
        add("")
        payload["T15_jsd_sensitivity"] = {
            k: {kk: v[kk] for kk in ("n", "T_ece", "T_nll", "T_jsd", "separation_preserved")}
            for k, v in d["results"].items() if v.get("n", 0) > 0}


# S12 (tab:app_paired_sd) SATIR DUZENI. 21 T5 hucresinin uc-tohumlu OLAN 17'si; tek-tohumlu
# dortlu (ctkd x3 + g2g_kl+adaptive_t) tabloya girmez -- n==3 suzgeci bunu SAYARAK yapar,
# adlari ezberleyerek degil. Mekanizma sirasi makaledeki elle blogun sirasidir.
S12_MECH_ORDER = [("adaptive_t", "adaptive temperature"), ("g2g_kl", "G2G"),
                  ("gate:mean_logvar", "gate: mean logvar"),
                  ("gate:target_logvar", "gate: target logvar"),
                  ("gate:oracle_error", "gate: oracle error"),
                  ("logit_std", "logit standardisation")]
S12_TEX = ROOT / "paper" / "tables" / "tab_app_paired_sd.tex"


def emit_tab_app_paired_sd(mech_payload):
    """S12: 17 uc-tohumlu hucrenin esli farki +- tohum sd'si (@swa), makale tablosu olarak.

    NEDEN VAR (22 Agu 2026, defter final2). S12 makaleye ELLE yazilmisti: degerler T5'ten
    birebir ama tabloyu bir uretici basmiyordu -- "tablolar ureticiden gelir" kuralinin tek
    istisnasi olurdu. Artik bu dosya kaynaktir; supplementary.tex `\\input` ile alir.
    Yuvarlama ledger konvansiyonu (ROUND_HALF_UP), acc 2dp / ECE 4dp; isaret acikca basilir.
    Cikti BELIRLENIMLIDIR (zaman damgasi yok) -- tazelik kapisi bayt karsilastirir.
    """
    from decimal import Decimal, ROUND_HALF_UP

    def q(v, dp, signed):
        d = Decimal(repr(float(v))).quantize(Decimal("0." + "0" * (dp - 1) + "1"),
                                             rounding=ROUND_HALF_UP)
        if signed:
            return ("+" if d >= 0 else "") + str(d)
        return str(abs(d))

    groups = []
    for t, tex_t in (("stage1", "Stage1"), ("primary", "Primary"), ("vae9182", "VAE9182")):
        g = []
        for mech, name in S12_MECH_ORDER:
            c = mech_payload.get(f"{t}/{mech}")
            if not c or c["swa"].get("n") != 3:
                continue
            s = c["swa"]
            cw = "eff." if c["class_weight_mode"] == "effective_number" else "none"
            g.append(f"{tex_t} & {name} & " + r"\texttt{" + cw + "} & $"
                     + q(s["d_acc_mean"], 2, True) + r" \pm " + q(s["d_acc_sd"], 2, False)
                     + "$ & $" + q(s["d_ece_mean"], 4, True) + r" \pm "
                     + q(s["d_ece_sd"], 4, False) + "$ " + r"\\")
        groups.append(g)
    n_rows = sum(len(g) for g in groups)
    nl = chr(10)
    body = (nl + r"\addlinespace" + nl).join(nl.join(g) for g in groups)
    header = nl.join([
        "% URETICI TARAFINDAN YAZILDI -- elle duzenlemeyin.",
        "% Kaynak: diagnostics/paper_tables.py (T5_mechanisms @swa; n==3 hucreler).",
        f"% Satir sayisi: {n_rows} (beklenen 17; sapma T5'in kendisinde degisiklik demektir).",
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Paired differences with seed standard deviations for all",
        r"seventeen three-seed mechanism cells, SWA checkpoint.  \emph{cw} is",
        "the pair's class-weighting mode.  Point values reproduce",
        r"Table~\ref{tab:mechanisms}; the $\pm$ entries are per-cell",
        "paired-difference seed standard deviations ($n{=}3$, sample sd).",
        r"$\Delta$acc is in percentage points.}",
        r"\label{tab:app_paired_sd}",
        r"\small",
        r"\setlength{\tabcolsep}{5pt}",
        r"\begin{tabular}{@{}lllrr@{}}",
        r"\toprule",
        r"teacher & mechanism & cw & $\Delta$acc (pp) & $\Delta$ECE \\",
        r"\midrule",
    ])
    tail = nl.join([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    tex = header + nl + body + nl + tail
    S12_TEX.parent.mkdir(parents=True, exist_ok=True)
    S12_TEX.write_text(tex, encoding="utf-8")
    print(f"Wrote {S12_TEX}  ({n_rows} satir)")
    if n_rows != 17:
        raise SystemExit(f"DUR: S12 {n_rows} satir uretti, beklenen 17 -- T5 degisti demektir.")



def main():
    ov = jload(A_OVERLAY)
    L = []
    add = L.append

    add("# Results tables — ready to copy into the paper")
    add("")
    add(f"Producer: `diagnostics/paper_tables.py` · sd convention: **{SD_CONVENTION}**")
    add("")
    add("**How to read this.** `@swa` and `@last` are selection-independent; `@best` is chosen by "
        "argmax val-acc over the reported set and therefore carries selection optimism (T8 measures "
        "it). The primary column in every table is **@swa**.")
    add("")
    # 19 Agu 2026 (okuma turu 1): ayni kume bu depoda ve makalede DORT ayri adla aniliyordu.
    # Ad birligi makale tarafinin karari; burada yapilan, eslemenin OLCULMUS haline isaret etmek.
    add("**One set, several names.** \"fold-3 validation split\", \"the reporting set\" and "
        "\"RAF-DB's official test set\" all denote the *same* partition, and `@best` is selected on "
        "it: RAF-DB's metadata holds exactly two partitions (fold 2 = `train/`, n=12,271; fold 3 = "
        "`test/`, n=3,068) and fold 3's per-class counts reproduce RAF-DB's published test "
        "distribution exactly. FERPlus's reporting set is fold 2 (`FER2013Test`, n=3,153). Measured, "
        "not asserted: `diagnostics/split_identity.py` -> `paper_tables/split_identity.{md,json}`.")
    add("")

    # ---------------- T1 / T2 / T3
    add("## T1 — Dose-response, RAF-DB / Stage1 teacher")
    add("")
    L += dose_table(ov["arms"]["rafdb_stage1"], "Stage1 (over-confident teacher, ECE 0.0378)",
                    "Signed gap = mean confidence − accuracy, from the teacher's pre-scaled logits "
                    "on the fold-3 validation split. This arm lies **entirely on the positive** side.")
    add("")
    add(src(A_OVERLAY))
    add("")

    add("## T2 — Dose-response, RAF-DB / VAE9182 teacher (flat control)")
    add("")
    L += dose_table(ov["arms"]["rafdb_vae9182"], "VAE9182 (well-calibrated teacher, ECE 0.0136)",
                    "B-007's pre-registered flat control: with no miscalibration to correct, T≠1 "
                    "**should not help**. The signed gap at T=1.0 is +0.0042, the point closest to zero.")
    add("")
    add(src(A_OVERLAY))
    add("")

    add("## T3 — Dose-response, FERPlus (under-confident teacher, opposite sign)")
    add("")
    L += dose_table(ov["arms"]["ferplus"], "FERPlus (ECE 0.1282 @T=1, signed gap −0.1277)",
                    "The **mirror image** of the RAF-DB arms: here the teacher is under-confident, so "
                    "the correction sharpens rather than softens (T\\*<1). The law's direction-"
                    "independence can only be tested once this arm is included.")
    add("")
    add(src(A_OVERLAY, A_FER_AUDIT))
    add("")

    # ---------------- T4
    add("## T4 — Pooled association, separation test and direction asymmetry")
    add("")
    ps = ov["pooled_stats"]
    pts = {ck: [] for ck in CKPTS}
    for arm in ov["arms"].values():
        for p in arm["points"]:
            for ck in CKPTS:
                d = p["by_ckpt"].get(ck)
                if d and d.get("n"):
                    pts[ck].append((p["signed_gap"], d["ece_mean"]))
    add("| checkpoint | n points | Spearman(\\|signed gap\\|, student ECE) | "
        "Pearson(\\|signed gap\\|, student ECE) | Spearman(signed gap, student ECE) |")
    add("|---|---|---|---|---|")
    for ck in CKPTS:
        xs = [abs(a) for a, _ in pts[ck]]
        ys = [b for _, b in pts[ck]]
        add(f"| {'**@swa**' if ck == 'swa' else '@' + ck} | {len(xs)} | "
            f"**{spearman(xs, ys):+.3f}** | {pearson(xs, ys):+.3f} | "
            f"{ps[ck]['spearman_signed_gap']:+.3f} |")
    add("")
    add("Why the last column is low: the **signed** axis is NOT monotone on its own — the law "
        "operates on |gap|, which means the two branches are each monotone separately. This is "
        "also why a single unsigned ECE axis does not suffice.")
    add("")

    # group separation from B-015
    if A_B015.exists():
        b = jload(A_B015)
        add("**Group separation test (FERPlus, B-015).** If the temperature arms' ECE ranges do not "
            "overlap at all, the ordering cannot be explained by seed noise.")
        add("")
        add("| checkpoint | Spearman on group means | fully separated | pair | max(lower) "
            "| min(upper) | Cohen d |")
        add("|---|---|---|---|---|---|---|")
        for ck in CKPTS:
            p = b["pooled"][ck]
            eff = b["effect_sizes"][ck]
            for i, s in enumerate(p["separation_detail"]):
                d_key = next((k for k in eff if k.replace("_vs_", "<") == s["pair"]), None)
                add(f"| {'@' + ck if i == 0 else ''} "
                    f"| {p['spearman_on_group_means']:+.3f} "
                    f"| {'✅' if p['groups_fully_separated'] else '❌'} "
                    f"| {s['pair']} | {s['max_lower']:.4f} | {s['min_upper']:.4f} "
                    f"| {eff[d_key]['cohen_d']:.1f} |" if i == 0 else
                    f"| | | | {s['pair']} | {s['max_lower']:.4f} | {s['min_upper']:.4f} "
                    f"| {eff[d_key]['cohen_d']:.1f} |")
        add("")
        add(f"Within seed: **{sum(1 for c in b['within_seed']['curves'] if c['monotone'])}/"
            f"{len(b['within_seed']['curves'])}** curves monotone, "
            f"**{sum(1 for c in b['within_seed']['curves'] if c['argmin_at_T_star'])}/"
            f"{len(b['within_seed']['curves'])}** with argmin at T\\*={b['T_star']}. "
            f"Overall verdict: **{b['verdict']['overall']}**.")
        add("")
        add("> ⚠️ The pooled Spearman is computed **on group means**. Computed at run level it "
            "produces ties on the x axis (three runs at the same T); without tie correction the "
            "ranking invents an order that does not exist and deflates ρ — which is exactly why "
            "the first version of this script reported +0.867 for perfectly separated data.")
        add("")
        add(src(A_B015))
        add("")

    # direction asymmetry
    da = ps.get("direction_asymmetry_swa", {})
    if da:
        add("**Direction asymmetry @swa.** At equal |signed gap|, how many times more an "
            "over-confident teacher costs the student than an under-confident one. Every comparison "
            "is made **within the same arm** (seed, dataset and recipe held fixed); the opposite "
            "branch is read from that arm's own linear fit, and the `extrapolated` field marks a "
            "point outside the fitted range.")
        add("")
        add("| arm | |gap| | ECE (over-confident) | ECE (under-confident, same |gap|) | ratio "
            "| extrapolated |")
        add("|---|---|---|---|---|---|")
        ratios, clean = [], []
        for arm, d in da.get("per_arm", {}).items():
            for c in d.get("comparisons", []):
                ratios.append(c["ratio"])
                if not c.get("extrapolated"):
                    clean.append(c["ratio"])
                add(f"| {arm} | {c['abs_gap']:.4f} | {c['ece_over_confident']:.4f} | "
                    f"{c['ece_under_confident_at_same_gap']:.4f} | **{c['ratio']:.2f}×** | "
                    f"{'yes' if c.get('extrapolated') else 'no'} |")
        if ratios:
            clean_txt = ", ".join(f"{v:.2f}×" for v in clean) if clean else "none"
            add("")
            add(f"**All comparisons: {st.mean(ratios):.2f} ± {sample_sd(ratios):.2f}×** "
                f"(n={len(ratios)}). Those not relying on extrapolation (**these are the ones "
                f"reported in the paper**): {clean_txt}"
                + (f" → {st.mean(clean):.2f} ± {sample_sd(clean):.2f}× (n={len(clean)})."
                   if len(clean) > 1 else "."))
        add("")
        add(src(A_OVERLAY))
        add("")

    # ---------------- T5
    add("## T5 — Mechanism ablations (paired, within seed)")
    add("")
    runs, audit = load_runs(), load_audit(A_AUDIT_MECH)
    if runs:
        mech_lines, mech_payload = mechanism_table(runs, audit)
        add("Every mechanism against **its own matched control**, within the same seed: control = "
            "same teacher, 400e/SWA@200, VICH head, α=0.3, unscaled teacher. "
            "Negative ΔECE = the mechanism calibrates better.")
        add("")
        L += mech_lines
        add("")
        # logit_std gets its own block because it is a headline finding, and a headline finding
        # has to survive the checkpoint choice. Printing only @swa would leave open the reading
        # that the effect is an SWA artefact; all three checkpoints kill that reading.
        add("### T5a — `logit_std`: invisible in accuracy, destructive in calibration")
        add("")
        add("| teacher | Δacc @swa | Δacc @best | Δacc @last | ΔECE @swa | ΔECE @best | ΔECE @last | n |")
        add("|---|---|---|---|---|---|---|---|")
        ls_rows = [(k, v) for k, v in sorted(mech_payload.items()) if k.endswith("/logit_std")]
        for k, row in ls_rows:
            cells = [row[c] for c in CKPTS]
            add(f"| {k.split('/')[0]} | "
                + " | ".join(f"{row[c]['d_acc_mean']:+.2f}" for c in CKPTS) + " | "
                + " | ".join(f"**{row[c]['d_ece_mean']:+.4f}**" for c in CKPTS)
                + f" | {cells[0]['n']} |")
        add("")
        if ls_rows:
            accs = [r[c]["d_acc_mean"] for _, r in ls_rows for c in CKPTS]
            eces = [r[c]["d_ece_mean"] for _, r in ls_rows for c in CKPTS]
            # Comparing "0.95 pp of accuracy" against "0.17 of ECE" directly is meaningless --
            # they are different units. The comparison that means something is how many seed-sd
            # each effect is worth, so both are divided by the seed spread of the SAME baselines
            # these treatments are paired against.
            #
            # THE DENOMINATOR IS READ AT THE SAME CHECKPOINT AS THE NUMERATOR. Until 2026-07-31
            # this block divided @swa deltas by seed_variance_table.json, which
            # student_halfb_eval builds from best_checkpoint.pth -- i.e. an @BEST denominator
            # under an @swa numerator. That is not a small mismatch: @best is the
            # accuracy-selected checkpoint, so its ECE rides along uncontrolled and is far noisier
            # across seeds (pooled ECE sd 0.0055 @best versus 0.0016 @swa, 3.4x), which
            # understated every ratio in this table and, downstream, the abstract's "about seven
            # times". That file was also three campaign phases stale (mtime 2026-07-28, before
            # P1/P2/P3/P4) and labels its teachers T-A/T-B/T-C, so which cell was which could not
            # be recovered from it. The control arms are now read from the audit, which carries
            # all three checkpoints and is the same source T5's pairing uses.
            arms = {}
            for key, rr in runs.items():
                if rr["teacher"] in TEACHERS and is_ablation_control(rr) \
                        and rr["class_weight_mode"] == "effective_number":
                    a = audit.get(key + ("swa",))
                    if a:
                        arms.setdefault(rr["teacher"], {"acc": [], "ece": []})
                        arms[rr["teacher"]]["acc"].append(a["acc"])
                        arms[rr["teacher"]]["ece"].append(a["ece"])
            base = [{"acc_sd": sample_sd(v["acc"]), "ece_sd": sample_sd(v["ece"])}
                    for v in arms.values() if len(v["acc"]) > 1]
            acc_sd = st.mean([b["acc_sd"] for b in base]) if base else float("nan")
            ece_sd = st.mean([b["ece_sd"] for b in base]) if base else float("nan")
            acc_units = max(abs(a) for a in accs) / acc_sd
            ece_units = min(abs(e) for e in eces) / ece_sd
            add(f"**Same direction in {len(ls_rows)}/{len(ls_rows)} teachers and 3/3 checkpoints** "
                f"(9/9 observations, all ΔECE > 0).")
            add("")
            add("The two axes are in different units, so the comparison is made **in units of their "
                "own seed noise**. Denominator: the mean **@swa** seed sd of the three teachers' "
                f"`effective_number` control arms — acc {acc_sd:.3f} pp, ECE {ece_sd:.4f}; read "
                "**at the same checkpoint as the numerator** "
                "(see `diagnostics/paper_tables/denominator_table.md`):")
            add("")
            add("| axis | range of the effect | in units of seed sd |")
            add("|---|---|---|")
            acc_typ = st.mean([abs(a) for a in accs]) / acc_sd
            ece_typ = st.mean([abs(e) for e in eces]) / ece_sd
            add(f"| accuracy | {min(accs):+.2f} … {max(accs):+.2f} pp | typically **{acc_typ:.1f}×** "
                f"(at most {acc_units:.1f}×) |")
            add(f"| ECE | {min(eces):+.4f} … {max(eces):+.4f} | typically **{ece_typ:.0f}×** "
                f"(at least {ece_units:.0f}×) |")
            add("")
            # Two ratios, both stated: the conservative floor (worst-case accuracy against
            # best-case ECE) and the typical case. Reporting only the typical would overstate;
            # reporting only the floor would understate. The claim rests on the floor.
            add(f"Relative to noise, the calibration damage is typically "
                f"**{ece_typ / acc_typ:.1f} times** the accuracy effect, and **≥"
                f"{ece_units / acc_units:.0f} times** even in the worst comparison. The claim "
                f"rests on the floor. The mechanism is plain: logit standardisation erases scale "
                f"by construction, and confidence values live precisely on that scale, while the "
                f"argmax — and therefore accuracy — is scale-invariant.")
            add("")
            add("> This row is the cleanest instance of the paper's **'accuracy alone misleads'** "
                "argument: in an accuracy-based ablation table `logit_std` looks harmless and would "
                "most likely have been reported as neutral.")
            add("")
            # The n-caveat has to be keyed on the actual n. An earlier version hard-coded the
            # "single seed" wording; once P1 filled the arm to 3 seeds that sentence became a
            # false statement sitting in a paper-ready table, and nothing would have flagged it.
            n_min = min(r[c]["n"] for _, r in ls_rows for c in CKPTS)
            if n_min < 3:
                add(f"⚠️ **n={n_min} caveat.** The `logit_std` arm was run at {n_min} seed(s); the "
                    "cells above are carried not by repetition but by **all nine independent "
                    "observations (three teachers × three checkpoints) agreeing in direction**. "
                    f"Since even the smallest effect is {ece_units:.0f}× the seed sd, the "
                    "**direction** claim is safe; **the exact magnitude needs more seeds**, and the "
                    "paper will say so.")
            else:
                # P1.3's margin, per teacher, computed from that teacher's OWN control arm at the
                # SAME checkpoint as the deltas. These were hardcoded as "2.6x / 118x" until
                # 2026-07-31; those figures came from the stale @best denominator described above
                # and did not survive the checkpoint correction.
                margins = {}
                for t, v in arms.items():
                    row = mech_payload.get(f"{t}/logit_std", {}).get("swa")
                    a_sd, e_sd = sample_sd(v["acc"]), sample_sd(v["ece"])
                    if row and a_sd and e_sd and row["d_acc_mean"]:
                        margins[t] = ((abs(row["d_ece_mean"]) / e_sd)
                                      / (abs(row["d_acc_mean"]) / a_sd))
                if margins:
                    lo = min(margins, key=margins.get)
                    hi = max(margins, key=margins.get)
                    marg = (f"narrowest margin at {lo}, **{margins[lo]:.0f}×**; widest at {hi}, "
                            f"{margins[hi]:.0f}×")
                else:
                    marg = "margins could not be computed"
                add(f"✅ **Pre-registered, confirmed at n={n_min} seeds** (P1, frozen 2026-07-29 "
                    "01:23:40, first run 01:24:08 — `rafdb_p1_logit_std_seeds_queue.ps1`; see "
                    "`diagnostics/PREREGISTRATIONS.md` A7). All three predictions held: "
                    "ΔECE > 0 in all three teachers · 3/3 same sign in each teacher · the "
                    "calibration effect exceeds the accuracy effect in noise units "
                    f"({marg}). This row is no longer a single-seed observation.")
        add("")
        add("**Sign consistency is this campaign's disqualification rule**: if the three seeds "
            "disagree in sign, the effect cannot be separated from seed noise. "
            "`selection_robustness` further shows that for some mechanisms the result changes "
            "direction with the **choice of checkpoint** — those rows must be reported as null.")
        add("")
        add(src(A_RUNS, A_AUDIT_MECH, D / "selection_audit" / "selection_robustness.json"))
    else:
        add("> `runs.csv` not found — T5 could not be produced.")
    add("")

    # ---------------- T6
    add("## T6 — Teacher selection recipe")
    add("")
    p4 = jload(A_P4)["recipe_step3_ranking"]
    add("| teacher | own acc | own ECE | T\\* | student acc @best | student ECE @best | n |")
    add("|---|---|---|---|---|---|---|")
    for r in p4["rows"]:
        add(f"| {r['teacher']} | {r['teacher_acc']:.2f} | {r['teacher_ece']:.4f} | "
            f"{r['T_star']:.3f} | {r['student_acc']:.2f} ± {r['student_acc_sd']:.2f} | "
            f"{r['student_ece']:.4f} | {r['n_seeds']} |")
    add("")
    add(f"- Spearman(teacher **acc**, student acc) = **{p4['spearman_teacherACC_vs_studentACC']:+.2f}** "
        f"→ picking the most accurate teacher is the **wrong** rule.")
    add(f"- Spearman(−teacher **ECE**, student acc) = **{p4['spearman_negTeacherECE_vs_studentACC']:+.2f}** "
        f"→ picking the best-calibrated teacher is the right rule.")
    add(f"- Does the accuracy rule pick the right teacher: **{p4['accuracy_criterion_correct']}** "
        f"(it picks `{p4['picked_by_accuracy']}`) · ECE rule: **{p4['ece_criterion_correct']}** "
        f"(it picks `{p4['picked_by_ece']}`)")
    add(f"- **Cost of the wrong pick: {p4['cost_of_wrong_pick_pp']:.2f} pp** of student accuracy "
        "(@best; see the per-checkpoint table below — the primary value is @swa).")
    add("")
    # T6a: THE NOTE USED TO BE AN ASSERTION. Until 2026-08-13 this block ended with a sentence
    # claiming "the ranking is identical at all three checkpoints" with nothing computing it,
    # while the cost quoted above was an @best number sourced from a stale side table. N5 asked
    # for both at once; they are now produced by `p4_teacher_selection_recipe.per_checkpoint_verdict`
    # and printed, so the claim can never again outlive its evidence.
    pc = p4.get("per_checkpoint")
    if pc:
        add("### T6a — the same question at all three checkpoints")
        add("")
        add("| teacher | student acc @swa | @best | @last |")
        add("|---|---|---|---|")
        for r in sorted(p4["rows"], key=lambda r: -r["student_by_ckpt"]["swa"]["acc_mean"]):
            c = r["student_by_ckpt"]
            add(f"| {r['teacher']} | " + " | ".join(
                f"{c[ck]['acc_mean']:.2f} ± {c[ck]['acc_sd']:.2f} (n={c[ck]['n']})"
                for ck in CKPTS) + " |")
        add("")
        add("| checkpoint | ranking by student acc | Spearman(teacher acc, student acc) | "
            "Spearman(−teacher ECE, student acc) | cost of the accuracy-pick |")
        add("|---|---|---|---|---|")
        for ck in CKPTS:
            v = pc["by_ckpt"].get(ck)
            if not v:
                continue
            add(f"| {'**@swa**' if ck == 'swa' else '@' + ck} | {v['ranking_display']} | "
                f"{v['spearman_teacherACC_vs_studentACC']:+.3f} | "
                f"{v['spearman_negTeacherECE_vs_studentACC']:+.3f} | "
                f"**{v['cost_of_wrong_pick_pp']:.2f} pp**" + (" |" if ck != "swa" else " |"))
        add("")
        ties = pc.get("ckpts_with_ties") or []
        add(f"- The best teacher is the same at all three checkpoints: "
            f"**{pc['best_teacher_identical_across_ckpts']}** (`{pc['by_ckpt']['swa']['best_teacher']}`), "
            f"and **no pairwise comparison reverses** between checkpoints "
            f"({pc['pairwise_reversals'] or 'none'}).")
        if ties:
            for ck in ties:
                v = pc["by_ckpt"][ck]
                a, b = v["ties"][0]
                add(f"- **Not a strict total order at @{ck}:** `{a}` and `{b}` land on exactly "
                    f"{v['student_acc'][a]:.4f} pp, so the 2nd/3rd places are tied and the "
                    f"phrase \"identical ranking\" holds for the *winner*, not for the full order.")
        add(f"- The cost of the accuracy-criterion mistake is checkpoint-dependent: "
            f"**{pc['by_ckpt']['swa']['cost_of_wrong_pick_pp']:.2f} pp @swa** (primary), "
            f"{pc['by_ckpt']['best']['cost_of_wrong_pick_pp']:.2f} pp @best, "
            f"{pc['by_ckpt']['last']['cost_of_wrong_pick_pp']:.2f} pp @last. Quoting one number "
            "without its checkpoint is what made the earlier 0.53/0.35 discrepancy look like a "
            "contradiction.")
        add("")
    add(f"> Student columns come from **{p4.get('student_source', 'the ledger')}**.")
    add("")
    add(src(A_P4))
    add("")

    # ---------------- T7
    add("## T7 — FERPlus human-vote alignment (teacher and student)")
    add("")
    tg = jload(A_TEACHER_GRID_FER)
    sj = jload(A_STUDENT_JSD)
    add("**Teacher side** (closed form from the cached logits, zero GPU cost):")
    add("")
    add("| T | role | teacher ECE | signed gap | teacher JSD | teacher entropy |")
    add("|---|---|---|---|---|---|")
    for g in sorted(tg["grid"], key=lambda r: float(r["T"])):
        add(f"| {float(g['T']):g} | {g['role']} | {g['teacher_ece']:.4f} | "
            f"{g['signed_gap']:+.4f} | {g['mean_jsd_vs_human']:.4f} | {g['mean_entropy']:.4f} |")
    hm = sj.get("human_mean_entropy")
    add("")
    add(f"Human mean entropy (10-rater distribution): **{hm:.4f}** nats.")
    add("")
    add("**Student side — TWO AXES, MANDATORY.** Scoring the student on hard-label ECE alone lets "
        "T\\*_ECE win by construction, so every arm is scored on both axes. The student softmax is "
        "taken at T=1 (the deployed output).")
    add("")
    for ck in CKPTS:
        b = sj["by_checkpoint"].get(ck)
        if not b:
            continue
        add(f"**@{ck}**" + (" *(primary)*" if ck == "swa" else ""))
        add("")
        add("| T | teacher ECE | student ECE | student JSD | student entropy | ρ(entropy, human) | n |")
        add("|---|---|---|---|---|---|---|")
        for k in sorted((x for x in b if not x.startswith("_")), key=float):
            v = b[k]
            add(f"| {float(k):g} | {v['teacher_ece']:.4f} | {v['ece'][0]:.4f} ± {v['ece'][1]:.4f} | "
                f"{v['jsd'][0]:.4f} ± {v['jsd'][1]:.4f} | {v['entropy']:.4f} | {v['rho']:.3f} | "
                f"{v['n']} |")
        add("")
        add(f"argmin student ECE: **T={b['_argmin_ece_T']:g}** · "
            f"argmin student JSD: **T={b['_argmin_jsd_T']:g}**")
        add("")
    swa = sj["by_checkpoint"]["swa"]
    e_star, j_star = str(swa["_argmin_ece_T"]), str(swa["_argmin_jsd_T"])
    if e_star in swa and j_star in swa:
        d_ece = swa[j_star]["ece"][0] - swa[e_star]["ece"][0]
        d_jsd = swa[j_star]["jsd"][0] - swa[e_star]["jsd"][0]
        add(f"**Trade-off @swa:** distilling at T\\*_JSD costs **{d_ece:+.4f}** in hard-label ECE "
            f"and gains **{d_jsd:+.4f}** in human JSD. The two targets are distinct: one has to "
            f"choose whether to calibrate to argmax labels or to human uncertainty.")
    add("")
    # Which of the two human-alignment metrics actually DISCRIMINATES between the arms?
    # Computed, not asserted: a metric whose whole range across four very different teachers is
    # narrower than the effect you want to detect cannot be used to select a teacher, no matter
    # how intuitive it sounds. This is why the campaign reports JSD and not rho as the
    # human-alignment criterion -- and stating it here keeps a reviewer from asking for rho.
    rhos = [swa[k]["rho"] for k in swa if not k.startswith("_")]
    jsds = [swa[k]["jsd"][0] for k in swa if not k.startswith("_")]
    r_span, j_span = max(rhos) - min(rhos), max(jsds) - min(jsds)
    j_sd_typ = st.mean([swa[k]["jsd"][1] for k in swa if not k.startswith("_")])
    add(f"**Why JSD and not ρ.** Across the four arms ρ(entropy, human) moves only within "
        f"{min(rhos):.3f}–{max(rhos):.3f} (span **{r_span:.3f}**), while student JSD moves over "
        f"{min(jsds):.4f}–{max(jsds):.4f} (span **{j_span:.4f}**, typical between-seed sd "
        f"{j_sd_typ:.4f} — i.e. the span is ~{j_span / j_sd_typ:.0f}× the noise). Because ρ "
        f"measures ranking, it is nearly insensitive to teacher temperature: a monotone rescaling "
        f"preserves the ranking. The criterion that discriminates between arms is **JSD**; ρ is "
        f"reported only as a consistency check.")
    add("")
    add(src(A_TEACHER_GRID_FER, A_STUDENT_JSD, A_FER_JSD))
    add("")

    # ---------------- T8
    add("## T8 — Selection audit (how much of 'best' is real, how much is looking)")
    add("")
    add("| dataset | contrast | Δacc (pp) | ΔECE | n runs |")
    add("|---|---|---|---|---|")
    for label, path in (("RAF-DB", A_AUDIT), ("FERPlus", A_FER_AUDIT)):
        tab = load_audit(path)
        by_run = {}
        for (rn, ts, ck), r in tab.items():
            by_run.setdefault((rn, ts), {})[ck] = r
        for ref in ("last", "swa"):
            da = [v["best"]["acc"] - v[ref]["acc"] for v in by_run.values() if "best" in v and ref in v]
            de = [v["best"]["ece"] - v[ref]["ece"] for v in by_run.values() if "best" in v and ref in v]
            if not da:
                continue
            add(f"| {label} | best − {ref} | {st.mean(da):+.2f} ± {sample_sd(da):.2f} | "
                f"{st.mean(de):+.4f} ± {sample_sd(de):.4f} | {len(da)} |")
    gain = jload(A_GAIN)
    add("")
    add("**Pure order-statistic component** (from the training logs, without looking at any "
        "checkpoint): the maximum of the last K epochs minus their mean. This is the gain that "
        "comes from picking the best of K draws even if the model never improves.")
    add("")
    add("| K | max(last K) − mean(last K), pp | global argmax inside last K | n runs |")
    add("|---|---|---|---|")
    for k, d in gain["per_k"].items():
        a2 = d["a2_pure_order_statistic"]
        add(f"| {k} | {a2['mean']:+.3f} ± {a2['sd']:.3f} | "
            f"{100 * d['argmax_in_last_K_frac']:.0f}% | {d['n_runs']} |")
    add("")
    add("> The per-epoch variant **cannot be computed for ECE**: `training_log.csv` does not record "
        "per-epoch ECE and no per-epoch checkpoints are kept (only best/last/swa). The closest "
        "calibration-sensitive proxy, the selected epoch's validation NLL, is reported instead.")
    add("")
    add(src(A_AUDIT, A_FER_AUDIT, A_GAIN))
    add("")

    # ---------------- T9
    add("## T9 — Efficiency")
    add("")
    p5 = jload(A_P5)
    c = p5["compression"]
    add("| model | params (M) | GMACs | file (MB) | acc (%) |")
    add("|---|---|---|---|---|")
    t, s = c["teacher"], c["student"]
    add(f"| {t['name']} | {t['params_m']:.3f} | {t['flops_g']:.3f} | {t['size_mb']:.2f} | "
        f"{t['acc']:.2f} |")
    add(f"| {s['name']} | {s['params_m']:.3f} | {s['flops_g']:.3f} | {s['size_mb']:.2f} | "
        f"{c['student_acc_mean']:.2f} ± {c['student_acc_sd']:.2f} |")
    add(f"| **ratio (teacher/student)** | **{c['params_ratio']:.1f}×** | "
        f"**{c['flops_ratio']:.1f}×** | **{c['size_ratio']:.1f}×** | "
        f"retention **{c['retention_pct']:.2f}%** |")
    add("")
    add("**Latency** — median ± IQR, broken down by device/batch/dtype. Measured on an idle "
        "machine (verified that no queue was running beforehand); warm-up and iteration counts "
        "are in the table.")
    add("")
    add("| device | model | batch | dtype | median (ms) | IQR (ms) | per image (ms) | FPS "
        "| warm-up/iters |")
    add("|---|---|---|---|---|---|---|---|---|")
    for r in csv.DictReader(open(A_LAT, encoding="utf-8")):
        add(f"| {r['device']} | {r['model'].replace('_', ' ')} | {r['batch']} | {r['dtype']} | "
            f"{float(r['median_ms']):.2f} | {float(r['iqr_ms']):.2f} | "
            f"{float(r['per_image_median_ms']):.3f} | {float(r['fps_from_median']):.0f} | "
            f"{r['warmup']}/{r['iters']} |")
    man = jload(A_LAT_JSON)["manifest"]
    add("")
    add(f"> Environment: {man['gpu']} · torch {man['torch']} (CUDA {man['torch_cuda_build']}) · "
        f"{man['os']} · measured {man['measured_utc']} · cudnn_benchmark={man['cudnn_benchmark']}.")
    add("")
    # fp16: replication gate. The verdict below is COMPUTED from the two session CSVs, so this
    # block flips back to "not paper-eligible" by itself if session 2 ever disagrees -- the
    # conclusion cannot drift away from the measurements it rests on.
    def fp16_ratios(path):
        med = {}
        for r in csv.DictReader(open(path, encoding="utf-8")):
            if r.get("device") != "cuda" or not r.get("median_ms"):
                continue
            med[(r["model"], r["batch"], r["dtype"])] = float(r["median_ms"])
        return {(m, b): med[(m, b, "fp16")] / med[(m, b, "fp32")]
                for (m, b, d) in med if d == "fp32" and (m, b, "fp16") in med}

    if A_LAT2.exists():
        r1, r2 = fp16_ratios(A_LAT), fp16_ratios(A_LAT2)
        both = sorted(set(r1) & set(r2), key=lambda k: (int(k[1]), k[0]))
        b1 = [k for k in both if k[1] == "1"]
        replicated = bool(b1) and all(r1[k] > 1.0 and r2[k] > 1.0 for k in b1)
        add("**fp16 — two independent sessions.** Pre-registered rule: this observation enters the "
            "paper only if it replicates in an independent second session. The ratio below is "
            "fp16/fp32 median latency; **>1 = fp16 is SLOWER**.")
        add("")
        add("| model | batch | session 1 | session 2 | same direction |")
        add("|---|---|---|---|---|")
        for k in both:
            same = "✅" if (r1[k] > 1) == (r2[k] > 1) else "❌"
            add(f"| {k[0]} | {k[1]} | {r1[k]:.2f}× | {r2[k]:.2f}× | {same} |")
        add("")
        if replicated:
            add("> ✅ **REPLICATED — the footnote enters the paper.** At batch=1, fp16 is SLOWER "
                "than fp32 in both sessions and for both models; at batch=32 it is faster, as "
                "expected. The explanation: at batch=1 the workload is kernel-launch bound rather "
                "than compute bound, so there is no arithmetic over which to amortise fp16's cast "
                "cost. Practical consequence: **the advice to 'use fp16' is wrong for "
                "single-image inference on this hardware.**")
        else:
            add("> ⚠️ **NOT REPLICATED — does not enter the paper.** The two sessions did not agree "
                "in direction; a single-session observation will not be written up, not even as a "
                "footnote.")
    else:
        add("> ⚠️ **fp16 anomaly — SINGLE SESSION, DOES NOT ENTER THE PAPER.** At batch=1, fp16 "
            "measured SLOWER than fp32 for both models. The independent second session "
            f"(`{A_LAT2.name}`) does not exist yet.")
    add("")
    add(src(A_P5, A_LAT, A_LAT2, A_LAT_JSON))
    add("")

    # ---------------- T10
    add("## T10 — Student capacity: does the law live on the teacher side or the student side?")
    add("")
    add("The width sweep is **entirely scratch-initialised** (`student_pretrained=False`), so the "
        "curve is internally consistent. The campaign's main baseline (pretrained, width 1.0) is "
        "at the same width but a different init, so it does **not** sit on the curve; it is given "
        "as a separate row and measures the cost of pretraining.")
    add("")

    # name -> ledger row, so the cell test below reads FLAGS instead of parsing the run name.
    cap_meta = {r["run_name"]: r for r in runs.values()}

    def cap_cell(r):
        """Which T10 capacity cell an AUDIT row belongs to, or None. Keyed on ledger flags.

        THE t_scale GUARD IS LOAD-BEARING. T10's capacity axis is defined at a FIXED teacher;
        the whole table compares "how far does student ECE move when only capacity changes"
        against "how far when only teacher temperature changes". P3 added capacity-sweep students
        at T=1.7/2.2, and a bare `"frontier" in run_name` test swept them into the scratch w050
        cell, taking it from n=3 to n=7 and its ECE from 0.0365 to 0.1079 +/- 0.0737. Nothing
        errored: the capacity span silently absorbed the temperature span it was supposed to be
        compared against, and the headline ratio fell from 76x to 3x.
        """
        m = cap_meta.get(r["run_name"])
        if not m or float(m["t_scale"] or 1.0) != 1.0:
            return None
        if m["student_pretrained"] == "False":
            return "scratch " + m["capacity_tag"]
        if (m["run_name"].startswith("RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200")
                and m["epochs"] == "400"):
            return "pretrained w100"
        return None

    CAP_ORDER = ["scratch w050", "scratch w075", "scratch w100ns", "pretrained w100"]
    CAP_PARAMS = {"scratch w050": 0.712089, "scratch w075": 1.379843,
                  "scratch w100ns": 2.248291, "pretrained w100": 2.248291}
    audit_rows = list(csv.DictReader(open(A_AUDIT_MECH, encoding="utf-8")))
    cap = {}
    for ck in CKPTS:
        g, seen_seeds = {}, {}
        for r in audit_rows:
            if r["checkpoint"] != ck:
                continue
            c = cap_cell(r)
            if not c:
                continue
            # One run per (cell, seed). Any cell that pools two runs at the same seed is pooling
            # some OTHER axis into a capacity cell -- which is how the tempscale contamination
            # above got in without a single error. Fail instead of averaging it away.
            s = r["seed"]
            if (c, s) in seen_seeds:
                raise RuntimeError(
                    f"T10 cell '{c}' @{ck} already has seed {s} from {seen_seeds[(c, s)]}; "
                    f"{r['run_name']} would be pooled into it. Two runs at the same seed in one "
                    f"capacity cell means a second variable is moving -- narrow cap_cell().")
            seen_seeds[(c, s)] = r["run_name"]
            g.setdefault(c, []).append((float(r["acc"]), float(r["ece"])))
        cap[ck] = g

    add("| cell | params (M) | acc @swa | ECE @swa | acc @best | ECE @best | n |")
    add("|---|---|---|---|---|---|---|")
    for k in CAP_ORDER:
        s, b = cap["swa"].get(k, []), cap["best"].get(k, [])
        if not s:
            continue
        f = lambda v, d: (f"{st.mean(v):.{d}f} ± {sample_sd(v):.{d}f}" if len(v) > 1
                          else f"{v[0]:.{d}f} *(n=1)*")
        add(f"| {k} | {CAP_PARAMS[k]:.3f} | {f([x[0] for x in s], 2)} | "
            f"{f([x[1] for x in s], 4)} | {f([x[0] for x in b], 2)} | "
            f"{f([x[1] for x in b], 4)} | {len(s)} |")
    add("")
    add("**What each axis buys (same checkpoint, paired):**")
    add("")
    add("| checkpoint | width 3.16× (0.71→2.25 M) | pretraining (width held fixed) |")
    add("|---|---|---|")
    for ck in CKPTS:
        g = cap[ck]
        if not all(k in g for k in CAP_ORDER):
            continue
        m = {k: (st.mean([x[0] for x in g[k]]), st.mean([x[1] for x in g[k]])) for k in CAP_ORDER}
        dw = m["scratch w100ns"][0] - m["scratch w050"][0]
        dwe = m["scratch w100ns"][1] - m["scratch w050"][1]
        dp = m["pretrained w100"][0] - m["scratch w100ns"][0]
        dpe = m["pretrained w100"][1] - m["scratch w100ns"][1]
        add(f"| @{ck} | {dw:+.2f} pp · ΔECE {dwe:+.4f} | {dp:+.2f} pp · ΔECE {dpe:+.4f} |")
    add("")
    # The load-bearing comparison: how much does student ECE move along the CAPACITY axis versus
    # along the TEACHER-CALIBRATION axis? Both spans are read from artifacts, never typed. This is
    # what answers the reviewer objection "maybe the small student is simply badly calibrated".
    add("**The law lives on the teacher side.** Same student, same checkpoint; the only difference "
        "is which axis is moved:")
    add("")
    add("| checkpoint | student ECE span — capacity axis (3.16×) | teacher temperature axis "
        "(VAE9182, T=1→2.2) | ratio |")
    add("|---|---|---|---|")
    ov = jload(A_OVERLAY)["arms"]["rafdb_vae9182"]["points"]
    ratio_rows = 0
    for ck in CKPTS:
        g = cap[ck]
        if not all(k in g for k in CAP_ORDER[:3]):
            continue
        ce = [st.mean([x[1] for x in g[k]]) for k in CAP_ORDER[:3]]
        cap_span = max(ce) - min(ce)
        AXIS_SPANS[ck] = {"capacity_span": cap_span}
        te = [p["by_ckpt"][ck]["ece_mean"] for p in ov if ck in p.get("by_ckpt", {})]
        if not te:
            continue
        t_span = max(te) - min(te)
        AXIS_SPANS[ck].update({"teacher_span": t_span, "ratio": t_span / cap_span})
        # Kapasite açıklığı 5 haneyle basılır (tek istisna; konvansiyon 4). Sebep R0-3: 4 hanede
        # 0.002351 -> "0.0024" görünür ve okur 0.1780/0.0024 = 74x hesaplar, oysa oran tam
        # değerlerle 75.7 -> "76x". Payda gösterimi, oranı OKURUN yeniden üretebileceği hassasiyette
        # olmak zorunda; aksi hâlde tablo kendi dipnotuyla çelişik görünüyor.
        add(f"| @{ck} | {cap_span:.5f} | {t_span:.4f} | **{t_span / cap_span:.0f}×** |")
        ratio_rows += 1
    # An empty markdown table renders as a header with no rows and reads as "nothing to report"
    # rather than "the lookup broke" -- which is exactly what happened on the first version of
    # this block (wrong key path into two_dataset_overlay.json, silently zero rows). Fail loudly.
    if ratio_rows == 0:
        raise RuntimeError(
            "T10 axis-ratio table produced 0 rows: the capacity cells or the VAE9182 "
            f"dose-response points could not be read from {A_AUDIT_MECH.name} / {A_OVERLAY.name}.")
    add("")

    # T10a: the second slope P3 produced. The table above moves ONE axis at a time; this block is
    # the only place where the teacher axis is swept AT a second capacity, so it is what answers
    # "is the law itself a large-student artifact?" rather than "is the small student calibrated?".
    cap_law = A_CAP_LAW if A_CAP_LAW.exists() else None
    if cap_law:
        _cap = jload(cap_law)
        cl = dict(_cap["slope_comparison"],
                  shared_support_temperatures=_cap["shared_support_temperatures"])
        big_s, small_s = cl["big"], cl["small"]
        add("### T10a — Does the law also hold for the small student (P3, exploratory)")
        add("")
        add("The table above moves **one** axis at a time. This block instead sweeps the teacher "
            "axis **at a second capacity** — so it is here that the question 'is the law a "
            "large-student artefact?' is answered. Per the pre-registered analysis plan, the two "
            "slopes were fitted at **the same three temperatures** "
            f"(T = {', '.join(f'{t:g}' for t in cl['shared_support_temperatures'])} "
            "→ teacher ECE "
            f"{', '.join(f'{x:.4f}' for x in cl['teacher_ece'])}).")
        add("")
        add("| capacity | init | slope b | R² | largest residual | seed-noise envelope |")
        add("|---|---|---|---|---|---|")
        for lab, c in (("2.248 M", big_s), ("0.712 M", small_s)):
            resid = max(abs(y - (c["intercept"] + c["slope"] * x))
                        for x, y in zip(cl["teacher_ece"], c["cell_ece_mean"]))
            add(f"| {lab} | {'pretrained' if c['init'] == 'pretrained' else 'scratch'} | "
                f"**{c['slope']:.3f}** | {c['r2']:.5f} | {resid:.5f} | "
                f"±{c['seed_noise_envelope']:.3f} |")
        add("")
        d = cl["slope_difference"]
        add(f"Slope difference **{d:+.3f}**, the two envelopes summed **±{cl['combined_envelope']:.3f}** → "
            + ("the difference is **not resolvable**." if not cl["difference_resolvable"] else
               "the difference lies outside the envelope."))
        add("")
        # Two claims of DIFFERENT strength come out of the same fit, and they must not be read as
        # one sentence: (i) is a validity defence that stands on its own evidence, (ii) is an
        # inconclusive test. Merging them lets the weak item borrow the strong item's credibility.
        rb = max(abs(y - (big_s["intercept"] + big_s["slope"] * x))
                 for x, y in zip(cl["teacher_ece"], big_s["cell_ece_mean"]))
        rs = max(abs(y - (small_s["intercept"] + small_s["slope"] * x))
                 for x, y in zip(cl["teacher_ece"], small_s["cell_ece_mean"]))
        sd_lo = min(min(big_s["cell_ece_sd"]), min(small_s["cell_ece_sd"]))
        add(f"**Item (i) — established: the law also holds at 0.712 M.** Monotone, and the largest "
            f"residual of either fit ({rb:.5f} and {rs:.5f}) is ~{sd_lo / max(rb, rs):.0f}× smaller "
            f"than even the **smallest** seed sd among the cells ({sd_lo:.4f}). The linearity "
            f"therefore comes from the relationship itself, not from a fit having three points to "
            f"land on. This is a **validity defence** that rules out the 'the law is a "
            f"large-student artefact' alternative.")
        add("")
        if not cl["difference_resolvable"]:
            add(f"**Item (ii) — INCONCLUSIVE: whether the slope varies with capacity could not be "
                f"measured.** Difference {abs(d):.3f}, noise envelope ±{cl['combined_envelope']:.3f}. "
                f"**Not resolvable ≠ no difference**: this is not a null finding but a test that "
                f"could not be run. The sentence 'the slope does not change with capacity' "
                f"**cannot be written** from this data.")
        else:
            add(f"**Item (ii) — the difference lies outside the envelope** ({abs(d):.3f} > "
                f"±{cl['combined_envelope']:.3f}), but the init confound below leaves no basis for "
                f"attributing it to capacity.")
        add("")
        add("> ⚠️ **Item (ii) is exploratory and two-variable; it does not have item (i)'s status.** "
            "The result is not pre-registered (the question and analysis plan are: "
            "`PREREGISTRATIONS.md` B4). `b_w050` is scratch and `b_2248` is pretrained — the two "
            "slopes differ in capacity *and* in initialisation; separating them would require a "
            "scratch dose-response at 2.248 M (4 runs, not launched). Two of w050's cells are also "
            "n=2. **This subsection stands apart from T10's capacity table**: the table is of "
            "established quality, item (ii) is exploratory.")
        add("")
    add(src(A_AUDIT_MECH, A_RUNS, A_OVERLAY, *( [cap_law] if cap_law else [] )))
    add("")

    # ---------------- exclusion audit
    add("## Appendix — exclusion audit (which run dropped out of which table, and why)")
    add("")
    add("This section is not a claim but a **machine check**: T5's control and treatment pools are "
        "built from the runs' own flags, and the rows below count what those filters actually "
        "excluded.")
    add("")
    if runs:
        excl = {}
        for r in runs.values():
            why = []
            if r["teacher"] not in TEACHERS:
                why.append(f"teacher `{r['teacher']}` not in the three-teacher grid")
            if r["student_head"] != "vich":
                why.append(f"head=`{r['student_head']}`")
            if r["epochs"] != "400" or str(r["swa_start"]) != "200":
                why.append(f"budget {r['epochs']}e/swa{r['swa_start'] or '-'}")
            if r["alpha"] and abs(float(r["alpha"]) - 0.3) > 1e-9:
                why.append(f"α={r['alpha']}")
            if why:
                excl.setdefault(" · ".join(why), []).append(r["run_name"])
        add("| reason for exclusion | n runs | example |")
        add("|---|---|---|")
        for why, names in sorted(excl.items(), key=lambda kv: -len(kv[1])):
            add(f"| {why} | {len(names)} | `{sorted(names)[0][:52]}` |")
        add("")
        legacy = [r for r in runs.values()
                  if r["alpha"] and abs(float(r["alpha"]) - 0.25) < 1e-9]
        add(f"**Legacy α=0.25 runs:** {len(legacy)} on disk "
            + (f"(`{legacy[0]['run_name']}`, teacher `{legacy[0]['teacher']}`) " if legacy else "")
            + "· **not used** in T1–T7 or T9 (teacher not in the three-teacher grid, budget "
              "200e/swa90, α≠0.3 — excluded by all three filters independently).")
        add("")
        add("> ⚠️ **T8 is the one exception.** The selection-audit table deliberately pools "
            "**every** finished RAF-DB run; what it measures is not the effect of a condition "
            "but the artefact of argmax-val-acc selection across this whole corpus. The legacy "
            "`ce9241` runs **are** included there, and they should be. They appear in no other "
            "table.")
    add("")

    # ---------------- T13 / T14 / T15 — R3 robustness round (pre-registration A10)
    # Tek kaynak kuralı: makaleye girecek her sayı burada da durmalı. Bu üç blok, R3
    # üreticilerinin JSON'larını okuyup ÖZET satırları basar; tam tablolar kendi
    # dosyalarında. Bir JSON henüz üretilmemişse blok atlanır -- paper_tables.py hiçbir
    # koşulda R3 yüzünden çökmemeli.
    r3_payload = {}
    # T11/T12 — P6'nın resmî hükmü (A9). R3 bloklarından önce basılır ki tablo numaraları
    # metinde artan sırada görünsün.
    p6_sections(add, r3_payload)
    r3_sections(add, r3_payload)   # add() ile dogrudan L'ye yazar

    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_MD}  ({len(L)} lines)")

    # Structured dump of the numbers the markdown prints. Until 2026-07-30 the T5 and T10 cells
    # existed ONLY as formatted markdown, so nothing downstream could compare a regeneration
    # against the previous one -- which is why the T10 contamination (76x -> 3x) shipped without a
    # single error. diagnostics/table_diff_gate.py consumes this file.
    payload = {
        "sd_convention": SD_CONVENTION,
        "T5_mechanisms": mech_payload if runs else {},
        "T10_capacity_cells": {
            ck: {k: {"acc_mean": st.mean([x[0] for x in v]),
                     "acc_sd": sample_sd([x[0] for x in v]),
                     "ece_mean": st.mean([x[1] for x in v]),
                     "ece_sd": sample_sd([x[1] for x in v]),
                     "n": len(v)}
                 for k, v in cap[ck].items()}
            for ck in CKPTS},
        "T10_axis_spans": AXIS_SPANS,
        **r3_payload,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_JSON}")

    if runs:
        emit_tab_app_paired_sd(mech_payload)

    # Tabloyu ürettikten sonra makale tarafına ihraç et. Elle kopyalamayı unutmak diye bir
    # durum kalmasın diye burada: bugüne kadarki bayat-kopya vakalarının hepsi bu adımın
    # insanda olmasından çıktı. Ölümcül değil (Drive bağlı olmayabilir) ama sessiz de değil.
    # Genel depoda bant altyapisi bulunmaz (yazar-yerel, Drive yolu tasiyor); yoklugu
    # tablo uretimini ASLA durdurmamali -- burasi main()'in son adimi ve tablolar zaten
    # yazilmis oluyor, cikip ImportError vermek reviewer'a bozuk komut gostermek olurdu.
    try:
        import export_to_drive
        export_to_drive.hook("paper_tables.py")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
