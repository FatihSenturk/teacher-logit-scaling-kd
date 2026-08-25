"""Figure (d): FERPlus, the two incompatible definitions of "well calibrated".

WHAT IT ARGUES. FERPlus ships 10 human votes per image, so the same student can be scored two
ways: against the ARGMAX label (hard-label ECE) and against the human VOTE DISTRIBUTION (JSD).
These are different targets, and the teacher temperature that minimises one does not minimise the
other -- T*_ECE = 0.5063, T*_JSD = 0.74. Scoring a distillation method on hard-label ECE alone
therefore silently picks the teacher that is worst at reproducing human uncertainty, which is the
thing the 10-rater annotation was collected to measure.

WHY BOTH PANELS. Panel A shows the two curves crossing (the argmins are genuinely different, not
a rounding artefact). Panel B is the honest version of the same fact: no arm reaches the bottom-left
corner, so the choice is a trade-off, not an optimisation.

Rho against human entropy is deliberately NOT the axis here: it varies by only ~0.04 across arms
whose JSD varies by 0.02 at a seed-noise of 0.0005, i.e. rho cannot discriminate between them
(quantified in T7). Rank agreement is preserved by any monotone rescaling; the distribution match
is not.

All numbers read from artifacts. Read-only, zero GPU.
Outputs -> diagnostics/ferplus_jsd/ferplus_dual_axis.{png,json}
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION  # noqa: E402

JSD_DIR = ROOT / "diagnostics" / "ferplus_jsd"
STUDENT = JSD_DIR / "ferplus_student_jsd.json"
TEACHER = JSD_DIR / "ferplus_teacher_signed_grid.json"
CKPT = "swa"

ROLE = {"0.26": "over-sharpened", "0.5063": "T*_ECE / T*_NLL",
        "0.74": "T*_JSD", "1.0": "native"}

ECE_C, JSD_C = "#2471a3", "#c0392b"


def tlabel(t):
    """T'nin GÖRÜNEN etiketi: iki ondalık, sondaki sıfırlar atılır.

    Sebep: 0.5063 dört haneli bir fit çıktısı ve figürde okunmuyor -- eksende, iki
    açıklamada ve B panelinde aynı anda görünüp her seferinde göz yoruyor. Etikette 0.51
    yeterli; TAM DEĞER hiçbir yerde kaybolmuyor: JSON'a olduğu gibi yazılıyor, tablolarda
    (T14/T15) dört hane duruyor ve figür başlığı zaten metne bağlı. Yalnız çizim değişiyor.
    """
    return f"{float(t):.2f}".rstrip("0").rstrip(".")


def main():
    sj = json.loads(STUDENT.read_text())
    by = sj["by_checkpoint"][CKPT]
    ts = sorted((k for k in by if not k.startswith("_")), key=float)
    x = [float(t) for t in ts]
    ece = [by[t]["ece"][0] for t in ts]
    ece_sd = [by[t]["ece"][1] for t in ts]
    jsd = [by[t]["jsd"][0] for t in ts]
    jsd_sd = [by[t]["jsd"][1] for t in ts]
    n = by[ts[0]]["n"]

    i_ece, i_jsd = ece.index(min(ece)), jsd.index(min(jsd))
    if i_ece == i_jsd:
        # If one arm ever wins both, the figure's whole premise is gone -- say so rather than
        # drawing a "trade-off" that the data no longer supports.
        raise RuntimeError(f"argmin ECE and argmin JSD coincide at T={ts[i_ece]}; "
                           "there is no trade-off to plot -- revisit the claim, not the figure")

    hm = sj.get("human_mean_entropy")

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.0, 5.2))

    # ---- Panel A: the two curves, twin y
    axA.errorbar(x, ece, yerr=ece_sd, color=ECE_C, marker="o", capsize=3, lw=1.9,
                 label="öğrenci ECE (sert etikete karşı)")
    axA.set_xscale("log")
    axA.set_xticks(x)
    axA.set_xticklabels([f"{tlabel(t)}\n{ROLE.get(s, '')}" for t, s in zip(x, ts)], fontsize=8.5)
    axA.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    # En soldaki etiketin ikinci satırı ("over-sharpened") tick'ten geniş: ortalanınca
    # eksenin soluna taşıp y ekseni başlığının üstüne biniyordu. Uçtaki iki etiketi içeri
    # yasla, ortadakiler ortalı kalsın.
    ticklabels = axA.get_xticklabels()
    ticklabels[0].set_ha("left")
    ticklabels[-1].set_ha("right")
    axA.set_xlabel("öğretmen ön-ölçekleme sıcaklığı T")
    axA.set_ylabel("öğrenci ECE (15-bin)", color=ECE_C)
    axA.tick_params(axis="y", labelcolor=ECE_C)
    axA.scatter([x[i_ece]], [ece[i_ece]], s=210, facecolors="none", edgecolors=ECE_C, lw=2.2,
                zorder=5)
    # Bu nokta ECE eğrisinin MİNİMUMU, yani eğri ona hem soldan hem sağdan YUKARIDAN
    # iniyor: noktanın üstündeki her yer (sol-üst de, sağ-üst de) eğrinin üstüne düşer.
    # Boş olan tek komşuluk minimumun ALTI. Sol-alta yazıp sağa yaslıyoruz; x tick
    # etiketleri eksenin dışında kaldığı için çakışma kalmıyor.
    axA.annotate(f"argmin ECE\nT={tlabel(ts[i_ece])}", (x[i_ece], ece[i_ece]),
                 textcoords="offset points", xytext=(-11, -5), ha="right", va="top",
                 color=ECE_C, fontsize=8.5)

    axA2 = axA.twinx()
    axA2.errorbar(x, jsd, yerr=jsd_sd, color=JSD_C, marker="s", capsize=3, lw=1.9, ls="--",
                  label="öğrenci JSD (insan oyuna karşı)")
    axA2.set_ylabel("öğrenci JSD (nats, 10-oy dağılımına karşı)", color=JSD_C)
    axA2.tick_params(axis="y", labelcolor=JSD_C)
    axA2.scatter([x[i_jsd]], [jsd[i_jsd]], s=210, facecolors="none", edgecolors=JSD_C, lw=2.2,
                 zorder=5)
    # Offset upward: the natural down-left placement collides with the x tick labels, which sit
    # just below this point (it is the lowest point on the JSD curve, by construction).
    axA2.annotate(f"argmin JSD\nT={tlabel(ts[i_jsd])}", (x[i_jsd], jsd[i_jsd]),
                  textcoords="offset points", xytext=(12, 10), color=JSD_C, fontsize=8.5)

    h1, l1 = axA.get_legend_handles_labels()
    h2, l2 = axA2.get_legend_handles_labels()
    axA.legend(h1 + h2, l1 + l2, fontsize=8.5, loc="upper center")
    axA.set_title(f"A · İki hedef, iki farklı optimum  (n={n}/kol, @{CKPT})", fontsize=11)
    axA.grid(alpha=0.22)

    # ---- Panel B: the trade-off plane
    axB.errorbar(ece, jsd, xerr=ece_sd, yerr=jsd_sd, color="#444", marker="o", ls="none",
                 capsize=3, zorder=3)
    for xi, yi, t in zip(ece, jsd, ts):
        tag = ROLE.get(t, "")
        col = ECE_C if t == ts[i_ece] else (JSD_C if t == ts[i_jsd] else "#444")
        axB.annotate(f"T={tlabel(t)}\n{tag}", (xi, yi), textcoords="offset points",
                     xytext=(9, -4), fontsize=8.2, color=col)
    axB.scatter([ece[i_ece]], [jsd[i_ece]], s=210, facecolors="none", edgecolors=ECE_C, lw=2.2)
    axB.scatter([ece[i_jsd]], [jsd[i_jsd]], s=210, facecolors="none", edgecolors=JSD_C, lw=2.2)
    axB.set_xlabel("öğrenci ECE  ←  daha iyi")
    axB.set_ylabel("öğrenci JSD (insan oyu)  ↓  daha iyi")
    axB.set_title("B · Sol-alt köşe boş: iki hedef aynı anda tutmuyor", fontsize=11)
    axB.grid(alpha=0.22)
    dx, dy = ece[i_jsd] - ece[i_ece], jsd[i_jsd] - jsd[i_ece]
    axB.annotate("", xy=(ece[i_jsd], jsd[i_jsd]), xytext=(ece[i_ece], jsd[i_ece]),
                 arrowprops=dict(arrowstyle="->", color="#7d3c98", lw=1.7))
    axB.text((ece[i_ece] + ece[i_jsd]) / 2, (jsd[i_ece] + jsd[i_jsd]) / 2,
             f"  takas\n  ECE {dx:+.4f}\n  JSD {dy:+.4f}", color="#7d3c98", fontsize=8.6,
             va="center")
    xr = max(ece) - min(ece)
    axB.set_xlim(min(ece) - 0.12 * xr, max(ece) + 0.30 * xr)

    sub = f"insan ortalama entropisi {hm:.4f} nats" if hm else ""
    fig.suptitle("FERPlus: sert-etiket kalibrasyonu ile insan-belirsizliği hizalaması aynı şey "
                 f"değil  ({sub})", fontsize=12)
    fig.tight_layout()
    png = JSD_DIR / "ferplus_dual_axis.png"
    fig.savefig(png, dpi=180)
    plt.close(fig)

    (JSD_DIR / "ferplus_dual_axis.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION, "checkpoint": CKPT, "n_per_arm": n,
        "arms": [{"T": float(t), "role": ROLE.get(t), "student_ece": e, "student_ece_sd": es,
                  "student_jsd": j, "student_jsd_sd": js}
                 for t, e, es, j, js in zip(ts, ece, ece_sd, jsd, jsd_sd)],
        "argmin_ece_T": float(ts[i_ece]), "argmin_jsd_T": float(ts[i_jsd]),
        "tradeoff_ece": dx, "tradeoff_jsd": dy,
        "human_mean_entropy": hm,
    }, indent=2), encoding="utf-8")

    print(f"argmin ECE T={ts[i_ece]}  (ECE {min(ece):.4f})")
    print(f"argmin JSD T={ts[i_jsd]}  (JSD {min(jsd):.4f})")
    print(f"trade-off: ECE {dx:+.4f}, JSD {dy:+.4f}")
    print(f"\nSaved {png}")


if __name__ == "__main__":
    main()
