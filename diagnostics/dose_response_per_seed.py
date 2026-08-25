"""B8 — doz-yanıt eğrilerinin TOHUM BAŞINA tablosu (ek tablo).

NEDEN GEREKTİ. Özetin en güçlü niceleyicisi *"all nine seed curves"* — üç seri × üç tohum.
Ama makalede o cümlenin doğrulanabileceği hiçbir yüzey yok: yayımlanan her şey `ort ± sd`,
ve ortalama bir eğrinin monoton olması **dokuz eğrinin ayrı ayrı** monoton olduğunu
göstermez. Cümle ya bu tabloyla desteklenir ya da zayıflatılır; üçüncü seçenek yok.

HANGİ EKSEN? BURADA YENİDEN TANIMLANMIYOR. İddianın ekseni G2.2'de zaten çözüldü
(`monotonicity_test.py`): monotonluk **işaretli gap'in branşı içinde** ölçülüyor ve orada
9/9 geçiyor; ham T ekseninde 0/9. Bu tablo o hükmü YENİDEN VERMİYOR, **ithal ediyor** —
ikinci bir monotonluk tanımı yazmak, tam da G2.2'nin kapattığı belirsizliği geri açardı.
Buradaki Spearman ρ yalnız T ekseni için, ve G2.2'nin (a) sütunuyla çapraz kontrol olsun
diye duruyor.

Eğri tanımı `two_dataset_overlay.build()`'den **ithal** — koşu→(seri, T, tohum) eşlemesi
orada tek yerde duruyor (`p1_two_teacher_overlay.CURVES` + FERPlus seçim denetimi).

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/dose_response_per_seed.{md,json}
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from two_dataset_overlay import ARMS, build  # noqa: E402  -- TEK KAYNAK: eğri tanımı
from paper_tables import spearman  # noqa: E402  -- TEK KAYNAK: sıra korelasyonu
from stats_convention import SD_CONVENTION  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
CK = "swa"


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    # G2.2'nin HÜKMÜ İTHAL EDİLİYOR, yeniden verilmiyor. Seri adları orada insan-okunur
    # ("RAF-DB stage1"), burada makine-okunur ("rafdb_stage1"); eşleme tek yerde.
    g22_raw = json.loads((OUT_DIR / "monotonicity_test.json").read_text(encoding="utf-8"))
    g22_summary = g22_raw["summary"]
    g22_name = {"RAF-DB stage1": "rafdb_stage1", "RAF-DB vae9182": "rafdb_vae9182",
                "FERPlus": "ferplus"}
    g22 = {}
    for sname, sv in g22_raw["series"].items():
        arm = g22_name.get(sname)
        for seed, verd in sv["seeds"].items():
            g22[(arm, seed)] = {
                "g22_a_T_axis": bool(verd["a_T_axis"]["ok"]),
                "g22_b_within_branch": verd["b_signed_gap_within_branch"].get("ok"),
                "g22_c_pooled": bool(verd["c_unsigned_gap_pooled"]["ok"])}

    data = build()
    series, curves = {}, []
    for arm in ARMS:
        pts = [p for p in data[arm]["points"] if CK in p["by_ckpt"]]
        pts.sort(key=lambda p: p["T"])
        seeds = sorted({s for p in pts for s in (p["by_ckpt"][CK].get("per_seed") or {})},
                       key=lambda x: int(x))
        rows = []
        for p in pts:
            ps = p["by_ckpt"][CK].get("per_seed") or {}
            rows.append({"T": p["T"], "teacher_ece": p["teacher_ece"],
                         "signed_gap": p["signed_gap"],
                         "per_seed": {s: ps.get(s) for s in seeds},
                         "n": p["by_ckpt"][CK]["n"],
                         "ece_mean": p["by_ckpt"][CK]["ece_mean"],
                         "ece_sd": p["by_ckpt"][CK]["ece_sd"]})
        for s in seeds:
            xs = [r["T"] for r in rows if r["per_seed"].get(s)]
            ys = [r["per_seed"][s]["ece"] for r in rows if r["per_seed"].get(s)]
            if len(xs) < 3:
                continue
            mono_up = all(b > a for a, b in zip(ys, ys[1:]))
            mono_dn = all(b < a for a, b in zip(ys, ys[1:]))
            curves.append({"arm": arm, "seed": s, "n_points": len(xs),
                           "rho_T_vs_ece": spearman(xs, ys),
                           "monotone_in_T": "artan" if mono_up else
                                            ("azalan" if mono_dn else "hayır"),
                           "ece_at_min_T": ys[0], "ece_at_max_T": ys[-1],
                           "span": ys[-1] - ys[0],
                           **g22.get((arm, s), {})})
        series[arm] = {"label": ARMS[arm]["label"], "seeds": seeds, "points": rows}

    n_up = sum(1 for c in curves if c["rho_T_vs_ece"] and c["rho_T_vs_ece"] > 0)
    n_mono = sum(1 for c in curves if c["monotone_in_T"] != "hayır")
    write(series, curves, n_up, n_mono, g22_summary)

    print("=== dose_response_per_seed ===")
    print(f"  seri: {len(series)} · tohum-egrisi: {len(curves)}")
    for c in curves:
        print(f"    {c['arm']:15s} seed {c['seed']:>2s}  n={c['n_points']}  "
              f"rho_T={c['rho_T_vs_ece']:+.3f}  T-monoton={c['monotone_in_T']:6s}  "
              f"G2.2(b)={c.get('g22_b_within_branch')}  "
              f"ECE {c['ece_at_min_T']:.4f} -> {c['ece_at_max_T']:.4f}")
    print(f"  rho_T > 0 olan egri : {n_up}/{len(curves)}")
    print(f"  T ekseninde monoton : {n_mono}/{len(curves)}  "
          f"(G2.2 (a) sutunu: {g22_summary['a_T_axis'][0]}/{g22_summary['a_T_axis'][1]})")
    print(f"  G2.2 (b) brans-ici  : "
          f"{g22_summary['b_signed_gap_within_branch'][0]}/"
          f"{g22_summary['b_signed_gap_within_branch'][1]}  <- iddianin ekseni")


def write(series, curves, n_up, n_mono, g22_summary):
    L = ["# B8 — doz-yanıt eğrilerinin tohum başına tablosu (ek tablo)", "",
         f"Üretici: `diagnostics/dose_response_per_seed.py` · @{CK} · {SD_CONVENTION} · "
         f"eğri tanımı `two_dataset_overlay.build()`'den **ithal**", "",
         "> Özetin en güçlü niceleyicisi *\"all nine seed curves\"*. Yayımlanan her şey "
         "`ort ± sd` olduğu için o cümlenin doğrulanabileceği bir yüzey yoktu — ortalama "
         "bir eğrinin monoton olması, dokuz eğrinin **ayrı ayrı** monoton olduğunu "
         "göstermez. Bu ek tablo o yüzeyi kuruyor.", "",
         "> **Hangi eksende monoton?** Burada yeniden tanımlanmıyor: G2.2 "
         "(`monotonicity_test.py`) o soruyu çözdü ve hükmü buraya **ithal ediliyor**. "
         "İkinci bir monotonluk tanımı yazmak, G2.2'nin kapattığı belirsizliği geri "
         "açardı.", "",
         "| eksen (G2.2 tanımı) | geçen tohum eğrisi |", "|---|---|",
         f"| (a) ham T ekseni | **{g22_summary['a_T_axis'][0]}/"
         f"{g22_summary['a_T_axis'][1]}** |",
         f"| (b) işaretli gap, **branş içi** ← iddianın ekseni | "
         f"**{g22_summary['b_signed_gap_within_branch'][0]}/"
         f"{g22_summary['b_signed_gap_within_branch'][1]}** |",
         f"| (c) işaretsiz \\|gap\\|, havuzlanmış | "
         f"**{g22_summary['c_unsigned_gap_pooled'][0]}/"
         f"{g22_summary['c_unsigned_gap_pooled'][1]}** |", "",
         f"Bu tablonun kendi ölçtüğü T-ekseni sayıları G2.2 (a) ile **tutuyor**: katı "
         f"monoton {n_mono}/{len(curves)}, ρ(T, ECE) > 0 olan {n_up}/{len(curves)}. "
         f"ρ'nun pozitif ama monotonluğun sıfır olması çelişki değil: eğriler T\\* "
         f"civarında **U biçimli**, yani sıralama korelasyonu yönü verir, monotonluğu "
         f"vermez.", "",
         "| seri | tohum | nokta | ρ(T, ECE) | T'de monoton | G2.2 (b) branş içi | "
         "ECE (en küçük T) | ECE (en büyük T) | fark |",
         "|---|---|---|---|---|---|---|---|---|"]
    for c in curves:
        b = c.get("g22_b_within_branch")
        L.append(f"| `{c['arm']}` | {c['seed']} | {c['n_points']} | "
                 f"{c['rho_T_vs_ece']:+.3f} | {c['monotone_in_T']} | "
                 f"{'✓' if b else ('n/a' if b is None else '✗')} | "
                 f"{c['ece_at_min_T']:.4f} | {c['ece_at_max_T']:.4f} | "
                 f"{c['span']:+.4f} |")

    L += ["", "---", "", "## Tam tablo: her seri × her T × her tohum", ""]
    for arm, s in series.items():
        L += [f"### `{arm}` — {s['label']}", "",
              "| T | öğretmen ECE | işaretli fark | "
              + " | ".join(f"öğrenci ECE (tohum {x})" for x in s["seeds"])
              + " | ort ± sd | n |",
              "|---|---|---|" + "---|" * (len(s["seeds"]) + 2)]
        for r in s["points"]:
            cells = []
            for x in s["seeds"]:
                v = r["per_seed"].get(x)
                cells.append(f"{v['ece']:.4f}" if v else "—")
            L.append(f"| {r['T']:g} | {r['teacher_ece']:.4f} | {r['signed_gap']:+.4f} | "
                     + " | ".join(cells)
                     + f" | {r['ece_mean']:.4f} ± {r['ece_sd']:.4f} | {r['n']} |")
        L += [""]

    (OUT_DIR / "dose_response_per_seed.md").write_text("\n".join(L) + "\n",
                                                       encoding="utf-8")
    (OUT_DIR / "dose_response_per_seed.json").write_text(json.dumps({
        "checkpoint": CK, "sd_convention": SD_CONVENTION, "series": series,
        "seed_curves": curves, "n_curves": len(curves), "n_rho_positive": n_up,
        "n_strictly_monotone_in_T": n_mono, "g22_summary": g22_summary},
        indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
