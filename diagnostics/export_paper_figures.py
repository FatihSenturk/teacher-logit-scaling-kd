"""Export the five paper figures as vector PDFs into paper/figures/.

WHY A SEPARATE EXPORTER. The five producer scripts draw for on-screen review: titles in the
figure, wide layouts, colour carrying meaning. A journal figure wants none of that. Rather than
fork every producer with a --paper flag, this script re-draws from the JSON each producer already
writes, so the numbers cannot diverge from the tables while the styling is free to differ.

THE FOUR HOUSE RULES ENFORCED HERE:
  1. Vector, never raster: savefig(format="pdf", bbox_inches="tight"). No dpi involved.
  2. Colour-blind safe. Deuteranopia (~6% of men) collapses red/green, and the red/blue pairing
     used on screen is also unreliable in greyscale print. So EVERY series carries three
     redundant channels: an Okabe-Ito colour, its own MARKER, and its own LINESTYLE. Any one of
     the three is sufficient to tell the series apart.
  3. Type size. Figures are emitted at their true printed width (190 mm double column, 90 mm
     single) so the PDF is placed 1:1 and nothing is scaled down. With base font 9.5 pt the
     smallest text (tick labels, 8 pt) stays above the 7 pt floor. `check_type_sizes()` asserts
     this instead of trusting it.
  4. No title inside the figure -- titles belong to the LaTeX caption. Panel letters (a)/(b) are
     kept, since captions have to reference them.

Read-only w.r.t. results. Outputs -> paper/figures/*.pdf
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

D = ROOT / "diagnostics"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

MM = 1 / 25.4
W2 = 190 * MM          # double-column full width
CKPT = "swa"
MIN_PT = 7.0
# Every inline `fontsize=` in this file uses one of these two, so the guard below can cover
# annotations too -- scattered literals (7.2, 7.4, 7.6 ...) would be invisible to any check.
# STYLE PASS 2026-08-01: the set moved to 8 pt body / 7 pt secondary, so both constants collapse
# onto the 7 pt floor. They are kept as two names because they mark two different INTENTS
# (annotation vs. crowded legend); if the floor ever moves they must be free to diverge again.
SMALL = 7.0      # in-axes annotations and dense legends
TINY = 7.0       # the single most crowded legend (mechanism colours, 2 columns)

# Okabe-Ito: the standard colour-blind-safe qualitative palette.
BLUE, VERM, GREEN, ORANGE, SKY, PURPLE, BLACK = (
    "#0072B2", "#D55E00", "#009E73", "#E69F00", "#56B4E9", "#CC79A7", "#000000")


def house_style():
    plt.rcParams.update({
        # STYLE PASS 2026-08-01 -- applied to all NINE figures in one go so no figure is
        # handled twice. Serif (STIX/Times) to sit with the journal's body text instead of
        # against it; 8 pt body / 7 pt secondary. STIXGeneral ships WITH matplotlib, so it is
        # listed first: naming Times New Roman alone would silently fall back to DejaVu Sans on
        # any machine without it and the figure set would drift apart across machines.
        "font.family": "serif",
        "font.serif": ["STIXGeneral", "Times New Roman", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 8.0,
        "axes.labelsize": 8.0,
        "axes.titlesize": 8.0,
        "xtick.labelsize": 7.0,
        "ytick.labelsize": 7.0,
        "legend.fontsize": 7.0,
        "figure.titlesize": 8.0,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.4,
        "lines.markersize": 5.0,
        "errorbar.capsize": 2.0,
        "grid.alpha": 0.25,
        "grid.linewidth": 0.5,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
        # Embed TrueType rather than the default Type 3, which many publishers reject
        # outright and which cannot be edited in a prepress tool.
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def check_type_sizes():
    """Fail loudly if any configured size would print below the legibility floor.

    The whole point of emitting at true width is that the PDF is never scaled; this asserts the
    premise rather than assuming it, so a later rcParams edit cannot silently produce 6 pt ticks.
    """
    # Only TYPE sizes -- an earlier version matched every rcParam ending in "size" and tripped on
    # `lines.markersize` and `xtick.major.size`, which are drawing dimensions, not point sizes.
    font_keys = ("font.size", "axes.labelsize", "axes.titlesize", "xtick.labelsize",
                 "ytick.labelsize", "legend.fontsize", "legend.title_fontsize",
                 "figure.titlesize", "figure.labelsize")
    bad = {k: plt.rcParams[k] for k in font_keys
           if isinstance(plt.rcParams.get(k), (int, float)) and plt.rcParams[k] < MIN_PT}
    for name, v in (("SMALL", SMALL), ("TINY", TINY)):
        if v < MIN_PT:
            bad[name] = v
    if bad:
        raise RuntimeError(f"type below {MIN_PT} pt at printed size: {bad}")


def panel(ax, letter):
    ax.text(-0.14, 1.03, f"({letter})", transform=ax.transAxes,
            fontsize=10, fontweight="bold", va="bottom", ha="left")


def save_at_width(fig, path, target_mm, tol=1.0, max_iter=5):
    """PDF'i DİSKTE target_mm genişliğinde olacak şekilde kaydet, çizildiği tuval değil.

    `bbox_inches="tight"` boşluğu kırptığı için diske düşen sayfa her zaman figsize'dan dar
    oluyordu: 190 mm'lik tuvaller 185-187 mm, 90 mm'lik tek-sütun figür 82 mm olarak indi.
    LaTeX bunları `\\textwidth`/`\\columnwidth`e oturtunca her figür FARKLI bir oranda büyür
    (%2, %3, %10) ve sabitlediğimiz 8 pt / 7 pt basılı boyutta figürden figüre kayar --
    stil geçişinin ölçülebilir tek çıktısı tam olarak budur, o yüzden nominalde bırakılamaz.

    Her iki boyutu AYNI çarpanla ölçeklemek bunu güvenli kılıyor: yerleşimin tamamı göreli
    eksen koordinatlarında, dolayısıyla düzgün bir tuval yakınlaştırması hiçbir öğeyi yerinden
    oynatmaz, yalnız sabit-punto metnin kapladığı oransal yeri değiştirir.
    """
    import fitz
    w, h = fig.get_size_inches()
    got = None
    for _ in range(max_iter):
        # CreationDate SABİTLENİYOR (13 Ağu 2026). Matplotlib PDF'e koşu anının saatini gömüyordu,
        # dolayısıyla AYNI veriden üretilen figür her koşuda farklı BAYT veriyordu: ihraç adımı
        # her seferinde "makale fig: 5 yenilendi" diyordu (hep aynı beş dosya) ve bu satır
        # gerçek bir içerik değişikliğini gösteremez hâle gelmişti -- 7 Ağu'da tam bu beş PDF bu
        # yüzden yanlışlıkla "değişti" görünmüştü (`public_repo_staleness.py` başlığında kayıtlı).
        # Gürültüyü bastırmak yerine KAYNAĞINI kesmek doğrusu: sabit damgayla PDF'ler bayt
        # yeniden-üretilebilir olur ve "yenilendi" satırı yeniden anlam taşır. Çizim
        # DEĞİŞMİYOR -- yalnız dosya üstverisi.
        fig.savefig(path, format="pdf", bbox_inches="tight",
                    metadata={"CreationDate": None})
        doc = fitz.open(path)
        got = doc[0].rect.width / 72 * 25.4
        doc.close()
        if abs(got - target_mm) <= tol:
            return got
        k = target_mm / got
        w, h = w * k, h * k
        fig.set_size_inches(w, h)
    return got


def finish(fig, name, target_mm=190.0):
    p = OUT / name
    got = save_at_width(fig, p, target_mm)
    plt.close(fig)
    kb = p.stat().st_size / 1024
    print(f"  {name:<32} {kb:7.1f} KB   {got:.0f} mm on disk (hedef {target_mm:.0f})")
    return p


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- 1
def fig_two_teacher_overlay():
    # Round-5 C2 (27 Ağu 2026): y ekseni artık by_ckpt[CKPT] -- makalenin birincil
    # checkpoint beyanı (SWA, §5.4) ile aynı ve Tablo 1/2'nin @swa sütunuyla aynı
    # kaynaktan (donmuş seçim denetimi). Düz student_ece_mean best_checkpoint
    # önbelleğiydi ve seçim iyimserliği taşıyordu; SESSİZ geri dönüş yok -- by_ckpt
    # eksikse figür üretimi dursun, eski alana düşmesin.
    d = jload(D / "p1_dose_response" / "two_teacher_overlay.json")
    style = {"stage1": (BLUE, "o", "-", "Stage1 teacher"),
             "vae9182": (VERM, "s", "--", "VAE9182 teacher")}
    fig, ax = plt.subplots(figsize=(90 * MM, 68 * MM))
    for k, pts in d["curves"].items():
        c, m, ls, lab = style[k]
        missing = [p["T"] for p in pts if CKPT not in p.get("by_ckpt", {})]
        if missing:
            raise RuntimeError(
                f"two_teacher_overlay.json: {k} T={missing} has no by_ckpt[{CKPT!r}] -- "
                f"rerun diagnostics/p1_two_teacher_overlay.py; refusing the stale flat field.")
        pts = sorted(pts, key=lambda p: p["teacher_ece"])
        ax.errorbar([p["teacher_ece"] for p in pts],
                    [p["by_ckpt"][CKPT]["ece_mean"] for p in pts],
                    yerr=[p["by_ckpt"][CKPT]["ece_sd"] for p in pts],
                    color=c, marker=m, linestyle=ls, label=lab, ecolor=c, elinewidth=0.8)
    ax.set_xlabel("Teacher ECE (15-bin)")
    ax.set_ylabel("Student ECE (15-bin)")
    ax.grid(True)
    ax.legend(frameon=False)
    # Tek sütun: bu figürün hedefi 90 mm, ötekilerin 190.
    return finish(fig, "two_teacher_overlay.pdf", target_mm=90.0)


# --------------------------------------------------------------------------- 2
def fig_two_dataset_overlay():
    """(a) signed miscalibration axis, (b) the same data folded onto |sMG|.

    Panel (b) is not decoration: ECE is sign-blind, so on the signed axis the two directions are
    separate branches, and folding shows that the magnitude relation is monotone while the signed
    one is not. Both panels must therefore share the y scale -- otherwise the folding looks like
    it changed the data rather than the axis.
    """
    d = jload(D / "p1_dose_response" / "two_dataset_overlay.json")
    style = {
        "rafdb_stage1": (BLUE, "o", "-", "RAF-DB / Stage1"),
        "rafdb_vae9182": (VERM, "s", "--", "RAF-DB / VAE9182"),
        "ferplus": (GREEN, "^", ":", "FERPlus"),
    }
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(W2, 78 * MM), sharey=True)
    for key, arm in d["arms"].items():
        c, m, ls, lab = style[key]
        pts = [p for p in arm["points"] if CKPT in p.get("by_ckpt", {})]
        ece = lambda p: p["by_ckpt"][CKPT]["ece_mean"]
        sd = lambda p: p["by_ckpt"][CKPT]["ece_sd"]

        q = sorted(pts, key=lambda p: p["signed_gap"])
        axA.errorbar([p["signed_gap"] for p in q], [ece(p) for p in q], yerr=[sd(p) for p in q],
                     color=c, marker=m, linestyle=ls, label=lab, ecolor=c, elinewidth=0.8)

        # Panel (b): connect WITHIN each direction, never across. Folding puts an over-confident
        # and an under-confident teacher at the same x, but they do not lie on one curve -- the
        # campaign's own result is that over-confidence costs ~1.91x more at equal |sMG|. A single
        # polyline through the folded points would draw a zigzag and imply one shared relation,
        # i.e. it would contradict the finding the panel exists to show. Two branches per arm make
        # each one monotone and put the asymmetry on display as the gap between them.
        for branch, fill in (("over", c), ("under", "none")):
            sub = [p for p in pts if (p["signed_gap"] > 0) == (branch == "over")]
            if not sub:
                continue
            sub.sort(key=lambda p: abs(p["signed_gap"]))
            axB.errorbar([abs(p["signed_gap"]) for p in sub], [ece(p) for p in sub],
                         yerr=[sd(p) for p in sub], color=c, marker=m, linestyle=ls,
                         markerfacecolor=fill, markeredgecolor=c, ecolor=c, elinewidth=0.8)
    axA.axvline(0, color=BLACK, lw=0.8, ls=(0, (1, 3)))
    # Direction labels live in the xlabel, not as in-axes text: placed inside the axes they
    # collided with whichever curve happened to run through that corner, and which curve that is
    # changes whenever the data does.
    axA.set_xlabel("Signed teacher miscalibration (mean confidence $-$ accuracy)\n"
                   r"$\longleftarrow$ under-confident            "
                   r"over-confident $\longrightarrow$")
    axA.set_ylabel("Student ECE @SWA (15-bin)")
    axB.set_xlabel("Folded magnitude  $|$sMG$|$")
    for ax, L in ((axA, "a"), (axB, "b")):
        ax.grid(True)
        panel(ax, L)
    axA.legend(frameon=False, loc="upper center", fontsize=SMALL)
    axB.legend(handles=[
        Line2D([], [], color=BLACK, marker="o", markerfacecolor=BLACK, linestyle="none",
               markersize=5, label="over-confident branch (filled)"),
        Line2D([], [], color=BLACK, marker="o", markerfacecolor="none", linestyle="none",
               markersize=5, label="under-confident branch (open)")],
        frameon=False, loc="upper left", fontsize=SMALL)
    fig.tight_layout()
    return finish(fig, "two_dataset_overlay_swa.pdf")


# --------------------------------------------------------------------------- 3
def fig_mechanism_diagnostic():
    d = jload(D / "paper_tables" / "mechanism_diagnostic.json")
    pts = d["points"]
    hi = [p for p in pts if p["mechanism"] == "logit_std"]
    rest = [p for p in pts if p["mechanism"] != "logit_std"]
    tmark = {"stage1": "o", "primary": "s", "vae9182": "^"}
    mechs = sorted({p["mechanism"] for p in rest})
    pal = [BLUE, ORANGE, GREEN, SKY, PURPLE, BLACK, "#8C6D31"]
    mcol = {m: pal[i % len(pal)] for i, m in enumerate(mechs)}

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(W2, 78 * MM))

    def draw(ax, subset, colour_by_mech):
        ax.axhline(0, color=BLACK, lw=0.7, ls=(0, (1, 3)))
        ax.axvline(0, color=BLACK, lw=0.7, ls=(0, (1, 3)))
        for p in subset:
            hot = p["mechanism"] == "logit_std"
            ax.errorbar(p["d_acc"], p["d_ece"],
                        xerr=(p["d_acc_sd"] if p["n"] > 1 else None),
                        yerr=(p["d_ece_sd"] if p["n"] > 1 else None),
                        marker=tmark.get(p["teacher"], "D"), linestyle="none",
                        markersize=6.5 if hot else 5,
                        markerfacecolor=(VERM if hot else
                                         (mcol[p["mechanism"]] if colour_by_mech else BLUE)),
                        markeredgecolor=BLACK, markeredgewidth=0.5,
                        # Hata çubuğu KOLUN RENGİNDE (stil geçişi 2026-08-01). Gri "#999" her
                        # noktaya aynı çubuğu veriyordu; kalabalık panelde hangi çubuğun hangi
                        # noktaya ait olduğu ancak yakınlıkla tahmin ediliyordu.
                        ecolor=(VERM if hot else
                                (mcol[p["mechanism"]] if colour_by_mech else BLUE)),
                        elinewidth=0.7)
        ax.set_xlabel(r"$\Delta$ accuracy @SWA (pp)")
        ax.grid(True)

    draw(axA, pts, colour_by_mech=False)
    axA.set_ylabel(r"$\Delta$ ECE @SWA")
    # Üç logit_std noktası da etiketleniyor, ama sabit tek bir kaydırmayla DEĞİL: stage1 (0.0906)
    # ve primary (0.0859) birbirine yeterince yakın ki aynı kaydırmada iki etiket üst üste biniyor
    # (7 pt'ye inildikten sonra daha da beter). Sıraya göre kademelendiriliyor.
    for rank, p in enumerate(sorted(hi, key=lambda q: -q["d_ece"])):
        axA.annotate("logit_std", (p["d_acc"], p["d_ece"]), textcoords="offset points",
                     xytext=(7, [-1, 5, -8][rank % 3]), fontsize=SMALL, color=VERM)
    panel(axA, "a")
    # Lejant sol ÜSTTEN çıkarıldı: en yüksek logit_std noktasının (vae9182, ΔECE 0.1388) yatay
    # hata çubuğu tam oradan geçiyor ve "Teacher" başlığının içinden kesiyordu. Sağ orta, bu
    # panelin tek gerçekten boş bölgesi -- veri sol tarafta ve sıfır bandında toplanıyor.
    axA.legend(handles=[Line2D([], [], ls="none", marker=m, markerfacecolor="none",
                               markeredgecolor=BLACK, markersize=5.5, label=t)
                        for t, m in tmark.items()],
               frameon=False, loc="center right", title="Teacher", title_fontsize=7)

    draw(axB, rest, colour_by_mech=True)
    # Short label: the long "(note the x24 finer scale)" version was taller than the axis and got
    # clipped by bbox_inches="tight". The scale difference belongs in the caption anyway.
    axB.set_ylabel(r"$\Delta$ ECE @SWA")
    panel(axB, "b")
    # OPAK BEYAZ ZEMİN (13 Ağu 2026). `frameon=False` iken uzun yatay hata çubukları lejant
    # yazısının içinden geçiyordu; eksen kırpması düzelince pencere büyüdüğü için çubuklar daha
    # da içeri giriyor. Çerçeve çizgisi yok (`edgecolor="none"`) -- istenen zemin, kutu değil.
    axB.legend(handles=[Line2D([], [], ls="none", marker="o", markerfacecolor=mcol[m],
                               markeredgecolor=BLACK, markersize=5, label=m) for m in mechs],
               frameon=True, facecolor="white", edgecolor="none", framealpha=1.0,
               loc="upper center", ncol=2, fontsize=TINY).set_zorder(6)
    # SINIRLAR ORTALAMALARDAN DEĞİL, HATA ÇUBUĞUNUN UÇLARINDAN (13 Ağu 2026).
    #
    # Eski hâl `min(d_ece)`/`max(d_ece)` kullanıyordu, yani pencereyi NOKTALARA göre kuruyordu;
    # çubuklar hesaba girmediği için iki tanesi alt sınırın altında kalıyor ve KIRPILIYORDU:
    # primary × gate:mean_logvar (−0.00558 ± 0.00923 → alt uç −0.01480) ve vae9182 × adaptive_t
    # (−0.00420 ± 0.00469 → −0.00889), eski alt sınır −0.00729'a karşı. Kırpılan çubuk okura
    # belirsizliği OLDUĞUNDAN KÜÇÜK gösterir -- bu panelin varlık sebebi tam da belirsizliği
    # göstermek olduğu için sessiz ama ciddi bir hata. n=1 noktalarının çubuğu yok, sd'leri
    # sıfır sayılır. Üst pay (0.45) lejant içindir; alt pay (0.06) yalnız nefes payı.
    def _ext(key, sd_key):
        lo = min(p[key] - ((p[sd_key] or 0.0) if p["n"] > 1 else 0.0) for p in rest)
        hi = max(p[key] + ((p[sd_key] or 0.0) if p["n"] > 1 else 0.0) for p in rest)
        return lo, hi
    y_lo, y_hi = _ext("d_ece", "d_ece_sd")
    y_span = y_hi - y_lo
    axB.set_ylim(y_lo - 0.06 * y_span, y_hi + 0.45 * y_span)
    fig.tight_layout()
    return finish(fig, "mechanism_diagnostic.pdf")


# --------------------------------------------------------------------------- 4
def fig_ferplus_dual_axis():
    d = jload(D / "ferplus_jsd" / "ferplus_dual_axis.json")
    arms = sorted(d["arms"], key=lambda a: a["T"])
    x = [a["T"] for a in arms]
    ece = [a["student_ece"] for a in arms]
    jsd = [a["student_jsd"] for a in arms]

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(W2, 78 * MM))

    axA.errorbar(x, ece, yerr=[a["student_ece_sd"] for a in arms], color=BLUE, marker="o",
                 linestyle="-", ecolor=BLUE, elinewidth=0.8, label="Student ECE (hard label)")
    axA.set_xscale("log")
    axA.set_xticks(x)
    axA.set_xticklabels([f"{t:g}" for t in x])
    axA.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    axA.set_xlabel("Teacher pre-scaling temperature $T$")
    axA.set_ylabel("Student ECE (15-bin)")
    ax2 = axA.twinx()
    ax2.errorbar(x, jsd, yerr=[a["student_jsd_sd"] for a in arms], color=VERM, marker="s",
                 linestyle="--", ecolor=VERM, elinewidth=0.8, label="Student JSD (human votes)")
    ax2.set_ylabel("Student JSD (nats)")
    h1, l1 = axA.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    axA.legend(h1 + h2, l1 + l2, frameon=False, loc="upper center", fontsize=SMALL)
    axA.grid(True)
    panel(axA, "a")
    for i, key, col in ((ece.index(min(ece)), "ece", BLUE), (jsd.index(min(jsd)), "jsd", VERM)):
        a = axA if key == "ece" else ax2
        a.scatter([x[i]], [min(ece) if key == "ece" else min(jsd)], s=110, facecolors="none",
                  edgecolors=col, linewidths=1.4, zorder=5)

    axB.errorbar(ece, jsd, xerr=[a["student_ece_sd"] for a in arms],
                 yerr=[a["student_jsd_sd"] for a in arms], color=BLACK, marker="D",
                 linestyle="none", ecolor=BLACK, elinewidth=0.7)
    for a in arms:
        # T=1 tek başına yukarı alınır: (6,-3) kaydırmasında etiket kendi elmasının ve yatay
        # hata çubuğunun üstüne biniyordu (panelin en sağ noktası, çubuk sağa doğru uzun).
        off = (2, 7) if a["T"] == 1 else (6, -3)
        axB.annotate(f"$T$={a['T']:g}", (a["student_ece"], a["student_jsd"]),
                     textcoords="offset points", xytext=off, fontsize=SMALL)
    ie, ij = ece.index(min(ece)), jsd.index(min(jsd))
    axB.scatter([ece[ie]], [jsd[ie]], s=110, facecolors="none", edgecolors=BLUE, linewidths=1.4)
    axB.scatter([ece[ij]], [jsd[ij]], s=110, facecolors="none", edgecolors=VERM, linewidths=1.4)
    axB.annotate("", xy=(ece[ij], jsd[ij]), xytext=(ece[ie], jsd[ie]),
                 arrowprops=dict(arrowstyle="->", color=PURPLE, lw=1.2))
    # Short labels: the long forms were taller than the axes and bbox_inches="tight" clipped
    # their trailing text. Units and direction go in the caption.
    axB.set_xlabel(r"Student ECE  ($\leftarrow$ better)")
    axB.set_ylabel(r"Student JSD  ($\downarrow$ better)")
    axB.grid(True)
    panel(axB, "b")
    xr = max(ece) - min(ece)
    axB.set_xlim(min(ece) - 0.12 * xr, max(ece) + 0.28 * xr)
    fig.tight_layout()
    return finish(fig, "ferplus_dual_axis.pdf")


# --------------------------------------------------------------------------- 5
def fig_p5_frontier():
    d = jload(D / "p5_efficiency" / "p5_frontier.json")
    wc = d["width_curve"]
    pre = d["pretrained_same_width"]
    xs = [w["params_m"] for w in wc]

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(W2, 78 * MM))
    for ax, key, sd, ylab, L in (
            (axA, "acc_mean", "acc_sd", "RAF-DB accuracy @SWA (%)", "a"),
            (axB, "ece_mean", "ece_sd", "Student ECE @SWA (15-bin)", "b")):
        ax.errorbar(xs, [w[key] for w in wc], yerr=[w[sd] for w in wc], color=BLUE,
                    marker="o", linestyle="-", ecolor=BLUE, elinewidth=0.8,
                    label="scratch init (width sweep)")
        ax.errorbar([pre["params_m"]], [pre[key]], yerr=[pre[sd]], color=VERM, marker="D",
                    linestyle="none", markersize=6.5, ecolor=VERM, elinewidth=0.8,
                    label="ImageNet pre-trained (same width)")
        ax.set_xscale("log")
        ax.set_xticks(xs)
        ax.set_xticklabels([f"{w['width']}\n{w['params_m']:.2f} M" for w in wc])
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlim(xs[0] * 0.82, xs[-1] * 1.25)
        ax.set_xlabel("Student width multiplier / parameters")
        ax.set_ylabel(ylab)
        ax.grid(True)
        panel(ax, L)
    # The teacher-temperature band is what makes panel (b) an argument rather than a flat line.
    # Light fill bounded by two dashed rules, NOT hatching: at this size "///" filled the entire
    # panel and competed with the data it was supposed to frame, while the dashed boundaries
    # survive greyscale printing on their own.
    span = d["contrasts"]["teacher_temperature_ece_span"]
    lo = min(w["ece_mean"] for w in wc) - 0.15 * span
    axB.axhspan(lo, lo + span, facecolor=VERM, alpha=0.10, lw=0, zorder=0,
                label="teacher-temperature axis span")
    for y in (lo, lo + span):
        axB.axhline(y, color=VERM, lw=0.7, ls=(0, (4, 3)), zorder=1)
    # Legends off the data: in panel (a) the in-axes legend put its sample markers exactly where
    # real points sit, so the swatches read as two extra measurements.
    axA.legend(frameon=False, loc="upper left", fontsize=SMALL)
    axB.legend(frameon=False, loc="upper left", fontsize=SMALL)
    fig.tight_layout()
    return finish(fig, "p5_frontier.pdf")


def main():
    house_style()
    check_type_sizes()
    print(f"Exporting vector PDFs -> {OUT}")
    made = [fig_two_teacher_overlay(), fig_two_dataset_overlay(), fig_mechanism_diagnostic(),
            fig_ferplus_dual_axis(), fig_p5_frontier()]
    print(f"\n{len(made)} PDFs written.")
    smallest = min([TINY, SMALL, plt.rcParams["xtick.labelsize"],
                    plt.rcParams["ytick.labelsize"], plt.rcParams["legend.fontsize"],
                    plt.rcParams["axes.labelsize"], plt.rcParams["font.size"]])
    print("Checks: vector (no raster), no in-figure titles, "
          "every series has colour + marker + linestyle, "
          f"smallest type {smallest:.1f} pt at true printed width (floor {MIN_PT} pt).")

    # Figürler yeniden çizildiği anda makale tarafındaki kopya bayatlar. İhracı buraya
    # bağlamak o pencereyi kapatıyor. (`_updated_*` klasörünün Drive'a hiç ulaşmamış olması
    # tam olarak bu kancanın yokluğundandı.)
    # Genel depoda bant altyapisi bulunmaz; yoklugu figur uretimini durdurmamali.
    try:
        import export_to_drive
        export_to_drive.hook("export_paper_figures.py")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
