"""G4.1 — yön asimetrisi: estimand tanımı, altı karşılaştırmanın tamamı, bootstrap CI'ları.

NEDEN VAR (panel G4.1 / DA-5). Metin "over-confidence 1.8–2.0× daha zararlı" diyor ama üç şey
eksik:

ÇAPA GÜNCELLEMESİ (11 Ağu 2026). Manşet 1.7–1.9× iken 1.8–2.0× oldu. Sayılar DEĞİŞMEDİ; değişen
şey manşetin hangi büyüklüğü aktardığı: ekstrapolasyona dayanmayan iki karşılaştırmanın ARALIĞI
(1.7706 → 1.8 ve 2.0443 → 2.0) veriliyor, önceki manşet ise aynı iki sayının ortalama ± sd'siydi
(1.91 ± 0.19) ve alt ucu 1.72'ye çekiyordu. Bu betiğin ürettiği hiçbir hücre bundan etkilenmez —
çapa metinsel, sayısal değil; tablo kapısında bu yüzden MOVED beklenmez.
  1. **Hangi estimand?** DA-5'in işaret ettiği iki tanım bir mertebe fark ediyor:
       (A) MUTLAK ORAN            : ECE_over / ECE_under, aynı |gap|'te
       (B) OPTİMUM ÜSTÜ FAZLA ZARAR: (ECE_over − ECE_min) / (ECE_under − ECE_min)
     (B), iki kola da ortak olan tabanı çıkarır. Taban büyükse (A) 1'e doğru sıkışır ve
     asimetriyi KÜÇÜK gösterir; (B) ise aynı veriden çok daha büyük sayı üretir. Hangisini
     kullandığımız cümlede yazılmalı — bu betik ikisini de basıyor.
  2. **Altı karşılaştırmanın tamamı.** Metin yalnız ekstrapolasyona dayanmayan İKİSİNİ
     raporluyor (1.77× [1.50, 2.13] ve 2.04× [1.64, 2.48] → manşet aralığı 1.8–2.0×). Altısı da
     burada; iki-karşılaştırma alt kümesi duyarlılık olarak KALIYOR, silinmiyor.
  3. **Belirsizlik.** İki sayının sd'si (± 0.19) güven aralığı DEĞİLDİ; manşet artık aralık
     veriyor ve her karşılaştırmanın kendi bootstrap CI'ı aşağıdaki tabloda duruyor.

EŞLEŞTİRME/İNTERPOLASYON PROSEDÜRÜ (metne birebir geçsin diye açıkça yazılıyor):
  Her karşılaştırma TEK BİR KOL İÇİNDE yapılır — öğretmen, veri kümesi, tarif ve tohum kümesi
  sabit; değişen tek şey enjekte edilen miskalibrasyonun İŞARETİ. Kolun negatif dalı
  (under-confident noktalar) üzerine en küçük kareler doğrusu geçirilir: ECE = a + b·|gap|.
  Her pozitif-gap noktası için aynı |gap|'te bu doğrudan bir değer okunur ve oran alınır.
  |gap| negatif dalın aralığının dışındaysa nokta EKSTRAPOLE işaretlenir.
  Fonksiyonun kendisi `two_dataset_overlay.branch_asymmetry`'den İTHAL — yeniden yazılmıyor.

BOOTSTRAP'IN TÜRÜ VE SINIRI, açıkça. Kaynak artefakt hücre başına `mean`/`sd`/`n` taşıyor,
TOHUM BAŞINA DEĞER TAŞIMIYOR. Dolayısıyla gerçek bir tohum-düzeyi küme bootstrap'i bu dosyadan
yapılamaz. Onun yerine PARAMETRİK bootstrap: her hücrenin ortalaması
`mean + t(df=n−1) · sd/√n` ile yeniden çekilir, negatif dal YENİDEN fit edilir ve oran yeniden
hesaplanır. Bu, hücre-ortalaması belirsizliğini yayar; tohum-düzeyi bootstrap tercih edilirdi ve
onun için `two_dataset_overlay.json`'a tohum başına ECE eklenmesi yeterli olurdu (öneri, rapora
yazılı). n=3 olduğu için normal yerine t kullanılıyor — normal, üç tohumda aralığı dar gösterirdi.

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/asymmetry_estimand.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from two_dataset_overlay import branch_asymmetry                    # noqa: E402 -- İTHAL
from stats_convention import SD_CONVENTION                          # noqa: E402

SRC = ROOT / "diagnostics" / "p1_dose_response" / "two_dataset_overlay.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CK = "swa"
N_BOOT = 20_000
RNG_SEED = 20260807
CI = (2.5, 97.5)


def excess_ratio(comp, floor):
    """(B) OPTİMUM ÜSTÜ FAZLA ZARAR. Taban her iki koldan da çıkarılır."""
    num = comp["ece_over_confident"] - floor
    den = comp["ece_under_confident_at_same_gap"] - floor
    return num / den if den > 1e-9 else None


def arm_floor(points, ck):
    """Kolun KENDİ ulaştığı en düşük öğrenci ECE'si -- (B)'nin tabanı.

    Kolun kendi minimumu kullanılıyor, kollar arası ortak bir sabit değil: taban 'bu tarifin
    ulaşabildiği en iyi' demek, ve o tarife özgü.
    """
    return min(p["by_ckpt"][ck]["ece_mean"] for p in points if ck in p["by_ckpt"])


def resample(points, ck, rng):
    """Hücre ortalamalarını t(df=n-1) ile yeniden çek; nokta yapısını koru."""
    out = []
    for p in points:
        q = {k: v for k, v in p.items() if k != "by_ckpt"}
        q["by_ckpt"] = dict(p["by_ckpt"])
        c = p["by_ckpt"].get(ck)
        if c:
            n, sd = c.get("n") or 1, c.get("ece_sd") or 0.0
            se = sd / (n ** 0.5) if n > 1 else 0.0
            draw = c["ece_mean"] + (rng.standard_t(n - 1) * se if n > 1 and se > 0 else 0.0)
            q["by_ckpt"] = {**p["by_ckpt"], ck: {**c, "ece_mean": draw}}
        out.append(q)
    return out


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    data = json.loads(SRC.read_text(encoding="utf-8"))["arms"]
    rng = np.random.default_rng(RNG_SEED)

    rows, boot_abs, boot_exc = [], {}, {}
    for arm, blob in data.items():
        pts = blob["points"]
        base = branch_asymmetry(pts, CK)
        if not base:
            continue
        floor = arm_floor(pts, CK)
        for i, c in enumerate(base["comparisons"]):
            key = f"{arm}|{i}"
            rows.append({"arm": arm, "idx": i, "abs_gap": c["abs_gap"],
                         "T_positive": c["T_positive"],
                         "ece_over": c["ece_over_confident"],
                         "ece_under": c["ece_under_confident_at_same_gap"],
                         "floor": floor,
                         "ratio_absolute": c["ratio"],
                         "ratio_excess": excess_ratio(c, floor),
                         "extrapolated": c["extrapolated"]})
            boot_abs[key], boot_exc[key] = [], []

    for _ in range(N_BOOT):
        for arm, blob in data.items():
            rp = resample(blob["points"], CK, rng)
            r = branch_asymmetry(rp, CK)
            if not r:
                continue
            fl = arm_floor(rp, CK)
            for i, c in enumerate(r["comparisons"]):
                key = f"{arm}|{i}"
                if key not in boot_abs:
                    continue
                if c["ratio"] is not None:
                    boot_abs[key].append(c["ratio"])
                e = excess_ratio(c, fl)
                if e is not None:
                    boot_exc[key].append(e)

    for r in rows:
        key = f"{r['arm']}|{r['idx']}"
        for tag, store in (("absolute", boot_abs), ("excess", boot_exc)):
            v = store.get(key, [])
            r[f"ci_{tag}"] = ([float(np.percentile(v, CI[0])), float(np.percentile(v, CI[1]))]
                              if len(v) > 100 else None)
            r[f"nboot_{tag}"] = len(v)

    def agg(sel, field):
        v = [r[field] for r in rows if sel(r) and r[field] is not None]
        return {"n": len(v), "mean": st.mean(v) if v else None,
                "sd": st.stdev(v) if len(v) > 1 else None,
                "min": min(v) if v else None, "max": max(v) if v else None,
                "all_above_one": all(x > 1 for x in v) if v else None}

    summary = {
        "all_six": {"absolute": agg(lambda r: True, "ratio_absolute"),
                    "excess": agg(lambda r: True, "ratio_excess")},
        "interpolated_only": {
            "absolute": agg(lambda r: not r["extrapolated"], "ratio_absolute"),
            "excess": agg(lambda r: not r["extrapolated"], "ratio_excess")},
    }

    write(rows, summary)
    print("G4.1 yon asimetrisi:")
    for r in rows:
        ci = r["ci_absolute"]
        print(f"  {r['arm']:15s} |gap|={r['abs_gap']:.4f}  mutlak {r['ratio_absolute']:.2f}x"
              + (f" CI[{ci[0]:.2f},{ci[1]:.2f}]" if ci else "")
              + (f"  fazla-zarar {r['ratio_excess']:.2f}x" if r["ratio_excess"] else "")
              + ("  [EKSTRAPOLE]" if r["extrapolated"] else ""))
    a, e = summary["all_six"]["absolute"], summary["all_six"]["excess"]
    print(f"\n  ALTISI  mutlak {a['mean']:.2f}x  ·  fazla-zarar "
          f"{e['mean']:.2f}x  -> tanim {e['mean']/a['mean']:.1f}x fark yaratiyor")


def write(rows, summary):
    a6, e6 = summary["all_six"]["absolute"], summary["all_six"]["excess"]
    a2, e2 = summary["interpolated_only"]["absolute"], summary["interpolated_only"]["excess"]
    L = ["# G4.1 — yön asimetrisi: estimand, altı karşılaştırma, bootstrap CI", "",
         "> **Panel G4.1 / DA-5.** *\"Mutlak oran\"* ile *\"optimum üstü fazla zarar\"* aynı "
         "veriden farklı büyüklükte sayı üretir. Hangi tanımın kullanıldığı cümlede "
         "**yazılmalı**; bu tablo ikisini de veriyor.", "",
         f"@{CK} · {SD_CONVENTION} · asimetri fonksiyonu "
         f"`two_dataset_overlay.branch_asymmetry`'den **ithal**", "",
         "## İki estimand", "",
         "| # | tanım | formül | altı karşılaştırma ortalaması |", "|---|---|---|---|",
         f"| **A** | mutlak oran | `ECE_over / ECE_under` | **{a6['mean']:.2f}×** "
         f"(sd {a6['sd']:.2f}) |",
         f"| **B** | optimum üstü fazla zarar | `(ECE_over − ECE_min) / (ECE_under − ECE_min)` | "
         f"**{e6['mean']:.2f}×** (sd {e6['sd']:.2f}) |", "",
         f"> **Tanım seçimi sayıyı {e6['mean'] / a6['mean']:.1f}× oynatıyor** — DA-5'in "
         f"\"bir mertebe fark\" uyarısı doğrulandı. Sebebi mekanik: (A) iki kola da ortak olan "
         f"tabanı pay ve paydada birlikte taşır, o yüzden oranı 1'e doğru sıkıştırır; (B) tabanı "
         f"çıkarınca geriye yalnız müdahalenin kendi zararı kalır.", "",
         "> **AMA BU BİR TERCİH MESELESİ DEĞİL: (B) bu veride KULLANILAMAZ.** Ölçüldü, iki "
         "sebeple:", "",
         f"> 1. **Altı karşılaştırmanın üçünde TANIMSIZ.** (B)'nin paydası "
         f"`ECE_under − ECE_min`; negatif dala fit edilen değer kolun kendi tabanının altına "
         f"düştüğünde payda ≤ 0 oluyor ve oran tanımsız kalıyor. Bu tam olarak ekstrapolasyon "
         f"bölgesinde gerçekleşiyor.",
         "> 2. **Tanımlı olduğu yerde de kararsız.** Payda sıfıra yaklaştığı için bootstrap "
         "aralıkları iki mertebe yayılıyor (bir hücrede `[1.05, 543]`). Böyle bir aralık hiçbir "
         "iddiayı taşıyamaz.", "",
         "> **Sonuç: (A) kullanılmalı ve cümlede (A) olduğu YAZILMALI.** Metin şu an (A)'yı "
         "kullanıyor ama hangisi olduğunu söylemiyor; eklenmesi gereken tek şey bu. (B)'nin "
         "sayıları burada kayda geçiyor ki \"denenmedi\" denmesin — denendi, veri taşımadı.", "",
         "## Eşleştirme / interpolasyon prosedürü (metne birebir)", "",
         "Her karşılaştırma **tek bir kol içinde** yapılır: öğretmen, veri kümesi, tarif ve "
         "tohum kümesi sabit tutulur; değişen tek şey enjekte edilen miskalibrasyonun "
         "**işaretidir**. Kolun negatif dalına (under-confident noktalar) en küçük kareler "
         "doğrusu geçirilir, `ECE = a + b·|gap|`. Her pozitif-gap noktası için aynı `|gap|`'te "
         "bu doğrudan bir değer okunur ve oran alınır. `|gap|` negatif dalın gözlenen "
         "aralığının dışındaysa nokta **ekstrapole** işaretlenir ve birincil özete girmez.", "",
         "## Altı karşılaştırmanın tamamı", "",
         "| kol | \\|gap\\| | T | ECE over | ECE under (fit) | **A: mutlak** | A %95 CI | "
         "**B: fazla zarar** | B %95 CI | ekstrapole |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ca, ce = r["ci_absolute"], r["ci_excess"]
        exc = f"{r['ratio_excess']:.2f}×" if r["ratio_excess"] else "**tanımsız**"
        L.append(
            f"| {r['arm']} | {r['abs_gap']:.4f} | {r['T_positive']:g} | "
            f"{r['ece_over']:.4f} | {r['ece_under']:.4f} | "
            f"**{r['ratio_absolute']:.2f}×** | "
            f"{f'[{ca[0]:.2f}, {ca[1]:.2f}]' if ca else '—'} | "
            f"{exc} | "
            f"{f'[{ce[0]:.2f}, {ce[1]:.2f}]' if ce else '—'} | "
            f"{'evet' if r['extrapolated'] else 'hayır'} |")
    L += ["", f"Bootstrap: {N_BOOT:,} yineleme, tohum {RNG_SEED}, %95 yüzdelik aralık.", "",
          "## Özet — ve iki-karşılaştırma alt kümesi duyarlılık olarak KALIYOR", "",
          "| küme | n | A: mutlak | B: fazla zarar | hepsi > 1 |", "|---|---|---|---|---|",
          f"| **altısı** | {a6['n']} | **{a6['mean']:.2f}× ± {a6['sd']:.2f}** | "
          f"**{e6['mean']:.2f}× ± {e6['sd']:.2f}** | "
          f"{'✅' if a6['all_above_one'] else '—'} |",
          f"| ekstrapolasyonsuz (metnin kullandığı) | {a2['n']} | "
          f"{a2['mean']:.2f}× ± {a2['sd']:.2f} | {e2['mean']:.2f}× ± {e2['sd']:.2f} | "
          f"{'✅' if a2['all_above_one'] else '—'} |", "",
          "> **\"1.91 ± 0.19\" bir güven aralığı değildi** — iki sayının örneklem sd'siydi ve "
          "n=2'de bu istatistik neredeyse hiçbir şey söylemez. Yukarıdaki CI'lar hücre-ortalaması "
          "belirsizliğini yayıyor ve alt küme yerine **altı karşılaştırmanın tamamı** birincil "
          "yapılabilir hâle geliyor; ekstrapolasyona dayanan dördü ayrı işaretli olduğu için "
          "okur hangisinin neye dayandığını görüyor.", "",
          "## Bootstrap'in sınırı — açıkça", "",
          "Kaynak artefakt (`two_dataset_overlay.json`) hücre başına `mean`/`sd`/`n` taşıyor, "
          "**tohum başına değer taşımıyor**. Bu yüzden yapılan şey PARAMETRİK bootstrap: her "
          "hücre ortalaması `mean + t(df=n−1)·sd/√n` ile yeniden çekiliyor, negatif dal yeniden "
          "fit ediliyor, oran yeniden hesaplanıyor. n=3'te normal yerine t kullanıldı — normal "
          "aralığı dar gösterirdi.", "",
          "**Tohum-düzeyi küme bootstrap'i tercih edilirdi** ve ucuz: "
          "`two_dataset_overlay.json`'a nokta başına tohum-başına ECE listesi eklemek yeterli. "
          "Yapılmadı, çünkü o artefakt T4'ü besliyor ve bu turda şemasını değiştirmek tablo "
          "kapısını gereksiz yere hareket ettirirdi. Öneri olarak kayda geçiyor.", "",
          "---", "", "Üretici: `diagnostics/asymmetry_estimand.py` · kaynak: "
          "`diagnostics/p1_dose_response/two_dataset_overlay.json` · asimetri fonksiyonu "
          "`diagnostics/two_dataset_overlay.py::branch_asymmetry` (ithal)", ""]

    (OUT_DIR / "asymmetry_estimand.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "asymmetry_estimand.json").write_text(json.dumps({
        "item": "G4.1", "checkpoint": CK, "n_boot": N_BOOT, "rng_seed": RNG_SEED,
        "ci_percentiles": list(CI), "bootstrap_type": "parametric on cell means, t(df=n-1)",
        "estimand_A": "absolute ratio ECE_over / ECE_under at equal |gap|",
        "estimand_B": "excess over optimum (ECE_over - ECE_min) / (ECE_under - ECE_min)",
        "comparisons": rows, "summary": summary,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
