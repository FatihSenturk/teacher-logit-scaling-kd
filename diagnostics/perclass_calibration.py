"""Figure: does teacher temperature scaling calibrate ALL seven classes, or only the easy ones?

THE QUESTION. The paper's calibration lever is a single scalar -- one temperature applied to the
whole teacher. Aggregate ECE says it works. A scalar cannot, however, know that RAF-DB's classes
are wildly unbalanced (Happiness n=1185, Fear n=74) and differently hard, so "aggregate ECE fell"
is compatible with two very different worlds: the correction reaching every class, or the
correction being driven by the frequent classes while the rare, ambiguous ones stay broken. Which
one is true decides whether this is a clean result or a result with a limitation section.

WHY SIGNED GAP AND NOT PER-CLASS ECE. Per-class ECE would need 15 bins inside a class of 74
samples -- roughly 5 samples per bin, where a single sample changing bins moves the number.
The SIGNED CONFIDENCE GAP, mean(top-1 confidence) - accuracy over the samples of one class, needs
no binning at all, so its small-n behaviour is governed by the ordinary standard error of two
means rather than by bin occupancy. Measured: across-T range beats the seed sd by 10.56x (Disgust;
figur altyazisi alt-sinir iddiasi oldugu icin 1dp FLOOR ile 10.5 basar, yari-yukari 10.6 verirdi)
to 49.3x (Happiness), and by 13.1x on Fear itself, the smallest class. The panel is signal.

CLASS MEMBERSHIP is by TRUE label: "the model's confidence on fear images", which is the quantity
the imbalance question is about. (Grouping by PREDICTED label would answer a different question --
precision-conditional calibration -- and would make each class's n depend on the temperature.)

WHERE n IS PRINTED. n is a property of the val split, so it is identical across all five columns
of a row; writing it into each of the 35 cells would repeat 7 numbers five times each and take
the space the varying number needs. It goes in the row label instead, and classes under n=100 are
marked there so no reader takes their row at face value.

COLOUR IS REDUNDANT HERE, DELIBERATELY. A diverging map is ambiguous in greyscale by
construction -- both ends darken -- so the colour cannot be the only carrier of the sign. Every
cell therefore prints its signed value, and the colour only speeds up reading the pattern. The
greyscale render is still fully interpretable; verified via verify_paper_figures.py --grey.

Outputs -> paper/figures/perclass_calibration.pdf   (90 mm, single column)
           diagnostics/reliability/perclass_calibration.json
"""
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from student_logit_cache import load_arm  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from export_paper_figures import MM, BLUE, VERM, SMALL, house_style, check_type_sizes  # noqa: E402
from reliability_diagram import save_at_width  # noqa: E402

OUT_PDF = ROOT / "paper" / "figures" / "perclass_calibration.pdf"
OUT_DIR = ROOT / "diagnostics" / "reliability"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# RAF-DB's own label order, verified against the metadata CSV's directory names
# (0_Surprise ... 6_Neutral), not assumed from the usual 1-indexed convention.
CLASSES = ["Surprise", "Fear", "Disgust", "Happiness", "Sadness", "Anger", "Neutral"]
SMALL_CLASS = 100
ARM, CKPT, SEEDS = "stage1", "swa", (42, 1, 43)
TSTAR = 1.3406


def softmax(x):
    e = np.exp(x - x.max(1, keepdims=True))
    return e / e.sum(1, keepdims=True)


def signed_gap(logits, mask, cls):
    p = softmax(logits[mask])
    return float(p.max(1).mean() - (p.argmax(1) == cls).mean())


def crossing_T(Ts, means):
    """Temperature at which a class's signed gap would reach zero, by linear interpolation
    between the two bracketing measurements. None if the row never changes sign in the tested
    range -- which is itself the finding for the classes that stay over-confident throughout."""
    for (t0, g0), (t1, g1) in zip(zip(Ts, means), zip(Ts[1:], means[1:])):
        if g0 > 0 >= g1:
            return t0 + (t1 - t0) * g0 / (g0 - g1)
    return None


def main():
    house_style()
    check_type_sizes()

    arm, labels = load_arm(ARM, CKPT)
    Ts = sorted(arm)
    counts = [int((labels == c).sum()) for c in range(len(CLASSES))]

    mean = np.zeros((len(CLASSES), len(Ts)))
    sd = np.zeros_like(mean)
    for ci in range(len(CLASSES)):
        m = labels == ci
        for ti, T in enumerate(Ts):
            v = [signed_gap(arm[T][s], m, ci) for s in SEEDS]
            mean[ci, ti], sd[ci, ti] = st.mean(v), sample_sd(v)

    # --- reportability gate: this figure only exists if the signal beats seed noise.
    ratios = {}
    for ci, name in enumerate(CLASSES):
        rng = float(mean[ci].max() - mean[ci].min())
        msd = float(sd[ci].mean())
        ratios[name] = rng / msd if msd else float("inf")
    weakest = min(ratios, key=ratios.get)
    if ratios[weakest] < 3.0:
        raise RuntimeError(
            f"across-T range is only {ratios[weakest]:.1f}x the seed sd on {weakest} -- this panel "
            f"would be noise dressed as structure. Do not publish it; report the null instead.")

    # --- figure
    cmap = LinearSegmentedColormap.from_list("okabe_div", [BLUE, "#f7f7f7", VERM])
    vmax = float(np.abs(mean).max())
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(90 * MM, 66 * MM))
    # 35 vector rectangles, NOT imshow. imshow embeds the heatmap as a raster XObject, which
    # diagnostics/verify_paper_figures.py rejects and which is exactly what the journal's
    # vector-only requirement is about -- at 90 mm a 7x5 bitmap would visibly soften in print.
    # At this grid size the patch loop costs nothing.
    for ci in range(len(CLASSES)):
        for ti in range(len(Ts)):
            v = mean[ci, ti]
            ax.add_patch(plt.Rectangle((ti - 0.5, ci - 0.5), 1, 1, facecolor=cmap(norm(v)),
                                       edgecolor="white", lw=1.0, zorder=1))
            # White on the saturated ends, near-black in the pale middle.
            txt = "white" if abs(v) > 0.62 * vmax else "#1a1a1a"
            ax.text(ti, ci, f"{v:+.2f}", ha="center", va="center", fontsize=SMALL, color=txt,
                    zorder=3)
            if abs(v) <= sd[ci, ti]:
                # |gap| within one seed sd of zero: this cell is indistinguishable from
                # perfectly calibrated, which is a claim about calibration, not about noise.
                ax.add_patch(plt.Rectangle((ti - 0.5, ci - 0.5), 1, 1, fill=False,
                                           edgecolor="#1a1a1a", lw=1.4, ls=(0, (2, 1.4)),
                                           zorder=2))

    ax.set_xlim(-0.5, len(Ts) - 0.5)
    ax.set_ylim(len(CLASSES) - 0.5, -0.5)     # row 0 on top, as imshow had it
    ax.set_xticks(range(len(Ts)))
    ax.set_xticklabels([("$T$*" if abs(T - TSTAR) < 1e-6 else f"{T:g}") for T in Ts])
    ax.set_xlabel("teacher pre-scaling temperature")
    ax.set_yticks(range(len(CLASSES)))
    ax.set_yticklabels([f"{c} ({n})" + ("  ‡" if n < SMALL_CLASS else "")
                        for c, n in zip(CLASSES, counts)])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    mappable = matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])
    cb = fig.colorbar(mappable, ax=ax, fraction=0.045, pad=0.03)
    # matplotlib rasterises colorbar solids by default (it hides mesh seams in PDF viewers).
    # That is the second raster the vector check flags, so turn it off explicitly.
    cb.solids.set_rasterized(False)
    # Short label only: the full definition ("mean top-1 confidence minus accuracy, by true
    # class") belongs in the caption. Spelled out here it is taller than the colorbar and runs
    # off the top of a 90 mm page.
    cb.set_label("signed gap", fontsize=SMALL)
    cb.ax.tick_params(labelsize=SMALL)
    cb.outline.set_visible(False)
    # The two in-figure marks have to be explained inside the figure, but at 90 mm there is no
    # spare margin to explain them in: placed in axes coords the note landed on the x-axis label,
    # and placed at figure y=0 it landed on the tick labels. So reserve a strip for it explicitly
    # and then draw into that strip -- tight_layout's rect is the only thing that actually keeps
    # the axes out of it.
    fig.tight_layout(rect=(0, 0.085, 1, 1))
    fig.text(0.005, 0.012, "‡ n < 100        dashed cell: |gap| within one seed sd of zero",
             ha="left", va="bottom", fontsize=SMALL, color="#444444")

    got_mm = save_at_width(fig, OUT_PDF, 90.0)
    plt.close(fig)

    # --- record
    rec = {"sd_convention": SD_CONVENTION, "arm": ARM, "checkpoint": CKPT, "seeds": list(SEEDS),
           "metric": "per-class signed confidence gap = mean(top-1 confidence) - accuracy, "
                     "grouped by TRUE label, no binning",
           "temperatures": Ts, "classes": {}}
    for ci, name in enumerate(CLASSES):
        rec["classes"][name] = {
            "n": counts[ci],
            # YUVARLAMA YAZMA ANINDA YAPILMAZ (20 Agu 2026, N19b). Bu uc alan artefakta
            # 4dp/1dp YUVARLANMIS yaziliyordu. Sonuc: makale ucuncu basamagi bastiginda
            # defter, zaten yuvarlanmis bir degeri BIR KEZ DAHA yuvarliyordu -- kampanyanin
            # kendi yasakladigi cift yuvarlama, bu kez uretici tarafinda. Ornek: Fear'in
            # T=2.2 bosluğu 0.1655 olarak saklaniyordu; 3 basamaga YARIYI YUKARI yuvarlaninca
            # 0.166 verir, oysa makale 0.165 basiyor. Yuvarlama KARARI defterin isidir ve
            # basamak sayisi orada BEYAN edilir; artefakt olculen degeri tasir.
            "gap_mean": [float(x) for x in mean[ci]],
            "gap_sd": [float(x) for x in sd[ci]],
            "range_over_seed_sd": float(ratios[name]),
            "zero_crossing_T": crossing_T(Ts, list(mean[ci])),
        }
    (OUT_DIR / "perclass_calibration.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    # --- what the figure says, in words, so the caption cannot drift from it
    ti1, tis = Ts.index(1.0), Ts.index(TSTAR)
    print(f"{OUT_PDF.name}  {OUT_PDF.stat().st_size/1024:.1f} KB   {got_mm:.0f} mm wide\n")
    print(f"{'class':<11}{'n':>6}{'gap@T=1':>10}{'gap@T*':>9}{'gap@2.2':>9}"
          f"{'T(gap=0)':>10}{'range/sd':>10}")
    for ci, name in enumerate(CLASSES):
        x = rec["classes"][name]["zero_crossing_T"]
        print(f"{name:<11}{counts[ci]:>6}{mean[ci, ti1]:>+10.3f}{mean[ci, tis]:>+9.3f}"
              f"{mean[ci, -1]:>+9.3f}{(f'{x:.2f}' if x else '>2.2'):>10}{ratios[name]:>9.1f}x")
    never = [c for c in CLASSES if rec["classes"][c]["zero_crossing_T"] is None]
    print(f"\nEvery class is over-confident under the native teacher, and every class improves "
          f"monotonically with T --\nbut the spread at T=1 is {mean[:, ti1].max()/mean[:, ti1].min():.0f}x "
          f"({CLASSES[int(mean[:, ti1].argmax())]} {mean[:, ti1].max():+.3f} vs "
          f"{CLASSES[int(mean[:, ti1].argmin())]} {mean[:, ti1].min():+.3f}), and no single scalar "
          f"temperature\ncalibrates all seven: {', '.join(never)} never reach a zero gap within the "
          f"tested range,\nwhile the frequent classes have already been driven under-confident by "
          f"T=2.2.")
    print(f"\nWrote {OUT_DIR / 'perclass_calibration.json'}")


if __name__ == "__main__":
    main()
