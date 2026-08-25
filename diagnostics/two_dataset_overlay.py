"""MAIN FIGURE CANDIDATE: one calibration law, two datasets, opposite directions.

THE ARGUMENT THE FIGURE HAS TO MAKE. B-007 (RAF-DB) and B-015 (FERPlus) each show that student
calibration tracks TEACHER calibration under post-hoc teacher temperature scaling. Shown
separately they read as two similar results. The claim worth a main figure is stronger: they are
the same law, and the law does not care about the DIRECTION of the teacher's miscalibration.

WHY THE X-AXIS MUST BE SIGNED. ECE is an absolute value, so it is direction-blind. On an ECE
axis:
  - Stage1's T=0.85 (over-CONFIDENT, ECE 0.0454) and T=1.70 (over-SMOOTH, ECE 0.0429) land on
    almost the same x while being opposite pathologies -- the curve folds back on itself and
    reads as a zigzag (quantified in diagnostics/p1_signed_miscalibration_overlay.py: |dECE|
    0.0025 vs |d signed gap| 0.0859, a 34x separation).
  - Worse for THIS figure: RAF-DB's native teacher is over-confident and FERPlus's is
    under-confident. On the ECE axis both arms pile onto the same positive half-line, so the
    one fact that makes the pairing interesting -- that the required correction runs in opposite
    directions -- is invisible.
On the signed axis (mean confidence - accuracy) the RAF-DB arm's native point sits at x>0 and
FERPlus's at x<0, and the two datasets become the two halves of a single V centred on x=0.
Panel (b) then folds that V at zero to show the magnitude-only relation.

CHECKPOINT CHOICE. @swa is PRIMARY, not @best. The 'best' checkpoint is chosen by argmax
val_acc on the very images the metric is then reported on (train_rafdb_kd.py:895-900 ->
:960-977), so every 'best' number carries selection optimism (+0.79 pp accuracy on RAF-DB,
+0.46 pp on FERPlus). SWA is a fixed rule that never looks at the eval set, so it is the
defensible checkpoint for a calibration claim. @best and @last go to a supplementary figure --
reported, not hidden, because B-007 was verified to be robust across all three.

DATA SOURCES (no new computation, all measured elsewhere):
  student ECE   RAF-DB  diagnostics/selection_audit/selection_audit.csv        (101 runs x 3 ckpt)
                FERPlus diagnostics/selection_audit/ferplus_selection_audit.csv (9 runs x 3 ckpt)
  run -> (teacher, T)   imported from p1_two_teacher_overlay.CURVES so there is ONE mapping in
                        the repo rather than a second, drifting copy
  teacher signed gap    RAF-DB  closed-form from diagnostics/teacher_ece_grid/teacher_val_logits_*.pt
                        FERPlus diagnostics/ferplus_jsd/ferplus_teacher_signed_grid.json

Outputs -> diagnostics/p1_dose_response/two_dataset_overlay_{swa,supp}.png
           diagnostics/p1_dose_response/two_dataset_overlay.json
"""
import csv
import json
import statistics as st
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

from p1_two_teacher_overlay import CURVES  # noqa: E402  (single source of run -> (teacher,T))
from stats_convention import SD_CONVENTION  # noqa: E402

GRID_DIR = ROOT / "diagnostics" / "teacher_ece_grid"
AUDIT_DIR = ROOT / "diagnostics" / "selection_audit"
OUT_DIR = ROOT / "diagnostics" / "p1_dose_response"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEACHER_GRID = json.loads((GRID_DIR / "teacher_ece_grid.json").read_text())
FERPLUS_GRID = json.loads(
    (ROOT / "diagnostics" / "ferplus_jsd" / "ferplus_teacher_signed_grid.json").read_text())

CHECKPOINTS = ("swa", "best", "last")
ARMS = {
    "rafdb_stage1": {
        "color": "#c0392b", "marker": "o",
        "label": "RAF-DB / Stage1 teacher  (native ECE 0.0378, T*=1.35, OVER-confident)"},
    "rafdb_vae9182": {
        "color": "#e67e22", "marker": "^",
        "label": "RAF-DB / VAE9182 teacher (native ECE 0.0136, T*=0.98, already calibrated)"},
    "ferplus": {
        "color": "#2471a3", "marker": "s",
        "label": "FERPlus / VICH teacher   (native ECE 0.1282, T*=0.51, UNDER-confident)"},
}

_LOGIT_CACHE = {}


def rafdb_signed_gap(teacher, T):
    """mean(top-1 softmax prob) - accuracy at temperature T. >0 over-confident, <0 under."""
    if teacher not in _LOGIT_CACHE:
        blob = torch.load(GRID_DIR / f"teacher_val_logits_{teacher}.pt", map_location="cpu",
                          weights_only=False)
        _LOGIT_CACHE[teacher] = (blob["logits"], blob["labels"])
    logits, labels = _LOGIT_CACHE[teacher]
    probs = F.softmax(logits / T, dim=1)
    conf, preds = probs.max(dim=1)
    return float(conf.mean() - (preds == labels).float().mean())


def load_audit(path, key):
    """(key(row), checkpoint) -> row, for whichever key identifies an arm's runs."""
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        out[(key(r), r["checkpoint"])] = r
    return out


def spearman(xs, ys):
    """Tie-corrected (midrank) Spearman -- the pooled point sets here can contain tied x."""
    def rank(a):
        order = sorted(range(len(a)), key=lambda i: a[i])
        r = [0.0] * len(a)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and a[order[j + 1]] == a[order[i]]:
                j += 1
            mid = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[order[k]] = mid
            i = j + 1
        return r
    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


def pearson(xs, ys):
    """Ham (sıralanmamış) doğrusal korelasyon — `tab_pooled`'un `r` (unsigned) sütunu.

    NEDEN 17 AĞU 2026'DA EKLENDİ. Sütun makalede duruyordu ama ÜRETİCİSİ YOKTU: sayı
    provenans defteri (N13) üç hücreyi "kayıtsız" diye işaretledi, çünkü havuzlanmış 14 nokta
    üzerinde Pearson hesaplayan hiçbir artefakt yoktu. Karar (Fatih, 17 Ağu): kanıtı silmek
    yerine kaynağı üretmek. Bu yüzden Spearman'ın YANINA, AYNI 14 noktayı toplayan AYNI
    döngüden hesaplanıyor — ikinci bir nokta kümesi ya da ikinci bir tanım getirmeden.
    Yardımcı istatistiktir: makale ilişkiyi zaten "a rank association, not a monotone
    response" diye niteliyor.
    """
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = (sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys)) ** 0.5
    return num / den if den else float("nan")


def branch_asymmetry(points, ck):
    """Is over-confidence as costly to the student as EQUAL-magnitude under-confidence?

    Panel (b) folds the signed axis at zero, which implicitly assumes the two directions cost the
    same. They do not, and the folded panel shows it as a visible zigzag: on Stage1, T=0.85
    (signed +0.0431, over-confident) and T=1.70 (signed -0.0427, over-smooth) have essentially
    identical |gap| yet student ECE 0.0797 vs 0.0447.

    Measured WITHIN one arm, so teacher, dataset, recipe and seed set are all held fixed and the
    only thing that differs is the SIGN of the injected miscalibration. For each positive-gap
    point we linearly interpolate (or extrapolate) the arm's own negative branch to the same
    |gap| and take the ratio. ratio > 1 means over-confidence is the more damaging direction.
    """
    pos = sorted([(abs(p["signed_gap"]), p["by_ckpt"][ck]["ece_mean"], p["T"])
                  for p in points if ck in p["by_ckpt"] and p["signed_gap"] > 0])
    neg = sorted([(abs(p["signed_gap"]), p["by_ckpt"][ck]["ece_mean"], p["T"])
                  for p in points if ck in p["by_ckpt"] and p["signed_gap"] < 0])
    if len(pos) < 1 or len(neg) < 2:
        return None
    # least-squares line through the negative branch: ECE = a + b*|gap|
    xs = [g for g, _, _ in neg]
    ys = [e for _, e, _ in neg]
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    a = my - b * mx
    rows = []
    for g, e, T in pos:
        pred = a + b * g
        rows.append({"T_positive": T, "abs_gap": g, "ece_over_confident": e,
                     "ece_under_confident_at_same_gap": pred,
                     "ratio": e / pred if pred > 0 else None,
                     "extrapolated": g < min(xs) or g > max(xs)})
    return {"negative_branch_fit": {"intercept": a, "slope": b, "n": len(neg)},
            "comparisons": rows}


def build():
    rafdb = load_audit(AUDIT_DIR / "selection_audit.csv", lambda r: r["run_name"])
    ferplus = load_audit(AUDIT_DIR / "ferplus_selection_audit.csv",
                         lambda r: (round(float(r["t_scale"]), 4), r["seed"]))

    data = {arm: {"points": []} for arm in ARMS}

    # ---- RAF-DB arms, via the shared CURVES mapping ----
    for teacher, per_T in CURVES.items():
        arm = f"rafdb_{teacher}"
        for T, by_seed in sorted(per_T.items()):
            # teacher_ece_grid.json stores the grid under "experiment_grid", keyed by the
            # REPR of the float, so T=1.0 is the key "1" and not "1.0". Look up both forms.
            eg = TEACHER_GRID[teacher]["experiment_grid"]
            t_ece = eg.get(repr(T), eg.get(str(T), eg.get(f"{T:g}")))
            if isinstance(t_ece, dict):                 # tolerate a nested {ece: ...} shape
                t_ece = t_ece.get("ece", t_ece.get("teacher_ece"))
            if t_ece is None:
                raise KeyError(f"no teacher ECE for {teacher} T={T} in {sorted(eg)}")
            rec = {"T": T, "teacher_ece": float(t_ece),
                   "signed_gap": rafdb_signed_gap(teacher, T), "by_ckpt": {}}
            for ck in CHECKPOINTS:
                vals = [(float(rafdb[(rn, ck)]["ece"]), float(rafdb[(rn, ck)]["acc"]))
                        for rn in by_seed.values() if (rn, ck) in rafdb]
                if not vals:
                    continue
                e = [v[0] for v in vals]
                a = [v[1] for v in vals]
                rec["by_ckpt"][ck] = {
                    "n": len(e),
                    "ece_mean": st.mean(e), "ece_sd": st.stdev(e) if len(e) > 1 else 0.0,
                    "acc_mean": st.mean(a), "acc_sd": st.stdev(a) if len(a) > 1 else 0.0,
                    # TOHUM BAŞINA DEĞERLER (14 Ağu, B8). Özetin en güçlü niceleyicisi
                    # "all nine seed curves"; ortalama ± sd o cümleyi doğrulatmaz, çünkü
                    # dokuz eğrinin AYRI AYRI monoton olduğunu göstermez. Eğriler zaten
                    # burada kuruluyor, eksik olan yalnız kaydediliyor olmalarıydı.
                    "per_seed": {str(s): {"run": rn,
                                          "ece": float(rafdb[(rn, ck)]["ece"]),
                                          "acc": float(rafdb[(rn, ck)]["acc"])}
                                 for s, rn in sorted(by_seed.items())
                                 if (rn, ck) in rafdb}}
            data[arm]["points"].append(rec)

    # ---- FERPlus arm ----
    fg = {round(r["T"], 4): r for r in FERPLUS_GRID["grid"]}
    seeds_present = sorted({k[0][1] for k in ferplus})
    for T in sorted(fg):
        rec = {"T": T, "teacher_ece": fg[T]["teacher_ece"],
               "signed_gap": fg[T]["signed_gap"], "by_ckpt": {}}
        for ck in CHECKPOINTS:
            vals = [(float(ferplus[((T, s), ck)]["ece"]), float(ferplus[((T, s), ck)]["acc"]))
                    for s in seeds_present if ((T, s), ck) in ferplus]
            if not vals:
                continue
            e = [v[0] for v in vals]
            a = [v[1] for v in vals]
            rec["by_ckpt"][ck] = {
                "n": len(e),
                "ece_mean": st.mean(e), "ece_sd": st.stdev(e) if len(e) > 1 else 0.0,
                "acc_mean": st.mean(a), "acc_sd": st.stdev(a) if len(a) > 1 else 0.0,
                "per_seed": {str(s): {"run": ferplus[((T, s), ck)].get("run_name", ""),
                                      "ece": float(ferplus[((T, s), ck)]["ece"]),
                                      "acc": float(ferplus[((T, s), ck)]["acc"])}
                             for s in seeds_present if ((T, s), ck) in ferplus}}
        if rec["by_ckpt"]:                       # skip T=0.74 until its students finish
            data["ferplus"]["points"].append(rec)
        else:
            print(f"  (FERPlus T={T} has no finished students yet -- omitted from the figure)")
    return data


def panel(ax, data, ck, folded, xlabel, ylabel, annotate=True):
    """folded=False -> x is the SIGNED gap; folded=True -> x is |signed gap|.

    `ck` is the checkpoint tag and `folded` the axis mode. They were once both passed through
    one overloaded `xkey` argument, which silently made the folded panel look up a checkpoint
    named "abs", find nothing, and render EMPTY. Separate parameters, so a mix-up is a TypeError
    rather than a blank axis.
    """
    def xof(p):
        return abs(p["signed_gap"]) if folded else p["signed_gap"]

    for arm, spec in ARMS.items():
        pts = [p for p in data[arm]["points"] if ck in p["by_ckpt"]]
        if not pts:
            continue
        pts.sort(key=xof)
        x = [xof(p) for p in pts]
        y = [p["by_ckpt"][ck]["ece_mean"] for p in pts]
        e = [p["by_ckpt"][ck]["ece_sd"] for p in pts]
        ax.errorbar(x, y, yerr=e, marker=spec["marker"], color=spec["color"], capsize=3,
                    lw=1.7, ms=6, label=spec["label"])
        if annotate:
            for xi, yi, p in zip(x, y, pts):
                ax.annotate(f"T={p['T']:g}", (xi, yi), textcoords="offset points",
                            xytext=(5, 5), fontsize=6.5, color=spec["color"])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.25)
    if not folded:
        # drawn after the data so the annotation can be anchored inside the final y-range
        ax.axvline(0.0, ls="--", color="gray", lw=1.1)
        lo, hi = ax.get_ylim()
        ax.text(0.0, lo + 0.97 * (hi - lo), "  perfectly\n  calibrated", fontsize=6.5,
                color="gray", va="top", ha="left")


def main():
    data = build()

    print(f"{'arm':<16}{'T':<9}{'teacherECE':<12}{'signed gap':<13}"
          f"{'studentECE@swa':<17}{'n'}")
    for arm in ARMS:
        for p in sorted(data[arm]["points"], key=lambda p: p["signed_gap"]):
            s = p["by_ckpt"].get("swa")
            te = f"{p['teacher_ece']:.4f}" if p["teacher_ece"] is not None else "  n/a "
            print(f"{arm:<16}{p['T']:<9g}{te:<12}{p['signed_gap']:<+13.4f}"
                  f"{s['ece_mean']:.4f} +/- {s['ece_sd']:.4f}   {s['n']}" if s else "")
        print()

    # ---- the one-law statistic: pooled across BOTH datasets on the magnitude axis ----
    stats = {}
    for ck in CHECKPOINTS:
        xs, ys, xs_signed = [], [], []
        for arm in ARMS:
            for p in data[arm]["points"]:
                if ck not in p["by_ckpt"]:
                    continue
                xs.append(abs(p["signed_gap"]))
                xs_signed.append(p["signed_gap"])
                ys.append(p["by_ckpt"][ck]["ece_mean"])
        stats[ck] = {"n_points": len(xs),
                     "spearman_abs_signed_gap": spearman(xs, ys),
                     "spearman_signed_gap": spearman(xs_signed, ys),
                     "pearson_abs_signed_gap": pearson(xs, ys),
                     "pearson_signed_gap": pearson(xs_signed, ys)}
        print(f"pooled across both datasets @{ck}: n={len(xs)} points   "
              f"Spearman(|signed gap|, student ECE) = {stats[ck]['spearman_abs_signed_gap']:+.3f}"
              f"   [signed version {stats[ck]['spearman_signed_gap']:+.3f}, expected ~0 "
              f"because the relation is V-shaped, not monotone, in the SIGNED variable]")
        print(f"    Pearson r on the same points = "
              f"{stats[ck]['pearson_abs_signed_gap']:+.3f} (unsigned) · "
              f"{stats[ck]['pearson_signed_gap']:+.3f} (signed)")

    # ---- direction asymmetry: is the folded axis actually sufficient? ----
    print("\n=== DIRECTION ASYMMETRY (within-arm, @swa): over-confident vs equally "
          "under-confident ===")
    asym = {}
    ratios_all = []
    for arm in ARMS:
        r = branch_asymmetry(data[arm]["points"], "swa")
        asym[arm] = r
        if not r:
            print(f"  {arm:<16} not enough points on both sides of zero")
            continue
        f = r["negative_branch_fit"]
        print(f"  {arm:<16} negative-branch fit ECE = {f['intercept']:+.4f} + "
              f"{f['slope']:.3f}|gap|  (n={f['n']})")
        for c in r["comparisons"]:
            tag = " [EXTRAPOLATED]" if c["extrapolated"] else ""
            print(f"      |gap|={c['abs_gap']:.4f} (T={c['T_positive']:g}): "
                  f"over-conf {c['ece_over_confident']:.4f} vs under-conf "
                  f"{c['ece_under_confident_at_same_gap']:.4f}  -> "
                  f"ratio {c['ratio']:.2f}x{tag}")
            if not c["extrapolated"]:
                ratios_all.append(c["ratio"])
    if ratios_all:
        print(f"\n  >>> interpolated (non-extrapolated) comparisons only: "
              f"{len(ratios_all)} of them, ratio "
              f"{st.mean(ratios_all):.2f}x +/- "
              f"{st.stdev(ratios_all) if len(ratios_all) > 1 else 0:.2f}, "
              f"all > 1 = {all(r > 1 for r in ratios_all)}")
        print("  >>> Teacher OVER-confidence is the more damaging direction for the student at "
              "equal |miscalibration|.")
        print("  >>> Consequence: |signed gap| alone does NOT fully determine student ECE; the "
              "law is monotone in each direction but with DIFFERENT slopes.")
    stats["direction_asymmetry_swa"] = {
        "per_arm": asym,
        "mean_ratio_interpolated_only": st.mean(ratios_all) if ratios_all else None,
        "n_interpolated": len(ratios_all),
        "all_ratios_above_one": all(r > 1 for r in ratios_all) if ratios_all else None}

    # ---------------- MAIN FIGURE: @swa only ----------------
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0))
    panel(axes[0], data, "swa", False,
          "Teacher signed miscalibration   (mean confidence $-$ accuracy)",
          "Student ECE @SWA (15-bin)")
    panel(axes[1], data, "swa", True,
          "|Teacher signed miscalibration|   (magnitude only)",
          "Student ECE @SWA (15-bin)")
    axes[0].set_title("(a) signed: every arm is V-shaped with its minimum at its own $T^*$;\n"
                      "the two datasets approach zero from OPPOSITE sides", fontsize=9.5)
    ratio_txt = (f"; over-confidence costs "
                 f"{stats['direction_asymmetry_swa']['mean_ratio_interpolated_only']:.1f}$\\times$ more"
                 if stats["direction_asymmetry_swa"]["mean_ratio_interpolated_only"] else "")
    axes[1].set_title(f"(b) folded at zero: Spearman "
                      f"{stats['swa']['spearman_abs_signed_gap']:+.3f}, but the folding is NOT "
                      f"exact\n(residual zigzag is the direction asymmetry{ratio_txt})",
                      fontsize=9.5)
    axes[0].legend(fontsize=6.8, loc="upper right", framealpha=0.95)
    ns = {p["by_ckpt"]["swa"]["n"] for arm in ARMS for p in data[arm]["points"]
          if "swa" in p["by_ckpt"]}
    note = "3 seeds per point" if ns == {3} else f"seeds per point: {sorted(ns)} (PARTIAL)"
    # The title must not claim direction-INDEPENDENCE: panel (b) measures a 1.8x direction
    # asymmetry, so "independent of direction" would contradict the figure's own data. The
    # defensible claim is that the law operates in BOTH directions and on BOTH datasets.
    # Başlık v2 ile hizalandı (7 Ağu 2026): yalnız ÖZNE değişti. "BOTH directions / BOTH
    # datasets" vurgusu korundu -- çift yönlülük iddiası sağlam, FERPlus ters yönde tekrarlıyor.
    fig.suptitle("Teacher-side logit scaling governs student calibration in BOTH directions "
                 "and on BOTH datasets\n"
                 f"(selection-independent SWA checkpoint, {note})", fontsize=11)
    fig.tight_layout()
    p_main = OUT_DIR / "two_dataset_overlay_swa.png"
    fig.savefig(p_main, dpi=180)
    plt.close(fig)

    # ---------------- SUPPLEMENTARY: @best and @last ----------------
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 9.2))
    for row, ck in enumerate(("best", "last")):
        panel(axes[row][0], data, ck, False,
              "Teacher signed miscalibration   (mean confidence $-$ accuracy)",
              f"Student ECE @{ck} (15-bin)")
        panel(axes[row][1], data, ck, True, "|Teacher signed miscalibration|",
              f"Student ECE @{ck} (15-bin)")
        axes[row][1].set_title(f"@{ck}: Spearman "
                               f"{stats[ck]['spearman_abs_signed_gap']:+.3f}", fontsize=9)
    axes[0][0].set_title("@best — ACCURACY-SELECTED, carries selection optimism", fontsize=9)
    axes[1][0].set_title("@last — selection-independent (final epoch)", fontsize=9)
    axes[0][0].legend(fontsize=6.5, loc="upper center")
    fig.suptitle("Supplementary: the same relation at the other two checkpoints", fontsize=11)
    fig.tight_layout()
    p_supp = OUT_DIR / "two_dataset_overlay_supp.png"
    fig.savefig(p_supp, dpi=180)
    plt.close(fig)

    (OUT_DIR / "two_dataset_overlay.json").write_text(
        json.dumps({"sd_convention": SD_CONVENTION, "arms": data, "pooled_stats": stats,
                    "checkpoint_note": "swa is primary; best carries selection optimism"},
                   indent=2), encoding="utf-8")
    print(f"\nSaved {p_main}")
    print(f"Saved {p_supp}")
    print(f"Saved {OUT_DIR / 'two_dataset_overlay.json'}")


if __name__ == "__main__":
    main()
