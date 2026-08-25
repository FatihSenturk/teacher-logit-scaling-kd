"""Figure: reliability diagram + confidence distribution, raw vs calibrated teacher (RAF-DB Stage1).

WHAT THE FIGURE HAS TO SHOW. Every calibration claim in this paper is currently a scalar -- ECE
in a table. Guo et al. (2017) made the reliability diagram the standard way to show WHERE a
model's confidence is wrong, and a calibration paper without one invites the obvious question of
what the ECE number is hiding. This figure answers it for the campaign's cleanest causal pair:
one student distilled from the raw Stage1 teacher (T=1.0) and one from the SAME teacher after
post-hoc temperature scaling to its fitted optimum (T*=1.3406). Nothing else differs -- same
recipe, same seeds, same student, same 3068 fold-3 images.

THREE PANELS:
  (a) student <- raw teacher        reliability, 15 equal-width bins
  (b) student <- calibrated teacher reliability, same bins
  (c) per-bin share of samples, both arms, broken axis -- where the confidence mass actually sits

WHY (c) HAS A BROKEN AXIS. 90 % of predictions land in the single top bin, so on a linear axis
the panel is one bar and eleven invisible ones. The first attempt used a log axis, which does
make the tail legible but destroys the headline: 89.9 % and 82.7 % are visually the same height
in log space, so the one number the panel exists to show -- mass LEAVING the saturated bin --
disappeared. A break at 8 % keeps both: the lower section resolves the 0.01-8 % tail, the upper
section resolves the top bin, and neither is compressed. The effect then reads directly as
top bin 89.9 % -> 82.7 % with the bin below it going 3.0 % -> 6.5 %.
Panel (c) also settles how (a)/(b) show per-bin n: repeating counts there would duplicate this
panel exactly, so instead those bars are made TRANSPARENT IN PROPORTION to their bin's share and
any bin holding under 0.5 % of samples is flagged with an open marker. A reader can therefore
never mistake the near-empty low-confidence bins -- one of which holds a single sample -- for
evidence.

WHAT "MEAN OF THREE SEEDS" MEANS HERE, PRECISELY:
  bars   pooled over the 3 seeds (9204 predictions). For equal-width bins, pooling IS the
         count-weighted seed mean of the per-bin statistics; an unweighted mean would give a
         bin that happens to be near-empty in one seed the same vote as a full one.
  ECE    the annotation reports mean +/- sample sd (n-1) ACROSS SEEDS -- i.e. the same number
         the Results table prints, so figure and table cannot disagree. The pooled-bin ECE is
         computed too and printed to stdout; if the two ever separate by more than 0.005 this
         script says so rather than letting the annotation quietly stop describing the bars.

Data: per-sample logits from diagnostics/student_logit_cache.py (built on cuda, each entry
bit-matched to its run's selection_audit.json). No GPU, no training here.

Outputs -> paper/figures/reliability_diagram.pdf  (190 mm)
           diagnostics/reliability/reliability_diagram.json
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from student_logit_cache import load_arm  # noqa: E402
from p1_two_teacher_overlay import CURVES  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from export_paper_figures import (  # noqa: E402  single source of house style
    MM, W2, BLUE, VERM, BLACK, SMALL, house_style, check_type_sizes, panel, save_at_width)

OUT_PDF = ROOT / "paper" / "figures" / "reliability_diagram.pdf"
OUT_DIR = ROOT / "diagnostics" / "reliability"
OUT_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_CSV = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"

N_BINS = 15
CKPT = "swa"
SEEDS = (42, 1, 43)
SPARSE = 0.005          # a bin under this share of samples is flagged as unreliable
ARM = "stage1"
# (T, teacher ECE at that T, panel letter, short label). Teacher ECEs come from the overlay
# artifact below, not from memory -- they are asserted against it at load time.
CONDS = [(1.0, "a", "raw teacher"), (1.3406, "b", "calibrated teacher ($T$*=1.34)")]


def _superseded_save_at_width(fig, path, target_mm, tol=1.0, max_iter=5):
    """SUPERSEDED 2026-08-01 -- canonical copy now lives in export_paper_figures.

    It was moved there because the five paper figures needed it too (they were landing at
    185/187/82 mm instead of 190/90), and a helper that fixes printed width belongs with the
    house style, not with one figure. This module re-exports the canonical one under the old
    name, so `from reliability_diagram import save_at_width` keeps working.

    Original docstring: Save so the PDF ON DISK measures target_mm wide, not the canvas.

    bbox_inches="tight" trims whitespace, so the page that lands on disk is always narrower than
    figsize. For this layout the gap was 26 mm (190 -> 164), which means LaTeX placing it at
    \\textwidth would scale it up 16 % and its type would print 16 % larger than every other
    figure in the paper -- legible, but visibly inconsistent across a figure set.
    Scaling BOTH dimensions by the same factor is what makes this safe: the layout is entirely in
    relative axes coordinates, so a uniform canvas zoom leaves every element exactly where it was
    and only changes how much room the fixed-point-size text takes up.
    """
    import fitz
    w, h = fig.get_size_inches()
    for _ in range(max_iter):
        fig.savefig(path, format="pdf", bbox_inches="tight")
        doc = fitz.open(path)
        got = doc[0].rect.width / 72 * 25.4
        doc.close()
        if abs(got - target_mm) <= tol:
            return got
        k = target_mm / got
        w, h = w * k, h * k
        fig.set_size_inches(w, h)
    return got


def softmax(x):
    e = np.exp(x - x.max(1, keepdims=True))
    return e / e.sum(1, keepdims=True)


def bin_index(conf, n_bins=N_BINS):
    """Exactly the binning of teacher_temperature_scaling_fit.confidence_ece: equal width on
    [0,1], bin i owns (lo, hi], and the first bin is closed on the left."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    return np.clip(np.digitize(conf, edges[1:-1], right=True), 0, n_bins - 1), edges


def reliability(logits, labels):
    """Per-bin (n, accuracy, mean confidence) plus the ECE those bins imply."""
    p = softmax(logits)
    conf, pred = p.max(1), p.argmax(1)
    correct = (pred == labels)
    idx, edges = bin_index(conf)
    out = []
    ece = 0.0
    for b in range(N_BINS):
        m = idx == b
        c = int(m.sum())
        if c == 0:
            out.append({"n": 0, "acc": None, "conf": None})
            continue
        a, cf = float(correct[m].mean()), float(conf[m].mean())
        out.append({"n": c, "acc": a, "conf": cf})
        ece += (c / len(conf)) * abs(a - cf)
    return out, edges, float(ece), float(conf.mean()), float(correct.mean())


def per_seed_ece():
    """{run_name: ECE @swa} straight out of the audited CSV the tables are built from."""
    out = {}
    for r in csv.DictReader(open(AUDIT_CSV, encoding="utf-8")):
        if r["checkpoint"] == CKPT:
            out[r["run_name"]] = float(r["ece"])
    return out


def teacher_eces():
    d = json.loads((ROOT / "diagnostics" / "p1_dose_response" /
                    "two_dataset_overlay.json").read_text())
    pts = d["arms"][f"rafdb_{ARM}"]["points"]
    return {round(float(p["T"]), 4): (p["teacher_ece"], p["signed_gap"]) for p in pts}


def draw_reliability(ax, bins, ece_txt, teacher_txt):
    edges = np.linspace(0.0, 1.0, N_BINS + 1)
    w = edges[1] - edges[0]
    total = sum(b["n"] for b in bins)
    max_share = max(b["n"] for b in bins) / total

    ax.plot([0, 1], [0, 1], color=BLACK, ls=":", lw=0.9, zorder=1)
    for b, lo in zip(bins, edges[:-1]):
        if b["n"] == 0:
            continue
        share = b["n"] / total
        # Transparency IS the sample count: a bin holding 1 of 9204 predictions must not draw
        # with the same authority as one holding 8278. sqrt keeps mid-sized bins visible.
        alpha = 0.15 + 0.80 * (share / max_share) ** 0.5
        x, acc, conf = lo + w / 2, b["acc"], b["conf"]
        ax.bar(x, acc, width=w * 0.92, color=BLUE, alpha=alpha, edgecolor=BLUE,
               linewidth=0.4, zorder=2)
        ax.bar(x, abs(conf - acc), bottom=min(acc, conf), width=w * 0.92, facecolor="none",
               edgecolor=VERM, hatch="///", linewidth=0.6, alpha=0.85, zorder=3)
        if share < SPARSE:
            ax.plot([x], [max(acc, conf) + 0.045], marker="o", mfc="none", mec=BLACK,
                    ms=3.2, mew=0.7, ls="none", zorder=4)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.10)
    ax.set_xlabel("confidence")
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.grid(True, ls="-", lw=0.4, alpha=0.2)
    ax.set_axisbelow(True)
    # Bottom-left is the one region a reliability diagram is guaranteed to leave empty: bars
    # live on the diagonal and this model's mass is all at high confidence.
    ax.text(0.035, 0.035, teacher_txt + "\n" + ece_txt, transform=ax.transAxes,
            fontsize=SMALL, va="bottom", ha="left", linespacing=1.35,
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="0.75", lw=0.5, alpha=0.92))


def main():
    house_style()
    check_type_sizes()

    arm, labels = load_arm(ARM, CKPT)
    audit = per_seed_ece()
    t_ece = teacher_eces()

    fig = plt.figure(figsize=(W2, 70 * MM))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 1.15],
                          height_ratios=[1.0, 2.4], wspace=0.30, hspace=0.10)
    # (a) and (b) span the full height; (c) is split into the two sections of a broken axis.
    axes = [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[:, 1])]
    ax_hi, ax_lo = fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[1, 2])

    record, hist = {"sd_convention": SD_CONVENTION, "n_bins": N_BINS, "checkpoint": CKPT,
                    "arm": ARM, "seeds": list(SEEDS), "conditions": {}}, {}

    for (T, letter, short), ax in zip(CONDS, axes[:2]):
        runs = CURVES[ARM][T]
        pooled_logits = np.concatenate([arm[T][s] for s in SEEDS], axis=0)
        pooled_labels = np.concatenate([labels] * len(SEEDS), axis=0)
        bins, _, pooled_ece, mconf, macc = reliability(pooled_logits, pooled_labels)

        eces = [audit[runs[s]] for s in SEEDS]
        m, sd = st.mean(eces), sample_sd(eces)
        if abs(pooled_ece - m) > 0.005:
            raise RuntimeError(
                f"T={T}: pooled-bin ECE {pooled_ece:.4f} and mean-of-seeds ECE {m:.4f} differ by "
                f"{abs(pooled_ece - m):.4f} (>0.005). The annotation would stop describing the "
                f"bars it sits on -- resolve before publishing this panel.")

        te, tgap = t_ece[round(T, 4)]
        draw_reliability(ax, bins,
                         ece_txt=f"teacher ECE {te:.4f}\nstudent ECE {m:.4f} ± {sd:.4f}",
                         teacher_txt=short)
        panel(ax, letter)
        if letter == "a":
            ax.set_ylabel("accuracy")
        else:
            # Same scale as (a); repeating the labels only steals width from the panels.
            ax.set_yticklabels([])
        hist[T] = [b["n"] for b in bins]
        record["conditions"][f"T={T:g}"] = {
            "runs": {str(s): runs[s] for s in SEEDS},
            "teacher_ece": te, "teacher_signed_gap": tgap,
            "student_ece_mean": m, "student_ece_sd": sd, "student_ece_per_seed": eces,
            "pooled_bin_ece": pooled_ece, "pooled_mean_conf": mconf, "pooled_accuracy": macc,
            "pooled_signed_gap": mconf - macc,
            # EN YUKSEK GUVEN KUTUSUNDAKI KUTLE (20 Agu 2026, N19b). Bu buyukluk bugune
            # kadar YALNIZ EKRANA basiliyordu (asagidaki "top-bin share" satiri) ve
            # makalede §5.1'de iki sayi olarak geciyordu -- ama hicbir artefakt alani
            # yoktu, yani makaledeki 89.9/82.7 bir uretici ciktisina baglanamiyordu.
            # Sayiyi ekrana basmak onu kayda gecirmez; alan olarak yaziyoruz.
            "top_bin": {
                "index": N_BINS - 1,
                "n": bins[-1]["n"],
                "n_pooled": sum(x["n"] for x in bins),
                "share_pct": 100.0 * bins[-1]["n"] / sum(x["n"] for x in bins),
            },
            "bins": bins,
        }

    # ---- panel (c): where the confidence mass sits, on a broken axis (see module docstring)
    edges = np.linspace(0.0, 1.0, N_BINS + 1)
    w = edges[1] - edges[0]
    style = {1.0: (BLUE, "", "raw teacher"), 1.3406: (VERM, "///", "calibrated ($T$*)")}
    for k, (T, _letter, _short) in enumerate(CONDS):
        counts = np.array(hist[T], dtype=float)
        share = 100.0 * counts / counts.sum()
        c, hatch, lab = style[T]
        x = edges[:-1] + w * (0.10 + 0.42 * k)
        for ax in (ax_hi, ax_lo):
            ax.bar(x, share, width=w * 0.40, align="edge", color="none" if hatch else c,
                   edgecolor=c, hatch=hatch, linewidth=0.6, label=lab if ax is ax_lo else None)
        # The top bin is the whole point of the break; label it so the shift is a number too.
        # Set just LEFT of the bars and vertically centred on each bar's top, so the number sits
        # at its own bar's level: right-aligned text above the bars overhangs x=1 and clips.
        ax_hi.text(edges[-2] - 0.008, share[-1], f"{share[-1]:.1f}",
                   fontsize=SMALL, ha="right", va="center", color=c)

    ax_hi.set_ylim(74, 99)
    ax_hi.set_yticks([80, 90])
    ax_lo.set_ylim(0, 8.4)
    ax_lo.set_yticks([0, 2, 4, 6, 8])
    for ax in (ax_hi, ax_lo):
        ax.set_xlim(0, 1)
        ax.grid(True, ls="-", lw=0.4, alpha=0.2)
        ax.set_axisbelow(True)
    ax_hi.spines["bottom"].set_visible(False)
    ax_lo.spines["top"].set_visible(False)
    ax_hi.set_xticklabels([])
    ax_hi.tick_params(bottom=False)
    ax_lo.set_xlabel("confidence")
    # One ylabel for the pair, placed on the figure so it centres across the break.
    ax_lo.set_ylabel("share of predictions (%)")
    ax_lo.yaxis.set_label_coords(-0.155, 0.72)
    # Break marks: the standard pair of slanted rules across the two facing spines.
    kw = dict(marker=[(-1, -0.6), (1, 0.6)], markersize=5, linestyle="none",
              color=BLACK, mec=BLACK, mew=0.8, clip_on=False)
    ax_hi.plot([0, 1], [0, 0], transform=ax_hi.transAxes, **kw)
    ax_lo.plot([0, 1], [1, 1], transform=ax_lo.transAxes, **kw)
    panel(ax_hi, "c")
    ax_lo.legend(loc="upper left", frameon=True, framealpha=0.92, handlelength=1.7,
                 borderpad=0.35, labelspacing=0.3, fontsize=SMALL)

    # Shared legend for (a)/(b), under the two reliability panels rather than inside them --
    # the bars occupy the diagonal, so any in-axes placement covers data in one panel or both.
    fig.legend(handles=[Patch(facecolor=BLUE, edgecolor=BLUE, alpha=0.75, label="accuracy"),
                        Patch(facecolor="none", edgecolor=VERM, hatch="///",
                              label="confidence excess"),
                        Line2D([], [], color=BLACK, ls="none", marker="o", mfc="none",
                               ms=3.2, mew=0.7, label=f"bin < {SPARSE*100:g}% of samples")],
               loc="lower left", bbox_to_anchor=(0.055, -0.10), ncol=3, fontsize=SMALL,
               frameon=False, handlelength=1.6, columnspacing=1.6)

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    got_mm = save_at_width(fig, OUT_PDF, 190.0)
    plt.close(fig)

    (OUT_DIR / "reliability_diagram.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")

    a, b = record["conditions"]["T=1"], record["conditions"]["T=1.3406"]
    print(f"{OUT_PDF.name}  {OUT_PDF.stat().st_size/1024:.1f} KB   190 mm wide\n")
    print(f"{'':22}{'raw (T=1)':>14}{'calibrated (T*)':>18}")
    for k, lbl, f in (("teacher_ece", "teacher ECE", "{:.4f}"),
                      ("student_ece_mean", "student ECE (mean)", "{:.4f}"),
                      ("student_ece_sd", "  sd across seeds", "{:.4f}"),
                      ("pooled_bin_ece", "pooled-bin ECE", "{:.4f}"),
                      ("pooled_mean_conf", "mean confidence", "{:.4f}"),
                      ("pooled_accuracy", "accuracy", "{:.4f}"),
                      ("pooled_signed_gap", "signed gap", "{:+.4f}")):
        print(f"{lbl:22}{f.format(a[k]):>14}{f.format(b[k]):>18}")
    # Ekrana basilan deger ARTIK alandan okunuyor: iki yerde iki kez hesaplanan bir sayi,
    # ikisi ayrisinca hangisinin dogru oldugunun bilinemedigi bir sayidir.
    print(f"{'top-bin share':22}{a['top_bin']['share_pct']:13.1f}%"
          f"{b['top_bin']['share_pct']:17.1f}%")
    print(f"\nWrote {OUT_DIR / 'reliability_diagram.json'}")


if __name__ == "__main__":
    main()
