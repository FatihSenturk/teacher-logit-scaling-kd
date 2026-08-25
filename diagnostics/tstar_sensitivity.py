"""R3-2: T* FİT KRİTERİ duyarlılığı — "neden NLL ile fit ettiniz?" itirazına ölçülü yanıt.

İTİRAZ (dış inceleme). Makale T*'ı NLL küçülterek fit ediyor (Guo et al. 2017), ama
raporladığı büyüklük ECE. Bu iki kriter aynı T'yi vermek zorunda değildir: NLL tüm
olasılık vektörünü cezalandırır, ECE yalnız max-prob'un kutulanmış sapmasını. Fark
nicelenmemişse, "T* kalibrasyon optimumudur" cümlesi fit kriterine gizlice bağlıdır.

BU BETİĞİN YAPTIĞI. Dört öğretmenin her biri için, TAM değerlendirme foldunda:
  T*_NLL  — dağıtılan değer (student_ts_baseline.fit_ts, AYNI fonksiyon)
  T*_ECE  — ECE(T)'nin sürekli argmin'i, aynı log-uzay sınırında Brent ile
  iki noktadaki ECE farkı ve |T*_NLL − T*_ECE|

BEKLENTİ YOKTUR. Bu bir envanterdir (ön-kayıt A10): fark ne çıkarsa yazılır, eşik yoktur.

ECE(T) PÜRÜZSÜZ DEĞİLDİR — ve bu sessizce geçilemez. ECE kutulanmış bir istatistiktir:
T değiştikçe örnekler kutu sınırlarını atlar, dolayısıyla ECE(T) parça-parça sabit
sıçramalar taşır. Sürekli bir optimize edici böyle bir yüzeyde yerel bir çukura
saplanabilir. Bu yüzden her Brent sonucu YOĞUN BİR GRID'e karşı doğrulanır (adım 0.005,
yayımlanmış gridlerin 10x altı): Brent'in bulduğu ECE, grid minimumundan belirgin
biçimde büyükse satır **LOCAL-MIN** diye işaretlenir ve grid değeri de basılır. Kapı
gizlenmez, tabloya girer.

VERİ: önbellekli öğretmen logitleri, forward yok, GPU yok. Yükleyiciler ve fold
tanımları tstar_stability'den import edilir (tek kaynak) — aynı n, aynı filtre, aynı
etiket doğrulaması.

Salt-okunur. Çıktı -> diagnostics/paper_tables/tstar_sensitivity.{md,json}
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import minimize_scalar

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from student_ts_baseline import fit_ts  # noqa: E402  (dağıtılan fit, AYNI fonksiyon)
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402
from tstar_stability import (  # noqa: E402  (aynı yükleyiciler, aynı foldlar)
    GRID_DIR, PUBLISHED, ferplus_kept, rafdb_names_and_labels)

OUT_DIR = ROOT / "diagnostics" / "paper_tables"

# fit_ts ile AYNI arama aralığı: iki kriter aynı kutuda aranmazsa fark, kriterin
# değil sınırın eseri olurdu.
LOG_BOUNDS = (np.log(0.05), np.log(10.0))
DENSE_STEP = 0.005          # Brent'i sınayan yoğun grid adımı
DENSE_RANGE = (0.10, 3.00)  # dört öğretmenin T* değerlerini de gridlerini de kapsar
LOCAL_MIN_TOL = 1e-5        # bunun üstünde bir fark yerel-minimum işareti sayılır

# Makalede fiilen DAĞITILAN T* (tstar_stability'nin çapa notundaki ayrım): stage1'de
# yayımlanan tam-fold fiti 1.3494 iken deneylerde 1.3406 kullanıldı.
DEPLOYED = {"stage1": 1.3406, "primary": 1.2613, "vae9182": 0.9829, "ferplus": 0.5063}


def ece_argmin_continuous(logits, labels):
    """ECE(T)'nin sürekli argmin'i — fit_ts ile aynı log-uzay, aynı sınır, Brent."""
    def ece(log_t):
        return confidence_ece(logits, labels, float(np.exp(log_t)))
    r = minimize_scalar(ece, bounds=LOG_BOUNDS, method="bounded")
    return float(np.exp(r.x)), float(r.fun)


def dense_grid_argmin(logits, labels):
    """Brent'in denetleyicisi. Yoğun grid üzerinde kaba kuvvet minimum."""
    ts = np.arange(DENSE_RANGE[0], DENSE_RANGE[1] + DENSE_STEP / 2, DENSE_STEP)
    best_T, best_e = None, float("inf")
    for T in ts:
        e = confidence_ece(logits, labels, float(T))
        if e < best_e:
            best_T, best_e = float(T), e
    return best_T, best_e, len(ts)


def nll(logits, labels, T):
    """T sıcaklığındaki çapraz-entropi. `fit_ts`'in küçülttüğü amaç fonksiyonunun kendisi —
    iki aday optimumu KARŞILAŞTIRMAK için gerekli, çünkü T'deki fark tek başına o farkın
    anlamlı olup olmadığını söylemez."""
    return float(torch.nn.functional.cross_entropy(logits / float(T), labels))


def one_teacher(tag, logits, labels, confirm_T=None):
    t_nll = fit_ts(logits, labels)
    t_ece, e_at_ece = ece_argmin_continuous(logits, labels)
    e_at_nll = confidence_ece(logits, labels, t_nll)
    g_T, g_e, n_grid = dense_grid_argmin(logits, labels)

    # Brent yoğun grid'den ANLAMLI ölçüde kötü bir nokta bulduysa yüzey pürüzsüz değil
    # demektir ve sürekli argmin tek başına raporlanamaz.
    local_min = (e_at_ece - g_e) > LOCAL_MIN_TOL
    out = {
        "n": int(labels.shape[0]),
        "T_star_nll": t_nll,
        "T_star_ece": t_ece,
        "abs_dT": abs(t_nll - t_ece),
        "ece_at_T_nll": e_at_nll,
        "ece_at_T_ece": e_at_ece,
        "d_ece": e_at_nll - e_at_ece,          # >= 0 beklenir: ECE kendi optimumunda daha küçük
        "ece_at_T1": confidence_ece(logits, labels, 1.0),
        # TS'in fiilen KALDIRDIĞI ECE. Bu sütun olmadan "fark küçüktür" cümlesi neye
        # göre küçük olduğunu söyleyemez — ve işareti negatife dönebilir (kalibrasyon
        # tabanındaki öğretmende TS ECE'yi ARTIRIR), o yüzden iddia değil hesap.
        "ece_removed_by_ts": confidence_ece(logits, labels, 1.0) - e_at_nll,
        "dense_grid_T": g_T, "dense_grid_ece": g_e, "dense_grid_points": n_grid,
        "local_min_flag": bool(local_min),
        # DIKKAT: bu iki alan BEYANDIR, ölçüm değil (elle yazılmış PUBLISHED/DEPLOYED
        # sözlükleri). Sayı defteri onlara BAĞLANMAZ -- bağlanırsa alan, basılı sayının elle
        # yazılmış kopyası olur ve bağ dairesel hale gelir (17 Ağu, N14).
        "published_full_nll": PUBLISHED[tag],
        "deployed_T": DEPLOYED[tag],
    }

    # ---- KANONİK vs TEYİT (17 Ağu 2026, N14 kararı) ----------------------------------------
    # Aynı niceliği (T*_NLL) iki BAĞIMSIZ uygulama hesaplıyor: burada `student_ts_baseline.fit_ts`
    # (log-uzay, [0.05,10], kampanyanın dağıttığı fit) ve `teacher_ece_grid.fit_temperature`.
    # İkinci değer `p4_teacher_selection` ile `temperature_fit.json` tarafından AYNEN rölelenir,
    # yani üç artefakt iki hesap taşır.
    # KARAR: BİRLEŞTİRİLMEDİ. Gün boyu kovaladığımız hastalık "aynı ad, iki farklı nicelik"ti;
    # bu onun tersi -- iki farklı hesap AYNI niceliği buluyor, yani çapraz doğrulama. Birleştirmek
    # doğrulamayı yok ederdi. Bu betik kanoniktir (T*'ın adanmış üreticisi); teyit kaydı burada.
    # ÖLÇÜLEN ŞEY T FARKI DEĞİL, AMAÇ FARKI: NLL iki adayı ayırt edebiliyor mu?
    if confirm_T is not None:
        c = float(confirm_T)
        out["cross_fit"] = {
            "canonical_fitter": "student_ts_baseline.fit_ts (log-space Brent, [0.05, 10])",
            "confirm_fitter": "teacher_ece_grid.fit_temperature",
            "confirm_relayed_by": ["p4_teacher_selection.recipe_step3_ranking.rows[].T_star",
                                   "teacher_temperature_scaling/temperature_fit.json"],
            "confirm_T_star": c,
            "abs_dT": abs(t_nll - c),
            "nll_at_canonical": nll(logits, labels, t_nll),
            "nll_at_confirm": nll(logits, labels, c),
        }
        out["cross_fit"]["d_nll"] = (out["cross_fit"]["nll_at_confirm"]
                                     - out["cross_fit"]["nll_at_canonical"])
        out["cross_fit"]["ece_at_confirm"] = confidence_ece(logits, labels, c)
        out["cross_fit"]["d_ece"] = out["cross_fit"]["ece_at_confirm"] - e_at_nll
    return out


def main():
    results = {}

    # Teyit fitleri: `teacher_ece_grid.json` yalnız üç RAF-DB öğretmenini taşır (FERPlus'ın
    # ikinci bir fiti yok, o yüzden onun cross_fit bloğu da olmaz -- yok olan bir teyidi
    # varmış gibi yazmak, teyidin kendisini değersizleştirir).
    grid = json.loads((GRID_DIR / "teacher_ece_grid.json").read_text(encoding="utf-8"))

    raf_names, raf_labels = rafdb_names_and_labels()
    for tag in ("stage1", "primary", "vae9182"):
        blob = torch.load(GRID_DIR / f"teacher_val_logits_{tag}.pt", map_location="cpu",
                          weights_only=False)
        if not torch.equal(blob["labels"], raf_labels):
            raise RuntimeError(f"{tag}: cached labels do not match the metadata fold-3 order")
        results[tag] = one_teacher(tag, blob["logits"].float(), blob["labels"],
                                   confirm_T=grid[tag]["T_star"])

    f_logits, f_labels, f_names = ferplus_kept()
    if len(f_names) != 3153:
        raise RuntimeError(f"FERPlus reporting set: expected 3153, found {len(f_names)}")
    results["ferplus"] = one_teacher("ferplus", f_logits, f_labels)

    any_local = any(r["local_min_flag"] for r in results.values())
    max_dT = max(r["abs_dT"] for r in results.values())
    max_dece = max(r["d_ece"] for r in results.values())

    L = ["# R3-2 — T* fitting-criterion sensitivity (NLL vs. ECE argmin)", "",
         "Producer: `diagnostics/tstar_sensitivity.py` · `T*_NLL` is the deployed fit "
         "(`student_ts_baseline.fit_ts`, the same function the campaign uses) · `T*_ECE` is the "
         "continuous argmin of ECE(T) found by bounded Brent over the **same** log-space "
         "interval [0.05, 10], so any difference is the criterion's and not the search box's · "
         "cached teacher logits, no forward pass. Pre-declared in `PREREGISTRATIONS.md` A10 "
         "(R3-2): **no expectation, no threshold** — the difference is reported as it falls.", "",
         "| teacher | n | T\\*_NLL | T\\*_ECE | **\\|ΔT\\*\\|** | ECE @T=1 | ECE @T\\*_NLL | "
         "ECE @T\\*_ECE | **ΔECE (criterion cost)** | ECE removed by TS | ratio | "
         "dense-grid check |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for tag, r in results.items():
        chk = (f"**LOCAL-MIN** (grid {r['dense_grid_ece']:.5f} @T={r['dense_grid_T']:.3f})"
               if r["local_min_flag"] else f"ok (T={r['dense_grid_T']:.3f})")
        rem = r["ece_removed_by_ts"]
        ratio = ("**n/a — TS adds ECE**" if rem <= 0 else f"{rem / r['d_ece']:.0f}×")
        L.append(f"| {tag} | {r['n']} | {r['T_star_nll']:.4f} | {r['T_star_ece']:.4f} | "
                 f"**{r['abs_dT']:.4f}** | {r['ece_at_T1']:.5f} | {r['ece_at_T_nll']:.5f} | "
                 f"{r['ece_at_T_ece']:.5f} | **{r['d_ece']:+.5f}** | {rem:+.5f} | {ratio} | "
                 f"{chk} |")

    gain_ok = {t: r for t, r in results.items() if r["ece_removed_by_ts"] > 0}
    gain_bad = {t: r for t, r in results.items() if r["ece_removed_by_ts"] <= 0}
    ratios = {t: r["ece_removed_by_ts"] / r["d_ece"] for t, r in gain_ok.items()}
    per_teacher = ", ".join(f"{t} {v:.0f}×" for t, v in ratios.items())
    L += ["",
          f"**Reported as it fell.** The two criteria disagree by at most **{max_dT:.4f}** in T "
          f"across the four teachers, and choosing the NLL optimum instead of the ECE optimum "
          f"costs at most **{max_dece:.5f}** in ECE. In the {len(gain_ok)} teachers where "
          f"temperature scaling removes ECE at all, that cost is "
          f"{min(ratios.values()):.0f}–{max(ratios.values()):.0f}× smaller than the ECE the "
          f"scaling removes ({per_teacher}), so for those teachers the reported calibration "
          "gains do not depend on which criterion locates T*.", ""]
    for tag, r in gain_bad.items():
        L += [f"> ⚠️ **{tag} is the exception, and it is not a rounding artefact.** This teacher "
              f"is already at its calibration floor (ECE {r['ece_at_T1']:.5f} at T=1), and the "
              f"NLL-fitted T*={r['T_star_nll']:.4f} makes its ECE **worse**, not better "
              f"({r['ece_at_T1']:.5f} → {r['ece_at_T_nll']:.5f}, "
              f"{-r['ece_removed_by_ts']:+.5f}). The ECE criterion instead finds "
              f"T*={r['T_star_ece']:.4f} — on the other side of 1 — and does reduce ECE to "
              f"{r['ece_at_T_ece']:.5f}. So the two criteria do not merely differ in magnitude "
              f"here: they disagree about the **direction** of the correction. The sentence "
              f"'the fitting criterion does not matter' cannot be written for {tag}.", ""]
    if any_local:
        L += ["> ⚠️ **Non-smooth surface.** ECE(T) is a binned statistic and is piecewise "
              "constant in places, so the continuous optimiser can settle away from the global "
              "minimum. Rows marked LOCAL-MIN are exactly those; the dense-grid value "
              f"(step {DENSE_STEP}, {DENSE_RANGE[0]}–{DENSE_RANGE[1]}) is printed beside them and "
              "is the one to quote for those teachers.", ""]
    else:
        L += [f"Every continuous argmin was confirmed against a dense grid "
              f"(step {DENSE_STEP} over {DENSE_RANGE[0]}–{DENSE_RANGE[1]}, "
              f"{results['stage1']['dense_grid_points']} points): no row is a local minimum.", ""]

    # --- KANONİK vs TEYİT bloğu: aynı niceliği iki uygulama buluyor
    xf = {t: r["cross_fit"] for t, r in results.items() if "cross_fit" in r}
    if xf:
        L += ["## Canonical vs. confirming fit of the same quantity", "",
              "`T*_NLL` is computed here by `student_ts_baseline.fit_ts` (the function the "
              "campaign deploys) and, independently, by `teacher_ece_grid.fit_temperature`. The "
              "second value is relayed verbatim by `p4_teacher_selection` and by "
              "`temperature_fit.json`, so three artifacts carry **two** computations. The two are "
              "**deliberately not merged**: two implementations agreeing on one quantity is a "
              "cross-check, and merging them would destroy it. This table is the confirmation "
              "record — and it reports the difference in the **objective**, not only in T, "
              "because a difference in T says nothing on its own about whether the fit disagrees.",
              "",
              "| teacher | canonical T\\* (`fit_ts`) | confirming T\\* (`fit_temperature`) | "
              "**\\|ΔT\\*\\|** | NLL @canonical | NLL @confirming | **ΔNLL** | ΔECE |",
              "|---|---|---|---|---|---|---|---|"]
        for t, c in xf.items():
            L.append(f"| {t} | {results[t]['T_star_nll']:.7f} | {c['confirm_T_star']:.7f} | "
                     f"**{c['abs_dT']:.2e}** | {c['nll_at_canonical']:.9f} | "
                     f"{c['nll_at_confirm']:.9f} | **{c['d_nll']:+.2e}** | {c['d_ece']:+.6f} |")
        worst_t = max(xf, key=lambda t: xf[t]["abs_dT"])
        L += ["", f"Largest disagreement in T is **{worst_t}** at "
              f"{xf[worst_t]['abs_dT']:.2e}, yet the objective separates the two candidates by "
              f"only {xf[worst_t]['d_nll']:+.2e} in NLL. The two fitters are therefore at the "
              f"same optimum to within their own convergence tolerance; the residual is the "
              f"parameterisation (log-space vs. linear box), not the estimand. FERPlus has no "
              f"second fit, so it has no row here.", ""]

    payload = {"pre_registration": "PREREGISTRATIONS.md A10 (R3-2); no success criterion",
               "fit_nll": "single-scalar TS, NLL, minimize_scalar bounded log-space [0.05, 10] "
                          "(= student_ts_baseline.fit_ts)",
               "fit_ece": "continuous argmin of 15-bin equal-width confidence ECE, bounded Brent, "
                          "same log-space interval",
               "dense_grid": {"step": DENSE_STEP, "range": list(DENSE_RANGE),
                              "tolerance": LOCAL_MIN_TOL},
               "results": results, "any_local_min": any_local,
               "max_abs_dT": max_dT, "max_d_ece": max_dece}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tstar_sensitivity.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "tstar_sensitivity.json").write_text(json.dumps(payload, indent=2),
                                                    encoding="utf-8")

    for tag, r in results.items():
        print(f"{tag:<9} T*_NLL {r['T_star_nll']:.4f}  T*_ECE {r['T_star_ece']:.4f}  "
              f"|dT| {r['abs_dT']:.4f}  dECE {r['d_ece']:+.5f}"
              f"{'  [LOCAL-MIN]' if r['local_min_flag'] else ''}")
    print(f"\nWrote {OUT_DIR / 'tstar_sensitivity.md'}")

    # Bant altyapısı genel depoda bulunmaz; yokluğu tablo üretimini durdurmamalı.
    try:
        import export_to_drive
        export_to_drive.hook("tstar_sensitivity.py")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
