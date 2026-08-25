"""Grafik özet (graphical abstract) — Elsevier şartnamesine: 5×13 cm'de okunur, tek şerit.

TASARIM KARARLARI
  - Tuval TAM 130×50 mm (13×5 cm): Elsevier özeti bu boyutta gösterir, biz de o boyutta
    çizeriz ki "küçültülünce okunur mu" sorusu hiç doğmasın. PNG 300 dpi'da 1535×591 px →
    şartnamenin 531×1328 px tabanının üstünde.
  - Üç blok: başlık şeridi (iddianın tek cümlesi), solda müdahalenin anatomisi (öğretmen
    logitleri → ÷T → softmax → öğrenci hedefi; neyin sabit neyin tedavi olduğu iki satırda),
    sağda kanıtın kendisi (iki-veri-kümesi doz-yanıt mini eğrisi, her kolun minimumu halkalı).
  - Sağ panel `two_dataset_overlay.json`dan okunur — makaledeki taç figürle AYNI artefakt,
    yani özet ile figür sayı kaynağını paylaşır ve ayrışamaz. Hata çubuğu yok: bu bir özet,
    ölçüm raporu değil; çubuklar 5 cm'de okunmaz ve tam figür makalede.
  - Ev stili (serif, Okabe-Ito, işaretçi+çizgi stili fazlalığı) aynen; GA figür kapısından
    da geçer (başlık şeridi kapının "en üstte metin" NOTUNU tetikler — GA'da başlık bilinçli
    olarak figürün İÇİNDEDİR, kapı hatası değildir).

Çıktı -> paper/figures/graphical_abstract.pdf (vektör) + .png (300 dpi)
Salt-okunur, GPU yok.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from export_paper_figures import (MM, BLUE, VERM, GREEN, BLACK, house_style)  # noqa: E402

A_OVERLAY = ROOT / "diagnostics" / "p1_dose_response" / "two_dataset_overlay.json"
OUT_PDF = ROOT / "paper" / "figures" / "graphical_abstract.pdf"
OUT_PNG = ROOT / "paper" / "figures" / "graphical_abstract.png"

W, H = 130 * MM, 50 * MM
# Tek cümle, iki satırda: 8 pt'de tek satır 130 mm'ye sığmıyor (ilk denemede tight-bbox tuvali
# 149 mm'ye genişletip 130x50'yi bozdu — GA'da tuval sabittir, metin tuvale uyar, tersi değil).
# Başlık v2 ile hizalandı (7 Ağu 2026). Eski özne "Teacher calibration" idi; müdahale edilen
# şey T (logit ölçekleme), kalibrasyon onun HAREKET ETTİRDİĞİ özellik. İki inceleme turunun
# başlığa itirazının özü buydu ve grafik özet gönderim paketine girdiği için tutarsızlık
# hakemin ilk sayfada göreceği türdendi.
HEADLINE_1 = "Teacher-side logit scaling governs student calibration"
# 7 Ağu 2026, Fatih'in kararı. Eski hâli "— causal evidence via prediction-preserving logit
# rescaling —" idi ve iki sorunu vardı: (a) HEADLINE_1 v2'ye geçince "logit scaling … logit
# rescaling" diye tekrarlıyordu, (b) daha önemlisi, başlıktan "Causal Evidence" ifadesi dış
# inceleme sonrası BİLEREK çıkarılmıştı (nedensel öznenin müdahaleyle uyumsuzluğu); grafik özet
# gönderim paketinin en görünür parçası olduğu için orada geri çekilen ifadeyi yeniden kurmak,
# başlık-figür tutarsızlığının ikinci bir hâli olurdu.
# Yeni hâli nedenselliği İDDİA etmek yerine onu sağlayan TASARIM ÖZELLİĞİNİ söylüyor (sabit
# öğretmen doğruluğu, çift yön) -- yani daha zayıf değil, daha savunulabilir.
HEADLINE_2 = "— dose–response at fixed teacher accuracy, in both directions —"


def box(ax, x, y, w, h, text, edge=BLACK, lw=0.9, fs=7.0, fc="white", tc=BLACK, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                fc=fc, ec=edge, lw=lw, mutation_aspect=1.0))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=tc,
            fontweight="bold" if bold else "normal")


def arrow(ax, x0, x1, y, color=BLACK):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=7,
                                 lw=0.9, color=color, shrinkA=0, shrinkB=0))


def left_pane(ax):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    yb, hb = 0.58, 0.30
    box(ax, 0.00, yb, 0.20, hb, "teacher\nlogits $\\mathbf{z}$")
    arrow(ax, 0.21, 0.27, yb + hb / 2)
    # Müdahalenin kendisi: tek vurgulu kutu.
    box(ax, 0.28, yb, 0.13, hb, "$\\div\\,T$", edge=VERM, lw=1.5, tc=VERM, bold=True)
    arrow(ax, 0.42, 0.48, yb + hb / 2, color=VERM)
    box(ax, 0.49, yb, 0.20, hb, "softmax\n$(\\mathbf{z}/T\\tau)$")
    arrow(ax, 0.70, 0.76, yb + hb / 2)
    box(ax, 0.77, yb, 0.23, hb, "student's\nsoft target")
    ax.text(0.345, yb + hb + 0.13, "post-hoc, fixed before\nstudent training",
            ha="center", va="center", fontsize=7.0, color=VERM, style="italic")
    # Sabit olan / tedavi olan — iddianın deneysel omurgası iki satırda.
    ax.text(0.0, 0.30, "teacher predictions & accuracy:", fontsize=7.0, ha="left", va="center")
    ax.text(1.0, 0.30, "UNCHANGED", fontsize=7.0, ha="right", va="center",
            fontweight="bold")
    ax.text(0.0, 0.13, "teacher calibration:", fontsize=7.0, ha="left", va="center")
    ax.text(1.0, 0.13, "the treatment variable", fontsize=7.0, ha="right", va="center",
            color=VERM, fontweight="bold")


def right_pane(ax):
    d = json.loads(A_OVERLAY.read_text(encoding="utf-8"))
    # Lejant patoloji etiketleri taşır, anonim "teacher A/B" değil (R0 sonrası düzeltme):
    # özet 5 cm'de tek başına okunacak, ve hikâye tam olarak öğretmenlerin patolojisi.
    style = {"rafdb_stage1": (BLUE, "o", "-", "over-confident teacher"),
             "rafdb_vae9182": (VERM, "s", "--", "well-calibrated teacher"),
             "ferplus": (GREEN, "^", ":", "under-confident (FERPlus)")}
    for key, (c, m, ls, lab) in style.items():
        pts = [p for p in d["arms"][key]["points"] if "swa" in p.get("by_ckpt", {})]
        pts.sort(key=lambda p: p["signed_gap"])
        xs = [p["signed_gap"] for p in pts]
        ys = [p["by_ckpt"]["swa"]["ece_mean"] for p in pts]
        ax.plot(xs, ys, color=c, marker=m, linestyle=ls, lw=1.1, markersize=3.4, label=lab)
        i = ys.index(min(ys))   # her kolun minimumu = kalibre edilmiş öğretmen (T*) noktası
        ax.scatter([xs[i]], [ys[i]], s=64, facecolors="none", edgecolors=c, linewidths=1.1,
                   zorder=5)
    ax.axvline(0, color=BLACK, lw=0.6, ls=(0, (1, 3)))
    ax.set_xlabel("teacher miscalibration (signed)", fontsize=7.0, labelpad=1.5)
    ax.set_ylabel("student ECE", fontsize=7.0, labelpad=1.5)
    ax.tick_params(labelsize=7.0, pad=1.5, length=2)
    ax.grid(True, alpha=0.2, lw=0.4)
    ax.legend(frameon=False, fontsize=7.0, loc="upper left", borderaxespad=0.1,
              handlelength=1.6, labelspacing=0.25)
    # Ok panelin İÇİNDE kalır: ilk yerleşim (xytext x=0.09) eksen sınırının dışındaydı ve ok
    # tuvalden dışarı fırlıyordu. Sol-alt, üç eğrinin de altındaki tek boş bölge.
    # Yıldız mathtext DIŞINDA: $T^*$ üst-simgeyi ~0.7x küçültüp 4.9 pt'ye düşürüyordu ve figür
    # kapısı (>= 7 pt) haklı olarak reddetti. "$T$*" yıldızı satır boyunda tutar.
    ax.annotate("$T$* (calibrated)", xy=(-0.012, 0.0185), xytext=(-0.26, 0.006),
                fontsize=7.0, color=BLACK, va="bottom",
                arrowprops=dict(arrowstyle="->", lw=0.7, color=BLACK,
                                shrinkA=2, shrinkB=6))


def main():
    house_style()
    # Ev stili savefig.bbox="tight" der; GA'da bu tuvali metne göre büyütür ve 130x50'yi bozar.
    # Burada tuval sözleşmedir: sabit kalır, taşan metin hata sayılır.
    plt.rcParams["savefig.bbox"] = "standard"
    fig = plt.figure(figsize=(W, H))
    fig.text(0.5, 0.975, HEADLINE_1, ha="center", va="top", fontsize=8.5, fontweight="bold")
    fig.text(0.5, 0.875, HEADLINE_2, ha="center", va="top", fontsize=7.5, style="italic")

    axL = fig.add_axes((0.015, 0.05, 0.46, 0.60))
    left_pane(axL)
    axR = fig.add_axes((0.585, 0.20, 0.40, 0.52))
    right_pane(axR)

    # CreationDate SABITLENIYOR (20 Agu 2026, N19b). Bu dosya `save_at_width` yolunu
    # KULLANMIYOR (GA'nin tuvali sabit 130x50 mm, otomatik genislik ayari onu bozar), o yuzden
    # 13 Agu'da butun figurlere uygulanan damga bastirmasi buraya ULASMAMISTI: her kosuda PDF
    # sadece `/CreationDate` yuzunden 4 bayt degisiyor ve calisma agacini kirletiyordu. Bugun
    # olculdu -- Level-1 kapisi butun ureticileri kosturdugu icin kapiyi her calistirisimizda
    # bu dosya "degismis" gorunuyordu. Cizim DEGISMIYOR, yalniz dosya ustverisi.
    fig.savefig(OUT_PDF, format="pdf", metadata={"CreationDate": None})
    fig.savefig(OUT_PNG, format="png", dpi=300)
    plt.close(fig)
    import fitz
    doc = fitz.open(OUT_PDF)
    w_mm = doc[0].rect.width / 72 * 25.4
    h_mm = doc[0].rect.height / 72 * 25.4
    doc.close()
    from PIL import Image
    px = Image.open(OUT_PNG).size
    print(f"{OUT_PDF.name}: {w_mm:.0f}x{h_mm:.0f} mm (hedef 130x50)")
    print(f"{OUT_PNG.name}: {px[0]}x{px[1]} px @300dpi (taban 1328x531) "
          f"{'OK' if px[0] >= 1328 and px[1] >= 531 else 'YETERSIZ'}")


if __name__ == "__main__":
    main()
