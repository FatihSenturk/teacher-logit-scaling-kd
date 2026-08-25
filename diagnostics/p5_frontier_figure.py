"""P5: the student-capacity frontier, and the figure that localises the calibration law.

WHAT THIS FIGURE ARGUES. The campaign's central claim is that student calibration is governed by
the TEACHER's calibration. The obvious reviewer objection is that a 2.2 M-parameter student is
simply too small to be well calibrated, and that everything we attribute to the teacher is really
a student-capacity effect. This figure answers that by sweeping the one axis the objection names
-- student width -- and showing that student ECE barely moves along it, while the same student's
ECE moves by two orders of magnitude more along the teacher-temperature axis.

Panel A (accuracy) carries a second, independent result: at fixed width, ImageNet pre-training is
worth about as much as tripling the parameter count -- at zero inference cost.

CONFOUND, HANDLED EXPLICITLY. All three width points are trained from scratch
(`student_pretrained=False`), so the width curve is internally clean. The campaign's main student
is pre-trained, so it is NOT a point on that curve -- it is plotted as a separate marker at the
same x, and the vertical distance between it and `scratch w100` is exactly the value of
pre-training. Drawing it as the curve's endpoint would silently mix the two axes.

Every number is read from artifacts (selection_audit.csv for the students, two_dataset_overlay.json
for the teacher-temperature band). Nothing is typed in. Read-only, zero GPU.

Outputs -> diagnostics/p5_efficiency/p5_frontier.{png,json}
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
OVERLAY = ROOT / "diagnostics" / "p1_dose_response" / "two_dataset_overlay.json"
OUT_DIR = ROOT / "diagnostics" / "p5_efficiency"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CKPT = "swa"                       # campaign primary; @best/@last go in the JSON, not the figure
PRETRAINED_PREFIX = "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200"
# params_m is deterministic per width; read once from the ledger rather than hard-coded here.
WIDTH_ORDER = ["w050", "w075", "w100ns"]
WIDTH_LABEL = {"w050": "0.50", "w075": "0.75", "w100ns": "1.00"}


def cell_of(r):
    """Figure cell for a ledger row, or None -- from FLAGS, never from the run name.

    `t_scale == 1.0` keeps P3's temperature-scaled capacity students out: they belong to the
    dose-response, and pooling them would put the w050 marker at the mean of {T=1.0, 1.7, 2.2},
    i.e. ECE 0.108 instead of 0.037, making the frontier appear to collapse at small width for no
    architectural reason (METHODS_DATA 5A.2).
    """
    if float(r["t_scale"] or 1.0) != 1.0:
        return None
    if r["student_pretrained"] == "False":
        return r["capacity_tag"]
    if r["run_name"].startswith(PRETRAINED_PREFIX) and r["epochs"] == "400":
        return "pretrained"
    return None


def params_by_width():
    """cell -> params (M), from runs.csv. Deterministic, so one row per cell suffices."""
    out = {}
    for r in csv.DictReader(open(ROOT / "runs.csv", encoding="utf-8")):
        k = cell_of(r)
        if k:
            out[k] = float(r["params_m"])
    return out


def collect():
    """cell -> {'acc': [...], 'ece': [...]} at CKPT, one entry per seed."""
    by_name = {r["run_name"]: cell_of(r)
               for r in csv.DictReader(open(ROOT / "runs.csv", encoding="utf-8"))}
    cells = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        if r["checkpoint"] != CKPT:
            continue
        key = by_name.get(r["run_name"])
        if not key:
            continue
        c = cells.setdefault(key, {"acc": [], "ece": []})
        c["acc"].append(float(r["acc"]))
        c["ece"].append(float(r["ece"]))
    return cells


def teacher_axis_span():
    """Student-ECE min/max across the VAE9182 teacher-temperature sweep, same checkpoint.

    Same student architecture, same budget, same seeds -- the ONLY difference from the capacity
    sweep is which axis is being moved. That is what makes the two spans comparable.
    """
    pts = json.loads(OVERLAY.read_text())["arms"]["rafdb_vae9182"]["points"]
    e = [p["by_ckpt"][CKPT]["ece_mean"] for p in pts if CKPT in p.get("by_ckpt", {})]
    if not e:
        raise RuntimeError(f"no VAE9182 dose-response points at @{CKPT} in {OVERLAY.name}")
    return min(e), max(e)


def stat(v):
    return st.mean(v), (sample_sd(v) if len(v) > 1 else 0.0), len(v)


def _logx(ax, xs, P):
    """Log x-axis labelled at the three measured widths only.

    Matplotlib keeps drawing its own MINOR tick labels on a log axis (a stray '2 x 10^0' landed
    on top of the 1.00 / 2.25 M label in the first render), so the minor formatter is cleared
    explicitly -- set_xticks alone only controls the major ticks.
    """
    ax.set_xscale("log")
    ax.set_xticks(xs)
    ax.set_xticklabels([f"{WIDTH_LABEL[w]}\n{P[w]:.2f} M" for w in WIDTH_ORDER])
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlim(xs[0] * 0.82, xs[-1] * 1.22)


def main():
    P, cells = params_by_width(), collect()
    missing = [w for w in WIDTH_ORDER + ["pretrained"] if w not in cells]
    if missing:
        raise RuntimeError(f"missing cells: {missing} -- frontier incomplete, refusing to plot")

    xs = [P[w] for w in WIDTH_ORDER]
    acc = [stat(cells[w]["acc"]) for w in WIDTH_ORDER]
    ece = [stat(cells[w]["ece"]) for w in WIDTH_ORDER]
    pre_acc, pre_ece = stat(cells["pretrained"]["acc"]), stat(cells["pretrained"]["ece"])
    px = P["pretrained"]
    t_lo, t_hi = teacher_axis_span()
    cap_span = max(m for m, _, _ in ece) - min(m for m, _, _ in ece)
    ratio = (t_hi - t_lo) / cap_span

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(12.4, 5.0))

    # ---- Panel A: accuracy
    axA.errorbar(xs, [m for m, _, _ in acc], yerr=[s for _, s, _ in acc],
                 color="#2471a3", marker="o", capsize=3, lw=1.8, label="scratch init (genişlik taraması)")
    axA.errorbar([px], [pre_acc[0]], yerr=[pre_acc[1]], color="#c0392b", marker="D",
                 markersize=9, capsize=3, ls="none", label="ImageNet ön-eğitimli (aynı genişlik)")
    axA.annotate("", xy=(px, pre_acc[0]), xytext=(px, acc[-1][0]),
                 arrowprops=dict(arrowstyle="<->", color="#c0392b", lw=1.4))
    # Label to the LEFT of the arrow: the pre-trained point sits at the largest x, so a
    # right-hand label is clipped by the axes edge.
    axA.text(px * 0.97, (pre_acc[0] + acc[-1][0]) / 2,
             f"ön-eğitim\n{pre_acc[0] - acc[-1][0]:+.2f} pp", color="#c0392b", fontsize=9,
             va="center", ha="right")
    axA.annotate("", xy=(xs[-1], acc[0][0]), xytext=(xs[0], acc[0][0]),
                 arrowprops=dict(arrowstyle="<->", color="#2471a3", lw=1.4))
    axA.text((xs[0] * xs[-1]) ** 0.5, acc[0][0] + 0.10,
             f"genişlik {xs[-1] / xs[0]:.2f}×  →  {acc[-1][0] - acc[0][0]:+.2f} pp",
             color="#2471a3", fontsize=9, ha="center", va="bottom")
    _logx(axA, xs, P)
    axA.set_xlabel("öğrenci genişlik çarpanı / parametre")
    axA.set_ylabel(f"RAF-DB doğruluk @{CKPT} (%)")
    axA.set_title("A · Ön-eğitim ≈ 3.16× kapasite (çıkarım maliyeti sıfır)", fontsize=11)
    axA.grid(alpha=0.25)
    axA.legend(fontsize=8.5, loc="upper left")

    # ---- Panel B: the argument
    axB.axhspan(t_lo, t_hi, color="#c0392b", alpha=0.12, zorder=0)
    axB.text(xs[0] * 0.93, (t_lo + t_hi) / 2,
             f"öğretmen sıcaklığı ekseni\n(T=1 → 2.2): {t_hi - t_lo:.4f}",
             color="#c0392b", fontsize=9.5, va="center", ha="left")
    axB.errorbar(xs, [m for m, _, _ in ece], yerr=[s for _, s, _ in ece],
                 color="#2471a3", marker="o", capsize=3, lw=1.8, zorder=3,
                 label="scratch init (genişlik taraması)")
    axB.errorbar([px], [pre_ece[0]], yerr=[pre_ece[1]], color="#c0392b", marker="D",
                 markersize=9, capsize=3, ls="none", zorder=3, label="ImageNet ön-eğitimli")
    _logx(axB, xs, P)
    axB.set_xlabel("öğrenci genişlik çarpanı / parametre")
    axB.set_ylabel(f"öğrenci ECE @{CKPT} (15-bin)")
    axB.set_title(f"B · Kapasite ekseni {cap_span:.4f} · öğretmen ekseni {t_hi - t_lo:.4f}  "
                  f"({ratio:.0f}×)", fontsize=11)
    axB.grid(alpha=0.25)
    axB.legend(fontsize=8.5, loc="upper right")

    fig.suptitle("Öğrenci kapasitesi kalibrasyonu belirlemiyor; öğretmen kalibrasyonu belirliyor "
                 f"(n=3/hücre, ± örneklem sd n−1, @{CKPT})", fontsize=12)
    fig.tight_layout()
    png = OUT_DIR / "p5_frontier.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)

    payload = {
        "sd_convention": SD_CONVENTION,
        "checkpoint": CKPT,
        "width_curve": [{"width": WIDTH_LABEL[w], "params_m": P[w],
                         "acc_mean": acc[i][0], "acc_sd": acc[i][1],
                         "ece_mean": ece[i][0], "ece_sd": ece[i][1], "n": acc[i][2]}
                        for i, w in enumerate(WIDTH_ORDER)],
        "pretrained_same_width": {"params_m": px, "acc_mean": pre_acc[0], "acc_sd": pre_acc[1],
                                  "ece_mean": pre_ece[0], "ece_sd": pre_ece[1], "n": pre_acc[2]},
        "contrasts": {
            "width_3x_acc_pp": acc[-1][0] - acc[0][0],
            "pretraining_acc_pp": pre_acc[0] - acc[-1][0],
            "capacity_ece_span": cap_span,
            "teacher_temperature_ece_span": t_hi - t_lo,
            "axis_ratio": ratio,
        },
        "confound_note": ("all width points are student_pretrained=False; the pre-trained student "
                          "is the same width, plotted separately, and is NOT the curve's endpoint"),
    }
    (OUT_DIR / "p5_frontier.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"width {xs[0]:.3f} -> {xs[-1]:.3f} M ({xs[-1] / xs[0]:.2f}x): "
          f"{acc[-1][0] - acc[0][0]:+.2f} pp acc")
    print(f"pre-training at fixed width:            {pre_acc[0] - acc[-1][0]:+.2f} pp acc")
    print(f"student ECE span, capacity axis:        {cap_span:.4f}")
    print(f"student ECE span, teacher-temp axis:    {t_hi - t_lo:.4f}   ratio {ratio:.0f}x")
    print(f"\nSaved {png}")
    print(f"Saved {OUT_DIR / 'p5_frontier.json'}")


if __name__ == "__main__":
    main()
