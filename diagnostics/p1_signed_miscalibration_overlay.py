"""Item 5: the overlay on a SIGNED miscalibration axis, which unfolds the ECE zigzag.

WHY THE ECE AXIS IS WRONG FOR THIS PLOT. ECE is an absolute value, so it is sign-blind: it
reports HOW MUCH a teacher is miscalibrated, never in WHICH DIRECTION. On the Stage1 curve
T=0.85 (over-CONFIDENT, ECE 0.0454) and T=1.70 (over-SMOOTH, ECE 0.0429) land on nearly the
same x, despite being opposite pathologies. The curve therefore folds back on itself and reads
as a zigzag rather than as the monotone relation it actually is.

TWO SIGNED AXES, both plotted:
  (a) mean confidence - accuracy   [the standard signed miscalibration / over-confidence gap]
      >0 = over-confident, <0 = under-confident. Directly interpretable, no reference needed.
  (b) log(T / T*)                  [signed distance from the teacher's own calibration optimum]
      >0 = over-softened past the optimum, <0 = over-sharpened. Puts both teachers on a
      common "how far from ideal, and which way" scale even though their T* differ
      (Stage1 1.3494 vs VAE9182 0.9829).

Both are computed from the cached teacher logits, so this costs no forward passes.

Outputs -> diagnostics/p1_dose_response/signed_miscalibration_overlay.{png,json}
"""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION  # noqa: E402

GRID_DIR = ROOT / "diagnostics" / "teacher_ece_grid"
OUT_DIR = ROOT / "diagnostics" / "p1_dose_response"
TEACHER_GRID = json.loads((GRID_DIR / "teacher_ece_grid.json").read_text())
OVERLAY = json.loads((OUT_DIR / "two_teacher_overlay.json").read_text())

STYLE = {
    "stage1":  {"color": "#c0392b", "marker": "o", "label": "Stage1  (T*=1.349, natively OVER-confident)"},
    "vae9182": {"color": "#2471a3", "marker": "s", "label": "VAE9182 (T*=0.983, natively calibrated)"},
}


def signed_gap(teacher, T):
    """mean(max softmax prob) - accuracy, at temperature T. >0 = over-confident."""
    blob = torch.load(GRID_DIR / f"teacher_val_logits_{teacher}.pt", map_location="cpu",
                      weights_only=False)
    logits, labels = blob["logits"], blob["labels"]
    probs = F.softmax(logits / T, dim=1)
    conf, preds = probs.max(dim=1)
    return float(conf.mean() - (preds == labels).float().mean())


def main():
    data = {}
    for teacher, pts in OVERLAY["curves"].items():
        tstar = TEACHER_GRID[teacher]["T_star"]
        rows = []
        for p in pts:
            rows.append({
                "T": p["T"],
                "teacher_ece": p["teacher_ece"],
                "signed_gap": signed_gap(teacher, p["T"]),
                "log_T_over_Tstar": math.log(p["T"] / tstar),
                "student_ece_mean": p["student_ece_mean"],
                "student_ece_sd": p["student_ece_sd"],
                "student_acc_mean": p["student_acc_mean"],
                "student_acc_sd": p["student_acc_sd"],
                "n": p["n"],
            })
        data[teacher] = {"T_star": tstar, "points": sorted(rows, key=lambda r: r["T"])}

    print(f"{'teacher':<10}{'T':<9}{'teacherECE':<12}{'signed gap':<13}{'log(T/T*)':<12}{'studentECE'}")
    for teacher, d in data.items():
        for r in d["points"]:
            print(f"{teacher:<10}{r['T']:<9g}{r['teacher_ece']:<12.4f}{r['signed_gap']:<+13.4f}"
                  f"{r['log_T_over_Tstar']:<+12.3f}{r['student_ece_mean']:.4f}")
        print()

    # --- demonstrate the fold that motivated this figure ---
    s1 = {r["T"]: r for r in data["stage1"]["points"]}
    if 0.85 in s1 and 1.7 in s1:
        a, b = s1[0.85], s1[1.7]
        print("The ECE fold, quantified (Stage1):")
        print(f"  T=0.85 : teacher ECE {a['teacher_ece']:.4f}  signed gap {a['signed_gap']:+.4f}  (over-confident)")
        print(f"  T=1.70 : teacher ECE {b['teacher_ece']:.4f}  signed gap {b['signed_gap']:+.4f}  (over-smooth)")
        print(f"  => |dECE| = {abs(a['teacher_ece']-b['teacher_ece']):.4f} (nearly identical x on the ECE axis)")
        print(f"     |d signed gap| = {abs(a['signed_gap']-b['signed_gap']):.4f} "
              f"(well separated once signed) -- this is the zigzag, removed.\n")

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.4))
    specs = [
        (0, "signed_gap", "Teacher signed miscalibration\n(mean confidence - accuracy)"),
        (1, "log_T_over_Tstar", "log(T / T*)   signed distance from the teacher's own optimum"),
    ]
    for col, xkey, xlabel in specs:
        for teacher, d in data.items():
            s = STYLE[teacher]
            pts = sorted(d["points"], key=lambda r: r[xkey])
            x = [r[xkey] for r in pts]
            for row, (ykey, sdkey, ylabel) in enumerate(
                    [("student_ece_mean", "student_ece_sd", "Student ECE (15-bin)"),
                     ("student_acc_mean", "student_acc_sd", "Student accuracy (%)")]):
                ax = axes[row][col]
                ax.errorbar(x, [r[ykey] for r in pts], yerr=[r[sdkey] for r in pts],
                            marker=s["marker"], color=s["color"], capsize=3, lw=1.8,
                            label=s["label"] if row == 0 else None)
                for r in pts:
                    ax.annotate(f"T={r['T']:g}", (r[xkey], r[ykey]), textcoords="offset points",
                                xytext=(5, 5), fontsize=7, color=s["color"])
                ax.set_ylabel(ylabel)
                ax.grid(alpha=0.25)
                if row == 1:
                    ax.set_xlabel(xlabel)
        axes[0][col].axvline(0.0, ls="--", color="gray", lw=1)
        axes[1][col].axvline(0.0, ls="--", color="gray", lw=1)
    axes[0][0].legend(fontsize=7, loc="upper left")
    axes[0][0].set_title("(a) signed over-confidence gap", fontsize=9)
    axes[0][1].set_title("(b) log distance from T*", fontsize=9)
    n_partial = sum(1 for d in data.values() for r in d["points"] if r["n"] < 3)
    note = "3 seeds" if n_partial == 0 else f"3 seeds; {n_partial} point(s) PARTIAL"
    fig.suptitle("Teacher calibration -> student outcome on SIGNED axes "
                 f"(dashed line = perfectly calibrated; {note})", fontsize=11)
    fig.tight_layout()
    out_png = OUT_DIR / "signed_miscalibration_overlay.png"
    fig.savefig(out_png, dpi=170)
    (OUT_DIR / "signed_miscalibration_overlay.json").write_text(
        json.dumps({"sd_convention": SD_CONVENTION, "arms": data}, indent=2), encoding="utf-8")
    print(f"Saved {out_png}")
    print(f"Saved {OUT_DIR / 'signed_miscalibration_overlay.json'}")


if __name__ == "__main__":
    main()
