"""B2 — §5.3'ün iki regresyon doğrusu: üreticisi var mı, spesifikasyonu ne?

SORU. Karşı-doğrulayıcı ~4.000 spesifikasyon taradı: RAF-DB'nin **0.765**'ine %0,8'e kadar
yaklaşabildi ama kesme noktası birlikte tutmadı; FERPlus'ın **0.582**'sine %11'den yakın
hiçbir spesifikasyon bulamadı. İstenen: iki doğrunun üreticisi ve tam spesifikasyonu, ya da
açık bir *\"bu sayıların üreticisi yok\"* hükmü.

CEVAP İKİ DOĞRU İÇİN AYRI ÇIKTI ve bu betik ikisini de kanıtıyla üretiyor:

  FERPlus 0.582 — **ÜRETİCİSİ VAR.** `b015_verdict.py`, havuzlanmış OLS, **@best**
      checkpoint, 9 koşu (3 T kolu × 3 tohum). Karşı-doğrulayıcının bulamamasının sebebi
      muhtemelen makalenin birincil checkpoint'i olan @swa'da aramış olması: aynı fit
      @swa'da **0.446**, @last'te **0.506** veriyor. Yani doğru yayımlı ama **birincil
      olmayan bir checkpoint'te** fit edilmiş ve bu hiçbir yerde yazmıyor.

  RAF-DB 0.765 — **ÜRETİCİSİ YOK.** Sayı `b015_verdict.py:68`'de bir **sabit** olarak
      duruyor (`RAFDB_FIT = {\"intercept\": 0.0244, \"slope\": 0.7653}`), yalnız
      veri-kümeleri-arası karşılaştırma satırında basılıyor, ve hiçbir betik onu
      hesaplamıyor. Bu betik defterden sistematik olarak arıyor (checkpoint × sınıf
      ağırlığı × denetim dosyası); üretilen bütün eğimler **1.35 … 1.66** aralığında,
      en yakını hedefe **%76** uzak. Sayı bu veriden çıkmıyor.

R² DE ÖLÇÜLÜYOR, çünkü itirazın ikinci yarısı oydu: her doğru KENDİ noktalarına karşı
değerlendiriliyor (9 koşu ve 3 grup ortalaması ayrı ayrı) ve en büyük artık, o hücrenin
tohum sd'sine oranıyla birlikte veriliyor.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/regression_line_provenance.{md,json}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from b015_verdict import RAFDB_FIT, TEACHER, linfit  # noqa: E402  -- TEK KAYNAK
from denominator_table import control_arms  # noqa: E402
from paper_tables import A_AUDIT, A_AUDIT_MECH, CKPTS, TEACHERS, load_audit, load_runs  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
B015 = ROOT / "diagnostics" / "selection_audit" / "b015_verdict.json"
GRID = ROOT / "diagnostics" / "teacher_ece_grid" / "teacher_ece_grid.json"
PRIMARY_CKPT = "swa"


def r2_and_residuals(xs, ys, slope, icept, sds=None):
    pred = [icept + slope * x for x in xs]
    res = [y - p for y, p in zip(ys, pred)]
    my = st.mean(ys)
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum(r * r for r in res)
    out = {"r2": (1 - sse / sst) if sst else None, "residuals": res,
           "max_abs_residual": max(abs(r) for r in res)}
    if sds:
        ratios = [abs(r) / s if s else None for r, s in zip(res, sds)]
        good = [x for x in ratios if x is not None]
        out["residual_over_seed_sd"] = ratios
        out["max_residual_over_seed_sd"] = max(good) if good else None
    return out


def ferplus():
    d = json.loads(B015.read_text(encoding="utf-8"))
    out = {}
    for ck in ("best", "swa", "last"):
        p = d["pooled"][ck]
        by_T = p["by_T"]
        # 9 koşu: her T kolunun üç tohumu. Tohum eğrileri `within_seed/curves`'te.
        pts9_x, pts9_y = [], []
        for c in d["within_seed"]["curves"]:
            if c["checkpoint"] != ck:
                continue
            for T, e in c["curve"].items():
                pts9_x.append(TEACHER[T]["ece"])
                pts9_y.append(e)
        gx = [TEACHER[T]["ece"] for T in by_T]
        gy = [by_T[T]["ece_mean"] for T in by_T]
        gsd = [by_T[T]["ece_sd"] for T in by_T]
        out[ck] = {
            "slope": p["fit_slope"], "intercept": p["fit_intercept"],
            "pearson": p["pearson_teacherECE"], "n_runs": len(pts9_y),
            "arms": {T: {"teacher_ece": TEACHER[T]["ece"], "role": TEACHER[T]["role"],
                         **by_T[T]} for T in by_T},
            "fit_on_9_runs": r2_and_residuals(pts9_x, pts9_y, p["fit_slope"],
                                              p["fit_intercept"]),
            "fit_on_3_group_means": r2_and_residuals(gx, gy, p["fit_slope"],
                                                     p["fit_intercept"], gsd),
        }
    return out


def rafdb_search():
    """RAF-DB'nin 0.765'i defterden çıkıyor mu? Sistematik tarama."""
    grid = json.loads(GRID.read_text(encoding="utf-8"))
    tece = {}
    for t in TEACHERS:
        eg = grid[t]["experiment_grid"]
        v = eg.get("1", eg.get("1.0"))
        tece[t] = float(v["teacher_ece"] if isinstance(v, dict) else v)

    runs = load_runs()
    cands = []
    for aname, apath in (("frozen", A_AUDIT), ("mechanism (unfrozen)", A_AUDIT_MECH)):
        audit = load_audit(apath)
        for ck in CKPTS:
            arms = control_arms(runs, audit, ck=ck)
            options = {"effective_number": None, "none": None, "havuz (iki mod ort.)": None}
            for cw in ("effective_number", "none"):
                xs = [tece[t] for t in TEACHERS if (t, cw) in arms]
                ys = [arms[(t, cw)]["ece_mean"] for t in TEACHERS if (t, cw) in arms]
                options[cw] = (xs, ys)
            xs, ys = [], []
            for t in TEACHERS:
                v = [arms[(t, c)]["ece_mean"] for c in ("effective_number", "none")
                     if (t, c) in arms]
                if v:
                    xs.append(tece[t])
                    ys.append(st.mean(v))
            options["havuz (iki mod ort.)"] = (xs, ys)
            for cw, (xs, ys) in options.items():
                if len(xs) < 3:
                    continue
                s, i = linfit(xs, ys)
                q = r2_and_residuals(xs, ys, s, i)
                cands.append({"audit": aname, "checkpoint": ck, "class_weight_mode": cw,
                              "slope": s, "intercept": i, "r2": q["r2"],
                              "dev_pct": 100 * abs(s - RAFDB_FIT["slope"])
                              / RAFDB_FIT["slope"]})
    cands.sort(key=lambda c: c["dev_pct"])
    return {"teacher_ece_T1": tece, "candidates": cands,
            "closest": cands[0] if cands else None,
            "slope_range": [min(c["slope"] for c in cands),
                            max(c["slope"] for c in cands)],
            "target": dict(RAFDB_FIT),
            "producer_found": bool(cands and cands[0]["dev_pct"] < 1.0)}


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    fp, rd = ferplus(), rafdb_search()
    write(fp, rd)
    print("=== regression_line_provenance ===")
    print("  FERPlus (b015_verdict.py, havuzlanmis OLS):")
    for ck, v in fp.items():
        star = "  <- YAYIMLI 0.582" if abs(v["slope"] - 0.582) < 0.002 else ""
        print(f"    @{ck:5s} slope {v['slope']:.4f}  icept {v['intercept']:+.5f}  "
              f"r {v['pearson']:+.4f}  R2(9 kosu) {v['fit_on_9_runs']['r2']:.4f}"
              f"  R2(3 ort) {v['fit_on_3_group_means']['r2']:.4f}{star}")
    print(f"    makalenin birincil checkpoint'i: @{PRIMARY_CKPT} -> "
          f"slope {fp[PRIMARY_CKPT]['slope']:.4f}")
    print("\n  RAF-DB (hedef 0.7653 / 0.0244):")
    print(f"    taranan spesifikasyon: {len(rd['candidates'])}")
    print(f"    uretilen egim araligi: {rd['slope_range'][0]:.4f} .. "
          f"{rd['slope_range'][1]:.4f}")
    c = rd["closest"]
    print(f"    en yakin: slope {c['slope']:.4f} ({c['dev_pct']:.1f}% uzak) "
          f"[{c['audit']}|{c['checkpoint']}|{c['class_weight_mode']}]")
    print(f"    URETICI BULUNDU MU: {'EVET' if rd['producer_found'] else 'HAYIR'}")


def write(fp, rd):
    prim = fp[PRIMARY_CKPT]
    pub = fp["best"]
    L = ["# B2 — §5.3'ün iki regresyon doğrusu: üreticisi ve spesifikasyonu", "",
         "Üretici: `diagnostics/regression_line_provenance.py` · fit ve öğretmen ECE'leri "
         "`b015_verdict.py`'den **ithal** (`linfit`, `TEACHER`, `RAFDB_FIT`)", "",
         "> İki doğru için iki ayrı cevap çıktı. Biri yayımlanabilir bir spesifikasyona "
         "sahip ama **yanlış checkpoint'te** fit edilmiş; diğerinin **üreticisi yok**.", "",
         "| doğru | hüküm |", "|---|---|",
         f"| FERPlus **{pub['slope']:.3f}** | ✅ üreticisi var — `b015_verdict.py`, "
         f"havuzlanmış OLS, **@best** |",
         f"| RAF-DB **{rd['target']['slope']:.3f}** | ❌ **üreticisi yok** — sabit olarak "
         f"yazılı, hiçbir betik hesaplamıyor |", "",
         "---", "",
         "## 1 · FERPlus — tam spesifikasyon", "", "| alan | değer |", "|---|---|",
         "| üretici | `diagnostics/b015_verdict.py` (ön-kayıt B-015, 2026-07-26 13:27:26) |",
         "| yordayıcı | öğretmen ECE (ölçeklenmiş öğretmenin kendi ECE'si) |",
         "| yanıt | öğrenci ECE |",
         "| kollar | T ∈ {" + ", ".join(sorted(pub["arms"], key=float)) + "} — "
         "B-017'nin T=0.74 kolu **kapsam dışı** (ayrı ön-kayıt) |",
         f"| n | {pub['n_runs']} koşu (3 kol × 3 tohum), havuzlanmış |",
         "| ağırlıklandırma | yok — düz OLS |",
         "| **checkpoint** | **@best** |", "",
         "| checkpoint | eğim | kesme | Pearson | R² (9 koşu) | R² (3 grup ort.) |",
         "|---|---|---|---|---|---|"]
    for ck in ("swa", "best", "last"):
        v = fp[ck]
        tag = " ← **yayımlı**" if ck == "best" else (
            " ← **makalenin birincil checkpoint'i**" if ck == PRIMARY_CKPT else "")
        L.append(f"| @{ck}{tag} | **{v['slope']:.4f}** | {v['intercept']:+.5f} | "
                 f"{v['pearson']:+.4f} | {v['fit_on_9_runs']['r2']:.4f} | "
                 f"{v['fit_on_3_group_means']['r2']:.4f} |")
    mr = pub["fit_on_3_group_means"].get("max_residual_over_seed_sd")
    L += ["", f"> **Karşı-doğrulayıcının bulamamasının sebebi çok muhtemelen checkpoint.** "
          f"Yayımlanan {pub['slope']:.3f} @best'ten geliyor; makalenin birincil "
          f"checkpoint'i @{PRIMARY_CKPT} ve orada aynı fit **{prim['slope']:.3f}** veriyor "
          f"(%{100 * abs(prim['slope'] - pub['slope']) / pub['slope']:.0f} fark). "
          f"Cümlede checkpoint yazmıyor.", "",
          f"> R² itirazı **ölçüldü**: 9 koşu üzerinde R² = {pub['fit_on_9_runs']['r2']:.4f}, "
          f"3 grup ortalaması üzerinde {pub['fit_on_3_group_means']['r2']:.4f}. En büyük "
          f"artık {pub['fit_on_3_group_means']['max_abs_residual']:.4f}"
          + (f", o hücrenin tohum sd'sinin **{mr:.1f} katı**." if mr else "."), "",
          "| T | rol | öğretmen ECE | öğrenci ECE (ort ± sd) | n | artık | artık / tohum sd |",
          "|---|---|---|---|---|---|---|"]
    res = pub["fit_on_3_group_means"]["residuals"]
    rat = pub["fit_on_3_group_means"].get("residual_over_seed_sd") or [None] * len(res)
    for (T, a), r, q in zip(pub["arms"].items(), res, rat):
        L.append(f"| {T} | {a['role']} | {a['teacher_ece']:.4f} | "
                 f"{a['ece_mean']:.4f} ± {a['ece_sd']:.4f} | {a['n']} | {r:+.4f} | "
                 + (f"{q:.1f}× |" if q else "— |"))

    c = rd["closest"]
    L += ["", "---", "", "## 2 · RAF-DB — **üreticisi yok**", "",
          "Sayı `diagnostics/b015_verdict.py:68`'de bir **sabit**:", "",
          "```python",
          "# RAF-DB's fitted law, for the cross-dataset comparison",
          f"RAFDB_FIT = {{\"intercept\": {rd['target']['intercept']}, "
          f"\"slope\": {rd['target']['slope']}}}",
          "```", "",
          "Deponun hiçbir yerinde bu iki sayıyı hesaplayan bir kod yok; yalnız "
          "veri-kümeleri-arası karşılaştırma satırında **basılıyor**. Kaç noktadan, hangi "
          "checkpoint'te, hangi sınıf-ağırlığında fit edildiği kayıtlı değil — kayıtlı olan "
          "tek yan bilgi \"Pearson +0.992, 3 teachers\" yorumu.", "",
          f"Bu betik defterden sistematik olarak aradı: **{len(rd['candidates'])} "
          f"spesifikasyon** (2 denetim dosyası × 3 checkpoint × 3 sınıf-ağırlığı seçeneği), "
          f"her biri üç öğretmenin T=1 ECE'sine karşı kontrol kolunun öğrenci ECE'si.", "",
          "| ölçüm | değer |", "|---|---|",
          f"| üretilen eğim aralığı | **{rd['slope_range'][0]:.4f} … "
          f"{rd['slope_range'][1]:.4f}** |",
          f"| hedef | {rd['target']['slope']:.4f} |",
          f"| en yakın spesifikasyon | {c['slope']:.4f} "
          f"(`{c['audit']} / @{c['checkpoint']} / {c['class_weight_mode']}`), "
          f"**%{c['dev_pct']:.0f} uzak** |",
          f"| üretici bulundu mu | **{'evet' if rd['producer_found'] else 'HAYIR'}** |", "",
          "| denetim | ckpt | sınıf ağırlığı | eğim | kesme | R² | hedeften uzaklık |",
          "|---|---|---|---|---|---|---|"]
    for k in rd["candidates"][:9]:
        L.append(f"| {k['audit']} | @{k['checkpoint']} | `{k['class_weight_mode']}` | "
                 f"{k['slope']:.4f} | {k['intercept']:+.5f} | {k['r2']:.4f} | "
                 f"%{k['dev_pct']:.0f} |")
    L += ["", "> **Hüküm: bu sayının üreticisi yok ve bu veriden çıkmıyor.** Üç öğretmen "
          "üzerinden kurulan her doğrunun eğimi 1.35'in üstünde; 0.765 en yakın "
          f"spesifikasyondan %{c['dev_pct']:.0f} uzak. Pearson +0.992 iddiası taranan "
          "spesifikasyonlarla uyumlu (hepsinde r ≈ 0.99), yani anlatı doğru ama **eğim "
          "değil**. Cümlenin işi zaten feragat olduğu için makaleden çıkarılması kayıpsız.",
          "", "---", "",
          "Kaynaklar: `diagnostics/selection_audit/b015_verdict.json` (FERPlus fit'i, "
          "havuzlanmış), `diagnostics/teacher_ece_grid/teacher_ece_grid.json` (öğretmen "
          "ECE'leri), `denominator_table.control_arms()` (öğrenci kontrol kolları).", ""]

    (OUT_DIR / "regression_line_provenance.md").write_text("\n".join(L) + "\n",
                                                           encoding="utf-8")
    (OUT_DIR / "regression_line_provenance.json").write_text(json.dumps({
        "ferplus": fp, "rafdb": rd, "primary_checkpoint": PRIMARY_CKPT},
        indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
