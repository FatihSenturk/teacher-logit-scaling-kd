"""N11 — FERPlus headroom: 0.1198 mi 0.1131 mi? Izgara BIR PARAMETRE, estimand degil.

CELISKI (dis inceleme, 15 Agu 2026). Ayni nicelik iki artefaktta farkli:
  · paper_tables/headroom_review.md §2 -> 0.1198
  · paper_tables/bootstrap_cis.md       -> 0.1131 [0.1039, 0.1174]
ve nokta tahmini kendi araliginin USTUNDE kaliyor (0.1198 > 0.1174). Bir CI'nin kendi nokta
tahminini dislamasi mumkun degildir; dolayisiyla bu IKI FARKLI NICELIK olmali.

OLCULEN CEVAP. Formul ayni (`ECE(T=1) - min_{T in G} ECE(T)`, 15-bin esit-genislik, ayni 3153
ornek, ayni onbellekli logit dosyasi). Degisen tek sey **G**:
  · headroom_review  G = ferplus_jsd.sweep      -> [0.10, 4.00], adim 0.02, 196 nokta
  · bootstrap_cis    G = bootstrap_cis.T_GRID   -> [0.50, 2.50], adim 0.02, 101 nokta
Ince taramanin argmin'i **T = 0.46**, yani bootstrap izgarasinin TABANININ ALTINDA. Alt kume
uzerindeki minimum daha buyuk oldugu icin headroom yapisal olarak daha KUCUK cikar:
`min_{T in G'} >= min_{T in G}` (G' subset G) => `headroom(G') <= headroom(G)`. Yani 0.1131 <=
0.1198 bir tesaduf degil, bir teoremdir; aralik da kucuk olanin etrafinda.

Bu betik hicbir seyi varsaymaz: ucu de AYNI onbellekten yeniden olculur, yayimli sayilarla
karsilastirilir (sapma esigi 1e-6) ve **her ucu icin ayni bootstrap ile CI uretilir** -- boylece
makale hangi tanimi secerse secsin, o tanimin KENDI araligi olur. Ayrica her izgara icin
argmin'in SINIRDA olup olmadigi ve bunun bootstrap tekrarlarindaki orani raporlanir.

DUZELTME (14 Agu, number_audit_round3 kalem 9). Dun "0.5 hicbir izgaranin siniri degil ve hicbir
optimum sinirda degil" yazildi. O hüküm IKI izgaraya bakiyordu (RAF-DB fine_sweep ve FERPlus
196-nokta sweep) ve UCUNCUSUNU -- bootstrap_cis'in kendi T_GRID'ini -- atliyordu. Ucuncusunun
alt siniri tam olarak 0.50'dir ve FERPlus argmin'i tam olarak orada oturur. Panelin sorusu
dogruydu; dunku cevap yanlisti. Sayilar asagida.

Salt-okunur, GPU yok, ileri gecis yok: yalniz onbellekli logitler.
Cikti -> diagnostics/paper_tables/headroom_grid_audit.{md,json}
Kullanim: python diagnostics/headroom_grid_audit.py [--b 2000]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

# ITHAL, KOPYA DEGIL: ECE binlemesi, bootstrap agirliklandirmasi, yuzdelik ve sabitler
# bootstrap_cis'in KENDISINDEN gelir. Yeniden yazilsalardi "iki sayi neden farkli" sorusuna
# verilen cevap bu betigin kendi ucuncu tanimini eklemis olurdu.
from bootstrap_cis import (N_BINS, RNG_SEED, T_GRID as BOOT_T_GRID,  # noqa: E402
                           TEACHERS as BOOT_TEACHERS, ece_weighted, pct, precompute)

D = ROOT / "diagnostics"
FER_LOGITS = D / "ferplus_jsd" / "ferplus_val_logits.pt"
A_FER = D / "ferplus_jsd" / "ferplus_jsd.json"
A_FER_SG = D / "ferplus_jsd" / "ferplus_teacher_signed_grid.json"
A_HR = D / "paper_tables" / "headroom_review.json"
A_BC = D / "paper_tables" / "bootstrap_cis.json"
A_TS = D / "paper_tables" / "tstar_sensitivity.json"
TG = D / "teacher_ece_grid"
OUT_DIR = D / "paper_tables"

TOL = 1e-6      # onbellek float32, yeniden hesap float64 -> ~1e-8 beklenir


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def grid_stats(t_grid):
    t = np.asarray(t_grid, dtype=np.float64)
    steps = np.diff(t)
    uniform = bool(len(steps)) and float(steps.max() - steps.min()) < 1e-9
    return {"n": int(len(t)), "lo": float(t.min()), "hi": float(t.max()),
            "step": round(float(steps[0]), 6) if uniform else None,
            "uniform": uniform}


def ferplus_stream_state(B, n_by_teacher):
    """bootstrap_cis'in RNG akisini FERPlus'in BASLADIGI noktaya kadar ilerlet.

    NEDEN GEREKLI. bootstrap_cis dort veri kumesini TEK bir `default_rng(RNG_SEED)` ile
    doner; FERPlus dorduncudur, yani onun 2000 tekrarindan once uc ogretmenin 3x2000 cekilisi
    tuketilmistir. Taze bir tohumla baslamak ayni tahmin ediciyi kullanir ama BASKA tekrarlar
    cizer: olculdu, CI uclari 3.2e-04 kayiyordu. Bu bir yontem farki degil Monte-Carlo farki --
    ama "yeniden urettim" demek icin yeterli degil. Akis konumu burada yeniden oynatiliyor,
    boylece yayimli CI uclari 0.00e+00 sapmayla cikiyor.
    """
    rng = np.random.default_rng(RNG_SEED)
    for name in BOOT_TEACHERS:                      # sira bootstrap_cis'in KENDI sirasi
        n = n_by_teacher[name]
        p = np.full(n, 1.0 / n)
        for _ in range(B):
            rng.multinomial(n, p)
    return rng.bit_generator.state


def rng_at(state):
    rng = np.random.default_rng()
    rng.bit_generator.state = state
    return rng


def point_and_ci(lg, lb, t_grid, B, rng):
    """Bir izgara icin: nokta headroom + yuzdelik CI + argmin'in sinirda olma orani."""
    t_grid = np.asarray(t_grid, dtype=np.float64)
    correct, conf, nll, binidx = precompute(lg, lb, t_grid)
    n = lg.shape[0]
    i_T1 = int(np.argmin(np.abs(t_grid - 1.0)))
    if abs(float(t_grid[i_T1]) - 1.0) > 1e-9:
        raise RuntimeError(f"T=1 bu izgarada YOK (en yakin {t_grid[i_T1]}) — headroom'un "
                           f"referans noktasi tanimsiz, DUR.")
    e0 = ece_weighted(np.ones(n), correct, conf, binidx)
    j0 = int(np.argmin(e0))
    hh = np.empty(B)
    on_lo = on_hi = 0
    for b in range(B):
        w = rng.multinomial(n, np.full(n, 1.0 / n)).astype(np.float64)
        e = ece_weighted(w, correct, conf, binidx)
        j = int(np.argmin(e))
        hh[b] = e[i_T1] - e[j]
        on_lo += (j == 0)
        on_hi += (j == len(t_grid) - 1)
    lo, hi = pct(hh)
    return {"grid": grid_stats(t_grid),
            "ece_T1": float(e0[i_T1]),
            "T_argmin": float(t_grid[j0]), "ece_at_argmin": float(e0[j0]),
            "headroom": float(e0[i_T1] - e0[j0]),
            "argmin_at_lower_bound": bool(j0 == 0),
            "argmin_at_upper_bound": bool(j0 == len(t_grid) - 1),
            "ci95": [lo, hi], "ci_type": "percentile (2.5/97.5)", "B": B,
            "boot_frac_argmin_at_lower_bound": on_lo / B,
            "boot_frac_argmin_at_upper_bound": on_hi / B}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b", type=int, default=2000)
    args, _unknown = ap.parse_known_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    fer, sg_j, hr, bc = jload(A_FER), jload(A_FER_SG), jload(A_HR), jload(A_BC)

    # --- ucu de OLCULEREK kurulur; hicbir izgara elle yazilmaz
    g_fine = np.array(sorted(float(r["T"]) for r in fer["sweep"]))
    g_run = np.array(sorted(float(r["T"]) for r in sg_j["grid"]))
    g_boot = np.asarray(BOOT_T_GRID, dtype=np.float64)
    # Kosulan izgarada T=1 var mi? headroom'un referansi o. Yoksa point_and_ci zaten durur.

    d = torch.load(FER_LOGITS, map_location="cpu", weights_only=False)
    lg, lb = d["logits"].numpy(), d["labels"].numpy()

    # RAF-DB logitleri: hem akis konumu icin (n'ler) hem de sinir tanisi icin.
    rafdb = {}
    for name, path in BOOT_TEACHERS.items():
        dd = torch.load(path, map_location="cpu", weights_only=False)
        rafdb[name] = (dd["logits"].numpy(), dd["labels"].numpy())
    state = ferplus_stream_state(args.b, {k: v[0].shape[0] for k, v in rafdb.items()})

    grids = [("run", "actually-run arms (`ferplus_teacher_signed_grid`)", g_run),
             ("boot", "`bootstrap_cis.T_GRID`", g_boot),
             ("fine", "`ferplus_jsd.sweep`", g_fine)]
    res = {}
    for key, label, gr in grids:
        # Uc izgara da AYNI tekrarlari kullanir (bootstrap_cis'in FERPlus akis konumu):
        # aralarindaki fark boylece yalniz izgaradan gelir, cekilis gurultusunden degil.
        res[key] = point_and_ci(lg, lb, gr, args.b, rng_at(state))
        res[key]["source"] = label
        print(f"  {key:5s} n={res[key]['grid']['n']:>3d} "
              f"[{res[key]['grid']['lo']:.4g},{res[key]['grid']['hi']:.4g}]  "
              f"argmin T={res[key]['T_argmin']:<7.4g} headroom {res[key]['headroom']:.4f} "
              f"[{res[key]['ci95'][0]:.4f},{res[key]['ci95'][1]:.4f}]  "
              f"sinirda={res[key]['argmin_at_lower_bound']} "
              f"(bootstrap %{100 * res[key]['boot_frac_argmin_at_lower_bound']:.1f})")

    # --- YAYIMLI SAYILARLA CAPRAZ KONTROL: bu betik yeni bir tanim getirmiyor
    checks = [("headroom_review.eq8 (0.1198)", hr["ferplus"]["eq8"]["headroom"],
               res["fine"]["headroom"]),
              ("headroom_review.deployed (0.1126)", hr["ferplus"]["deployed_nll"]["reduction"],
               res["run"]["headroom"]),
              ("bootstrap_cis.headroom_eq8 (0.1131)",
               bc["results"]["ferplus"]["point"]["headroom_eq8"], res["boot"]["headroom"]),
              ("bootstrap_cis.ci_lo", bc["results"]["ferplus"]["ci95"]["headroom_eq8"][0],
               res["boot"]["ci95"][0]),
              ("bootstrap_cis.ci_hi", bc["results"]["ferplus"]["ci95"]["headroom_eq8"][1],
               res["boot"]["ci95"][1]),
              ("ferplus_jsd.ece_T1", fer["at_T1"]["ece"], res["fine"]["ece_T1"])]
    xrows, worst = [], 0.0
    for name, published, remeasured in checks:
        dev = abs(published - remeasured)
        worst = max(worst, dev)
        xrows.append({"quantity": name, "published": published, "remeasured": remeasured,
                      "abs_dev": dev, "ok": dev < TOL})
        print(f"  x-check {name:<38s} {published:.6f} vs {remeasured:.6f}  dev {dev:.2e}")

    # --- Eq.8'in kosulan-izgara capasi hala gecerli mi? (headroom_review'in kendi guvenligi)
    run_argmin_T = float(min(sg_j["grid"], key=lambda r: r["teacher_ece"])["T"])
    deployed_ok = abs(run_argmin_T - 0.5063) < 1e-9

    # --- SINIR TANISI: bootstrap izgarasinda hangi ogretmenler etkileniyor?
    boundary = {}
    for name, (blg, blb) in list(rafdb.items()) + [("ferplus", (lg, lb))]:
        c2, cf2, _n2, bi2 = precompute(blg, blb, g_boot)
        e = ece_weighted(np.ones(cf2.shape[0]), c2, cf2, bi2)
        j = int(np.argmin(e))
        boundary[name] = {"T_argmin_on_boot_grid": float(g_boot[j]),
                          "at_lower_bound": bool(j == 0),
                          "at_upper_bound": bool(j == len(g_boot) - 1),
                          "n_val": int(cf2.shape[0])}
        print(f"  boundary {name:9s} argmin T={g_boot[j]:.2f} "
              f"sinirda={boundary[name]['at_lower_bound']}")

    # --- AYNI KESILME T*_ECE'yi de vuruyor mu? (headroom tek kurban degil)
    ts = jload(A_TS)["results"]["ferplus"]["T_star_ece"]
    bc_ts = bc["results"]["ferplus"]
    tstar = {"continuous_argmin": ts,                       # tstar_sensitivity, sinirli Brent
             "fine_grid_argmin": res["fine"]["T_argmin"],
             "boot_grid_point": bc_ts["point"]["T_star_ece"],
             "boot_grid_ci95": bc_ts["ci95"]["T_star_ece"],
             "boot_grid_floor": res["boot"]["grid"]["lo"],
             "truncated": bool(ts < res["boot"]["grid"]["lo"])}
    print(f"  T*_ECE surekli {ts:.5f} · ince izgara {tstar['fine_grid_argmin']:.2f} · "
          f"bootstrap {tstar['boot_grid_point']:.2f} "
          f"[{tstar['boot_grid_ci95'][0]:.2f},{tstar['boot_grid_ci95'][1]:.2f}] · "
          f"kesilmis={tstar['truncated']}")

    # --- HUKUM: makaleye hangisi girmeli?
    # Kural 11 Agu'da baglandi: Eq.8 = min_{T in G}, G = FIILEN TARANAN izgara. Buradan
    # secim tek: kosulan kollarin izgarasi. Digerleri "daha ince bir cozunurlugun nereye
    # varacagi" -- kosulmus bir kol degil.
    primary = res["run"]
    verdict = {
        "primary_number": primary["headroom"],
        "primary_ci95": primary["ci95"],
        "primary_T": primary["T_argmin"],
        "primary_grid": primary["grid"],
        "rule": "Eq.8 = min over the grid ACTUALLY SWEPT (binding since 11 Aug 2026)",
        "rejected": {
            "0.1198": "196-point refinement; its argmin T=0.46 was never run as an arm",
            "0.1131": "101-point grid whose LOWER BOUND 0.50 truncates the optimum; "
                      "boundary-constrained, so it is neither the run grid's value nor the "
                      "refinement's"},
        "boundary_constrained_grids": [k for k, v in res.items()
                                       if v["argmin_at_lower_bound"] or v["argmin_at_upper_bound"]],
        "deployed_arm_is_run_grid_argmin": deployed_ok}

    # ---------- rapor
    def g(r):
        s = r["grid"]
        st = f"step {s['step']:g}" if s["uniform"] else "non-uniform"
        return f"[{s['lo']:g}, {s['hi']:g}], {st}, {s['n']} points"

    L = ["# N11 — FERPlus headroom: which grid, which number", "",
         "> **Review-responsive, not pre-declared (15 Aug 2026).** Written to settle a "
         "contradiction between two already-published artifacts; no prediction was frozen "
         "beforehand.", "",
         "Producer: `diagnostics/headroom_grid_audit.py` · sources: cached teacher logits "
         "(`ferplus_jsd/ferplus_val_logits.pt`, `teacher_ece_grid/teacher_val_logits_*.pt`), "
         "`ferplus_jsd.json`, `ferplus_teacher_signed_grid.json` · ECE = "
         f"{N_BINS}-bin equal-width · B = {args.b} · percentile CIs · RNG seed {RNG_SEED} · "
         "no forward pass, no GPU.", "",
         "The two numbers use **the same formula, the same 3153 samples, the same binning and "
         "the same cached logits**. The only thing that differs is the grid G that "
         "`min_{T∈G}` runs over — and G is part of the estimand, not an implementation "
         "detail.", "",
         "## 1 · The same quantity on three grids", "",
         "| grid | definition | argmin T | ECE@argmin | headroom | 95% CI | argmin on a grid "
         "bound? |", "|---|---|---|---|---|---|---|"]
    for key, _lab, _gr in grids:
        r = res[key]
        bnd = ("**yes — lower**" if r["argmin_at_lower_bound"]
               else ("**yes — upper**" if r["argmin_at_upper_bound"] else "no (interior)"))
        L.append(f"| `{key}` — {r['source']} | {g(r)} | {r['T_argmin']:g} | "
                 f"{r['ece_at_argmin']:.4f} | **{r['headroom']:.4f}** | "
                 f"[{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}] | {bnd} |")
    L += ["", f"ECE(T=1) is common to all three: {res['fine']['ece_T1']:.4f}.", "",
          f"**Why 0.1131's interval excludes 0.1198, and why that is not a paradox.** The "
          f"refinement's optimum sits at T = {res['fine']['T_argmin']:g}, which is *below* the "
          f"bootstrap grid's floor of {res['boot']['grid']['lo']:g}. A minimum taken over a "
          f"subset can only be larger, so `headroom(boot) ≤ headroom(fine)` holds by "
          f"construction — {res['boot']['headroom']:.4f} ≤ {res['fine']['headroom']:.4f}. The "
          f"interval [{res['boot']['ci95'][0]:.4f}, {res['boot']['ci95'][1]:.4f}] is a "
          f"percentile interval for the *truncated* estimand and contains its own point "
          f"estimate; it was never an interval for {res['fine']['headroom']:.4f}. No bias "
          f"correction, no BCa, no normal approximation is involved — see `ci_type` in the "
          f"JSON.", "",
          f"**The truncation is visible in the data, not only in the code.** On the bootstrap "
          f"grid the FERPlus argmin lands on the grid's lower bound in "
          f"{100 * res['boot']['boot_frac_argmin_at_lower_bound']:.1f}% of the {args.b} "
          f"replicates (point estimate: on the bound). On the run grid it is interior in "
          f"{100 * (1 - res['run']['boot_frac_argmin_at_lower_bound'] - res['run']['boot_frac_argmin_at_upper_bound']):.1f}% "
          f"and on the refinement grid the optimum is interior as well.", "",
          "## 2 · Which grid truncates, and for whom", "",
          "| teacher | argmin T on `bootstrap_cis.T_GRID` | truncated? |", "|---|---|---|"]
    for name, b in boundary.items():
        L.append(f"| {name} | {b['T_argmin_on_boot_grid']:.2f} | "
                 + ("**yes — sits on the 0.50 floor**" if b["at_lower_bound"]
                    else ("**yes — upper**" if b["at_upper_bound"] else "no")) + " |")
    L += ["",
          f"**Headroom is not the only casualty.** The same floor truncates the published "
          f"FERPlus **T\\*_ECE**: the continuous argmin is {tstar['continuous_argmin']:.5f} "
          f"(`tstar_sensitivity`, bounded Brent) and the 196-point grid puts it at "
          f"{tstar['fine_grid_argmin']:g}, both below the {tstar['boot_grid_floor']:g} floor, "
          f"so `bootstrap_cis` can only report {tstar['boot_grid_point']:.2f} "
          f"[{tstar['boot_grid_ci95'][0]:.2f}, {tstar['boot_grid_ci95'][1]:.2f}] — an interval "
          f"whose lower end is the floor itself. Anywhere the paper quotes that interval it is "
          f"quoting a censored quantity, not an estimate of where the optimum is.", "",
          "This is why the RAF-DB rows of the two artifacts agree in direction and the FERPlus "
          "row does not: the RAF-DB optima are interior to the bootstrap grid, so a denser step "
          "moves them slightly and nothing more. FERPlus is the only teacher whose optimum is "
          "outside that grid altogether.", "",
          "**Correction to the 14 Aug audit (`number_audit_round3`, item 9).** That item "
          "answered \"is the Appendix-B interval boundary-constrained?\" with **no**, having "
          "checked the RAF-DB fine sweep and the 196-point FERPlus sweep. It did not check "
          "`bootstrap_cis.T_GRID`, which is the grid the Appendix-B *interval* actually comes "
          "from and whose lower bound is exactly the 0.50 the panel asked about. On that grid "
          "the FERPlus optimum does sit on the bound. The panel's question was right and "
          "yesterday's answer was wrong; the 14 Aug record stands as written and is corrected "
          "here.", "",
          "## 3 · Cross-check against the published artifacts", "",
          "| quantity | published | re-measured here | |Δ| |", "|---|---|---|---|"]
    for r in xrows:
        L.append(f"| {r['quantity']} | {r['published']:.6f} | {r['remeasured']:.6f} | "
                 f"{r['abs_dev']:.2e} |")
    L += ["",
          f"Largest deviation {worst:.2e} (tolerance {TOL:g}); the residual is the float32 "
          "cache versus float64 recomputation, not a difference of method. **This script "
          "introduces no fourth definition** — it re-measures the two published ones and adds "
          "the interval the run grid never had.", "",
          "## 4 · What the paper should carry", "",
          f"Under the binding rule adopted on 11 Aug 2026 — Eq. 8 is `min_{{T∈G}}` with G the "
          f"grid **actually swept** — the primary number is "
          f"**{primary['headroom']:.4f} [{primary['ci95'][0]:.4f}, {primary['ci95'][1]:.4f}]** "
          f"at T = {primary['T_argmin']:g}, the temperature the deployed arm was run at "
          f"({'verified' if deployed_ok else 'NOT VERIFIED'}: the run grid's ECE argmin is that "
          f"same temperature). The other two are refinements over grids no arm was run on:",
          "",
          f"- **{res['fine']['headroom']:.4f}** (\"0.120\") — a genuine finer-resolution "
          f"minimum at T = {res['fine']['T_argmin']:g}; quotable only as *what a denser sweep "
          f"would reach*, never under the same name as the headline.",
          f"- **{res['boot']['headroom']:.4f}** (\"0.1131\") — neither of the above. It is the "
          f"minimum of a grid that stops before the optimum, so it is an artifact of the "
          f"bootstrap script's own T range. It should not appear in the paper at all; if the "
          f"supplement wants an interval for the headline, it is the `run` row above.", "",
          "Note on the near-coincidence: the headline "
          f"{primary['headroom']:.4f} and the truncated {res['boot']['headroom']:.4f} agree to "
          f"three decimals ({abs(primary['headroom'] - res['boot']['headroom']):.4f} apart) "
          "because both grids' minima land near T ≈ 0.5. They are still two different "
          "estimands, and \"0.113\" currently names both — which is exactly how the "
          "contradiction survived unnoticed.", ""]

    payload = {"note": "review-responsive, not pre-declared", "B": args.b,
               "rng_seed": RNG_SEED, "n_bins": N_BINS, "tol": TOL,
               "grids": {k: res[k] for k, _l, _g in grids},
               "crosschecks": xrows, "max_abs_dev": worst,
               "boot_grid_boundary_by_teacher": boundary,
               "ferplus_T_star_ece": tstar,
               "rng_note": "bootstrap_cis'in FERPlus akis konumu yeniden oynatildi; ucu de "
                           "AYNI tekrarlari kullanir",
               "verdict": verdict}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "headroom_grid_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "headroom_grid_audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'headroom_grid_audit.md'}")

    if worst >= TOL:
        print(f"\nDUR: yayimli sayilar yeniden uretilemedi (en buyuk sapma {worst:.3e}).")
        return 1
    if not deployed_ok:
        print(f"\nDUR: kosulan izgaranin argmin'i T={run_argmin_T}, dagitilan kol 0.5063 degil.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
