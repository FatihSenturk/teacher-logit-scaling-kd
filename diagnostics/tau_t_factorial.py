"""B4 — τ×T tasarımının dört kolu, kurucu (τ, T) değerleriyle.

NEDEN GEREKTİ. Üç bağımsız hakem P6.1'i "confounded" diye okudu ve **üçü de yanıldı**:
tasarımda τ ile T ayrı ayrı oynatılıyor, birlikte değil. Sorun bilimde değil sergilemede
— makalede kolların **kurucu (τ, T) değerleri hiçbir yerde yok**, yalnız çarpımları
(T·τ = 5.10 ve 10.20) görünüyor. Çarpımı verip bileşenleri vermemek, okuyucuyu tam da
hakemlerin düştüğü yere iter.

BU TABLO ÜÇ ŞEY BASIYOR:
  1. Dört kol, her biri kendi (τ, T) çiftiyle, üç tohumda ham ECE ve doğruluk.
  2. İki EŞLEŞMİŞ ÇİFT (aynı T·τ çarpımı) — P6.1'in çökme testi bunlar.
  3. ÜÇ MARJİNAL KONTRAST — çarpım sabit tutulmadan, bir faktör sabit tutularak:
       τ etkisi @ T=1.70 · τ etkisi @ T=0.85 · T etkisi @ τ=6
     Bu üçü tasarımın confound OLMADIĞININ kanıtı: her kontrast tek bir faktörü oynatıyor
     ve üçünün de iki kolu defterde mevcut.

Kol tanımları `p6_1_early_reading.PAIRS`'ten **ithal** — koşu adı da (τ, T) de orada
beyanlı; buraya ikinci bir liste yazmak iki tanımın ayrışmasına davetiye olurdu.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/tau_t_factorial.{md,json}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from p6_1_early_reading import PAIRS, SEEDS, load_swa  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"


def arms():
    """(τ, T) -> {tohum: koşu adı}. Dört kol, ikisi iki çifte de giriyor olabilir."""
    out = {}
    for pair, sides in PAIRS.items():
        for side in ("lo", "hi"):
            tmpl, tau, t = sides[side]
            out.setdefault((tau, t), {"template": tmpl, "runs": {}})
            for s in SEEDS:
                out[(tau, t)]["runs"][s] = tmpl.format(s=s)
    return out


def measured(a, swa):
    ece = [swa[a["runs"][s]]["ece"] for s in SEEDS if a["runs"][s] in swa]
    acc = [swa[a["runs"][s]]["acc"] for s in SEEDS if a["runs"][s] in swa]
    return {"n": len(ece), "seeds": [s for s in SEEDS if a["runs"][s] in swa],
            "ece": ece, "acc": acc,
            "ece_mean": st.mean(ece) if ece else None, "ece_sd": sample_sd(ece),
            "acc_mean": st.mean(acc) if acc else None, "acc_sd": sample_sd(acc)}


def contrast(x, y, swa, label, holds, varies):
    """Tohum-içi eşleştirilmiş fark: x kolu − y kolu, iki eksende."""
    d_ece, d_acc, seeds = [], [], []
    for s in SEEDS:
        rx, ry = x["runs"][s], y["runs"][s]
        if rx not in swa or ry not in swa:
            continue
        d_ece.append(swa[rx]["ece"] - swa[ry]["ece"])
        d_acc.append(swa[rx]["acc"] - swa[ry]["acc"])
        seeds.append(s)
    if not d_ece:
        return None
    return {"label": label, "held_fixed": holds, "varied": varies, "seeds": seeds,
            "n": len(d_ece), "d_ece": d_ece, "d_acc": d_acc,
            "d_ece_mean": st.mean(d_ece), "d_ece_sd": sample_sd(d_ece),
            "d_acc_mean": st.mean(d_acc), "d_acc_sd": sample_sd(d_acc),
            "ece_signs": "".join("+" if v > 0 else "-" for v in d_ece),
            "acc_signs": "".join("+" if v > 0 else "-" for v in d_acc)}


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    swa = load_swa()
    A = arms()
    rows = {f"tau{tau}_T{t}": {"tau": tau, "T": float(t), **measured(a, swa),
                               "runs": a["runs"]}
            for (tau, t), a in sorted(A.items())}

    # eşleşmiş çiftler (aynı çarpım) — P6.1'in kendi kontrastları
    matched = []
    for pair, sides in PAIRS.items():
        lo, hi = sides["lo"], sides["hi"]
        c = contrast(A[(lo[1], lo[2])], A[(hi[1], hi[2])], swa, pair,
                     f"T·τ = {lo[1] * float(lo[2]):.2f}",
                     f"τ {lo[1]}→{hi[1]}, T {lo[2]}→{hi[2]}")
        if c:
            matched.append(c)

    # MARJİNAL kontrastlar: tek faktör oynuyor
    marg = []
    keys = set(A)
    for (tau_a, t_a) in sorted(keys):
        for (tau_b, t_b) in sorted(keys):
            if (tau_a, t_a) >= (tau_b, t_b):
                continue
            if t_a == t_b:
                lbl, holds, varies = (f"τ etkisi @ T={t_a}", f"T = {t_a}",
                                      f"τ {tau_a} → {tau_b}")
            elif tau_a == tau_b:
                lbl, holds, varies = (f"T etkisi @ τ={tau_a}", f"τ = {tau_a}",
                                      f"T {t_a} → {t_b}")
            else:
                continue
            c = contrast(A[(tau_b, t_b)], A[(tau_a, t_a)], swa, lbl, holds, varies)
            if c:
                marg.append(c)

    write(rows, matched, marg)
    print("=== tau_t_factorial ===")
    print(f"  kol: {len(rows)}")
    for k, v in rows.items():
        print(f"    tau={v['tau']:2d}  T={v['T']:.2f}  n={v['n']}  "
              f"ECE {v['ece_mean']:.4f}±{v['ece_sd']:.4f}  "
              f"acc {v['acc_mean']:.3f}±{v['acc_sd']:.3f}")
    print(f"  eslesmis cift (ayni carpim): {len(matched)}")
    print(f"  MARJINAL kontrast (tek faktor): {len(marg)}")
    for c in marg:
        print(f"    {c['label']:22s} [{c['varied']}]  dECE {c['d_ece_mean']:+.4f} "
              f"({c['ece_signs']})  dacc {c['d_acc_mean']:+.3f} ({c['acc_signs']})")


def write(rows, matched, marg):
    L = ["# B4 — τ×T tasarımı: dört kol, kurucu (τ, T) değerleriyle", "",
         f"Üretici: `diagnostics/tau_t_factorial.py` · @swa · {SD_CONVENTION} · kol "
         f"tanımları `p6_1_early_reading.PAIRS`'ten **ithal**", "",
         "> Üç bağımsız hakem bu bölümü *confounded* diye okudu ve **üçü de yanıldı**. "
         "Tasarımda τ ile T ayrı ayrı oynuyor. Sorun sergilemede: makalede yalnız "
         "**çarpım** (T·τ) görünüyor, kurucu değerler hiçbir yerde yok. Bu tablo onları "
         "basıyor ve üç **marjinal** kontrastı ekliyor — her biri tek bir faktörü "
         "oynatıyor, yani confound olmadığının doğrudan kanıtı.", "",
         "## 1 · Dört kol", "",
         "| τ | T | n | ECE (ort ± sd) | doğruluk (ort ± sd) | tohumlar |",
         "|---|---|---|---|---|---|"]
    for v in rows.values():
        L.append(f"| **{v['tau']}** | **{v['T']:.2f}** | {v['n']} | "
                 f"{v['ece_mean']:.4f} ± {v['ece_sd']:.4f} | "
                 f"{v['acc_mean']:.3f} ± {v['acc_sd']:.3f} | {v['seeds']} |")

    L += ["", "### Tohum tohum", "",
          "| τ | T | " + " | ".join(f"ECE s{s}" for s in SEEDS) + " | "
          + " | ".join(f"acc s{s}" for s in SEEDS) + " |",
          "|---|---|" + "---|" * (2 * len(SEEDS))]
    for v in rows.values():
        L.append(f"| {v['tau']} | {v['T']:.2f} | "
                 + " | ".join(f"{e:.4f}" for e in v["ece"]) + " | "
                 + " | ".join(f"{a:.3f}" for a in v["acc"]) + " |")

    L += ["", "## 2 · Eşleşmiş çiftler — aynı T·τ çarpımı (P6.1'in çökme testi)", "",
          "| çift | değişen | n | ΔECE (ort ± sd) | işaret | Δacc (pp, ort ± sd) | işaret |",
          "|---|---|---|---|---|---|---|"]
    for c in matched:
        L.append(f"| **{c['label']}** | {c['varied']} | {c['n']} | "
                 f"{c['d_ece_mean']:+.4f} ± {c['d_ece_sd']:.4f} | `{c['ece_signs']}` | "
                 f"{c['d_acc_mean']:+.3f} ± {c['d_acc_sd']:.3f} | `{c['acc_signs']}` |")

    L += ["", "## 3 · Marjinal kontrastlar — **tek faktör oynuyor**", "",
          "Bu üç satır hakem itirazının doğrudan cevabı. Her birinde bir faktör sabit "
          "tutuluyor, diğeri oynatılıyor; iki kol da defterde mevcut, yani kontrast "
          "türetilmiş değil **ölçülmüş**.", "",
          "| kontrast | sabit | değişen | n | ΔECE (ort ± sd) | işaret | "
          "Δacc (pp, ort ± sd) | işaret |", "|---|---|---|---|---|---|---|---|"]
    for c in marg:
        L.append(f"| **{c['label']}** | {c['held_fixed']} | {c['varied']} | {c['n']} | "
                 f"{c['d_ece_mean']:+.4f} ± {c['d_ece_sd']:.4f} | `{c['ece_signs']}` | "
                 f"{c['d_acc_mean']:+.3f} ± {c['d_acc_sd']:.3f} | `{c['acc_signs']}` |")
    L += ["", "> Tasarımın confound olmadığı buradan okunur: τ'nun etkisi **iki ayrı T "
          "değerinde ayrı ayrı** ölçülebiliyor ve T'nin etkisi **sabit τ'da** "
          "ölçülebiliyor. Üç kontrastın üçü de tek değişkenli.", "",
          "---", "",
          "Kaynak: `diagnostics/selection_audit/selection_audit_unfrozen.csv` @swa · "
          "kol tanımı: `diagnostics/p6_1_early_reading.py::PAIRS`", ""]

    (OUT_DIR / "tau_t_factorial.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "tau_t_factorial.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION, "arms": rows, "matched_pairs": matched,
        "marginal_contrasts": marg}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
