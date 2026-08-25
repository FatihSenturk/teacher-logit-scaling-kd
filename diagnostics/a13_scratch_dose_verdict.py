"""A13 hükmü: 2.248 M scratch doz-yanıtı — eğim başlatmaya mı, kapasiteye mi duyarlı?

NE TEST EDİLİYOR. B4'ün eğim karşılaştırması iki değişkeni birden oynatıyordu: `b_w050`
scratch ve 0.712 M, `b_2248` ön-eğitimli ve 2.248 M. Confound koşulardan önce yazılıydı ve
ayrıştırmanın 2.248 M'de scratch bir doz-yanıtı gerektirdiği de. A13 tam o dört koşu. Aynı
uyuşmazlık 76×'lik kaldıraç oranında da var (panel R1-W7): kapasite kolu scratch, sıcaklık
kolu ön-eğitimli.

DONMUŞ PLAN — B4'ten harfiyen devralındı (PREREGISTRATIONS A12/A13, commit b71e6ad, etiket
a12-a13-predeclared). Bu betik ilk sonuç okunmadan commit'lendi.

  1. Eğim AYNI ÜÇ SICAKLIKTA fit edilir: T ∈ {1.0, 1.7, 2.2}. 5-noktalı fit'e karşı 3-noktalı
     fit koymak kapasiteyi fit desteğiyle karıştırırdı.
  2. Belirsizlik en-kötü-durum tohum-gürültüsü ZARFI'dır, GÜVEN ARALIĞI DEĞİL. İki hücre n=2,
     tek serbestlik derecesi; eğime hata çubuğu uydurulmaz.
  3. Hücre başına TOHUM TEKİLLİĞİ kapısı: bir kapasite hücresinde aynı tohumdan iki koşu
     bulunması tanım gereği ikinci bir değişkenin hareket ettiği anlamına gelir → RuntimeError.

Fit ve zarf matematiği `capacity_law_check`'ten İTHAL — yeniden yazılmıyor, aynı kod yolu.

TAHMİN (sayı görülmeden): başlatma karşılaştırması zarfın DIŞINA ÇIKMAYACAK — eğim,
öğrencinin başlatmasının değil öğretmenin kalibrasyonunun yönettiği bir büyüklük.
YANLIŞLAYICI: |b_scratch2248 − b_pretrained2248| iki zarfın toplamını aşarsa, "yasa öğrenci
artefaktı değil" savunması başlatma ekseninde ayrıca savunulmak zorunda kalır.

"EĞİM KAPASİTEYLE DEĞİŞMİYOR" CÜMLESİ HİÇBİR SONUÇTA YAZILMAYACAK. Zarf bir eşdeğerlik testi
değildir; çözünmemek yokluk göstermez.

DONMUŞ DENETİM DOSYASINA DOKUNULMAZ. A13 koşuları 2026-07-31 kesmesinin dışında; hüküm
`selection_audit_unfrozen.csv`'den okunur. Makalenin N=131 alıntısını taşıyan
`selection_audit.csv` bu betik tarafından ne okunur ne yazılır.

Salt-okunur, GPU yok. Çıktı -> diagnostics/a13_scratch_dose/a13_verdict.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

import capacity_law_check as clc                                  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd             # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "a13_scratch_dose"
OUT_DIR.mkdir(parents=True, exist_ok=True)
UNFROZEN = ROOT / "diagnostics" / "selection_audit" / "selection_audit_unfrozen.csv"

SHARED_T = (1.0, 1.7, 2.2)
CKPT = "swa"


def cells_unfrozen():
    """clc.frontier_cells(), ama donmamış denetim dosyasından.

    Üyelik kuralı (`student_pretrained == False`) ve hücre etiketleri clc'nin kendi
    fonksiyonundan geliyor; değişen tek şey okunan CSV. Donmuş dosya yerinde kalıyor --
    geri yükleme try/finally ile garanti.
    """
    old = clc.AUDIT
    clc.AUDIT = UNFROZEN
    try:
        return clc.frontier_cells()
    finally:
        clc.AUDIT = old


def seed_uniqueness_gate(cells):
    """B4'ün 3. şartı: bir hücrede aynı tohumdan iki koşu = ikinci bir değişken hareket ediyor."""
    for (w, t), c in sorted(cells.items()):
        if len(set(c["seeds"])) != len(c["seeds"]):
            raise RuntimeError(
                f"({w}, T={t:g}) hücresinde tohum tekrarı var: {sorted(c['seeds'])}. "
                f"Bu, hücrede tohum dışında bir değişkenin de oynadığı anlamına gelir; "
                f"eğim fit edilmez.")


def fit(xs, ys, sds):
    b, a, r2 = clc.linfit(xs, ys)
    return {"slope": b, "intercept": a, "r2": r2, "envelope": clc.slope_envelope(xs, sds),
            "cell_ece_mean": ys, "cell_ece_sd": sds}


def compare(name, left, right, isolates):
    d = left["slope"] - right["slope"]
    env = left["envelope"] + right["envelope"]
    return {"name": name, "isolates": isolates, "d_slope": d, "combined_envelope": env,
            "resolvable": abs(d) > env,
            "note": "zarf güven aralığı DEĞİLDİR; çözünmemek yokluk göstermez"}


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    pts = [p for p in json.loads(clc.OVERLAY.read_text())["arms"]["rafdb_vae9182"]["points"]
           if CKPT in p.get("by_ckpt", {})]
    tece = {p["T"]: p["teacher_ece"] for p in pts}
    big = {p["T"]: p["by_ckpt"][CKPT] for p in pts}

    cells = cells_unfrozen()
    seed_uniqueness_gate(cells)

    have = {t: ("w100ns", t) in cells for t in SHARED_T}
    missing_T = [t for t, ok in have.items() if not ok]
    n_new = sum(len(cells[("w100ns", t)]["ece"]) for t in SHARED_T if have[t] and t != 1.0)

    xs = [tece[t] for t in SHARED_T]
    small = {t: cells[("w050", t)] for t in SHARED_T}
    f_small = fit(xs, [st.mean(small[t]["ece"]) for t in SHARED_T],
                  [sample_sd(small[t]["ece"]) for t in SHARED_T])
    f_bigpre = fit(xs, [big[t]["ece_mean"] for t in SHARED_T], [big[t]["ece_sd"] for t in SHARED_T])

    comparisons, f_bigscr = [], None
    if not missing_T:
        scr = {t: cells[("w100ns", t)] for t in SHARED_T}
        f_bigscr = fit(xs, [st.mean(scr[t]["ece"]) for t in SHARED_T],
                       [sample_sd(scr[t]["ece"]) for t in SHARED_T])
        comparisons = [
            compare("scratch2248 vs pretrained2248", f_bigscr, f_bigpre, "BAŞLATMA"),
            compare("scratch2248 vs scratch0712", f_bigscr, f_small, "KAPASİTE"),
            compare("pretrained2248 vs scratch0712", f_bigpre, f_small,
                    "ikisi birden (B4'ün mevcut, confound'lu karşılaştırması)"),
        ]

    if missing_T:
        summary = (f"EKSİK — w100ns'te T={[f'{t:g}' for t in missing_T]} hücresi yok "
                   f"({n_new}/4 yeni koşu diskte); hüküm yazılmaz")
    else:
        init = comparisons[0]
        cap = comparisons[1]
        parts = []
        parts.append("BAŞLATMA TAHMİNİ YANLIŞLANDI — eğim başlatmaya duyarlı"
                     if init["resolvable"] else
                     "BAŞLATMA TAHMİNİ TUTTU — eğim farkı başlatmayla açıklanmıyor")
        parts.append("T10a (ii) ARTIK SONUÇLU: eğim farkı kapasiteye atfedilebilir"
                     if cap["resolvable"] else
                     "T10a (ii) SONUÇSUZ KALIYOR — ama artık confound yüzünden değil, gürültü yüzünden")
        summary = " · ".join(parts)

    write(summary, missing_T, n_new, f_small, f_bigpre, f_bigscr, comparisons, cells, tece)
    print(f"A13: yeni kosu {n_new}/4 diskte" + (f", eksik T={missing_T}" if missing_T else ""))
    print(f"ozet: {summary}")


def write(summary, missing_T, n_new, f_small, f_bigpre, f_bigscr, comparisons, cells, tece):
    L = ["# A13 — 2.248 M scratch doz-yanıtı", "",
         "> **ÖN-BEYANLI.** `PREREGISTRATIONS.md` A13, commit `b71e6ad`, etiket "
         "`a12-a13-predeclared`. Analiz planı B4'ten harfiyen devralındı; tahmin ve üç "
         "sonuç-cümlesi koşulardan önce yazıldı. Bu betik de ilk sonuç okunmadan commit'lendi.",
         "", f"**HÜKÜM: {summary}**", "",
         f"Üretici: `diagnostics/a13_scratch_dose_verdict.py` · @{CKPT} · {SD_CONVENTION} · "
         f"fit ve zarf `capacity_law_check`'ten ithal", "",
         "> **Donmuş denetim dosyasına dokunulmadı.** A13 koşuları 2026-07-31 kesmesinin "
         "dışında; hüküm `selection_audit_unfrozen.csv`'den okundu. Makalenin N=131 alıntısını "
         "taşıyan `selection_audit.csv` ne okundu ne yazıldı.", "",
         "## Üç eğim, aynı üç sıcaklıkta", "",
         "| kol | başlatma | kapasite | eğim b | R² | zarf |", "|---|---|---|---|---|---|"]
    rows = [("w050", "scratch", "0.712 M", f_small),
            ("2248 ön-eğitimli", "ön-eğitimli", "2.248 M", f_bigpre)]
    if f_bigscr:
        rows.append(("w100ns", "**scratch**", "2.248 M", f_bigscr))
    for lab, init, cap, f in rows:
        L.append(f"| {lab} | {init} | {cap} | **{f['slope']:.3f}** | {f['r2']:.5f} | "
                 f"±{f['envelope']:.3f} |")
    L += ["", "Fit desteği üç sıcaklıkta da aynı (T = 1.0 / 1.7 / 2.2) — 5-noktalı fit'e karşı "
              "3-noktalı fit koymak kapasiteyi fit desteğiyle karıştırırdı (B4'ün 1. şartı).", ""]

    if missing_T:
        L += [f"> **EKSİK.** `w100ns` kolunda T={', '.join(f'{t:g}' for t in missing_T)} hücresi "
              f"henüz yok ({n_new}/4 yeni koşu diskte). Üç noktadan azıyla eğim fit edilmez; "
              f"karşılaştırmalar koşular bitince yazılacak.", ""]
    else:
        L += ["## Üç karşılaştırma", "",
              "| karşılaştırma | izole ettiği | Δb | birleşik zarf | çözünüyor mu |",
              "|---|---|---|---|---|"]
        for c in comparisons:
            L.append(f"| {c['name']} | **{c['isolates']}** | {c['d_slope']:+.3f} | "
                     f"±{c['combined_envelope']:.3f} | "
                     f"{'✅ evet' if c['resolvable'] else '❌ hayır'} |")
        L += ["", "**Zarf bir güven aralığı DEĞİLDİR.** İki hücrede n=2, tek serbestlik "
                  "derecesi. Zarf, yalnız tohum gürültüsünün fit edilen eğimi en çok ne kadar "
                  "oynatabileceğinin bir sınırıdır. **\"Eğim kapasiteyle değişmiyor\" cümlesi "
                  "yazılmayacak** — çözünmemek yokluk göstermez.", ""]

    L += ["## Hücre envanteri (scratch kolu)", "",
          "| kapasite | T | öğretmen ECE | n | öğrenci ECE ort | sd | tohumlar |",
          "|---|---|---|---|---|---|---|"]
    for (w, t), c in sorted(cells.items(), key=lambda kv: (kv[1]["params_m"], kv[0][1])):
        sd = sample_sd(c["ece"]) if len(c["ece"]) > 1 else None
        L.append(f"| {c['params_m']:.3f} M ({w}) | {t:g} | "
                 f"{tece.get(t, float('nan')):.4f} | {len(c['ece'])} | "
                 f"{st.mean(c['ece']):.4f} | {f'{sd:.4f}' if sd else '—'} | "
                 f"{sorted(c['seeds'])} |")
    L += ["", "Tohum tekilliği kapısı geçildi: hiçbir hücrede aynı tohumdan iki koşu yok "
              "(olsaydı hüküm `RuntimeError` ile dururdu — tekrar, hücrede tohum dışında bir "
              "değişkenin de oynadığı anlamına gelirdi).", ""]

    (OUT_DIR / "a13_verdict.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "a13_verdict.json").write_text(json.dumps({
        "preregistered": True, "block": "A13", "commit": "b71e6ad",
        "tag": "a12-a13-predeclared", "summary": summary,
        "complete": not missing_T, "new_runs_on_disk": n_new, "missing_T": missing_T,
        "shared_support": list(SHARED_T), "sd_convention": SD_CONVENTION,
        "audit_source": "selection_audit_unfrozen.csv (frozen file untouched)",
        "envelope_is_not_a_confidence_interval": True,
        "fits": {"scratch0712": f_small, "pretrained2248": f_bigpre, "scratch2248": f_bigscr},
        "comparisons": comparisons,
    }, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
