"""B3(a) + B6 — 27× ailesinin paydaları, ve ölçütün minimum saptanabilir etkisi.

İKİ SORU, TEK KAYNAK. Round-3'ün iki maddesi aynı 18 sayıyı istiyor ve ayrı ayrı üretmek
onların ayrışmasına davetiye olurdu:

  B3(a) "27×/23×/52×/2.6× ailesini okuyucu yeniden hesaplayabilsin" — o aile
        `noise_units.py`'de (|ΔECE|/σ_ECE) ÷ (|Δacc|/σ_acc) olarak kuruluyor ve
        PAYDALARI burada duran kontrol-kolu tohum sd'leri. Yayımda oranlar var,
        paydalar yok; oran yeniden hesaplanamıyor.
  B6    "12 unresolved hücre yorumlanabilsin" — ölçüt |Δ| ≥ 2σ_kontrol olduğuna göre
        **2σ**, o hücrede saptanabilecek EN KÜÇÜK etkidir. Bir hücrenin "unresolved"
        olması "etki yok" demek değil, "bu tabanın altında kalıyor" demektir; taban
        yazılmadan cümle yorumlanamaz.

18 SAYI NEREDEN GELİYOR. Ölçüt tek bir kontrol kolu tanımına dayanıyor
(`paper_tables.is_ablation_control`) ve o kol her öğretmen için İKİ sınıf-ağırlığı
modunda var. 27× ailesi `logit_std` mekanizmasından üretiliyor, o da
`effective_number` modunda koşuyor — dolayısıyla ailenin paydaları
**3 öğretmen × 3 checkpoint × 2 eksen = 18**. Diğer mod (`none`, gate kollarının
kontrolü) ayrıca basılıyor: 12 unresolved hücrenin beşi gate hücresi ve onların tabanı
o moddan gelir. Toplam 36 sayı; hangisinin hangi soruya ait olduğu sütunda yazılı.

ORANLAR SAĞLAMA OLARAK YENİDEN KURULUYOR. Tablo yalnız paydaları basmıyor; aynı
paydalarla `logit_std` ailesinin dokuz oranını yeniden hesaplayıp `noise_units.json`
ile karşılaştırıyor. Sayılar tutmuyorsa bu betik durur — iki üretici arasında sessiz
bir ayrışma, tam olarak bu tablonun kapatmak için var olduğu şey.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/control_sd_mde.{md,json}
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from paper_tables import A_AUDIT_MECH, CKPTS, TEACHERS, load_audit, load_runs  # noqa: E402
from denominator_table import control_arms  # noqa: E402  -- TEK KAYNAK: payda tanımı
from stats_convention import SD_CONVENTION  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
THRESHOLD = 2.0                       # ölçütün eşiği; criterion_applied.py ile aynı sayı
FAMILY_CW = "effective_number"        # 27× ailesinin koştuğu sınıf-ağırlığı modu


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    runs, audit = load_runs(), load_audit(A_AUDIT_MECH)
    rows = []
    for ck in CKPTS:
        arms = control_arms(runs, audit, ck=ck)
        for (t, cw), v in sorted(arms.items()):
            for axis, sd_key, mean_key in (("ece", "ece_sd", "ece_mean"),
                                           ("acc", "acc_sd", "acc_mean")):
                sd, level = v[sd_key], v[mean_key]
                rows.append({
                    "checkpoint": ck, "teacher": t, "class_weight_mode": cw, "axis": axis,
                    "control_sd": sd, "control_level": level, "n": v["n"],
                    "seeds": v["seeds"], "mde_2sd": THRESHOLD * sd,
                    "mde_pct_of_level": 100.0 * THRESHOLD * sd / level if level else None,
                    "in_27x_family": (cw == FAMILY_CW)})

    fam = [r for r in rows if r["in_27x_family"]]
    ece_swa = [r for r in rows if r["axis"] == "ece" and r["checkpoint"] == "swa"]
    mde_all = [r["mde_2sd"] for r in rows if r["axis"] == "ece"]
    mde_swa = [r["mde_2sd"] for r in ece_swa]
    pct_swa = [r["mde_pct_of_level"] for r in ece_swa]

    check = crosscheck(rows)
    write(rows, fam, check, mde_swa, pct_swa, mde_all)

    print("=== control_sd_mde ===")
    print(f"  payda satiri            : {len(rows)}  "
          f"(27x ailesinin paydasi: {len(fam)})")
    print(f"  2sd (ECE) @swa araligi  : {min(mde_swa):.4f} .. {max(mde_swa):.4f}")
    print(f"  ...kontrol duzeyine oran: %{min(pct_swa):.1f} .. %{max(pct_swa):.1f}")
    print(f"  2sd (ECE) uc ckpt hepsi : {min(mde_all):.4f} .. {max(mde_all):.4f}")
    print(f"  noise_units capraz kont.: {check['verdict']} "
          f"(en buyuk sapma {check['max_dev']:.2e})")
    return 0 if check["ok"] else 1


def crosscheck(rows):
    """Aynı paydalarla `noise_units`'in dokuz oranını yeniden kur ve karşılaştır."""
    p = OUT_DIR / "noise_units.json"
    if not p.exists():
        return {"ok": True, "verdict": "noise_units.json yok — atlandı", "max_dev": 0.0,
                "cells": []}
    nu = json.loads(p.read_text(encoding="utf-8"))
    sd = {(r["checkpoint"], r["teacher"], r["class_weight_mode"], r["axis"]): r["control_sd"]
          for r in rows}
    cells, dev = [], 0.0
    for key, g in (nu.get("nine_cell_grid") or {}).items():
        if not g or "ratio" not in g:
            continue
        ck, t = key.split("|")
        s_e = sd.get((ck, t, FAMILY_CW, "ece"))
        s_a = sd.get((ck, t, FAMILY_CW, "acc"))
        if not s_e or not s_a or not g.get("d_acc_mean"):
            continue
        mine = (abs(g["d_ece_mean"]) / s_e) / (abs(g["d_acc_mean"]) / s_a)
        d = abs(mine - g["ratio"])
        dev = max(dev, d)
        cells.append({"checkpoint": ck, "teacher": t, "noise_units": g["ratio"],
                      "rebuilt": mine, "dev": d})
    ok = dev < 1e-9
    return {"ok": ok, "max_dev": dev, "cells": cells,
            "verdict": "GEÇTİ" if ok else "AYRIŞMA"}


def write(rows, fam, check, mde_swa, pct_swa, mde_all):
    L = ["# B3(a) + B6 — kontrol tohum sd'leri (paydalar) ve ölçütün minimum "
         "saptanabilir etkisi", "",
         f"Üretici: `diagnostics/control_sd_mde.py` · {SD_CONVENTION} · payda tanımı "
         f"`denominator_table.control_arms()`'tan **ithal**", "",
         "> İki soru aynı 18 sayıya bakıyor. **B3(a):** yayımda 27×/23×/52×/2.6× oranları "
         "var ama paydaları yok, yani okuyucu oranı yeniden kuramıyor. **B6:** ölçüt "
         "`|Δ| ≥ 2σ_kontrol` olduğuna göre **2σ**, o hücrede saptanabilecek en küçük "
         "etkidir — `unresolved` bir hücre \"etki yok\" demek değil, **\"bu tabanın "
         "altında\"** demektir, ve taban yazılmadan cümle yorumlanamaz.", "",
         "## Özet", "", "| kalem | değer |", "|---|---|",
         f"| payda satırı (öğretmen × checkpoint × eksen × sınıf-ağırlığı) | {len(rows)} |",
         f"| bunların 27× ailesine ait olanı (`{FAMILY_CW}`) | **{len(fam)}** |",
         f"| **2σ (ECE) @swa** — ölçütün tabanı | **{min(mde_swa):.4f} … "
         f"{max(mde_swa):.4f}** |",
         f"| aynı taban, kontrol kolunun ECE düzeyine oran | **%{min(pct_swa):.1f} … "
         f"%{max(pct_swa):.1f}** |",
         f"| 2σ (ECE), üç checkpoint birlikte | {min(mde_all):.4f} … {max(mde_all):.4f} |",
         "", "---", "",
         "## 1 · Paydalar — 27× ailesinin 18 sayısı", "",
         f"`logit_std` `{FAMILY_CW}` modunda koştuğu için ailenin paydaları o kontrol "
         f"kolundan gelir: **3 öğretmen × 3 checkpoint × 2 eksen = 18**. Aile dışındaki "
         f"18 sayı (`none` kolu) hemen altında — 12 `unresolved` hücrenin beşi gate "
         f"hücresi ve onların tabanı o koldan çıkar.", "",
         "| ckpt | öğretmen | cw | eksen | kontrol düzeyi | **σ (payda)** | n | tohumlar | "
         "27× ailesi |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        fmt = "{:.4f}" if r["axis"] == "ece" else "{:.3f}"
        L.append(f"| {r['checkpoint']} | {r['teacher']} | `{r['class_weight_mode']}` | "
                 f"{r['axis'].upper()} | {fmt.format(r['control_level'])} | "
                 f"**{fmt.format(r['control_sd'])}** | {r['n']} | {r['seeds']} | "
                 f"{'✅' if r['in_27x_family'] else '—'} |")

    L += ["", "### Çapraz kontrol — aynı paydalarla `noise_units`'in dokuz oranı", "",
          f"Paydalar basılmakla kalmıyor, oranlar bu paydalardan **yeniden kuruluyor** ve "
          f"`noise_units.json` ile karşılaştırılıyor. Sonuç: **{check['verdict']}**, en "
          f"büyük sapma `{check['max_dev']:.2e}`. Tutmasaydı bu betik çıkış kodu 1 "
          f"verirdi — iki üretici arasında sessiz ayrışma, bu tablonun kapatmak için var "
          f"olduğu şeyin ta kendisi.", ""]
    if check["cells"]:
        L += ["| ckpt | öğretmen | `noise_units` | buradan yeniden kurulan | sapma |",
              "|---|---|---|---|---|"]
        L += [f"| {c['checkpoint']} | {c['teacher']} | {c['noise_units']:.4f}× | "
              f"{c['rebuilt']:.4f}× | {c['dev']:.2e} |" for c in check["cells"]]
        L += [""]

    L += ["## 2 · B6 — ölçütün minimum saptanabilir etkisi (2σ)", "",
          "Aynı satırlar, bu kez ölçüt tarafından okunuşuyla. **2σ**, o öğretmen-checkpoint "
          "hücresinde ölçütün `established` diyebileceği en küçük |Δ|'dır; ikinci sütun onu "
          "kontrol kolunun kendi düzeyine oranlar, çünkü ECE 0.028 olan bir öğrenci ile "
          "0.075 olan bir öğrenci için aynı mutlak taban aynı şeyi ifade etmez.", "",
          "| ckpt | öğretmen | cw | eksen | **2σ (mutlak)** | kontrol düzeyi | "
          "**2σ / düzey** |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        fmt = "{:.4f}" if r["axis"] == "ece" else "{:.3f}"
        L.append(f"| {r['checkpoint']} | {r['teacher']} | `{r['class_weight_mode']}` | "
                 f"{r['axis'].upper()} | **{fmt.format(r['mde_2sd'])}** | "
                 f"{fmt.format(r['control_level'])} | "
                 f"**%{r['mde_pct_of_level']:.1f}** |")
    L += ["", f"> @swa, ECE ekseninde taban **{min(mde_swa):.4f} … {max(mde_swa):.4f}**, "
          f"yani kontrol kolunun kendi ECE düzeyinin **%{min(pct_swa):.1f} … "
          f"%{max(pct_swa):.1f}**'i. `unresolved` bir hücre için söylenebilecek doğru "
          f"cümle şu: *bu tasarım, o hücrede bu büyüklüğün altındaki bir etkiyi üç tohumla "
          f"ayırt edemez.* @best ve @last'te taban daha yüksek — kontrol kolunun tohum "
          f"yayılımı o checkpoint'lerde daha geniş, yani aynı ölçüt orada daha kördür.", "",
          "---", "",
          "Üretici: `diagnostics/control_sd_mde.py` · payda: "
          "`diagnostics/denominator_table.py::control_arms` (ithal) · eşik "
          f"{THRESHOLD:g}× (`criterion_applied.py` ile aynı sabit)", ""]

    (OUT_DIR / "control_sd_mde.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "control_sd_mde.json").write_text(json.dumps({
        "sd_convention": SD_CONVENTION, "threshold": THRESHOLD,
        "family_class_weight_mode": FAMILY_CW, "rows": rows,
        "n_family_denominators": len(fam), "crosscheck": check,
        "mde_ece_swa_min": min(mde_swa), "mde_ece_swa_max": max(mde_swa),
        "mde_ece_swa_pct_min": min(pct_swa), "mde_ece_swa_pct_max": max(pct_swa),
        "mde_ece_all_min": min(mde_all), "mde_ece_all_max": max(mde_all),
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
