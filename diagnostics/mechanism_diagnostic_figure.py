"""Figure (c): the mechanism ablation on BOTH axes at once -- Δaccuracy against ΔECE.

WHAT IT ARGUES. A conventional ablation table reports one number per mechanism: Δaccuracy. On
that axis every mechanism in this grid looks similar and unremarkable, and `logit_std` in
particular looks harmless. Plotting the same runs against ΔECE separates them immediately:
`logit_std` sits far off the calibration axis while barely moving on the accuracy axis. The
figure is the campaign's "accuracy-only ablation misleads" claim in one panel.

READING THE QUADRANTS. Down-and-right is strictly good (more accurate, better calibrated);
up-and-left is strictly bad. The other two quadrants are trade-offs that an accuracy-only table
cannot even express -- which is the point.

SAME SOURCE AS T5. The deltas are taken from `paper_tables.mechanism_table`, not recomputed, so
the figure cannot drift from the table it illustrates: matched control per (teacher, seed), same
budget/alpha gate, same paired differencing.

Read-only, zero GPU. Outputs -> diagnostics/paper_tables/mechanism_diagnostic.{png,json}
"""
import json
import statistics as st
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from paper_tables import A_AUDIT_MECH, load_audit, load_runs, mechanism_table  # noqa: E402
from stats_convention import SD_CONVENTION  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
CKPT = "swa"

TEACHER_MARKER = {"stage1": "o", "primary": "s", "vae9182": "^"}
HILITE = "logit_std"


def main():
    runs, audit = load_runs(), load_audit(A_AUDIT_MECH)
    _, payload = mechanism_table(runs, audit)

    pts = []
    for key, row in sorted(payload.items()):
        teacher, mech = key.split("/", 1)
        c = row.get(CKPT) or {}
        if c.get("d_acc_mean") is None or c.get("d_ece_mean") is None:
            continue
        pts.append({"teacher": teacher, "mechanism": mech,
                    "d_acc": c["d_acc_mean"], "d_ece": c["d_ece_mean"],
                    "d_acc_sd": c["d_acc_sd"], "d_ece_sd": c["d_ece_sd"], "n": c["n"]})
    if not pts:
        raise RuntimeError("no mechanism points -- runs.csv or selection_audit.csv is stale")

    hi = [p for p in pts if p["mechanism"] == HILITE]
    rest = [p for p in pts if p["mechanism"] != HILITE]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.0, 5.4),
                                   gridspec_kw={"width_ratios": [1.15, 1]})

    # Panel B previously annotated every point; with 16 points in a 0.01-tall window the labels
    # overlapped into an unreadable stack. Encoding mechanism as COLOUR and teacher as MARKER
    # carries the same information with zero collisions, and the exact numbers live in T5 anyway.
    mechs = sorted({p["mechanism"] for p in pts if p["mechanism"] != HILITE})
    cmap = plt.get_cmap("tab10")
    MECH_COLOR = {m: cmap(i % 10) for i, m in enumerate(mechs)}
    MECH_COLOR[HILITE] = "#c0392b"

    def draw(ax, subset, annotate):
        ax.axhline(0, color="#555", lw=1, zorder=1)
        ax.axvline(0, color="#555", lw=1, zorder=1)
        for p in subset:
            hot = p["mechanism"] == HILITE
            ax.errorbar(p["d_acc"], p["d_ece"],
                        xerr=(p["d_acc_sd"] if p["n"] > 1 else None),
                        yerr=(p["d_ece_sd"] if p["n"] > 1 else None),
                        marker=TEACHER_MARKER.get(p["teacher"], "D"),
                        markersize=11 if hot else 8,
                        color=("#c0392b" if hot else
                               (MECH_COLOR[p["mechanism"]] if annotate else "#2471a3")),
                        ecolor="#aaa", capsize=2.5, ls="none", zorder=4 if hot else 3)
        ax.set_xlabel(f"Δ doğruluk @{CKPT} (pp)   →  daha doğru")
        ax.set_ylabel(f"Δ ECE @{CKPT}   ↑  daha KÖTÜ kalibre")
        ax.grid(alpha=0.22)

    # Left: everything, so logit_std's distance is visible on the real scale.
    draw(axL, pts, annotate=False)
    # Üç logit_std noktası da AYNI (9, -2) ofsetini kullanıyordu ve bu üç ayrı çakışma
    # üretiyordu: (i) stage1 ile primary ΔECE'de yalnız 0.005 ayrı, iki etiket birbirinin
    # üstüne biniyordu; (ii) primary soldaki nokta olduğu için sağa yazılan etiketi stage1'in
    # işaretçisinin üstünden geçiyordu; (iii) vae9182'nin etiketi kendi yatay hata çubuğunun
    # üstüne düşüyordu (o çubuk +0.70'e kadar uzanıyor). Ofsetler bu yüzden öğretmene özel:
    # primary SOLA yazılır (stage1'den uzaklaşır), stage1 sağa-yukarı, vae9182 yukarı
    # (hata çubuğunu temizler).
    LABEL_OFFSET = {"primary": ((-11, -4), "right"),
                    "stage1": ((11, 2), "left"),
                    "vae9182": ((11, 9), "left")}
    for p in hi:
        (dx_pt, dy_pt), ha = LABEL_OFFSET.get(p["teacher"], ((9, -2), "left"))
        axL.annotate(f"logit_std ({p['teacher']})", (p["d_acc"], p["d_ece"]),
                     textcoords="offset points", xytext=(dx_pt, dy_pt), ha=ha,
                     fontsize=8.5, color="#c0392b")
    ymax = max(p["d_ece"] for p in pts)
    axL.set_title("A · Gerçek ölçek: doğrulukta neredeyse hiçbir şey olmuyor,\n"
                  "kalibrasyonda `logit_std` tabloyu terk ediyor", fontsize=10.5)
    axL.text(0.02, 0.97, f"logit_std ΔECE'si diğer tüm\nmekanizmaların {ymax / max(abs(p['d_ece']) for p in rest):.0f}× üstünde",
             transform=axL.transAxes, va="top", fontsize=8.5, color="#c0392b", zorder=6,
             # zorder: vae9182'nin yatay hata çubuğu (+0.70'e kadar uzanıyor) bu kutunun
             # ilk satırının içinden geçip metni üstü çizili gösteriyordu. Kutu öne alındı.
             bbox=dict(boxstyle="round,pad=0.35", fc="#fdf2f0", ec="#c0392b", lw=0.8))

    # Right: zoom on everything else, where the real trade-offs live.
    draw(axR, rest, annotate=True)
    # SINIRLAR HATA ÇUBUĞUNUN UÇLARINDAN (13 Ağu 2026) -- aynı düzeltme
    # `export_paper_figures.fig_mechanism_diagnostic` içinde de var (kural üç satırlık aritmetik
    # olduğu için ithal edilmiyor, ama iki yerde de aynı olmak ZORUNDA: aynı veriyi gösteren iki
    # çıktı farklı pencere gösteremez).
    #
    # Eski hâl pencereyi NOKTA ORTALAMALARINDAN kuruyordu ve bu panelde **9 yatay + 2 dikey**
    # çubuğu kırpıyordu (ölçüldü). Kırpılan çubuk belirsizliği olduğundan küçük gösterir; bu
    # panelin işi tam da belirsizliği göstermek. n=1 noktalarının sd'si sıfır sayılır.
    def _ext(key, sd_key):
        lo = min(p[key] - ((p[sd_key] or 0.0) if p["n"] > 1 else 0.0) for p in rest)
        hi = max(p[key] + ((p[sd_key] or 0.0) if p["n"] > 1 else 0.0) for p in rest)
        return lo, hi
    x_lo, x_hi = _ext("d_acc", "d_acc_sd")
    y_lo, y_hi = _ext("d_ece", "d_ece_sd")
    x_span, y_span = x_hi - x_lo, y_hi - y_lo
    axR.set_xlim(x_lo - 0.05 * x_span, x_hi + 0.05 * x_span)
    # üst pay lejant için (loc="upper center"), alt pay yalnız nefes payı
    axR.set_ylim(y_lo - 0.06 * y_span, y_hi + 0.45 * y_span)
    axR.set_title("B · `logit_std` hariç yakınlaştırma:\nasıl takaslar burada  (y ölçeği 24× daha dar)",
                  fontsize=10.5)
    axR.text(0.98, 0.03, "sağ-alt çeyrek = kesin iyileşme", transform=axR.transAxes,
             ha="right", va="bottom", fontsize=8, color="#1e8449")
    axR.legend(handles=[plt.Line2D([], [], ls="none", marker="o", color=MECH_COLOR[m],
                                   markersize=7, label=m) for m in mechs],
               fontsize=7.4, loc="upper center", ncol=3, title="mekanizma (renk)",
               title_fontsize=7.6, framealpha=0.92)

    handles = [plt.Line2D([], [], ls="none", marker=m, color="#555", markersize=8, label=t)
               for t, m in TEACHER_MARKER.items()]
    handles.append(plt.Line2D([], [], ls="none", marker="o", color="#c0392b", markersize=10,
                              label="logit_std"))
    axL.legend(handles=handles, fontsize=8.5, loc="lower right",
               title="öğretmen (şekil)", title_fontsize=8)

    fig.suptitle("Mekanizma ablasyonu iki eksende: yalnız doğruluğa bakan bir tablo "
                 "`logit_std`'i 'nötr' diye raporlardı", fontsize=12)
    fig.tight_layout()
    png = OUT_DIR / "mechanism_diagnostic.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)

    (OUT_DIR / "mechanism_diagnostic.json").write_text(
        json.dumps({"sd_convention": SD_CONVENTION, "checkpoint": CKPT, "points": pts},
                   indent=2), encoding="utf-8")
    print(f"{len(pts)} mechanism points @{CKPT} ({len(hi)} logit_std)")
    print(f"largest abs(dECE) excluding logit_std: {max(abs(p['d_ece']) for p in rest):.4f}")
    print(f"logit_std dECE range: {min(p['d_ece'] for p in hi):+.4f} .. {max(p['d_ece'] for p in hi):+.4f}")
    print(f"\nSaved {png}")


if __name__ == "__main__":
    main()
