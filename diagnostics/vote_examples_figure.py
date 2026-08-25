"""Figure 6: FERPlus rater votes vs teacher softmax, before and after T*_JSD scaling.

WHAT THIS FIGURE IS FOR. The FERPlus leg of the argument rests on a claim that is easy to state
and hard to believe from a table: the teacher's softmax, once scaled to T*_JSD, is not merely
"better calibrated" in the abstract -- it moves toward the shape of the actual 10-rater vote
distribution. Four columns of real examples, spanning the whole range of human disagreement,
let a reader check that claim by eye against the raw data instead of taking JSD 0.0492 -> 0.0440
on faith.

COLUMN SELECTION IS A RULE, NOT A CHOICE. Hand-picking examples for a figure like this is the
single easiest way to overstate a result, so the columns are the val-set samples NEAREST to the
10th, 40th, 70th and 95th percentiles of human vote entropy, and the chosen indices, their
entropies and the number of tied candidates all go to JSON. Ties are large at the low end --
31.8 % of FERPlus val has entropy exactly 0 (unanimous raters) -- so the tie is broken by lowest
loader index, which is deterministic and carries no information about how the example looks.

IMAGES ARE SHOWN AT NATIVE 48x48. FER2013 images are 48x48 greyscale and will look blocky. That
is the dataset, so interpolation="none" is used: matplotlib then embeds the array itself in the
PDF at its own resolution rather than resampling it to the figure's, and the reader sees exactly
the pixels the network saw. These four raster images are the ONLY raster content in the paper's
figure set, and diagnostics/verify_paper_figures.py is told to expect exactly four here.

CORRECTNESS GATE. The vote distributions are re-derived here from the metadata CSV through the
same path mapping the JSD analysis used, and the resulting per-sample entropies are asserted
against diagnostics/ferplus_jsd/per_sample_human_entropy.npy. If the row alignment between
logits and votes were ever off by even one sample, the panels would silently pair the wrong face
with the wrong votes -- which is exactly the kind of error a figure cannot show you.

Vote normalisation follows ferplus_human_vote_jsd.py: each row is divided by its OWN vote sum,
not by a fixed 10, because the 8 emotion votes do not always sum to 10 (1176 of 3153 rows).

Outputs -> paper/figures/vote_examples.pdf              (190 mm)
           diagnostics/ferplus_jsd/vote_examples.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from export_paper_figures import MM, W2, BLUE, VERM, SMALL, house_style, check_type_sizes  # noqa: E402
from reliability_diagram import save_at_width  # noqa: E402

JSD_DIR = ROOT / "diagnostics" / "ferplus_jsd"
OUT_PDF = ROOT / "paper" / "figures" / "vote_examples.pdf"
IMG_ROOT = ROOT / "data" / "FERPlus_processed"
METADATA = ROOT / "configs" / "FERPlus_majority_metadata.csv"
VAL_FOLDS = [2]

EMOTIONS = ["neutral", "happiness", "surprise", "sadness", "anger", "disgust", "fear", "contempt"]
SHORT = ["neu", "hap", "sur", "sad", "ang", "dis", "fea", "con"]
PERCENTILES = (10, 40, 70, 95)
T_JSD = 0.74
EPS = 1e-12


def entropy(p):
    return -(p * np.log(p + EPS)).sum(axis=1)


def jsd(p, q):
    """Per-sample Jensen-Shannon divergence in NATS -- same definition and units as
    diagnostics/ferplus_human_vote_jsd.py, so the per-column numbers printed on the panels are
    comparable to the campaign's mean JSD of 0.0492 (T=1) and 0.0440 (T*)."""
    m = 0.5 * (p + q)

    def kl(a, b):
        return (a * (np.log(a + EPS) - np.log(b + EPS))).sum(axis=1)
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def load_data():
    blob = torch.load(JSD_DIR / "ferplus_val_logits.pt", map_location="cpu", weights_only=False)
    logits, paths = blob["logits"].float(), blob["paths"]

    df = pd.read_csv(METADATA)
    df = df[df["fold"].isin(VAL_FOLDS)].reset_index(drop=True)
    by_name = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows = [by_name[Path(p).name] for p in paths]          # loader order, not CSV order
    votes = df.loc[rows, EMOTIONS].to_numpy(dtype=np.float64)
    sums = votes.sum(axis=1, keepdims=True)
    if (sums <= 0).any():
        raise RuntimeError("a val row has zero total votes; it cannot be normalised")
    p_human = votes / sums

    # Gate: this must reproduce the entropy the JSD analysis computed, or the votes here are
    # attached to different samples than the logits are.
    h = entropy(p_human)
    ref = np.load(JSD_DIR / "per_sample_human_entropy.npy")
    if h.shape != ref.shape or not np.allclose(h, ref, atol=1e-5):
        raise RuntimeError(
            f"human entropy does not match per_sample_human_entropy.npy "
            f"(max |d| = {np.abs(h - ref).max():.2e}) -- the vote rows and the logits are not "
            f"aligned, so every panel would pair the wrong face with the wrong votes.")

    img_paths = [df.loc[r, "path"] for r in rows]
    # Only AFTER the gate: a unanimous row gives -(1*log 1) = -0.0, which formats as "-0.00".
    # Entropy is non-negative by definition, so clamp the sign artefact away for display.
    return logits, p_human, np.maximum(h, 0.0), img_paths, votes, sums.ravel()


def pick_columns(h):
    """Sample nearest each percentile of human vote entropy. Deterministic under ties."""
    out = []
    for p in PERCENTILES:
        target = float(np.percentile(h, p))
        d = np.abs(h - target)
        i = int(np.argmin(d))                       # lowest loader index among the nearest
        out.append({"percentile": p, "target_entropy": target, "index": i,
                    "entropy": float(h[i]), "n_tied_candidates": int((d == d[i]).sum())})
    return out


def main():
    house_style()
    check_type_sizes()

    logits, p_human, h, img_paths, votes, vote_sums = load_data()
    cols = pick_columns(h)

    q1 = F.softmax(logits, dim=1).numpy()
    qj = F.softmax(logits / T_JSD, dim=1).numpy()
    # Per-example distance to the rater votes, annotated on rows 3 and 4. Without it a reader
    # would naturally read "T* minimises mean JSD" as "T* moves every example closer to the
    # humans", which is false -- it is a mean over 3153 samples and individual examples move
    # both ways. The number on each panel says which happened for that face.
    d1, dj = jsd(p_human, q1), jsd(p_human, qj)

    # Rows 2-4 share one y scale so the three distributions are directly comparable; the scale
    # is set by the largest bar anywhere in the figure, which at the low-entropy end is a
    # unanimous human vote at 1.0.
    ymax = max(max(p_human[c["index"]].max(), q1[c["index"]].max(), qj[c["index"]].max())
               for c in cols)
    ylim = min(1.0, ymax * 1.12) if ymax < 0.9 else 1.04

    fig = plt.figure(figsize=(W2, 96 * MM))
    gs = fig.add_gridspec(4, 4, height_ratios=[1.35, 1.0, 1.0, 1.0],
                          hspace=0.22, wspace=0.16)

    x = np.arange(len(EMOTIONS))
    # Short row labels on purpose. A rotated ylabel is bounded by its own panel's height, and
    # each of these panels is ~18 mm tall; "teacher  $T$*=0.74" overflowed into the row above it.
    # The legend already names the two sources, so the label only has to carry the temperature.
    ROWS = [("human", BLUE, "///"),
            ("$T$ = 1.0", VERM, ""),
            (f"$T$* = {T_JSD:g}", VERM, "")]

    first_col_axes = []          # üst sıra etiketinin hizalanacağı referans satırlar
    top_label_ax = None

    for ci, c in enumerate(cols):
        i = c["index"]

        # --- row 1: the face, at native 48x48
        axi = fig.add_subplot(gs[0, ci])
        arr = np.array(Image.open(IMG_ROOT / img_paths[i]))
        axi.imshow(arr, cmap="gray", vmin=0, vmax=255, interpolation="none")
        axi.set_xticks([])
        axi.set_yticks([])
        for s in axi.spines.values():
            s.set_linewidth(0.6)
            s.set_color("0.4")
        axi.text(0.5, 1.06, f"p{c['percentile']}   $H$ = {c['entropy']:.2f} nats",
                 transform=axi.transAxes, ha="center", va="bottom", fontsize=SMALL)
        if ci == 0:
            # ÜST SIRA HİZASI. imshow kareyi korumak için eksen kutusunu hücrenin içinde
            # DARALTIR; ylabel de daralmış kutuya yapıştığı için "FERPlus val" alttaki üç
            # satır etiketinden (human / T=1.0 / T*=0.74) belirgin biçimde sağda kalıyordu --
            # dört satırlık bir ızgarada tek satırın etiketi hizasız duruyordu. Etiketi
            # eksene değil FİGÜRE bağlıyoruz ve x'ini alttaki satırlardan ölçüyoruz
            # (aşağıda, tüm eksenler kurulduktan sonra), böylece daralma hizayı bozamaz.
            axi.set_ylabel("FERPlus val", fontsize=SMALL)
            top_label_ax = axi

        # --- rows 2-4: the three distributions over the same 8 classes
        for ri, (vals, (label, colour, hatch), note) in enumerate(
                zip((p_human[i], q1[i], qj[i]), ROWS,
                    (None, f"JSD {d1[i]:.3f}", f"JSD {dj[i]:.3f}")), start=1):
            ax = fig.add_subplot(gs[ri, ci])
            ax.bar(x, vals, width=0.74,
                   facecolor="none" if hatch else colour, edgecolor=colour,
                   hatch=hatch, linewidth=0.6)
            if note:
                ax.text(0.97, 0.92, note, transform=ax.transAxes, ha="right", va="top",
                        fontsize=SMALL, color="#333333")
            ax.set_ylim(0, ylim)
            ax.set_xlim(-0.7, len(EMOTIONS) - 0.3)
            ax.grid(True, axis="y", ls="-", lw=0.4, alpha=0.2)
            ax.set_axisbelow(True)
            ax.tick_params(length=2)
            if ci == 0:
                ax.set_ylabel(label, fontsize=SMALL)
                first_col_axes.append(ax)
            else:
                ax.set_yticklabels([])
            if ri == 3:
                ax.set_xticks(x)
                ax.set_xticklabels(SHORT, rotation=90, fontsize=SMALL)
            else:
                ax.set_xticks(x)
                ax.set_xticklabels([])

    # Üst sıranın "FERPlus val" etiketini alttaki üç satır etiketiyle aynı x'e getir.
    # align_ylabels tek başına yetmiyor: imshow'un en-boy daraltması ÇİZİM anında
    # uygulanıyor, o yüzden önce bir kez çizdirip daralmış kutunun gerçek konumunu
    # okuyoruz, sonra etiketi eksen koordinatında geri itiyoruz.
    if top_label_ax is not None and first_col_axes:
        # Çapa noktası ile metnin sol kenarı aynı şey değil, o yüzden tek atışta
        # hesaplamıyoruz: BİLİNEN bir eksen-x'ten başlayıp çiziyor, iki etiketin gerçek sol
        # kenarını ölçüyor, farkı eksen-x birimine çevirip düzeltiyoruz.
        #
        # Başlangıcın bilinen olması şart: set_label_coords çağrılmadan ylabel'ın transformu
        # x'te PİKSEL taşır, get_position() oradan eksen-kesri diye okunursa etiket yüzlerce
        # eksen genişliği uzağa fırlar (ilk denemede tam bu oldu: artık 8834 px, tight bbox
        # patlayıp figür 1890x150'ye çöktü).
        GUESS = -0.30
        lbl = top_label_ax.yaxis.label
        top_label_ax.yaxis.set_label_coords(GUESS, 0.5)
        fig.canvas.draw()
        target = min(a.yaxis.label.get_window_extent().x0 for a in first_col_axes)
        box = top_label_ax.get_position()
        delta_px = lbl.get_window_extent().x0 - target
        top_label_ax.yaxis.set_label_coords(
            GUESS - delta_px / (box.width * fig.bbox.width), 0.5)
        fig.canvas.draw()
        resid = abs(lbl.get_window_extent().x0 - target)
        if resid > 2.0:
            # Kozmetik bir hiza yüzünden figür üretimi durmamalı; güvenli konuma dön ve söyle.
            top_label_ax.yaxis.set_label_coords(GUESS, 0.5)
            print(f"  [UYARI] ust sira etiketi hizalanamadi (artik {resid:.1f} px); "
                  f"guvenli konuma donuldu")
        else:
            print(f"  top-row label aligned with the rows below (residual {resid:.2f} px)")

    fig.legend(handles=[Patch(facecolor="none", edgecolor=BLUE, hatch="///",
                              label="human raters (10 votes)"),
                        Patch(facecolor=VERM, edgecolor=VERM, label="teacher softmax")],
               loc="lower left", bbox_to_anchor=(0.075, -0.035), ncol=2, fontsize=SMALL,
               frameon=False, handlelength=1.6, columnspacing=2.0)

    got_mm = save_at_width(fig, OUT_PDF, 190.0)
    plt.close(fig)

    rec = {"figure": "vote_examples.pdf", "n_val": int(len(h)), "val_folds": VAL_FOLDS,
           "selection_rule": "sample nearest each percentile of human vote entropy; ties broken "
                             "by lowest loader index",
           "T_jsd": T_JSD, "classes": EMOTIONS, "shared_y_limit": ylim,
           "human_entropy_percentiles": {str(p): float(np.percentile(h, p))
                                         for p in (0, 10, 25, 40, 50, 70, 90, 95, 100)},
           "columns": []}
    for c in cols:
        i = c["index"]
        rec["columns"].append({
            **c,
            "image_path": img_paths[i],
            "image_shape": list(np.array(Image.open(IMG_ROOT / img_paths[i])).shape),
            "vote_counts": [int(v) for v in votes[i]],
            "vote_sum": int(vote_sums[i]),
            "human_p": [round(float(v), 4) for v in p_human[i]],
            "teacher_p_T1": [round(float(v), 4) for v in q1[i]],
            "teacher_p_Tjsd": [round(float(v), 4) for v in qj[i]],
            "human_argmax": EMOTIONS[int(p_human[i].argmax())],
            "teacher_argmax": EMOTIONS[int(q1[i].argmax())],
            "jsd_T1": round(float(d1[i]), 4),
            "jsd_Tjsd": round(float(dj[i]), 4),
            "jsd_delta": round(float(dj[i] - d1[i]), 4),
        })
    rec["jsd_mean_all_val"] = {"T1": round(float(d1.mean()), 4),
                              "Tjsd": round(float(dj.mean()), 4),
                              "improved_fraction": round(float((dj < d1).mean()), 4)}
    (JSD_DIR / "vote_examples.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")

    print(f"{OUT_PDF.name}  {OUT_PDF.stat().st_size/1024:.1f} KB   {got_mm:.0f} mm wide\n")
    print(f"{'col':>4}{'pct':>5}{'H (nats)':>10}{'ties':>7}{'image':>26}"
          f"{'human argmax':>15}{'teacher argmax':>16}")
    for k, c in enumerate(rec["columns"]):
        print(f"{k+1:>4}{c['percentile']:>5}{c['entropy']:>10.3f}{c['n_tied_candidates']:>7}"
              f"{Path(c['image_path']).name:>26}{c['human_argmax']:>15}{c['teacher_argmax']:>16}")
    print(f"\n{'col':>4}{'JSD @T=1':>11}{'JSD @T*':>10}{'delta':>9}")
    for k, c in enumerate(rec["columns"]):
        print(f"{k+1:>4}{c['jsd_T1']:>11.4f}{c['jsd_Tjsd']:>10.4f}{c['jsd_delta']:>+9.4f}")
    m = rec["jsd_mean_all_val"]
    print(f"\nWHOLE val set (n={len(h)}): mean JSD {m['T1']:.4f} -> {m['Tjsd']:.4f}; "
          f"T* moves {100*m['improved_fraction']:.1f}% of samples CLOSER to the raters.")
    print(f"shared y limit for rows 2-4: {ylim:.2f}")
    print(f"Wrote {JSD_DIR / 'vote_examples.json'}")


if __name__ == "__main__":
    main()
