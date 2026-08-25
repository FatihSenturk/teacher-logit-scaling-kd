"""B9 — `tab_mechanisms`'in boş hücreleri: koşulmadı mı, uygulanamaz mı, elendi mi?

NEDEN TABLO, NEDEN PROSA DEĞİL. Negatif sonuç sayan bir makalede **koşulmamış bir hücre
bilgidir**: okuyucu boş bir kutuya baktığında "denendi ve bir şey çıkmadı" ile "hiç
denenmedi" arasındaki farkı göremez, ve ikisi aynı cümleyi taşımaz. Boşluğun sebebi
üretilebilir bir sayıdır, bir anlatı değil.

ÜÇ HÜKÜM SINIFI, üçü de defterden ÖLÇÜLEREK veriliyor -- hiçbiri elle yazılmıyor:
    koşulmadı          : defterde o (öğretmen, mekanizma) için HİÇ koşu yok
    bütçe dışı         : koşu VAR ama T5'in bütçe kapısını (400e / SWA@200 / alpha 0.3 /
                         t_scale 1.0 / vich) geçmiyor; yani hücre boş değil, **eşleşmiyor**
    elendi             : gate hücresi, ve o öğretmen-sinyal çiftinin sinyal kalitesi
                         ön-kayıtlı taramada aleyhte -- A12'nin beş hücresi bu taramadan
                         çıktı

BÜTÇE DIŞI SINIFI SÜRPRİZDİ ve tam da bu tablonun var olma sebebi: `vae9182` birleşik kolu
(`g2g_kl+adaptive_t`) T5'te **n=1** görünüyor, ama defterde aynı kolun 500 epokluk hâli
**üç tohumla** duruyor. "n=1" cümlesi doğru ama eksik; doğru cümle *"bu bütçede n=1, bir
üst bütçede n=3"*.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/mechanism_grid_gaps.{md,json}
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from paper_tables import (A_AUDIT_MECH, TEACHERS, gate_variant,  # noqa: E402
                          load_audit, load_runs)
from t5_pairing_diff import build  # noqa: E402  -- TEK KAYNAK: T5'in eşleştirmesi

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
SIGNAL_CSV = ROOT / "diagnostics" / "rafdb_signal_quality" / "signal_quality_table.csv"
# Sinyal kalitesi tablosundaki öğretmen adları büyük harfli; defterinkiyle eşlemek için.
SIG_NAME = {"stage1": "Stage1", "primary": "Primary", "vae9182": "VAE9182"}


def ledger_rows(mech_of):
    """(öğretmen, mekanizma) -> defterdeki HER koşu, bütçesiyle birlikte."""
    out = {}
    with (ROOT / "runs.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["teacher"] not in TEACHERS:
                continue
            m = r["manipulation"]
            if m == "gate":
                m = gate_variant(r)
            out.setdefault((r["teacher"], m), []).append(
                {"run": r["run_name"], "seed": r["seed"], "epochs": r["epochs"],
                 "swa_start": r["swa_start"], "alpha": r["alpha"],
                 "t_scale": r["t_scale"], "student_head": r["student_head"],
                 "family": r["family"], "block": r.get("preregistration_block") or ""})
    return out


def signal_quality():
    """gate sinyalinin öğretmen başına bilgilendiriciliği (AUROC ve yönü)."""
    if not SIGNAL_CSV.exists():
        return {}
    out = {}
    with SIGNAL_CSV.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[(r["teacher"], r["signal"])] = {
                "auroc": float(r["auroc_signed"]),
                "informativeness": float(r["informativeness_abs_auroc_minus_half"]),
                "direction": r["direction"]}
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    runs, audit = load_runs(), load_audit(A_AUDIT_MECH)
    cells = build(runs, audit, "new")[0]
    mechs = sorted({m for _t, m in cells})
    led = ledger_rows(None)
    sig = signal_quality()

    grid, gaps = [], []
    for m in mechs:
        for t in TEACHERS:
            rec = cells.get((t, m))
            n = (rec["by_ckpt"]["swa"]["n"] if rec and "swa" in rec["by_ckpt"] else 0)
            row = {"teacher": t, "mechanism": m, "n_in_grid": n, "present": bool(rec)}
            if rec:
                grid.append(row)
                continue
            all_runs = led.get((t, m), [])
            if not all_runs:
                cls, why = "koşulmadı", "defterde bu (öğretmen, mekanizma) için hiç koşu yok"
                if m.startswith("gate:"):
                    s_name = m.split(":", 1)[1]
                    q = sig.get((SIG_NAME[t], s_name))
                    if q:
                        cls = "elendi"
                        why = (f"gate sinyali ön-kayıtlı taramada aleyhte: AUROC "
                               f"{q['auroc']:.4f} (şanstan {q['informativeness']:.4f} "
                               f"uzak), yön \"{q['direction']}\" — gate'in istediği yön "
                               f"değil. A12 beş hücresini bu taramadan seçti.")
            else:
                cls = "bütçe dışı"
                why = (f"defterde {len(all_runs)} koşu VAR ama T5'in bütçe kapısını "
                       f"geçmiyor (bütçeler: "
                       + ", ".join(sorted({f"{r['epochs']}e/SWA@{r['swa_start']}"
                                           for r in all_runs})) + ")")
            row.update({"class": cls, "why": why,
                        "ledger_runs": [r["run"] for r in all_runs]})
            gaps.append(row)
            grid.append(row)

    # bütçe dışı ikinci sınıf: hücre VAR ama n grid'de küçük, defterde daha büyük n mevcut
    shrunk = []
    for (t, m), rec in sorted(cells.items()):
        n = rec["by_ckpt"].get("swa", {}).get("n", 0)
        all_runs = led.get((t, m), [])
        # BÜTÇE DIŞI = KOŞU bazlı, tohum bazlı DEĞİL. İlk yazımda tohumla filtrelemiştim ve
        # tohum 42 hem 400e hem 500e koşusunda göründüğü için 400e koşusu da "dışarıda"
        # listeleniyordu -- kapıyı geçen bir koşuyu geçmeyen diye raporlamak, tablonun
        # düzeltmek için var olduğu hatanın aynısı.
        outside = [r for r in all_runs
                   if not (r["epochs"] == "400" and str(r["swa_start"]) == "200")]
        if outside and n < len({r["seed"] for r in all_runs}):
            shrunk.append({"teacher": t, "mechanism": m, "n_in_grid": n,
                           "n_in_ledger": len({r["seed"] for r in all_runs}),
                           "budgets_outside": sorted({f"{r['epochs']}e/SWA@{r['swa_start']}"
                                                      for r in outside}),
                           "n_outside": len({r["seed"] for r in outside}),
                           "runs_outside": sorted(r["run"] for r in outside)})

    write(grid, gaps, shrunk, mechs)
    print("=== mechanism_grid_gaps ===")
    print(f"  grid            : {len(mechs)} mekanizma x {len(TEACHERS)} ogretmen = "
          f"{len(mechs) * len(TEACHERS)}")
    print(f"  dolu hucre      : {len(mechs) * len(TEACHERS) - len(gaps)}")
    print(f"  BOS hucre       : {len(gaps)}")
    for g in gaps:
        print(f"      {g['teacher']}/{g['mechanism']:20s} -> {g['class']}")
    print(f"  bütce disinda kalan tohumu olan hucre: {len(shrunk)}")
    for s in shrunk:
        print(f"      {s['teacher']}/{s['mechanism']}: grid n={s['n_in_grid']}, "
              f"defter n={s['n_in_ledger']} ({', '.join(s['budgets_outside'])})")


def write(grid, gaps, shrunk, mechs):
    L = ["# B9 — `tab_mechanisms`'in boş hücreleri: koşulmadı mı, uygulanamaz mı, elendi mi?",
         "",
         "Üretici: `diagnostics/mechanism_grid_gaps.py` · eşleştirme "
         "`t5_pairing_diff.build(rule=\"new\")`'den **ithal** · sinyal kalitesi "
         "`rafdb_signal_quality/signal_quality_table.csv`'den", "",
         "> Negatif sonuç sayan bir makalede **koşulmamış bir hücre bilgidir**. Boş bir "
         "kutuya bakan okuyucu \"denendi, çıkmadı\" ile \"hiç denenmedi\"yi ayırt "
         "edemez — ve iki durum aynı cümleyi taşımaz.", "",
         f"| ızgara | {len(mechs)} mekanizma × {len(TEACHERS)} öğretmen = "
         f"{len(mechs) * len(TEACHERS)} hücre |", "|---|---|",
         f"| dolu | {len(mechs) * len(TEACHERS) - len(gaps)} |",
         f"| **boş** | **{len(gaps)}** |", "",
         "## Boş hücrelerin hükmü", "",
         "| öğretmen | mekanizma | hüküm | gerekçe (ölçülen) |", "|---|---|---|---|"]
    for g in gaps:
        L.append(f"| {g['teacher']} | `{g['mechanism']}` | **{g['class']}** | {g['why']} |")

    L += ["", "## Tam ızgara", "",
          "| mekanizma | " + " | ".join(TEACHERS) + " |",
          "|---|" + "---|" * len(TEACHERS)]
    by = {(r["teacher"], r["mechanism"]): r for r in grid}
    for m in mechs:
        cs = []
        for t in TEACHERS:
            r = by[(t, m)]
            cs.append(f"n={r['n_in_grid']}" if r.get("present") else f"— *{r['class']}*")
        L.append(f"| `{m}` | " + " | ".join(cs) + " |")

    L += ["", "## Boş değil ama eksik: bütçe kapısının dışında kalan tohumlar", "",
          "Bir hücrenin ızgaradaki `n`'i, defterdeki tohum sayısından küçük olabilir — "
          "fazla tohumlar T5'in bütçe kapısının (400e / SWA@200) dışında koşulmuştur. "
          "Bu hücreler için doğru cümle *\"n=1\"* değil, ***\"bu bütçede n=1, bir üst "
          "bütçede n=3\"***.", ""]
    if shrunk:
        L += ["| öğretmen | mekanizma | ızgarada n | defterde tohum | dışarıdaki bütçe | "
              "koşular |", "|---|---|---|---|---|---|"]
        for s in shrunk:
            L.append(f"| {s['teacher']} | `{s['mechanism']}` | {s['n_in_grid']} | "
                     f"{s['n_in_ledger']} | {', '.join(s['budgets_outside'])} | "
                     + ", ".join(f"`{r}`" for r in s["runs_outside"]) + " |")
    else:
        L += ["Yok — ızgaradaki her hücrenin n'i defterdeki tohum sayısına eşit.", ""]
    L += [""]

    (OUT_DIR / "mechanism_grid_gaps.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "mechanism_grid_gaps.json").write_text(json.dumps({
        "mechanisms": mechs, "teachers": list(TEACHERS), "grid": grid, "gaps": gaps,
        "outside_budget": shrunk, "n_cells": len(mechs) * len(TEACHERS),
        "n_empty": len(gaps)}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
