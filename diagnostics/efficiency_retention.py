"""G4.4 — verim: öğrenci/öğretmen doğruluk oranı, BİRİNCİL @swa.

NEDEN VAR (panel G4.4). Makalenin verim cümlesi **%98.32** diyor ve bu sayı `best`
checkpoint'inden geliyor. `best`, raporlanan 3068 görüntüde argmax val-acc ile seçiliyor —
yani seçim ve raporlama AYNI görüntüleri kullanıyor ve sayı seçim iyimserliği taşıyor. Bir
kalibrasyon makalesinin verim iddiası, hiç gözetlemeyen bir kuralla ölçülmelidir.

Panel bunu sayıyla sordu: "(89.95/91.82 = %97.96?)". Bu betik cevabı ölçüyor: **evet**.

NE DEĞİŞİYOR. Birincil sayı @swa'ya geçiyor, @best parantezde kalıyor. Hiçbir sayı
silinmiyor — üç checkpoint de raporlanıyor ki okur farkın büyüklüğünü görsün.

YAPI SAYILARI İTHAL EDİLİYOR. Parametre/FLOP/boyut ve öğretmen doğruluğu
`p5_efficiency_frontier`'ın kendi sabitlerinden alınıyor, buraya yeniden yazılmıyor — iki
dosyanın aynı öğretmeni farklı sayılarla anlatması bu kampanyanın zaten bir kez yaşadığı
hata sınıfı.

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/efficiency_retention.{json,md}
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from p5_efficiency_frontier import TEACHER, STUDENT                  # noqa: E402 -- İTHAL
from stats_convention import SD_CONVENTION, sample_sd                # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit_unfrozen.csv"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CKPTS = ("swa", "best", "last")
PRIMARY = "swa"
SEEDS = (42, 1, 43)

# Manşet öğrenci kolu -- p5_efficiency_frontier'ın "T-C baseline" hücresiyle AYNI koşular.
ARM = "RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200"
ARM_RUNS = (ARM, f"{ARM}_seed1", f"{ARM}_seed43")


def load(ck):
    """(koşu adı -> satır) @ck. Aynı (koşu, ckpt) iki kez varsa hüküm sıraya bağlı olurdu."""
    out = {}
    for r in csv.DictReader(AUDIT.open(encoding="utf-8")):
        if r["checkpoint"] != ck or r["run_name"] not in ARM_RUNS:
            continue
        if r["run_name"] in out:
            raise RuntimeError(f"{r['run_name']} @{ck} denetimde iki kez var — "
                               f"seçim satır sırasına bırakılmaz.")
        out[r["run_name"]] = r
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    t_acc = TEACHER["acc"]
    rows = {}
    for ck in CKPTS:
        d = load(ck)
        missing = [n for n in ARM_RUNS if n not in d]
        if missing:
            raise RuntimeError(f"@{ck} eksik koşu: {missing} — kol tamam değilken oran yazılmaz.")
        accs = [float(d[n]["acc"]) for n in ARM_RUNS]
        m = st.mean(accs)
        rows[ck] = {"n": len(accs), "acc_mean": m, "acc_sd": sample_sd(accs),
                    "per_run": {n: float(d[n]["acc"]) for n in ARM_RUNS},
                    "retention_pct": 100 * m / t_acc, "gap_pp": t_acc - m}

    # Seçim iyimserliğinin bu kolda ölçülmüş büyüklüğü -- genel denetim ortalaması değil,
    # tam olarak bu üç koşunun kendi farkı.
    opt_best_last = rows["best"]["acc_mean"] - rows["last"]["acc_mean"]
    opt_best_swa = rows["best"]["acc_mean"] - rows["swa"]["acc_mean"]

    comp = {"params_ratio": TEACHER["params_m"] / STUDENT["params_m"],
            "flops_ratio": TEACHER["flops_g"] / STUDENT["flops_g"],
            "size_ratio": TEACHER["size_mb"] / STUDENT["size_mb"]}

    write(rows, comp, t_acc, opt_best_last, opt_best_swa)
    print("G4.4 verim orani:")
    for ck in CKPTS:
        r = rows[ck]
        star = "  <-- BIRINCIL" if ck == PRIMARY else ""
        print(f"  @{ck:5s} {r['acc_mean']:.3f} / {t_acc:.2f} = {r['retention_pct']:.2f}%  "
              f"(acik {r['gap_pp']:.2f} pp){star}")
    print(f"\nsecim iyimserligi bu kolda: best-swa {opt_best_swa:+.3f} pp, "
          f"best-last {opt_best_last:+.3f} pp")


def write(rows, comp, t_acc, opt_bl, opt_bs):
    p = rows[PRIMARY]
    L = ["# G4.4 — verim: öğrenci/öğretmen doğruluk oranı", "",
         "> **Panel G4.4.** Makalenin verim cümlesi `best` checkpoint'inden geliyordu. `best`, "
         "raporlanan 3068 görüntüde argmax val-acc ile seçiliyor — seçim ve raporlama aynı "
         "görüntüler, dolayısıyla sayı seçim iyimserliği taşıyor. Birincil sayı **@swa**'ya "
         "geçiyor; @best parantezde kalıyor, silinmiyor.", "",
         f"**BİRİNCİL: {p['acc_mean']:.2f} / {t_acc:.2f} = %{p['retention_pct']:.2f}** "
         f"(@best: %{rows['best']['retention_pct']:.2f})", "",
         f"Kol: `{ARM}` (+`_seed1`, +`_seed43`) · {SD_CONVENTION}", "",
         "## Üç checkpoint", "",
         "| checkpoint | n | öğrenci doğruluk | oran | açık (pp) |", "|---|---|---|---|---|"]
    for ck in CKPTS:
        r = rows[ck]
        mark = " **(birincil)**" if ck == PRIMARY else ""
        L.append(f"| `{ck}`{mark} | {r['n']} | {r['acc_mean']:.3f} ± {r['acc_sd']:.3f} | "
                 f"**%{r['retention_pct']:.2f}** | {r['gap_pp']:.2f} |")
    L += ["", f"Öğretmen: {TEACHER['name']}, {t_acc:.2f}%.", "",
          "## Seçim iyimserliği, bu kolda ölçülmüş", "",
          f"- `best` − `swa` = **{opt_bs:+.3f} pp** → oranı %{opt_bs * 100 / t_acc:+.2f} puan şişiriyor",
          f"- `best` − `last` = **{opt_bl:+.3f} pp**", "",
          "Yani iki sayı arasındaki fark küçük ama **tek yönlü**: `best` her zaman kayırır, "
          "çünkü tanımı gereği maksimumu seçer. Bir kalibrasyon makalesinde verim iddiasının "
          "gözetlemeyen bir kurala dayanması, farkın büyüklüğünden bağımsız olarak doğru olandır.",
          "",
          "## Sıkıştırma (yapısal, deterministik — checkpoint'ten bağımsız)", "",
          "| eksen | öğretmen | öğrenci | oran |", "|---|---|---|---|",
          f"| parametre | {TEACHER['params_m']:.3f} M | {STUDENT['params_m']:.3f} M | "
          f"**{comp['params_ratio']:.1f}×** |",
          f"| FLOPs | {TEACHER['flops_g']:.4f} G | {STUDENT['flops_g']:.4f} G | "
          f"**{comp['flops_ratio']:.1f}×** |",
          f"| boyut | {TEACHER['size_mb']:.1f} MB | {STUDENT['size_mb']:.2f} MB | "
          f"**{comp['size_ratio']:.1f}×** |", "",
          "Bu üç oran ölçüm değil sayım; checkpoint seçiminden etkilenmezler ve olduğu gibi "
          "kalırlar. Yapı sayıları `p5_efficiency_frontier`'dan **ithal** edildi.", "",
          "## Tohum bazında", "",
          "| koşu | " + " | ".join(f"@{c}" for c in CKPTS) + " |",
          "|---|" + "---|" * len(CKPTS)]
    for n in ARM_RUNS:
        L.append(f"| `{n}` | " + " | ".join(f"{rows[c]['per_run'][n]:.3f}" for c in CKPTS) + " |")
    L += ["", "---", "",
          "Üretici: `diagnostics/efficiency_retention.py` · veri: "
          "`diagnostics/selection_audit/selection_audit_unfrozen.csv` · yapı sayıları: "
          "`diagnostics/p5_efficiency_frontier.py` (ithal)", ""]

    (OUT_DIR / "efficiency_retention.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "efficiency_retention.json").write_text(json.dumps({
        "item": "G4.4", "primary_checkpoint": PRIMARY, "arm": ARM, "arm_runs": list(ARM_RUNS),
        "teacher": TEACHER, "student": STUDENT, "compression": comp,
        "by_checkpoint": rows, "sd_convention": SD_CONVENTION,
        "selection_optimism_pp": {"best_minus_swa": opt_bs, "best_minus_last": opt_bl},
        "headline": {"retention_pct_swa": rows["swa"]["retention_pct"],
                     "retention_pct_best": rows["best"]["retention_pct"]},
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
