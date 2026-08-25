"""Seçim denetiminin DAĞILIMI: 131 koşunun best−last farkları, iki eksen yan yana.

NİÇİN ORTALAMA YETMİYOR. T8 tek satırda "+0.766 ± 0.431 pp" diyor ve bu, hakemin sorduğu soruyu
cevaplamıyor: bu bir kaç koşunun sürüklediği bir ortalama mı, yoksa külliyat genelinde sistematik
bir kayma mı? Dağılım bunu tek bakışta kesiyor — doğruluk bulutu **129/131 koşuda** sıfırın
sağında, yani kayma neredeyse tek taraflı; kalibrasyon bulutu ise sıfırın iki yanına da yayılıyor.

FİGÜRÜN TAŞIDIĞI İDDİA, TAM HÂLİYLE. Doğrulukla epoch seçmek doğruluğu **sistematik** olarak
şişiriyor (ortalama kendi sd'sinin 1.78 katı, %98 tek yönlü); aynı seçim kalibrasyonu **tutarlı
bir yöne itmiyor** (ortalama kendi sd'sinin yalnız 0.32 katı, işaretler iki yanda). İkisi aynı
grafikte durmalı, çünkü asıl bulgu ikisinin **karşıtlığı**: seçim ölçütü doğruluk olduğu için
iyimserlik doğruluk ekseninde birikiyor, ECE ise kontrolsüz sürükleniyor.

> "sıfır-merkezli" ifadesi ECE paneli için yaklaşıktır ve figürde öyle de yazılmıyor: ortalama
> −0.0029, yani sıfırın tam üstünde değil, kendi sd'sinin üçte biri kadar altında. Panelde
> ölçülen sayı basılıyor, yuvarlanmış bir anlatı değil.

DONMUŞ KÜME KULLANILIR. Kaynak `selection_audit.csv` (N=131, kesme 2026-07-31-06:00) —
donmamış üst küme (`selection_audit_unfrozen.csv`) DEĞİL. Bu bir seçim-iyimserliği figürü ve
makale donmuş sayıyı alıntılıyor; üst kümeyi okumak figürü metinle çelişkiye sokardı.

Salt-okunur, GPU yok.
Çıktı -> paper/figures/selection_distribution.pdf + diagnostics/selection_audit/
         selection_distribution.json
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from export_paper_figures import (MM, W2, BLUE, VERM, BLACK, SMALL,  # noqa: E402
                                  house_style, check_type_sizes, panel)
from reliability_diagram import save_at_width  # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
OUT_PDF = ROOT / "paper" / "figures" / "selection_distribution.pdf"
OUT_DIR = ROOT / "diagnostics" / "selection_audit"
FROZEN_N = 131
REF = "last"   # best − last; @swa karşılaştırması n=118'de tanımlı, dipnotta anılıyor


def load_deltas(ref=REF):
    by = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        by.setdefault((r["run_name"], r["timestamp"]), {})[r["checkpoint"]] = r
    d_acc, d_ece = [], []
    for v in by.values():
        if "best" in v and ref in v:
            d_acc.append(float(v["best"]["acc"]) - float(v[ref]["acc"]))
            d_ece.append(float(v["best"]["ece"]) - float(v[ref]["ece"]))
    return d_acc, d_ece


def describe(x):
    m, sd = st.mean(x), sample_sd(x)
    return {"n": len(x), "mean": m, "sd": sd, "median": st.median(x),
            "min": min(x), "max": max(x),
            "n_positive": sum(1 for v in x if v > 0),
            "mean_over_sd": abs(m) / sd if sd else float("nan")}


def draw(ax, x, s, colour, xlabel, unit, letter):
    """Histogram + koşu-başına tüy (rug) + sıfır ve ortalama çizgileri.

    Rug bilerek var: histogram binlemeye bağlıdır, tüyler değil. İkisi birlikte, 'bu şekil bin
    genişliğinin eseri mi' sorusunu figürün kendi içinde kapatıyor.
    """
    bins = np.histogram_bin_edges(x, bins="fd")
    ax.hist(x, bins=bins, color=colour, alpha=0.30, edgecolor=colour, linewidth=0.7, zorder=2)
    top = ax.get_ylim()[1]

    # ±1 sd bandı, iki kesikli sınırla: gri baskıda dolgu kaybolsa da sınırlar kalır.
    ax.axvspan(s["mean"] - s["sd"], s["mean"] + s["sd"], facecolor=colour, alpha=0.10,
               lw=0, zorder=0)
    for b in (s["mean"] - s["sd"], s["mean"] + s["sd"]):
        ax.axvline(b, color=colour, lw=0.7, ls=(0, (4, 3)), zorder=3)
    # Sıfır ve ortalama farklı ÇİZGİ STİLİ taşıyor, yalnız farklı renk değil.
    ax.axvline(0, color=BLACK, lw=0.9, ls=(0, (1, 3)), zorder=4)
    ax.axvline(s["mean"], color=colour, lw=1.4, ls="-", zorder=5)

    # rug: her koşu bir tüy
    ax.plot(x, np.full(len(x), -top * 0.045), marker="|", ls="none", color=colour,
            markersize=4, markeredgewidth=0.6, alpha=0.65, clip_on=False, zorder=6)
    ax.set_ylim(-top * 0.09, top * 1.02)

    ax.set_xlabel(xlabel)
    ax.set_ylabel("number of runs")
    ax.grid(True, axis="y")
    panel(ax, letter)
    # Açıklama kutusu BOŞ tarafa konur, ve boş taraf veriden bulunur. Sabit bir köşe seçmek
    # (ilk sürüm sol üstü seçiyordu) doğruluk panelinde metni sıfır çizgisinin üstüne bindirdi;
    # veri değiştiğinde hangi köşenin boş olduğu da değişeceği için sabit seçim tekrar bozulur.
    # Doluluk yalnız çubuk yüksekliği DEĞİL: ilk sürüm doğruluk panelinde sol üçte biri "daha boş"
    # bulup (2 vs 3 çubuk) metni oraya koydu, ama orada sıfır çizgisi vardı ve metin onun üstüne
    # bindi. Dikey çizgiler de yer kaplar, o yüzden onlar da doluluğa sayılıyor.
    counts, _ = np.histogram(x, bins=bins)
    third = max(1, len(counts) // 3)
    lo, hi = bins[0], bins[-1]
    busy = [float(counts[:third].max()), float(counts[-third:].max())]
    for line in (0.0, s["mean"]):
        f = (line - lo) / (hi - lo) if hi > lo else 0.5
        if f < 1 / 3:
            busy[0] += 1e3
        elif f > 2 / 3:
            busy[1] += 1e3
    ha, xf = ("left", 0.02) if busy[0] <= busy[1] else ("right", 0.98)
    ax.annotate(f"mean {s['mean']:+{unit}} ± {s['sd']:{unit}}\n"
                f"{s['n_positive']}/{s['n']} runs > 0\n"
                f"|mean| = {s['mean_over_sd']:.2f} × sd",
                xy=(xf, 0.97), xycoords="axes fraction",
                va="top", ha=ha, fontsize=SMALL)


def main():
    house_style()
    check_type_sizes()
    d_acc, d_ece = load_deltas()
    if len(d_acc) != FROZEN_N:
        raise RuntimeError(
            f"donmuş küme {FROZEN_N} koşu tutmalı, {len(d_acc)} eşleşti. Figür makalenin "
            f"alıntıladığı N ile aynı kümeden çizilmezse metinle çelişir; önce "
            f"selection_audit_table.py'yi (kesmesiz) çalıştır.")
    sa, se = describe(d_acc), describe(d_ece)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(W2, 74 * MM))
    draw(axA, d_acc, sa, BLUE, r"$\Delta$ accuracy (best $-$ last), pp", ".3f", "a")
    draw(axB, d_ece, se, VERM, r"$\Delta$ ECE (best $-$ last)", ".4f", "b")
    fig.legend(handles=[
        Line2D([], [], color=BLACK, lw=0.9, ls=(0, (1, 3)), label="zero"),
        Line2D([], [], color=BLACK, lw=1.4, ls="-", label="mean"),
        Line2D([], [], color=BLACK, lw=0.7, ls=(0, (4, 3)), label=r"mean $\pm$ 1 sd"),
        Line2D([], [], color=BLACK, marker="|", ls="none", markersize=4, label="single run")],
        frameon=False, ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.02),
        fontsize=SMALL)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    got = save_at_width(fig, OUT_PDF, 190.0)
    plt.close(fig)

    rec = {"source": str(AUDIT.relative_to(ROOT)).replace("\\", "/"),
           "inclusion_set": f"frozen N={FROZEN_N}", "contrast": f"best - {REF}",
           "sd_convention": SD_CONVENTION,
           "d_acc_pp": sa, "d_ece": se,
           "note": "best-swa is defined on 118 of the 131 runs (13 have no SWA checkpoint) and "
                   "is quoted in T8, not drawn here: a second panel pair on a different n would "
                   "invite reading the two as the same sample."}
    (OUT_DIR / "selection_distribution.json").write_text(json.dumps(rec, indent=2),
                                                        encoding="utf-8")

    print(f"{OUT_PDF.name}  {OUT_PDF.stat().st_size / 1024:.1f} KB   {got:.0f} mm wide")
    for nm, s, u in (("d_acc (pp)", sa, ".3f"), ("d_ece    ", se, ".4f")):
        print(f"  {nm}  ort {s['mean']:+{u}} +/- {s['sd']:{u}}  "
              f"medyan {s['median']:+{u}}  aralik [{s['min']:+{u}}, {s['max']:+{u}}]  "
              f">0: {s['n_positive']}/{s['n']}  |ort|/sd {s['mean_over_sd']:.2f}")
    print(f"Wrote {OUT_DIR / 'selection_distribution.json'}")


if __name__ == "__main__":
    main()
