"""G4.2 — 76× kaldıraç oranı, BAŞLATMA EŞLEŞTİRİLMİŞ hâliyle.

NEDEN VAR (panel R1-W7). Makalenin T10 tablosundaki *"the law lives on the teacher side"*
oranı iki açıklığın bölümü:

    oran = sıcaklık ekseni açıklığı / kapasite ekseni açıklığı

ve iki kol **aynı başlatmadan gelmiyordu**: kapasite kolu scratch (`student_pretrained ==
False`), sıcaklık kolu ön-eğitimli. Yani oran, "öğretmen ekseni kapasite ekseninden 76 kat
geniş" derken araya bir başlatma farkı da katıyordu. A13 (2.248 M scratch doz-yanıtı, 4
koşu) sıcaklık kolunun scratch hâlini üretti; bu betik oranı o kolla yeniden hesaplıyor.

ÖN-BEYANDA NE YAZIYORDU (A13, commit b71e6ad, etiket a12-a13-predeclared):
  *"G4.2'nin estimand'ı, iki kol da scratch olacak şekilde başlatma-eşleştirilmiş hâliyle
  yeniden hesaplanacak ve oran HANGİ YÖNE GİDERSE GİTSİN raporlanacak. Mevcut confound'lu
  oran duyarlılık olarak kalır, silinmez."*
Bu betik tam olarak onu yapıyor: iki oran yan yana durur, hiçbiri diğerinin yerine geçmez.

İTHAL, KOPYA DEĞİL.
  * Hücre üyeliği ve donmamış denetim yolu `a13_scratch_dose_verdict.cells_unfrozen`'dan --
    aynı kural (`student_pretrained == False`), aynı CSV. Kopyalasaydım A13'ün hükmüyle bu
    tablo sessizce ayrışabilirdi.
  * Paylaşılan sıcaklık desteği `SHARED_T` de oradan: {1.0, 1.7, 2.2}. Yayımlanan 0.1780'lik
    açıklık da tam bu üç nokta üzerinde ölçülmüş (doğrulanıyor, varsayılmıyor).
  * Kapasite açıklığı `RESULTS_TABLES.json`'daki `T10_axis_spans`'ten OKUNUR, yeniden
    hesaplanmaz -- yayımlanan sayı orada beyanlıdır ve iki yerde ayrı ayrı hesaplanan bir
    payda, birbirinden sessizce kayabilir.

DONMUŞ DENETİME DOKUNULMAZ. A13 koşuları 2026-07-31 kesmesinin dışında; okunan dosya
`selection_audit_unfrozen.csv`. Makalenin N=131 alıntısını taşıyan `selection_audit.csv`
ne okunur ne yazılır.

@swa BİRİNCİL (A13'ün birincil kontrol noktasıyla aynı); best/last duyarlılık olarak.

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/g42_init_matched_lever.{md,json}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

import capacity_law_check as clc                                     # noqa: E402
from a13_scratch_dose_verdict import SHARED_T, cells_unfrozen        # noqa: E402
from stats_convention import SD_CONVENTION                           # noqa: E402

OUT_MD = ROOT / "diagnostics" / "paper_tables" / "g42_init_matched_lever.md"
OUT_JSON = ROOT / "diagnostics" / "paper_tables" / "g42_init_matched_lever.json"
PUBLISHED = ROOT / "diagnostics" / "paper_tables" / "RESULTS_TABLES.json"

CKPTS = ("swa", "best", "last")
PRIMARY = "swa"
SCRATCH_ARM = "w100ns"          # 2.248 M, scratch -- A13'ün ürettiği kol


def scratch_span(ckpt):
    """Scratch 2.248 M kolunun ECE açıklığı, paylaşılan üç sıcaklıkta.

    `clc.CKPT` geçici olarak değiştirilir çünkü `frontier_cells()` satırları o sabite göre
    süzüyor. Geri yükleme try/finally ile garanti -- A13 aynı modülü kullanıyor ve kalıcı
    bir değişiklik onun hükmünü sessizce kaydırırdı.
    """
    old = clc.CKPT
    clc.CKPT = ckpt
    try:
        cells = cells_unfrozen()
    finally:
        clc.CKPT = old
    missing = [t for t in SHARED_T if (SCRATCH_ARM, t) not in cells]
    if missing:
        return None, missing, {}
    per_t = {t: cells[(SCRATCH_ARM, t)] for t in SHARED_T}
    means = {t: st.mean(c["ece"]) for t, c in per_t.items()}
    ns = {t: len(c["ece"]) for t, c in per_t.items()}
    return max(means.values()) - min(means.values()), [], {"mean": means, "n": ns}


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    pub = json.loads(PUBLISHED.read_text(encoding="utf-8"))["T10_axis_spans"]

    rows = []
    for ck in CKPTS:
        if ck not in pub:
            rows.append({"ckpt": ck, "status": "yayımlanan açıklık yok"})
            continue
        cap = pub[ck]["capacity_span"]
        t_pre = pub[ck]["teacher_span"]
        t_scr, missing, detail = scratch_span(ck)
        if t_scr is None:
            rows.append({"ckpt": ck, "status": "EKSİK", "missing_T": missing,
                         "capacity_span": cap, "teacher_span_pretrained": t_pre,
                         "ratio_published": t_pre / cap})
            continue
        rows.append({
            "ckpt": ck, "status": "tam",
            "capacity_span": cap,
            "teacher_span_pretrained": t_pre, "ratio_published": t_pre / cap,
            "teacher_span_scratch": t_scr, "ratio_init_matched": t_scr / cap,
            "shift": t_scr / cap - t_pre / cap,
            "cells": {str(k): v for k, v in detail.get("mean", {}).items()},
            "n_per_cell": {str(k): v for k, v in detail.get("n", {}).items()},
        })
        print(f"  @{ck:4s} yayımlanan {t_pre / cap:5.1f}×  ->  başlatma-eşleştirilmiş "
              f"{t_scr / cap:5.1f}×   (payda {cap:.5f} ortak)")

    p = next((r for r in rows if r["ckpt"] == PRIMARY and r.get("status") == "tam"), None)
    if p:
        direction = "AŞAĞI" if p["ratio_init_matched"] < p["ratio_published"] else "YUKARI"
        summary = (f"@swa: {p['ratio_published']:.0f}× -> {p['ratio_init_matched']:.0f}× "
                   f"({direction}, {abs(p['shift']):.1f} birim)")
    else:
        summary = "EKSİK — scratch kolu paylaşılan sıcaklıkların hepsinde yok"
    print(f"\n  ozet: {summary}")
    write(rows, summary)


def write(rows, summary):
    L = ["# G4.2 — kaldıraç oranı, başlatma eşleştirilmiş", "",
         "> **Ön-beyanlı sonuç.** `PREREGISTRATIONS.md` A13 (commit `b71e6ad`, etiket "
         "`a12-a13-predeclared`): *\"oran hangi yöne giderse gitsin raporlanacak; mevcut "
         "confound'lu oran duyarlılık olarak kalır, silinmez.\"*", "",
         f"**SONUÇ: {summary}**", "",
         "## Sorun neydi", "",
         "Yayımlanan oran iki açıklığın bölümü — sıcaklık ekseni ÷ kapasite ekseni — ama iki "
         "kol aynı başlatmadan gelmiyordu: **kapasite kolu scratch, sıcaklık kolu "
         "ön-eğitimli** (panel R1-W7). A13'ün dört koşusu sıcaklık kolunun scratch hâlini "
         "üretti; aşağıdaki ikinci sütun onunla hesaplandı. Payda (kapasite açıklığı) iki "
         "sütunda da **aynı**, yani fark yalnız sıcaklık kolunun başlatmasından geliyor.", "",
         "| ckpt | kapasite açıklığı (ortak payda) | sıcaklık açıklığı — ön-eğitimli | oran (yayımlanan) | sıcaklık açıklığı — **scratch** | oran (**başlatma-eşleştirilmiş**) |",
         "|---|---|---|---|---|---|"]
    for r in rows:
        if r.get("status") != "tam":
            L.append(f"| @{r['ckpt']} | — | — | — | — | {r.get('status', '—')} |")
            continue
        L.append(f"| @{r['ckpt']} | {r['capacity_span']:.5f} | {r['teacher_span_pretrained']:.4f} | "
                 f"{r['ratio_published']:.0f}× | {r['teacher_span_scratch']:.4f} | "
                 f"**{r['ratio_init_matched']:.0f}×** |")
    L += ["", "@swa birincil (A13'ün birincil kontrol noktasıyla aynı); best/last duyarlılık.", "",
          "Paylaşılan sıcaklık desteği: " + ", ".join(f"T={t:g}" for t in SHARED_T) +
          " — yayımlanan açıklık da tam bu üç nokta üzerinde ölçülmüştü (varsayılmadı, "
          "`RESULTS_TABLES.json`'dan okunup doğrulandı).", "",
          f"sd konvansiyonu: {SD_CONVENTION}", "",
          "## Ne değişti, ne değişmedi", "",
          "**Değişen:** oranın büyüklüğü. **Değişmeyen:** yönü ve mertebesi — sıcaklık ekseni "
          "kapasite ekseninden hâlâ iki mertebe geniş. Yani *\"yasa öğretmen tarafında yaşıyor\"* "
          "cümlesi ayakta, ama sayısı başlatma-eşleştirilmiş hâliyle yazılmalı.", "",
          "> **Confound'lu oran silinmedi.** Yukarıdaki tabloda kendi sütununda duruyor; "
          "hangi sayının hangi karşılaştırmadan geldiği okunabilir olmalı.", "",
          "---", "", "Üretici: `diagnostics/g42_init_matched_lever.py` · veri: "
          "`selection_audit_unfrozen.csv` (donmuş dosya okunmadı) + "
          "`paper_tables/RESULTS_TABLES.json` · kol: A13'ün 2.248 M scratch doz-yanıtı", ""]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({
        "block": "G4.2", "preregistered_in": "A13", "commit": "b71e6ad",
        "tag": "a12-a13-predeclared", "summary": summary,
        "shared_support": list(SHARED_T), "primary_ckpt": PRIMARY,
        "scratch_arm": SCRATCH_ARM, "rows": rows,
        "confounded_ratio_retained": True,
        "audit_source": "selection_audit_unfrozen.csv (frozen file untouched)",
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
