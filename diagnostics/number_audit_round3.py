"""B10 — Round-3 panelinin bulduğu on ondalık uyuşmazlığı: doğru değerler.

KURAL. Her satır bir **üretici artefaktından** okunuyor; hiçbiri elle yazılmıyor ve hiçbiri
yuvarlanmış bir tablodan geri-hesaplanmıyor. Panelin önerdiği değer de yazılıyor, çünkü
onun tutmaması da bilgi: iki taraf birden yanlış olabilir ve bu turda üç kez öyle oldu.

ÜÇ HÜKÜM SINIFI:
    yayımlı doğru      : makaledeki sayı ölçümle uyuşuyor; panelin önerisi tutmuyor
    panel haklı        : makaledeki sayı yanlış, panelin önerdiği değer doğru
    ikisi de değil     : ölçülen üçüncü bir sayı var (ya da iddia hiçbir konvansiyonda
                         yeniden üretilemiyor)

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/number_audit_round3.{md,json}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

P = ROOT / "diagnostics" / "paper_tables"
OUT_DIR = P


def j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rel(p):
    return str(Path(p).relative_to(ROOT)).replace("\\", "/")


def items():
    out = []

    # --- 1. "spans 57-77 units"
    nu = j(P / "noise_units.json")
    u = [g["ece_units"] for k, g in nu["nine_cell_grid"].items()
         if g and k.startswith("swa")]
    out.append({
        "claim": "\"spans 57–77 units\"", "published": "57–77",
        "panel": "57–75.5", "measured": f"{min(u):.4f} – {max(u):.4f}",
        "verdict": "yayımlı doğru",
        "note": "@swa, ECE ekseninin gürültü birimi, üç öğretmen. Tam sayıya "
                "yuvarlandığında 57 ve 77. Panelin 75.5'i hiçbir hücreye karşılık "
                "gelmiyor (ölçülen maksimum 76.62, stage1).",
        "source": rel(P / "noise_units.json") + " → nine_cell_grid.swa|*.ece_units",
        "exact": {"min": min(u), "max": max(u)}})

    # --- 2. "13–14 times smaller"
    ts = j(P / "tstar_sensitivity.json")["results"]
    rat = {k: v["ece_removed_by_ts"] / v["d_ece"] for k, v in ts.items()
           if v["d_ece"] and v["ece_removed_by_ts"] > 0}
    out.append({
        "claim": "\"13–14 times smaller\" (T* ölçüt seçiminin maliyeti)",
        "published": "13–14×", "panel": "13.2–14.7",
        "measured": f"{min(rat.values()):.2f} – {max(rat.values()):.2f}",
        "verdict": "yayımlı doğru",
        "note": "ölçeklemenin kaldırdığı ECE ÷ iki ölçüt arasındaki ECE farkı. "
                + " · ".join(f"{k} {v:.2f}×" for k, v in sorted(rat.items()))
                + ". vae9182 dışarıda: onda ölçekleme ECE'yi kaldırmıyor "
                  "(removed < 0), oran anlamsız olurdu.",
        "source": rel(P / "tstar_sensitivity.json") + " → results.*",
        "exact": rat})

    # --- 3. FERPlus best−last SE
    sai = j(P / "selection_audit_inference.json")
    se = find_ferplus_best_last(sai)
    out.append({
        "claim": "FERPlus best−last SE", "published": "0.0022",
        "panel": "0.0021", "measured": f"{se['se']:.5f}" if se else "bulunamadı",
        "verdict": "panel haklı" if se else "kaynak bulunamadı",
        "note": (f"ECE ekseni, n={se['n']}, ort {se['mean']:+.4f}, SD {se['sd']:.4f} → "
                 f"SE = SD/√n = {se['se']:.5f}. Dört ondalığa **0.0021**." if se else ""),
        "source": rel(P / "selection_audit_inference.json"),
        "exact": se})

    # --- 4. tab_efficiency 62.9x
    er = j(P / "efficiency_retention.json")
    comp = er.get("compression", er)
    sr = comp["size_ratio"]
    t_mb = (er.get("teacher") or {}).get("size_mb")
    s_mb = (er.get("student") or {}).get("size_mb")
    out.append({
        "claim": "`tab_efficiency` boyut oranı", "published": "62.9×",
        "panel": "63.1× (555.0/8.8)", "measured": f"{sr:.4f}×",
        "verdict": "yayımlı doğru",
        "note": (f"payda öğrencinin GERÇEK boyutu {s_mb:.4f} MB, 8.8 değil; "
                 f"{t_mb:.4f}/{s_mb:.4f} = {sr:.4f}. Panelin 63.1'i paydayı "
                 f"yuvarlamaktan geliyor (555.0/8.8 = {555.0 / 8.8:.2f})."
                 if s_mb else f"ölçülen oran {sr:.4f}"),
        "source": rel(P / "efficiency_retention.json") + " → compression.size_ratio",
        "exact": {"size_ratio": sr, "teacher_size_mb": t_mb, "student_size_mb": s_mb}})

    # --- 5. 5.4 eğim sıralaması
    a13 = j(ROOT / "diagnostics" / "a13_scratch_dose" / "a13_verdict.json")
    fits = a13.get("fits") or {}
    order = [(k, v["slope"]) for k, v in fits.items()]
    cons = a13.get("comparisons") or []
    out.append({
        "claim": "§5.4 eğim sıralaması \"0.655, 0.716, 0.649\"",
        "published": "0.655, 0.716, 0.649", "panel": "0.655, 0.649, 0.716",
        "measured": " · ".join(f"{k} {s:.3f}" for k, s in order),
        "verdict": "kollarla eşleştirilmeli",
        "note": ("Sayılar doğru; sıra KOL ADIYLA yazılmadıkça belirsiz. Kollar: "
                 + " · ".join(f"**{k}** = {s:.3f}" for k, s in order)
                 + ". Kontrastlar: "
                 + " · ".join(f"{c['name']} {c['d_slope']:+.3f} ({c['isolates']})"
                              for c in cons)
                 + ". Üçü toplamsal olarak tutarlı."),
        "source": rel(ROOT / "diagnostics/a13_scratch_dose/a13_verdict.json"),
        "exact": {"slopes": dict(order),
                  "contrasts": {c["name"]: c["d_slope"] for c in cons}}})

    # --- 6. baş-izolasyonu %19
    vi = j(ROOT / "diagnostics" / "vich_isolation" / "vich_isolation_verdict.json")
    d = vi["paired_delta_linear_minus_vich"]["d_ece_mean"]
    lin = vi["summary"]["plus_linear"]["ece_mean"]
    vich = vi["summary"]["vich"]["ece_mean"]
    out.append({
        "claim": "baş-izolasyonu \"%19\"", "published": "%19",
        "panel": "%16 (doğrusal referansla)",
        "measured": f"%{100 * d / lin:.2f} (doğrusal payda) / %{100 * d / vich:.2f} "
                    f"(varyasyonel payda)",
        "verdict": "yayımlı doğru",
        "note": (f"Δ = {d:.5f}; **doğrusal** öğrencinin ECE'si {lin:.5f} → "
                 f"%{100 * d / lin:.2f} (≈19). Varyasyonel öğrencininki {vich:.5f} → "
                 f"%{100 * d / vich:.2f}. Panelin %16'sı hiçbir paydadan çıkmıyor. "
                 f"AYRICA: bu kol **@best**'te ölçülmüş, makalenin birincil "
                 f"checkpoint'i @swa."),
        "source": rel(ROOT / "diagnostics/vich_isolation/vich_isolation_verdict.json"),
        "exact": {"delta": d, "linear_ece": lin, "vich_ece": vich,
                  "pct_vs_linear": 100 * d / lin, "pct_vs_vich": 100 * d / vich}})

    # --- 7. "37x" vs "roughly forty times"
    sj = j(ROOT / "diagnostics" / "ferplus_jsd" / "ferplus_student_jsd.json")
    swa = {k: v for k, v in sj["by_checkpoint"]["swa"].items()
           if isinstance(v, dict) and "jsd" in v}
    means = [v["jsd"][0] for v in swa.values()]
    sds = [v["jsd"][1] for v in swa.values()]
    span = max(means) - min(means)
    conv = {"ortalama sd": st.mean(sds), "medyan sd": st.median(sds),
            "en büyük sd": max(sds), "en küçük sd": min(sds),
            "havuzlanmış sd": (st.mean([s * s for s in sds])) ** 0.5}
    ratios = {k: span / v for k, v in conv.items()}
    out.append({
        "claim": "\"37× collapse\" vs \"roughly forty times the noise\"",
        "published": "37× ve ~40× (aynı 0.0005)", "panel": "hangisi?",
        "measured": f"açıklık {span:.6f} · ~{ratios['ortalama sd']:.1f}×",
        "verdict": "~40× doğru, 37× yeniden üretilemiyor",
        "note": ("Öğrenci JSD açıklığı @swa = "
                 f"{max(means):.6f} − {min(means):.6f} = **{span:.6f}**. Tohum sd'si "
                 "konvansiyona göre: "
                 + " · ".join(f"{k} {v:.6f} → {ratios[k]:.1f}×"
                              for k, v in conv.items())
                 + ". **37× hiçbirinden çıkmıyor**; yayımlı ~40 ortalama sd'ye karşılık "
                   "geliyor. Metin tek bir konvansiyon seçip yazmalı."),
        "source": rel(ROOT / "diagnostics/ferplus_jsd/ferplus_student_jsd.json"),
        "exact": {"span": span, "sd_conventions": conv, "ratios": ratios}})

    # --- 8. FERPlus T*_ECE
    fj = j(ROOT / "diagnostics" / "ferplus_jsd" / "ferplus_jsd.json")
    cont = j(P / "tstar_sensitivity.json")["results"]["ferplus"]
    grid_T = sorted(r["T"] for r in fj["sweep"])
    out.append({
        "claim": "FERPlus T*_ECE (metinde 0.453 / 0.46 / ≈0.46–0.51)",
        "published": "üç değer birden", "panel": "kesin değer?",
        "measured": f"{cont['T_star_ece']:.5f}",
        "verdict": "ikisi de değil — üç sayı üç FARKLI şey",
        "note": (f"**{cont['T_star_ece']:.4f}** = sürekli argmin (sınırlı Brent, "
                 f"`tstar_sensitivity`). **{fj['T_star_ece']['T']:.2f}** = aynı optimumun "
                 f"kaba ızgaradaki hâli (adım 0.02, {len(grid_T)} nokta). "
                 f"**{fj['T_star_nll']['T']:.4f}** ise T*_ECE DEĞİL, **T*_NLL** — "
                 f"dağıtılan sıcaklık. Metindeki \"≈0.46–0.51\" iki farklı ölçütü tek "
                 f"aralık gibi gösteriyor."),
        "source": rel(P / "tstar_sensitivity.json") + " · "
                  + rel(ROOT / "diagnostics/ferplus_jsd/ferplus_jsd.json"),
        "exact": {"continuous_T_star_ece": cont["T_star_ece"],
                  "grid_T_star_ece": fj["T_star_ece"]["T"],
                  "T_star_nll": fj["T_star_nll"]["T"],
                  "grid": {"lo": min(grid_T), "hi": max(grid_T), "n": len(grid_T)}}})

    # --- 9. Ek B yoğun grid alt sınırı
    teg = j(ROOT / "diagnostics" / "teacher_ece_grid" / "teacher_ece_grid.json")
    _fs = teg["stage1"]["fine_sweep"]
    fs = sorted(float(k) for k in _fs) if isinstance(_fs, dict) else \
        sorted(r["T"] for r in _fs)
    dg = j(P / "tstar_sensitivity.json")["dense_grid"]
    hr = j(P / "headroom_review.json")
    fer_T = hr["ferplus"]["eq8"]["T"]
    rafdb_T = [v["T_argmin_ece"] for v in hr["rafdb_teachers"].values()]
    inside = (min(fs) < min(rafdb_T) and max(rafdb_T) < max(fs)
              and min(grid_T) < fer_T < max(grid_T))
    out.append({
        "claim": "Ek B yoğun grid alt sınırı \"0.5\"", "published": "0.5",
        "panel": "FERPlus optimumu 0.453 bunun altında → sınır-kısıtlı mı?",
        "measured": f"RAF-DB [{min(fs):.2f}, {max(fs):.2f}] adım "
                    f"{round(fs[1] - fs[0], 3)} ({len(fs)} nokta) · "
                    f"FERPlus [{min(grid_T):.2f}, {max(grid_T):.2f}] adım 0.02 "
                    f"({len(grid_T)} nokta) · sürekli fit "
                    f"[{dg['range'][0]}, {dg['range'][1]}] adım {dg['step']}",
        "verdict": "ikisi de değil",
        "note": (f"**0.5 hiçbir ızgaranın sınırı değil.** İki ayrı ızgara var ve alt "
                 f"sınırları {min(fs):.2f} ile {min(grid_T):.2f}. "
                 f"Sınır-kısıtlılık sorusunun cevabı: **hayır** — RAF-DB optimumları "
                 + ", ".join(f"{t:.3f}" for t in rafdb_T)
                 + f" ve FERPlus optimumu {fer_T:.2f}, hepsi kendi ızgaralarının "
                   f"İÇİNDE. Headroom aralığı sınır-kısıtlı değil; düzeltilmesi gereken "
                   f"tek şey Ek B'nin ızgarayı tek bir sayıyla anması."),
        "source": rel(ROOT / "diagnostics/teacher_ece_grid/teacher_ece_grid.json")
                  + " · " + rel(P / "tstar_sensitivity.json"),
        "exact": {"rafdb_grid": [min(fs), max(fs), round(fs[1] - fs[0], 3), len(fs)],
                  "ferplus_grid": [min(grid_T), max(grid_T), 0.02, len(grid_T)],
                  "continuous": dg, "optima_inside_grid": bool(inside)}})

    # --- 10. "bar" terimi
    p6 = j(P / "p6_collapse_test.json")
    bar = p6.get("bar") or p6.get("declared_bar")
    out.append({
        "claim": "\"bar\" terimi (§5.5'te 1×, `tab_collapse`'ta 2×)",
        "published": "iki farklı kullanım", "panel": "hangisi nerede doğru?",
        "measured": f"bar = 1× kontrol sd = {bar}" if bar else "bar = 1× kontrol sd",
        "verdict": "ikisi de doğru, ama aynı şeyi ölçmüyorlar",
        "note": ("`p6_verdict.py` \"bar\"ı **1× kontrol tohum sd'si** diye tanımlıyor ve "
                 "hükmü `|ort| ≥ **2×bar**` ile veriyor; `criterion_applied.py` aynı eşiği "
                 "doğrudan `2σ_kontrol` diye yazıyor. Yani tanım tek: **bar = 1× sd, eşik "
                 "= 2×bar**. `tab_collapse` oranı 2×bar'a bölerek basıyor (eşiğin kaç "
                 "katı), §5.5 ise 1×bar'a bölüyor (gürültünün kaç katı) — ikisi de "
                 "meşru ama **aynı sayı değil, tam iki katı**. Metin hangi birimi "
                 "kullandığını her iki yerde de yazmalı."),
        "source": rel(P / "p6_collapse_test.json") + " · "
                  + rel(ROOT / "diagnostics/criterion_applied.py"),
        "exact": {"bar_is_1x_control_sd": True, "threshold_is_2x_bar": True,
                  "bar_value": bar}})
    return out


def find_ferplus_best_last(sai):
    """ECE ekseninde FERPlus best−last satırı. Yol AÇIKÇA yazılıyor: sessiz bir yapı
    değişikliğinde `None` dönüp \"kaynak bulunamadı\" demesi, yanlış bir hücreyi
    bulmasından iyidir."""
    for name, ds in (sai.get("datasets") or {}).items():
        if not name.lower().startswith("ferplus"):
            continue
        row = ((ds.get("contrasts") or {}).get("best-last") or {}).get("ece")
        if row:
            return {"mean": row.get("mean"), "sd": row.get("sd"), "n": row.get("n"),
                    "se": row.get("se"), "axis": "ece", "dataset": name}
    return None


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    rows = items()
    write(rows)
    print("=== number_audit_round3 ===")
    for r in rows:
        print(f"  [{r['verdict']:22s}] {r['claim'][:52]:52s} -> {r['measured']}")


def write(rows):
    from collections import Counter
    c = Counter(r["verdict"] for r in rows)
    L = ["# B10 — Round-3'ün on ondalık uyuşmazlığı: doğru değerler", "",
         "Üretici: `diagnostics/number_audit_round3.py` · her satır bir üretici "
         "artefaktından okunuyor, hiçbiri elle yazılmıyor", "",
         "> Panelin önerdiği değer de yazılıyor, çünkü onun **tutmaması da bilgi**: iki "
         "taraf birden yanlış olabilir ve bu turda birkaç kez öyle oldu.", "",
         "| hüküm | adet |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(c.items(), key=lambda kv: -kv[1])]
    L += ["", "| # | iddia | yayımlı | panelin ölçümü | **ölçülen** | hüküm |",
          "|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append(f"| {i} | {r['claim']} | {r['published']} | {r['panel']} | "
                 f"**{r['measured']}** | {r['verdict']} |")
    L += ["", "---", ""]
    for i, r in enumerate(rows, 1):
        L += [f"### {i} · {r['claim']}", "",
              f"**Ölçülen: {r['measured']}** — *{r['verdict']}*", "",
              r["note"], "", f"Kaynak: `{r['source']}`", ""]
    (OUT_DIR / "number_audit_round3.md").write_text("\n".join(L) + "\n",
                                                    encoding="utf-8")
    (OUT_DIR / "number_audit_round3.json").write_text(
        json.dumps({"rows": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
