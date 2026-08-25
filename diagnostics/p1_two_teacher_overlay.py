"""CROWN FIGURE: teacher calibration -> student calibration, on the teacher-ECE axis.

The dose-response experiments manipulate a knob T. But T has no cross-teacher meaning:
T=1.34 is the calibration optimum for Stage1 and a serious mis-setting for VAE9182.
Plotting against T therefore cannot show that the two teachers obey ONE law -- it shows
two unrelated curves.

Re-expressing the x-axis as the teacher's own ECE at that T (computed analytically from
cached teacher logits, diagnostics/teacher_ece_grid.py) puts both teachers on a common,
physically meaningful axis. The claim under test (B-007, calibration-conditioned
headroom):

    Student calibration is governed by TEACHER calibration, not by the knob.
    Consequently a teacher already at its calibration floor (VAE9182, ECE 0.0136,
    T*=0.98) has NO headroom to be rescued: every T != 1 only injects miscalibration.
    A miscalibrated teacher (Stage1, ECE 0.0378, T*=1.35) has 0.0220 of removable
    miscalibration, and removing it transfers to the student.

Falsifiable and pre-registered: if the VAE9182 student curve shows its own deep U with a
minimum away from T=1, or if the two teachers' points do NOT collapse onto a common
trend in teacher-ECE, the law is wrong.

Runs on partial data: any (T, seed) still training is simply omitted and the point's n
is annotated, so the figure can be inspected mid-queue without misreading it as final.

Outputs -> diagnostics/p1_dose_response/two_teacher_overlay.{png,json}
"""
import glob
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from teacher_temperature_scaling_fit import build_val_images, confidence_ece  # noqa: E402
from student_halfb_eval import eval_logits, student_from_run  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "p1_dose_response"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TEACHER_GRID = json.loads((ROOT / "diagnostics" / "teacher_ece_grid" / "teacher_ece_grid.json").read_text())

SEEDS = (42, 1, 43)
# teacher -> T -> {seed: run_name}. T=1.0 rows reuse each teacher's existing unmanipulated
# baseline (identical recipe, no --teacher-temperature-scale), so they are free.
CURVES = {
    "stage1": {
        0.85:   {s: f"RAFDB_stage1_tempscale_T085_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        1.00:   {42: "RAFDB_vichteacher_stage1_9224_betaKD_b070_T6_224_best_400e_swa200",
                 1:  "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1",
                 43: "RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed43"},
        1.3406: {42: "RAFDB_stage1_tempscale_T1341_halfA_baseline_b070_T6_224_400e_swa200",
                 1:  "RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed1",
                 43: "RAFDB_stage1_tempscale_T134_b070_T6_224_400e_swa200_seed43"},
        1.70:   {s: f"RAFDB_stage1_tempscale_T170_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        2.20:   {s: f"RAFDB_stage1_tempscale_T220_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
    },
    "vae9182": {
        0.85:   {s: f"RAFDB_vae9182_tempscale_T085_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        1.00:   {42: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200",
                 1:  "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed1",
                 43: "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200_seed43"},
        1.3406: {s: f"RAFDB_vae9182_tempscale_T134_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        1.70:   {s: f"RAFDB_vae9182_tempscale_T170_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
        2.20:   {s: f"RAFDB_vae9182_tempscale_T220_b070_T6_224_400e_swa200_seed{s}" for s in SEEDS},
    },
}
STYLE = {
    "stage1":  {"color": "#c0392b", "marker": "o", "label": "Stage1  (teacher ECE 0.0378, T*=1.35) - miscalibrated"},
    "vae9182": {"color": "#2471a3", "marker": "s", "label": "VAE9182 (teacher ECE 0.0136, T*=0.98) - well calibrated"},
}

_VAL = None


def student_stats(run_name):
    """Accuracy + 15-bin ECE on fold-3 val, cached per run in calibration.json."""
    global _VAL
    dirs = sorted(glob.glob(str(ROOT / "results/unified_students" / run_name / "*")))
    dirs = [d for d in dirs if Path(d, "best_checkpoint.pth").exists()
            and Path(d, "metrics_best.json").exists()]
    if not dirs:
        return None
    d = Path(dirs[-1])
    cal = d / "calibration.json"
    if cal.exists():
        c = json.loads(cal.read_text())
        return c["acc_recomputed"], c["ece"]
    if _VAL is None:
        _VAL = build_val_images()
    images, labels = _VAL
    lg = eval_logits(student_from_run(d), images)
    acc = float((lg.argmax(1) == labels).float().mean() * 100.0)
    ece = confidence_ece(lg, labels, 1.0)
    cal.write_text(json.dumps({"ece": ece, "acc_recomputed": acc, "n_val": int(labels.shape[0]),
                               "method": "15-bin confidence ECE, fold-3 val, best_checkpoint.pth"},
                              indent=2), encoding="utf-8")
    return acc, ece


def collect():
    out = {}
    for teacher, by_T in CURVES.items():
        grid = TEACHER_GRID[teacher]["experiment_grid"]
        pts = []
        for T in sorted(by_T):
            accs, eces = [], []
            for s in SEEDS:
                r = student_stats(by_T[T][s]) if s in by_T[T] else None
                if r:
                    accs.append(r[0])
                    eces.append(r[1])
            if not accs:
                print(f"  [{teacher}] T={T:<7} no finished runs yet")
                continue
            t_ece = grid[f"{T:g}"]["teacher_ece"]
            pts.append({"T": T, "teacher_ece": t_ece, "n": len(accs),
                        "student_acc_mean": st.mean(accs), "student_acc_sd": sample_sd(accs),
                        "student_ece_mean": st.mean(eces), "student_ece_sd": sample_sd(eces)})
            print(f"  [{teacher}] T={T:<7} teacherECE={t_ece:.4f}  "
                  f"studentECE={st.mean(eces):.4f}+/-{sample_sd(eces):.4f}  "
                  f"acc={st.mean(accs):.3f}+/-{sample_sd(accs):.3f}  n={len(accs)}"
                  + ("" if len(accs) == 3 else "   <-- PARTIAL"))
        out[teacher] = pts
    return out


def headroom_table(data):
    """The B-007 numbers: teacher-side removable miscalibration vs. what the student realized."""
    rows = []
    for teacher, pts in data.items():
        if not pts:
            continue
        tg = TEACHER_GRID[teacher]
        at1 = next((p for p in pts if p["T"] == 1.00), None)
        best = min(pts, key=lambda p: p["student_ece_mean"])
        accs = [p["student_acc_mean"] for p in pts]
        rows.append({
            "teacher": teacher,
            "teacher_own_acc": tg["own_acc_pct"],
            "teacher_ece_T1": tg["ece_T1"],
            "teacher_T_star": tg["T_star"],
            # teacher-side HEADROOM: miscalibration post-hoc scaling can remove (>=0 means rescuable)
            "teacher_headroom_dECE": tg["ece_T1"] - min(tg["fine_sweep"].values()),
            # student-side REALIZED gain at the best grid point
            "student_ece_T1": at1["student_ece_mean"] if at1 else None,
            "student_ece_best": best["student_ece_mean"],
            "student_best_T": best["T"],
            "student_realized_dECE": (at1["student_ece_mean"] - best["student_ece_mean"]) if at1 else None,
            "student_acc_U_depth_pp": max(accs) - min(accs),
            "n_points": len(pts),
            "complete": all(p["n"] == 3 for p in pts) and len(pts) == 5,
        })
    return rows


def correlations(data):
    """How tightly does teacher ECE track student ECE? Computed WITHIN each teacher
    (where T is the only thing that moved) and POOLED across teachers (the stronger
    claim: one law, not two coincidences)."""
    def pearson(x, y):
        n = len(x)
        mx, my = sum(x) / n, sum(y) / n
        dx, dy = [a - mx for a in x], [b - my for b in y]
        num = sum(a * b for a, b in zip(dx, dy))
        den = (sum(a * a for a in dx) * sum(b * b for b in dy)) ** 0.5
        return num / den if den else float("nan")

    def spearman(x, y):
        def rank(v):
            order = sorted(range(len(v)), key=lambda i: v[i])
            r = [0.0] * len(v)
            for pos, i in enumerate(order):
                r[i] = pos + 1
            return r
        return pearson(rank(x), rank(y))

    out, px, py = {}, [], []
    for teacher, pts in data.items():
        if len(pts) < 3:
            continue
        x = [p["teacher_ece"] for p in pts]
        y = [p["student_ece_mean"] for p in pts]
        px += x
        py += y
        out[teacher] = {"n": len(x), "pearson": pearson(x, y), "spearman": spearman(x, y)}
    if len(px) >= 4:
        out["pooled"] = {"n": len(px), "pearson": pearson(px, py), "spearman": spearman(px, py)}
    return out


def main():
    print("Collecting student runs (cached where available)...\n")
    data = collect()
    rows = headroom_table(data)
    corr = correlations(data)

    print("\n=== teacher ECE -> student ECE correlation ===")
    for k, v in corr.items():
        print(f"  {k:<10} n={v['n']:<3} pearson={v['pearson']:+.3f}  spearman={v['spearman']:+.3f}")

    print("\n=== B-007 headroom table ===")
    hdr = (f"{'teacher':<10}{'own acc':<10}{'ECE(T=1)':<11}{'T*':<8}"
           f"{'teacher headroom':<19}{'student realized':<19}{'student best T':<16}{'acc U-depth':<13}{'complete'}")
    print(hdr)
    for r in rows:
        print(f"{r['teacher']:<10}{r['teacher_own_acc']:<10.2f}{r['teacher_ece_T1']:<11.4f}"
              f"{r['teacher_T_star']:<8.3f}{r['teacher_headroom_dECE']:<19.4f}"
              f"{(r['student_realized_dECE'] if r['student_realized_dECE'] is not None else float('nan')):<19.4f}"
              f"{r['student_best_T']:<16g}{r['student_acc_U_depth_pp']:<13.3f}{r['complete']}")

    # ---- figure ----
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.8))
    for teacher, pts in data.items():
        if not pts:
            continue
        s = STYLE[teacher]
        pts_sorted = sorted(pts, key=lambda p: p["teacher_ece"])
        x = [p["teacher_ece"] for p in pts_sorted]
        ax1.errorbar(x, [p["student_ece_mean"] for p in pts_sorted],
                     yerr=[p["student_ece_sd"] for p in pts_sorted],
                     marker=s["marker"], color=s["color"], capsize=3, lw=1.8, label=s["label"])
        ax2.errorbar(x, [p["student_acc_mean"] for p in pts_sorted],
                     yerr=[p["student_acc_sd"] for p in pts_sorted],
                     marker=s["marker"], color=s["color"], capsize=3, lw=1.8, label=s["label"])
        for p in pts_sorted:
            tag = f"T={p['T']:g}" + ("" if p["n"] == 3 else f" (n={p['n']})")
            ax1.annotate(tag, (p["teacher_ece"], p["student_ece_mean"]),
                         textcoords="offset points", xytext=(5, 5), fontsize=7, color=s["color"])
            ax2.annotate(tag, (p["teacher_ece"], p["student_acc_mean"]),
                         textcoords="offset points", xytext=(5, 5), fontsize=7, color=s["color"])
    for ax, ylab in ((ax1, "Student ECE (15-bin)"), (ax2, "Student accuracy (%)")):
        ax.set_xscale("log")
        ax.set_xlabel("Teacher ECE at the distilled temperature  (log scale)")
        ax.set_ylabel(ylab)
        ax.grid(alpha=0.25, which="both")
    # Başlık v2 ile hizalandı (7 Ağu 2026). Bu başlık ihraç edilen PDF'te görünmüyor
    # (dışa aktarımda figür-içi başlıklar kaldırılıyor), yalnız tanılama PNG'sini etkiliyor —
    # yine de değişti, ki repo içinde iki farklı iddia cümlesi dolaşmasın.
    ax1.set_title("Teacher-side logit scaling governs student calibration", fontsize=10)
    ax2.set_title("Accuracy is comparatively insensitive", fontsize=10)
    ax1.legend(fontsize=7, loc="upper left")
    # Title must not claim 3 seeds while any point is still partial.
    n_partial = sum(1 for pts in data.values() for p in pts if p["n"] < 3)
    seed_note = "3 seeds" if n_partial == 0 else f"3 seeds; {n_partial} point(s) still PARTIAL"
    fig.suptitle(f"RAF-DB dose-response, two teachers on a common teacher-ECE axis ({seed_note})",
                 fontsize=11)
    fig.tight_layout()
    out_png = OUT_DIR / "two_teacher_overlay.png"
    fig.savefig(out_png, dpi=170)

    (OUT_DIR / "two_teacher_overlay.json").write_text(
        json.dumps({"sd_convention": SD_CONVENTION,
                    "curves": data, "headroom_table": rows, "correlations": corr}, indent=2),
        encoding="utf-8")
    print(f"\nSaved {out_png}")
    print(f"Saved {OUT_DIR / 'two_teacher_overlay.json'}")


if __name__ == "__main__":
    main()
