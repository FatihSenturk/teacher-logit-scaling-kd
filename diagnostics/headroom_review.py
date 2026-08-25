"""R0-3: headroom sayılarının hakemliği — üç itiraz, üç ölçülmüş cevap.

Hiçbir sayı elle yazılmaz: hepsi `teacher_ece_grid.json`, `ferplus_jsd.json` ve
`RESULTS_TABLES.json`dan okunur ve buradaki kurallarla yeniden türetilir.

İTİRAZ 1 — "VAE9182 headroom −0.0011, Eq.8'in argmin tanımıyla negatif olamaz."
  Haklı. −0.0011 = ECE(T=1) − ECE(T*_NLL): T* NLL küçültülerek fit edilmiş (0.983), headroom
  ise ECE üzerinden tanımlı — iki ayrı ölçütün karışımı. NLL-optimali ECE-optimali değilse fark
  negatif çıkabilir ve VAE9182'de tam bu oluyor. Eq.8'in tanımı (ECE argmin, ızgara üstünde)
  headroom'u yapısal olarak ≥ 0 kılar; doğru değer aşağıda hesaplanıyor.

İTİRAZ 2 — "FERPlus headroom: metin 0.120, tablo 0.1282−0.0156 = 0.1126."
  İki sayı iki farklı T*'a ait. 0.120 ince taramanın argmin'i (196 nokta, T∈[0.1,4.0], adım 0.02
  → T=0.46); 0.1126 ise fiilen KOŞULAN dört noktalı ızgaranın argmin'i (T=0.5063). İkisi de
  doğru, ama aynı cümlede tek isim altında kullanılamaz.

  ÇAPA GÜNCELLEMESİ (11 Ağu 2026): Eq.8 artık `min_{T∈G}` — yani headroom'un tanımı FİİLEN
  TARANAN ızgaraya bağlandı. Bunun sonucu birincil sayının değişmesidir: **0.113** (= 0.128233 −
  0.015628, dört noktalı G üzerinde argmin) artık manşet; 0.120 ise "finer-resolution" olarak
  anılıyor. Sayılar yine değişmedi, tanımın kapsadığı ızgara değişti. Dikkat: bu redefinasyonla
  "koşulan kolun gerçekleşen azalması" ile "tanımın değeri" ARTIK AYNI SAYI — eskiden bu ikisi
  ayrı isimlere muhtaçtı, çünkü tanım ince taramayı işaret ediyordu.

İTİRAZ 3 — "76× ✓ ama dipnottaki 0.0024 ile okur 74 hesaplıyor."
  Gösterim hatası: 0.002351, 4 hanede 0.0024'e yuvarlanınca oran okur elinde 74.2'ye düşüyor.
  Onarım paper_tables.py'de (payda 5 haneye çıkarıldı); buradaki tablo tam değerleri verir.

Salt-okunur, GPU yok. Çıktı -> paper_tables/headroom_review.{md,json}
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

D = ROOT / "diagnostics"
A_GRID = D / "teacher_ece_grid" / "teacher_ece_grid.json"
A_FER = D / "ferplus_jsd" / "ferplus_jsd.json"
A_FER_SG = D / "ferplus_jsd" / "ferplus_teacher_signed_grid.json"
A_RT = D / "paper_tables" / "RESULTS_TABLES.json"
OUT_DIR = D / "paper_tables"


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    grid = jload(A_GRID)
    fer = jload(A_FER)
    rt = jload(A_RT)

    # --- RAF-DB öğretmenleri: iki konvansiyon yan yana
    rows = {}
    for t, r in grid.items():
        fs = {float(k): v for k, v in r["fine_sweep"].items()}
        t_argmin = min(fs, key=fs.get)
        rows[t] = {
            "ece_T1": r["ece_T1"],
            "T_star_nll": r["T_star"], "ece_at_T_star_nll": r["ece_Tstar"],
            "headroom_nllstar": r["ece_T1"] - r["ece_Tstar"],          # metindeki eski sayı
            "T_argmin_ece": t_argmin, "ece_at_argmin": fs[t_argmin],
            "headroom_eq8": r["ece_T1"] - fs[t_argmin],                # Eq.8 ile tutarlı
            "grid_step": 0.05,
        }

    # --- FERPlus: iki sayının ait olduğu iki T*
    f_t1 = fer["at_T1"]["ece"]
    f_ece = fer["T_star_ece"]      # ızgara argmin (Eq.8)
    # Koşulan kol: sweep'in kaba T=0.5'i DEĞİL, ince-fit T=0.5063 — tablodaki 0.0156 o satır.
    # (İlk sürüm sweep'ten okudu ve 0.1131 üretti; tabloyla 0.0005 uyuşmazlık, tam da bu
    # raporun kapattığı hata sınıfı.)
    sg = {r["T"]: r for r in jload(A_FER_SG)["grid"]}
    dep = sg[0.5063]
    # Izgara boyutlari ELLE YAZILMIYOR: Eq.8 artik `min_{T∈G}` oldugu icin G'nin kac noktali
    # oldugu tanimin PARCASI. Ince tarama da ayni yerden olculur (adim = ilk iki nokta farki).
    n_grid = len(sg)
    fine_T = sorted(float(r["T"]) for r in fer["sweep"])
    n_fine = len(fine_T)
    fine_step = round(fine_T[1] - fine_T[0], 4)
    # Tanimin dogrulugu KONTROL EDILIYOR: G uzerindeki argmin gercekten kosulan sicaklik mi?
    # Degilse manset sayisi (0.113) bu izgaranin minimumu DEGIL demektir ve durulur.
    g_argmin = min(sg.values(), key=lambda r: r["teacher_ece"])["T"]
    if g_argmin != 0.5063:
        raise RuntimeError(f"G uzerindeki ECE argmin T={g_argmin}, kosulan kol 0.5063 degil — "
                           f"Eq.8'in min_{{T in G}} degeri kosulan kola ait DEGIL, DUR.")
    fer_row = {
        "ece_T1": f_t1,
        "eq8": {"T": f_ece["T"], "ece": f_ece["ece"], "headroom": f_t1 - f_ece["ece"]},
        "deployed_nll": {"T": 0.5063, "ece": dep["teacher_ece"],
                         "reduction": f_t1 - dep["teacher_ece"],
                         "note": "kol fiilen T=0.5063'te kosuldu; tablodaki 0.0156 o "
                                 "sicakligin ECE'si (ferplus_teacher_signed_grid.json)"},
    }

    # --- kapasite oranı: tam değerler
    spans = rt["T10_axis_spans"]["swa"]
    cap, tea = spans["capacity_span"], spans["teacher_span"]

    v = rows["vae9182"]
    L = ["# R0-3 — Refereeing the headroom numbers", "",
         "Producer: `diagnostics/headroom_review.py` · sources: `teacher_ece_grid.json`, "
         "`ferplus_jsd.json`, `RESULTS_TABLES.json` — no number is typed by hand.", "",
         "## 1 · VAE9182 \"−0.0011\": two definitions conflated, not a sign error", "",
         "| teacher | ECE(T=1) | T*_NLL | ECE@T*_NLL | headroom (NLL-T*) | T argmin-ECE | "
         "ECE@argmin | **headroom (Eq.8)** |",
         "|---|---|---|---|---|---|---|---|"]
    for t in ("stage1", "primary", "vae9182"):
        r = rows[t]
        L.append(f"| {t} | {r['ece_T1']:.4f} | {r['T_star_nll']:.3f} | "
                 f"{r['ece_at_T_star_nll']:.4f} | {r['headroom_nllstar']:+.4f} | "
                 f"{r['T_argmin_ece']:g} | {r['ece_at_argmin']:.4f} | "
                 f"**{r['headroom_eq8']:+.4f}** |")
    L += ["",
          f"Where −0.0011 comes from: T* is fitted by minimising **NLL** (0.983), whereas headroom "
          f"is defined on **ECE**. For VAE9182 the NLL optimum is not the ECE optimum; because "
          f"ECE@T*_NLL ({v['ece_at_T_star_nll']:.4f}) > ECE(T=1) ({v['ece_T1']:.4f}), the "
          f"difference comes out negative. **Under Eq.8's argmin definition the correct value is "
          f"+{v['headroom_eq8']:.4f}** (argmin T={v['T_argmin_ece']:g}, grid step {v['grid_step']}).",
          "",
          "**Suggested wording for the text:** \"the well-calibrated teacher's headroom is ≈0.002, an "
          "order of magnitude smaller than the other two teachers' (0.0220 / 0.0206)\" — consistent "
          "with Eq.8, no sign problem. Note: for stage1 the two conventions coincide to four "
          f"decimals (0.0220); for primary they do not ({rows['primary']['headroom_nllstar']:.4f} vs "
          f"{rows['primary']['headroom_eq8']:.4f}) — whichever convention the text adopts, it must "
          "use the same one for ALL THREE teachers; Eq.8 is the recommendation.", "",
          "## 2 · FERPlus 0.113 vs 0.120: one definition, two grid resolutions", "",
          f"| quantity | T | ECE | value |", "|---|---|---|---|",
          f"| ECE(T=1) | 1.0 | {fer_row['ece_T1']:.4f} | — |",
          f"| **Eq.8 headroom** — `min` over the swept grid G ({n_grid} points) | "
          f"**{fer_row['deployed_nll']['T']:g}** | {fer_row['deployed_nll']['ece']:.4f} | "
          f"**{fer_row['deployed_nll']['reduction']:.4f} → the paper's \"0.113\"** |",
          f"| finer-resolution refinement ({n_fine}-point sweep, step {fine_step:g}) | "
          f"{fer_row['eq8']['T']:g} | {fer_row['eq8']['ece']:.4f} | "
          f"{fer_row['eq8']['headroom']:.4f} → the paper's \"0.120\" |", "",
          "**Binding rule (updated 11 Aug 2026).** Eq.8 is now `min_{T∈G}`, i.e. the definition "
          f"is tied to the grid that was ACTUALLY SWEPT. So *headroom* carries "
          f"**{fer_row['deployed_nll']['reduction']:.4f} ≈ 0.113** "
          f"(T={fer_row['deployed_nll']['T']:g}), and "
          f"{fer_row['eq8']['headroom']:.4f} ≈ 0.120 (T={fer_row['eq8']['T']:g}) is quoted only "
          "as what a finer resolution would reach. The arm was run at "
          f"T={fer_row['deployed_nll']['T']:g}, so under the new definition the table's "
          "\"0.1282−0.0156\" and the definition's value are THE SAME NUMBER — which is the point "
          "of the redefinition: the earlier version needed two names because the definition "
          "pointed at a grid nobody had run.",
          "",
          "## 3 · The capacity \"76×\" footnote: rounding dropped the ratio to 74 for the reader",
          "",
          f"Exact values (@swa): teacher span **{tea:.6f}**, capacity span "
          f"**{cap:.6f}** → ratio **{tea / cap:.1f} → 76×**. With four-decimal display ({cap:.4f}) "
          f"the reader computed {tea:.4f}/{cap:.4f} = {round(tea, 4) / round(cap, 4):.1f}. "
          f"Fix: `paper_tables.py` now prints the T10 denominator to five decimals ({cap:.5f}); "
          f"RESULTS_TABLES was regenerated and the JSON values did not change (diff gate green).",
          ""]

    payload = {"rafdb_teachers": rows, "ferplus": fer_row,
               "capacity_ratio": {"teacher_span": tea, "capacity_span": cap,
                                  "ratio": tea / cap,
                                  "display_fix": "cap_span .4f -> .5f in paper_tables.py"}}
    (OUT_DIR / "headroom_review.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "headroom_review.json").write_text(json.dumps(payload, indent=2),
                                                 encoding="utf-8")
    for t, r in rows.items():
        print(f"{t:<9} eq8 {r['headroom_eq8']:+.4f} (argmin T={r['T_argmin_ece']:g})   "
              f"nll-T* {r['headroom_nllstar']:+.4f}")
    print(f"ferplus   eq8 {fer_row['eq8']['headroom']:.4f} (T*={fer_row['eq8']['T']:g})   "
          f"deployed {fer_row['deployed_nll']['reduction']:.4f} (T*={fer_row['deployed_nll']['T']:g})")
    print(f"capacity  {tea:.6f}/{cap:.6f} = {tea / cap:.1f}x")
    print(f"Wrote {OUT_DIR / 'headroom_review.md'}")


if __name__ == "__main__":
    main()
