"""G2.2 — "monotone within all nine seed curves" iddiasının estimandı.

İTİRAZ (Round-2 panel, R1/P0 ve DA-C1): özet "student calibration error tracks the magnitude of
teacher miscalibration monotonically … monotone within all nine seed curves" diyor, ama
MONOTONLUĞUN HANGİ EKSENDE ölçüldüğü hiçbir yerde tanımlı değil. Tanımsız bir test, yanlışlanamaz
bir cümledir. DA ayrıca birincil tablodan branşlar-arası karşı örnekler gösteriyor.

NE ÜRETİLİYOR. Üç seri × 3 tohum = dokuz tohum eğrisi, ÜÇ FARKLI EKSENDE ayrı ayrı sınanır:

  (a) T ekseninde     : noktalar T'ye göre sıralanır; öğrenci ECE'si monoton mu (herhangi yönde)?
  (b) işaretli gap, BRANŞ-İÇİ : noktalar öğretmenin işaretli gap'inin İŞARETİNE göre iki branşa
                        ayrılır (aşırı-güven / aşırı-yumuşak); her branş kendi içinde |gap|
                        artışına göre sıralanır; öğrenci ECE'si ARTMAYAN olmamalı, yani
                        azalmayan mı (iddianın yönü)?
  (c) işaretsiz |gap| : bütün noktalar branş ayrımı OLMADAN |gap|'e göre sıralanır; aynı test.

(b) ile (c) arasındaki tek fark branş ayrımıdır — bu yüzden ikisi doğrudan karşılaştırılabilir
ve "havuzlama mı kırıyor?" sorusuna cevap verir.

TEK NOKTALI BRANŞ TUZAĞI. FERPlus'ın aşırı-güven branşında yalnız bir nokta var. "Bütün adımlar
azalmayan" testi boş adım listesinde vacuously TRUE döner; bu, sınanmamış bir hücreyi ✓ diye
raporlamak olurdu. Bu yüzden <2 noktalı branşlar açıkça `n/a` işaretlenir ve geçer sayılmaz.

VERİ (ikisi de mevcut artefakt, yeniden ölçüm yok):
  öğrenci ECE, tohum düzeyi -> paper_tables/robustness_metrics.json (metrik `ece_ew_15`,
                               makalenin 15-bin eşit-genişlik ECE'si)
  öğretmen işaretli gap      -> p1_dose_response/two_dataset_overlay.json (`signed_gap`)

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/monotonicity_test.{md,json}
Kullanım: python diagnostics/monotonicity_test.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION  # noqa: E402

A_ROB = ROOT / "diagnostics" / "paper_tables" / "robustness_metrics.json"
A_OV = ROOT / "diagnostics" / "p1_dose_response" / "two_dataset_overlay.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

METRIC = "ece_ew_15"
SEEDS = ("42", "1", "43")
# two_dataset_overlay arm adı -> robustness_metrics seri adı
ARM_TO_SERIES = {"rafdb_stage1": "RAF-DB stage1",
                 "rafdb_vae9182": "RAF-DB vae9182",
                 "ferplus": "FERPlus"}

HONESTY = (
    "> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel "
    "report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is "
    "unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts."
)


def non_decreasing(seq, labels):
    """Dizi azalmayan mı? Kırılma noktaları etiketleriyle döner."""
    breaks = [f"{labels[i]}→{labels[i + 1]} ({seq[i + 1] - seq[i]:+.4f})"
              for i in range(len(seq) - 1) if seq[i + 1] < seq[i]]
    return (not breaks), breaks


def monotone_any(seq, labels):
    """Herhangi bir yönde monoton mu? (a) ekseni için: iddia yön belirtmiyor."""
    inc, inc_b = non_decreasing(seq, labels)
    dec_seq = [-x for x in seq]
    dec, dec_b = non_decreasing(dec_seq, labels)
    if inc:
        return True, "non-decreasing", []
    if dec:
        return True, "non-increasing", []
    return False, "neither", inc_b if len(inc_b) <= len(dec_b) else dec_b


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rob = json.loads(A_ROB.read_text(encoding="utf-8"))
    ov = json.loads(A_OV.read_text(encoding="utf-8"))

    results, payload = {}, {}
    for arm, sname in ARM_TO_SERIES.items():
        s = rob["series"][sname]
        Ts = s["T"]
        pts = ov["arms"][arm]["points"]
        # T -> signed_gap, T eşlemesi toleranslı (float yazımı iki dosyada farklı olabilir)
        gap = {}
        for T in Ts:
            m = [p for p in pts if abs(p["T"] - T) < 1e-9]
            if len(m) != 1:
                raise RuntimeError(f"{arm}: T={T} için overlay'de {len(m)} eşleşme")
            gap[T] = m[0]["signed_gap"]

        by_seed = s["metrics"][METRIC]["by_seed"]
        results[sname], payload[sname] = {}, {"T": Ts, "signed_gap": {str(T): gap[T] for T in Ts},
                                              "seeds": {}}
        for sd in SEEDS:
            ece = by_seed[sd]                      # Ts ile aynı sırada
            cell = {}

            # (a) T ekseni
            ok_a, direction, br_a = monotone_any(ece, [f"T={T:g}" for T in Ts])
            cell["a_T_axis"] = {"ok": ok_a, "direction": direction, "breaks": br_a}

            # (b) işaretli gap, branş-içi
            branches = {}
            for sign, name in ((1, "over-confident (gap>0)"), (-1, "over-smooth (gap<0)")):
                idx = [i for i, T in enumerate(Ts) if (gap[T] > 0) == (sign > 0)]
                idx.sort(key=lambda i: abs(gap[Ts[i]]))
                if len(idx) < 2:
                    branches[name] = {"n_points": len(idx), "ok": None,
                                      "note": "n/a — fewer than 2 points, nothing to test",
                                      "breaks": []}
                    continue
                seq = [ece[i] for i in idx]
                lab = [f"|gap|={abs(gap[Ts[i]]):.4f}" for i in idx]
                ok, br = non_decreasing(seq, lab)
                branches[name] = {"n_points": len(idx), "ok": ok, "breaks": br,
                                  "sequence": seq, "labels": lab}
            tested = [b for b in branches.values() if b["ok"] is not None]
            cell["b_signed_gap_within_branch"] = {
                "branches": branches,
                "ok": (all(b["ok"] for b in tested) if tested else None),
                "n_branches_tested": len(tested)}

            # (c) işaretsiz |gap|, havuzlanmış
            idx = sorted(range(len(Ts)), key=lambda i: abs(gap[Ts[i]]))
            seq = [ece[i] for i in idx]
            lab = [f"|gap|={abs(gap[Ts[i]]):.4f}" for i in idx]
            ok_c, br_c = non_decreasing(seq, lab)
            cell["c_unsigned_gap_pooled"] = {"ok": ok_c, "breaks": br_c,
                                             "sequence": seq, "labels": lab}

            results[sname][sd] = cell
            payload[sname]["seeds"][sd] = cell

    # ---- özet sayımları
    def count(axis, key="ok"):
        n_ok = n_tot = 0
        for sname in results:
            for sd in SEEDS:
                v = results[sname][sd][axis][key]
                if v is None:
                    continue
                n_tot += 1
                n_ok += bool(v)
        return n_ok, n_tot

    a_ok, a_tot = count("a_T_axis")
    b_ok, b_tot = count("b_signed_gap_within_branch")
    c_ok, c_tot = count("c_unsigned_gap_pooled")

    L = ["# G2.2 — What axis is \"monotone within all nine seed curves\" measured on?", "",
         HONESTY, "",
         f"Producer: `diagnostics/monotonicity_test.py` · metric `{METRIC}` (the paper's 15-bin "
         f"equal-width ECE) · @swa · {SD_CONVENTION}", "",
         "The abstract's monotonicity claim never names its axis. This table runs the same nine "
         "seed curves on three candidate axes. (b) and (c) differ **only** by whether the two "
         "miscalibration branches are pooled, so the pair isolates what pooling does.", "",
         "| axis | definition | seed curves passing |", "|---|---|---|",
         f"| (a) T | points ordered by teacher pre-scaling T; monotone in either direction | "
         f"**{a_ok}/{a_tot}** |",
         f"| (b) signed gap, within branch | split by sign of teacher signed gap, then ordered by "
         f"\\|gap\\| within each branch; student ECE non-decreasing | **{b_ok}/{b_tot}** |",
         f"| (c) unsigned \\|gap\\|, pooled | all points ordered by \\|gap\\|, branches pooled; "
         f"student ECE non-decreasing | **{c_ok}/{c_tot}** |", ""]

    for sname in results:
        L += [f"## {sname}", "",
              "| seed | (a) T axis | (b) within branch | (c) pooled \\|gap\\| |",
              "|---|---|---|---|"]
        for sd in SEEDS:
            c = results[sname][sd]
            a = c["a_T_axis"]
            a_txt = "✓ " + a["direction"] if a["ok"] else "✗ " + (a["breaks"][0] if a["breaks"]
                                                                  else "not monotone")
            b = c["b_signed_gap_within_branch"]
            if b["ok"] is None:
                b_txt = "n/a"
            elif b["ok"]:
                b_txt = f"✓ ({b['n_branches_tested']} branch tested)"
            else:
                brs = [f"{k}: {'; '.join(v['breaks'])}" for k, v in b["branches"].items()
                       if v["ok"] is False]
                b_txt = "✗ " + " / ".join(brs)
            cc = c["c_unsigned_gap_pooled"]
            c_txt = "✓" if cc["ok"] else "✗ " + "; ".join(cc["breaks"])
            L.append(f"| {sd} | {a_txt} | {b_txt} | {c_txt} |")
        # branş kompozisyonu — tek noktalı branş burada görünsün
        any_seed = results[sname][SEEDS[0]]["b_signed_gap_within_branch"]["branches"]
        comp = ", ".join(f"{k}: {v['n_points']} point(s)"
                         + ("  **not testable**" if v["ok"] is None else "")
                         for k, v in any_seed.items())
        L += ["", f"Branch composition: {comp}.", ""]

    L += ["---", "",
          "Sources: `paper_tables/robustness_metrics.json` (seed-level student ECE) and "
          "`p1_dose_response/two_dataset_overlay.json` (teacher signed gap). No re-measurement: "
          "both are existing artifacts.", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "monotonicity_test.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "monotonicity_test.json").write_text(json.dumps(
        {"metric": METRIC, "note": "review-responsive, not pre-declared",
         "summary": {"a_T_axis": [a_ok, a_tot],
                     "b_signed_gap_within_branch": [b_ok, b_tot],
                     "c_unsigned_gap_pooled": [c_ok, c_tot]},
         "series": payload}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"(a) T ekseni              : {a_ok}/{a_tot}")
    print(f"(b) branş-içi işaretli gap: {b_ok}/{b_tot}")
    print(f"(c) havuzlanmış |gap|     : {c_ok}/{c_tot}")
    print(f"\nWrote {OUT_DIR / 'monotonicity_test.md'}")


if __name__ == "__main__":
    main()
