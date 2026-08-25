"""8(a): the efficiency frontier -- our three student capacities on (params, MACs) x (acc, ECE),
positioned against published lightweight FER models.

WHAT IS OURS AND WHAT IS NOT. Our four points (three scratch widths + the pre-trained student) and
the teacher come from artifacts in this repo. Published models come from
`diagnostics/literature_fer_models.csv`, which ships EMPTY: numbers that enter a paper figure have
to be transcribed from the source, and a figure that silently contains half-remembered baselines is
worse than one that plots nothing. If the file has no data rows the figure still renders -- our
curve alone -- and both the console and the caption say so.

THE CALIBRATION PANEL IS THE POINT. Accuracy-vs-compute frontiers are standard. The second panel
plots ECE against compute, and it is nearly always empty on the literature side, because
lightweight-FER papers report accuracy and FLOPs and essentially never calibration. That emptiness
is a finding, not a gap in the plot.

CAPACITY CONFOUND. All three widths are scratch-init; the pre-trained student is the same width as
the largest, drawn separately. See T10 -- it is not the curve's endpoint.

Read-only, zero GPU. Outputs -> diagnostics/p5_efficiency/efficiency_frontier.{png,json,md}
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
RUNS = ROOT / "runs.csv"
LIT = ROOT / "diagnostics" / "literature_fer_models.csv"
OUT_DIR = ROOT / "diagnostics" / "p5_efficiency"
CKPT = "swa"

PRETRAINED_PREFIX = "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200"
TEACHER = {"name": "POSTERv2 (teacher)", "params_m": 58.334272, "gmacs": 8.482723136,
           "size_mb": 555.0154619216919, "acc": 91.8187744458931, "ece": 0.0136}


def load_literature():
    """Rows with at least params_m and rafdb_acc. Comment lines start with '#'."""
    if not LIT.exists():
        return [], []
    rows, partial = [], []
    with open(LIT, encoding="utf-8") as fh:
        for r in csv.DictReader(l for l in fh if not l.lstrip().startswith("#")):
            if not (r.get("model") or "").strip():
                continue
            try:
                p, a = float(r["params_m"]), float(r["rafdb_acc"])
            except (TypeError, ValueError):
                partial.append(r.get("model", "?"))
                continue
            e = None
            try:
                e = float(r["rafdb_ece"]) if (r.get("rafdb_ece") or "").strip() else None
            except ValueError:
                e = None
            g = None
            try:
                g = float(r["gmacs"]) if (r.get("gmacs") or "").strip() else None
            except ValueError:
                g = None
            rows.append({"model": r["model"].strip(), "params_m": p, "gmacs": g,
                         "acc": a, "ece": e, "source_note": (r.get("source_note") or "").strip()})
    return rows, partial


def cell_of(r):
    """Efficiency-frontier cell for a ledger row, or None -- from FLAGS, never from the name.

    Two guards, both learned the hard way (METHODS_DATA 5A.2):
      t_scale == 1.0   P3 added capacity-sweep students distilled from a TEMPERATURE-SCALED
                       teacher. Those belong to the calibration dose-response: a T=2.2 student
                       carries ECE ~0.20 and would drag the w050 cell from 0.037 to 0.108 while
                       its params and GMACs stay exactly where they were.
      pretrained flag  distinguishes the scratch sweep from the pre-trained anchor at width 1.0,
                       which is the comparison the frontier figure exists to make.
    """
    if float(r["t_scale"] or 1.0) != 1.0:
        return None
    if r["student_pretrained"] == "False":
        return "scratch " + r["capacity_tag"]
    if r["run_name"].startswith(PRETRAINED_PREFIX) and r["epochs"] == "400":
        return "pretrained w100"
    return None


def ours():
    meta, by_name = {}, {}
    for r in csv.DictReader(open(RUNS, encoding="utf-8")):
        k = cell_of(r)
        if not k:
            continue
        by_name[r["run_name"]] = k
        meta.setdefault(k, {"params_m": float(r["params_m"]), "gmacs": float(r["flops_g"])})
    cells = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        if r["checkpoint"] != CKPT:
            continue
        k = by_name.get(r["run_name"])
        if not k:
            continue
        c = cells.setdefault(k, {"acc": [], "ece": []})
        c["acc"].append(float(r["acc"]))
        c["ece"].append(float(r["ece"]))
    out = []
    for k, c in cells.items():
        if k not in meta:
            continue
        out.append({"cell": k, **meta[k],
                    "acc": st.mean(c["acc"]), "acc_sd": sample_sd(c["acc"]),
                    "ece": st.mean(c["ece"]), "ece_sd": sample_sd(c["ece"]), "n": len(c["acc"])})
    return sorted(out, key=lambda r: (r["params_m"], r["cell"]))


def main():
    pts = ours()
    if not pts:
        raise RuntimeError("no capacity points -- runs.csv / selection_audit.csv stale")
    lit, partial = load_literature()
    curve = [p for p in pts if p["cell"].startswith("scratch")]
    pre = [p for p in pts if not p["cell"].startswith("scratch")]
    lit_with_ece = [m for m in lit if m["ece"] is not None]

    # ---------------- table
    L = ["# 8(a) — Efficiency frontier", "",
         f"Producer: `diagnostics/efficiency_frontier.py` · @{CKPT} · {SD_CONVENTION}", "",
         "| nokta | params (M) | GMACs | acc (%) | ECE | n | kaynak |",
         "|---|---|---|---|---|---|---|"]
    for p in curve + pre:
        L.append(f"| {p['cell']} | {p['params_m']:.3f} | {p['gmacs']:.3f} | "
                 f"{p['acc']:.2f} ± {p['acc_sd']:.2f} | {p['ece']:.4f} ± {p['ece_sd']:.4f} | "
                 f"{p['n']} | this work |")
    L.append(f"| {TEACHER['name']} | {TEACHER['params_m']:.3f} | {TEACHER['gmacs']:.3f} | "
             f"{TEACHER['acc']:.2f} | {TEACHER['ece']:.4f} | 1 | this work (teacher) |")
    for m in lit:
        g = f"{m['gmacs']:.3f}" if m["gmacs"] is not None else "—"
        e = f"{m['ece']:.4f}" if m["ece"] is not None else "**yok**"
        L.append(f"| {m['model']} | {m['params_m']:.3f} | {g} | {m['acc']:.2f} | {e} | — | "
                 f"{m['source_note'] or 'literature'} |")
    L += ["", f"**Literature rows: {len(lit)}**"
              + ("" if lit else "  — `diagnostics/literature_fer_models.csv` is empty; "
                                "the figure was drawn from our points only.")]
    if lit:
        L.append(f"**{len(lit_with_ece)}/{len(lit)}** of them report ECE; "
                 f"the rest cannot appear in the calibration panel.")
    (OUT_DIR / "efficiency_frontier.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # ---------------- figure
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.0, 5.2))
    for ax, ykey, ysd, ylab, ttl in (
            (axA, "acc", "acc_sd", f"RAF-DB accuracy @{CKPT} (%)", "A · Accuracy vs. compute"),
            (axB, "ece", "ece_sd", f"student ECE @{CKPT}  ↓ better", "B · Calibration vs. compute")):
        ax.errorbar([p["params_m"] for p in curve], [p[ykey] for p in curve],
                    yerr=[p[ysd] for p in curve], color="#2471a3", marker="o", capsize=3,
                    lw=1.9, label="this work — scratch width sweep", zorder=3)
        for p in pre:
            ax.errorbar([p["params_m"]], [p[ykey]], yerr=[p[ysd]], color="#c0392b", marker="D",
                        markersize=9, capsize=3, ls="none", zorder=4,
                        label="this work — pretrained (same width)")
        ax.scatter([TEACHER["params_m"]], [TEACHER[ykey]], marker="*", s=260, color="#7d3c98",
                   zorder=4, label="teacher (POSTERv2)")
        shown = [m for m in lit if (ykey == "acc" or m["ece"] is not None)]
        if shown:
            ax.scatter([m["params_m"] for m in shown],
                       [m["acc"] if ykey == "acc" else m["ece"] for m in shown],
                       marker="x", s=60, color="#555", zorder=3, label="published lightweight FER")
            for m in shown:
                ax.annotate(m["model"], (m["params_m"], m["acc"] if ykey == "acc" else m["ece"]),
                            textcoords="offset points", xytext=(5, 4), fontsize=7.2, color="#555")
        elif ykey == "ece":
            msg = ("literature table empty —\nno comparison points added" if not lit
                   else "none of the added models\nreports ECE")
            ax.text(0.5, 0.42, msg, transform=ax.transAxes, ha="center", va="center",
                    fontsize=10, color="#888",
                    bbox=dict(boxstyle="round,pad=0.5", fc="#f4f4f4", ec="#bbb"))
        ax.set_xscale("log")
        ax.set_xlabel("parametre (M, log)")
        ax.set_ylabel(ylab)
        ax.set_title(ttl, fontsize=11)
        ax.grid(alpha=0.22)
    axA.legend(fontsize=8, loc="lower right")
    # The title must not assert anything about the literature that the literature table does not
    # yet contain. With an empty table the honest title is descriptive; the "accuracy everywhere,
    # calibration nowhere" claim only earns its place once rows exist to back it.
    if lit:
        title = (f"Efficiency frontier: {len(lit)} published models "
                 f"{len(lit_with_ece)}'i kalibrasyon bildiriyor")
    else:
        title = ("Efficiency frontier — this work's capacity points "
                 "(literature comparison not yet added)")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout()
    png = OUT_DIR / "efficiency_frontier.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)

    (OUT_DIR / "efficiency_frontier.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION, "checkpoint": CKPT,
        "ours": pts, "teacher": TEACHER,
        "literature_rows": lit, "literature_unparseable": partial,
        "literature_with_ece": len(lit_with_ece),
    }, indent=2), encoding="utf-8")

    print(f"our capacity points: {len(pts)}   literature rows: {len(lit)}")
    if partial:
        print(f"  skipped (missing params_m or rafdb_acc): {partial}")
    if not lit:
        print("  NOTE: literature_fer_models.csv has no data rows. Figure drawn with our points")
        print("        only. To position against published models, add rows with at minimum:")
        print("        model, params_m, rafdb_acc  (+ gmacs, rafdb_ece, source_note if available)")
    print(f"\nSaved {png}")
    print(f"Saved {OUT_DIR / 'efficiency_frontier.md'}")


if __name__ == "__main__":
    main()
