"""G4.5 — hücre-başına eşleştirilmiş-fark sd'si + dokuz hücreli gürültü-birimi tablosu.

NEDEN VAR (panel G4.5). Metin *"typically 77 / never below 55"* diyor: kalibrasyon etkisinin
doğruluk etkisini kaç GÜRÜLTÜ BİRİMİ aştığı. İki sorun:
  1. "Typically" bir istatistik değil. Medyan mı, ortalama mı? İkisi farklı sayı verir ve
     hangisinin kullanıldığı yazılmadıkça iddia denetlenemez.
  2. "Never below 55" bir MİNİMUM iddiası, yani tek bir hücre onu düşürebilir. Hangi hücreler
     üzerinden alındığı yazılmadıkça hangi kümenin minimumu olduğu bilinmiyor.
Bu betik dokuz hücrenin (üç checkpoint × üç öğretmen) tamamını açıkça basıyor ve üç özet
istatistiği de (medyan, ortalama, minimum) YAN YANA veriyor -- hangisinin "typically" olduğu
metin tarafında seçilsin, ama sayı burada görünür olsun.

GÜRÜLTÜ BİRİMİ TANIMI, açıkça: bir hücrenin etkisi, o kolun KENDİ kontrolünün aynı metrikteki
tohum sd'sine bölünür. Oran ise
        (|ΔECE| / σ_ECE)  ÷  (|Δdoğruluk| / σ_acc)
yani "kalibrasyon etkisi kaç gürültü birimi" ÷ "doğruluk etkisi kaç gürültü birimi". İki eksen
farklı birimde olduğu için tek bir ortak ölçeğe indirmenin başka yolu yok; payda seçimi
`denominator_table.control_arms`'tan İTHAL ediliyor, burada yeniden tanımlanmıyor.

EŞLEŞTİRME de ithal: `t5_pairing_diff.build(..., rule="new")`. Kontrol, tedavinin KENDİ
tohumuyla ve KENDİ class_weight_mode'uyla eşleşir -- eski kural class_weight'i yok sayıp
kontrolleri sessizce gölgeliyordu.

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/noise_units.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from paper_tables import A_AUDIT_MECH, CKPTS, TEACHERS, load_audit, load_runs  # noqa: E402
from denominator_table import control_arms                                     # noqa: E402 -- TEK KAYNAK
from t5_pairing_diff import build                                              # noqa: E402 -- İTHAL
from stats_convention import SD_CONVENTION, sample_sd                          # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Metnin "77 / 55" cümlesinin konusu: logit standardizasyonu (T5a'nın kolu).
FOCUS = "logit_std"


def ratio_cell(cell_ck, ctrl):
    """Kalibrasyon etkisi ÷ doğruluk etkisi, ikisi de kendi gürültü biriminde."""
    if not ctrl or not ctrl.get("ece_sd") or not ctrl.get("acc_sd"):
        return None
    ece_units = abs(cell_ck["d_ece_mean"]) / ctrl["ece_sd"]
    acc_units = abs(cell_ck["d_acc_mean"]) / ctrl["acc_sd"]
    if acc_units == 0:
        return None
    return {"ece_units": ece_units, "acc_units": acc_units, "ratio": ece_units / acc_units}


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    # A_AUDIT_MECH: mekanizma karsilastirmalarinin okudugu denetim dosyasi -- hangi
    # dosya oldugu paper_tables'ta TEK YERDE tanimli, buraya yeniden yazilmiyor.
    runs, audit = load_runs(), load_audit(A_AUDIT_MECH)
    cells, shadowed, _ = build(runs, audit, rule="new")

    # --- dokuz hücre: checkpoint × öğretmen, FOCUS mekanizması
    grid, ratios = {}, []
    for ck in CKPTS:
        arms = control_arms(runs, audit, ck=ck)
        for t in TEACHERS:
            rec = cells.get((t, FOCUS))
            if not rec or ck not in rec["by_ckpt"]:
                grid[f"{ck}|{t}"] = None
                continue
            c = rec["by_ckpt"][ck]
            ctrl = arms.get((t, rec["class_weight_mode"]))
            r = ratio_cell(c, ctrl)
            grid[f"{ck}|{t}"] = {
                "n": c["n"], "d_ece_mean": c["d_ece_mean"], "d_ece_sd": c["d_ece_sd"],
                "d_acc_mean": c["d_acc_mean"], "d_acc_sd": c["d_acc_sd"],
                "signs": c["d_ece_signs"],
                "sigma_ece": ctrl["ece_sd"] if ctrl else None,
                "sigma_acc": ctrl["acc_sd"] if ctrl else None,
                "control_n": ctrl["n"] if ctrl else None, **(r or {})}
            if r:
                ratios.append(r["ratio"])

    summary = None
    if ratios:
        summary = {"n_cells": len(ratios), "median": st.median(ratios),
                   "mean": st.mean(ratios), "min": min(ratios), "max": max(ratios),
                   "sd": sample_sd(ratios) if len(ratios) > 1 else None}

    # --- HAVUZ PAYDASI ile aynı hesap. Metnin "77"si buradan geliyor gibi görünüyor:
    # denominator_table zaten T5a'nın havuz paydası kullandığını yazıyor. İki konvansiyonu
    # yan yana basmadan "77 tutmuyor" demek eksik olurdu -- hangi konvansiyonda tuttuğunu,
    # hangisinde tutmadığını göstermek gerekir.
    pooled = {}
    for ck in CKPTS:
        arms = control_arms(runs, audit, ck=ck)
        if not arms:
            continue
        p_ece = st.mean([v["ece_sd"] for v in arms.values()])
        p_acc = st.mean([v["acc_sd"] for v in arms.values()])
        rs = {}
        for t in TEACHERS:
            rec = cells.get((t, FOCUS))
            if not rec or ck not in rec["by_ckpt"]:
                continue
            c = rec["by_ckpt"][ck]
            if c["d_acc_mean"] == 0:
                continue
            rs[t] = (abs(c["d_ece_mean"]) / p_ece) / (abs(c["d_acc_mean"]) / p_acc)
        if rs:
            v = list(rs.values())
            pooled[ck] = {"sigma_ece_pooled": p_ece, "sigma_acc_pooled": p_acc,
                          "per_teacher": rs, "median": st.median(v), "mean": st.mean(v),
                          "min": min(v), "max": max(v), "n_cells": len(v)}

    # --- hücre başına eşleştirilmiş-fark sd'si, TÜM mekanizma hücreleri
    per_cell = []
    for (t, mech), rec in sorted(cells.items()):
        row = {"teacher": t, "mechanism": mech, "class_weight_mode": rec["class_weight_mode"]}
        for ck in CKPTS:
            c = rec["by_ckpt"].get(ck)
            row[ck] = ({"n": c["n"], "d_ece_mean": c["d_ece_mean"], "d_ece_sd": c["d_ece_sd"],
                        "d_acc_mean": c["d_acc_mean"], "d_acc_sd": c["d_acc_sd"],
                        "signs": c["d_ece_signs"]} if c else None)
        per_cell.append(row)

    write(grid, summary, per_cell, shadowed, pooled)
    print(f"G4.5 dokuz hucre ({FOCUS}), oran = kalibrasyon / dogruluk gurultu birimi:")
    for ck in CKPTS:
        line = []
        for t in TEACHERS:
            g = grid.get(f"{ck}|{t}")
            line.append(f"{t}={g['ratio']:.1f}x" if g and "ratio" in g else f"{t}=—")
        print(f"  @{ck:5s} " + "  ".join(line))
    if summary:
        print(f"\n  medyan {summary['median']:.1f}x · ortalama {summary['mean']:.1f}x · "
              f"min {summary['min']:.1f}x · max {summary['max']:.1f}x  (n={summary['n_cells']})")
    print(f"  hucre basina esdeger-fark sd tablosu: {len(per_cell)} mekanizma hucresi")


def write(grid, summary, per_cell, shadowed, pooled):
    L = ["# G4.5 — gürültü birimleri: dokuz hücre + hücre-başına eşleştirilmiş-fark sd'si", "",
         "> **Panel G4.5.** Metnin *\"typically 77 / never below 55\"* cümlesi denetlenebilir "
         "olsun diye dokuz hücrenin tamamı ve üç özet istatistik yan yana basılıyor. "
         "**\"Typically\" bir istatistik değildir** — medyan ve ortalama farklı sayı verir; "
         "hangisinin kastedildiği metinde YAZILMALI.", "",
         f"{SD_CONVENTION} · mekanizma: `{FOCUS}` · payda `denominator_table.control_arms`'tan, "
         f"eşleştirme `t5_pairing_diff.build(rule=\"new\")`'den **ithal**", "",
         "## Gürültü birimi tanımı", "",
         "Bir hücrenin etkisi, o kolun **kendi** kontrolünün **aynı metrikteki** tohum sd'sine "
         "bölünür. Raporlanan oran:", "",
         "```", "  (|ΔECE| / σ_ECE)  ÷  (|Δdoğruluk| / σ_acc)", "```", "",
         "İki eksen farklı birimde olduğu için ortak ölçeğe indirmenin başka yolu yok. "
         "**σ her checkpoint için ayrı ölçülür** — kontrol kolunun tohum yayılımı @swa ile "
         "@best'te aynı değildir.", ""]

    if summary:
        L += ["## Üç özet istatistik — hangisinin \"typically\" olduğu metinde seçilsin", "",
              "| istatistik | değer |", "|---|---|",
              f"| **medyan** | **{summary['median']:.1f}×** |",
              f"| **ortalama** | **{summary['mean']:.1f}×** |",
              f"| minimum | **{summary['min']:.1f}×** |",
              f"| maksimum | {summary['max']:.1f}× |",
              f"| hücre | {summary['n_cells']} |", ""]
        L += [f"> Medyan ile ortalama arasında "
              f"{abs(summary['mean'] - summary['median']):.1f}× fark var — bu tam olarak "
              f"\"typically\" kelimesinin belirsiz bıraktığı fark. Minimum iddiası "
              f"(**{summary['min']:.1f}×**) ise tek bir hücreye dayanıyor ve o hücre aşağıda "
              f"adıyla görünüyor.", ""]

    if pooled:
        L += ["## Aynı hesap, HAVUZ paydasıyla — metnin \"77\"si buradan geliyor", "",
              "T5a havuz paydası kullanıyor (üç öğretmenin kontrol sd'lerinin ortalaması), "
              "yukarıdaki tablo ise her kolun KENDİ paydasını. İkisi farklı sayı verir; "
              "hangisinin kullanıldığı cümlede yazılmalı.", "",
              "| checkpoint | " + " | ".join(TEACHERS) + " | medyan | **ortalama** | min |",
              "|---|" + "---|" * (len(TEACHERS) + 3)]
        for ck in CKPTS:
            q = pooled.get(ck)
            if not q:
                continue
            cellstr = " | ".join(f"{q['per_teacher'].get(t, float('nan')):.1f}×" for t in TEACHERS)
            L.append(f"| {ck} | {cellstr} | {q['median']:.1f}× | **{q['mean']:.1f}×** | "
                     f"{q['min']:.1f}× |")
        sw = pooled.get("swa")
        if sw:
            L += ["", f"> **\"Typically\" = ORTALAMA, ve yalnız @swa.** Havuz paydasıyla @swa "
                  f"ortalaması **{sw['mean']:.1f}×** — metnin *77*'sine en yakın sayı bu. "
                  f"Medyan aynı satırda {sw['median']:.1f}×, yani kelime seçimi sayıyı "
                  f"{abs(sw['mean'] - sw['median']):.0f}× oynatıyor.",
                  f"> **Ama *\"never below 55\"* HİÇBİR KONVANSİYONDA TUTMUYOR.** Havuz "
                  f"paydasıyla @swa minimumu **{sw['min']:.1f}×** (primary), kendi paydasıyla "
                  f"dokuz hücrenin minimumu **{min(g['ratio'] for g in grid.values() if g and 'ratio' in g):.1f}×**. "
                  f"Taban iddiası ya kaldırılmalı ya da ölçülen sayıyla değiştirilmeli.", ""]

    L += ["## Dokuz hücre (checkpoint × öğretmen)", "",
          "| checkpoint | öğretmen | n | ΔECE | σ_ECE | ECE birimi | Δacc (pp) | σ_acc | "
          "acc birimi | **oran** |", "|---|---|---|---|---|---|---|---|---|---|"]
    for ck in CKPTS:
        for t in TEACHERS:
            g = grid.get(f"{ck}|{t}")
            if not g:
                L.append(f"| {ck} | {t} | — | — | — | — | — | — | — | — |")
                continue
            r = f"**{g['ratio']:.1f}×**" if "ratio" in g else "—"
            L.append(f"| {ck} | {t} | {g['n']} | {g['d_ece_mean']:+.4f} | "
                     f"{g['sigma_ece']:.4f} | {g.get('ece_units', float('nan')):.1f} | "
                     f"{g['d_acc_mean']:+.3f} | {g['sigma_acc']:.4f} | "
                     f"{g.get('acc_units', float('nan')):.1f} | {r} |")
    L += ["", "> **Oranın büyük olması, doğruluk etkisinin küçük olmasından da gelebilir.** "
              "Payda `|Δdoğruluk| / σ_acc`; doğruluk etkisi gürültünün içinde kaldığında bu "
              "sayı küçülür ve oran şişer. O yüzden iki bileşen de ayrı sütun olarak basılıyor — "
              "oran tek başına okunmamalı.", ""]

    # İKİ EKSEN BİRDEN (14 Ağu, B3). Tablo bugüne kadar yalnız ΔECE sd'sini basıyordu ve
    # ölçüt doğruluk ekseninde de uygulanıyor -- beş öğrenilmiş-sinyal gate hücresine
    # (bkz. criterion_applied G3.3). Tek eksen basmak, o beş hücrenin paydasını okuyucudan
    # saklıyordu. Sayı zaten JSON'da vardı; eksik olan sütundu.
    L += ["## Hücre-başına eşleştirilmiş-fark sd'si (tüm mekanizma hücreleri, İKİ EKSEN)", "",
          "| öğretmen | mekanizma | cw | " +
          " | ".join(f"n@{c} · ΔECE sd · Δacc sd" for c in CKPTS) + " |",
          "|---|---|---|" + "---|" * len(CKPTS)]
    for row in per_cell:
        cs = []
        for ck in CKPTS:
            c = row[ck]
            cs.append(f"{c['n']} · {c['d_ece_sd']:.4f} · {c['d_acc_sd']:.3f}" if c else "—")
        L.append(f"| {row['teacher']} | `{row['mechanism']}` | "
                 f"{row['class_weight_mode']} | " + " | ".join(cs) + " |")
    L += ["", "n=1 olan hücrelerde sd tanımsızdır ve boş görünür — bu bir eksiklik değil, "
              "tek tohumdan yayılım ölçülemez. A12 (gerçek-sinyal gate n=3) bittiğinde "
              "`gate:*` satırlarının n'i artacak ve bu tablo yeniden üretilmeli.", ""]

    if shadowed:
        L += ["## Gölgelenen kontroller (eski eşleştirme kuralının sessizce attıkları)", "",
              "| anahtar | tutulan | atılan |", "|---|---|---|"]
        L += [f"| {' / '.join(s['key'])} | `{s['kept']}` | `{s['discarded']}` |"
              for s in shadowed]
        L.append("")

    L += ["---", "", "Üretici: `diagnostics/noise_units.py` · payda: "
          "`diagnostics/denominator_table.py::control_arms` (ithal) · eşleştirme: "
          "`diagnostics/t5_pairing_diff.py::build` (ithal)", ""]

    (OUT_DIR / "noise_units.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "noise_units.json").write_text(json.dumps({
        "item": "G4.5", "focus_mechanism": FOCUS, "sd_convention": SD_CONVENTION,
        "definition": "(|d_ece|/sigma_ece) / (|d_acc|/sigma_acc); sigma from that arm's own "
                      "control, per checkpoint",
        "nine_cell_grid": grid, "summary": summary, "per_cell_paired_sd": per_cell,
        # HAVUZ paydasi sonuclari JSON'a da yaziliyor: metnin "77"sinin karsiligi olan 73.1x
        # burada yasiyor ve tablo kapisi ancak JSON'da olani izleyebilir. Ilk surumde yalniz
        # md'ye render ediliyordu -- yani en cok korunmasi gereken sayi korumasizdi.
        "pooled": pooled,
        "shadowed_controls": shadowed,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
