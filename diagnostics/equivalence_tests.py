"""G3.4 — TOST eşdeğerlik testleri: "ayırt edilemez" iddialarının denetlenmesi.

İTİRAZ (Round-2 panel). Makale iki yerde "istatistiksel olarak ayırt edilemez" diyor:
  (a) oracle kapısının DOĞRULUK null'ları — oracle kolunun "hatadan haberdar tanı" (11 Ağu 2026
      çerçevesi; öncesi "üst sınır" idi) iddiasını taşıyorlar. Fark önemsiz değil: null'lar
      hatadan TÜRETİLEN sinyaller için konuşur, teacher-variance/girdi-zorluğu gibi hatadan
      türetilmeyenler kapsam dışıdır ve ayrıca sınanır (A12);
  (b) §5.7'de öğrenci-tarafı TS ile öğretmen-tarafı T* kolunun ECE'si.
Ama ikisi de yüksek p değerinden çıkarılmış. Yüksek p **eşdeğerlik kanıtı değildir**; yalnız
farkın kanıtlanamadığını söyler. n=3'te bu ayrım kritik: güç o kadar düşüktür ki hiçbir şey
kanıtlanamaz ve her karşılaştırma "ayırt edilemez" görünür.

TOST (two one-sided tests) doğru aracı sağlar: eşdeğerlik İDDİA EDİLECEKSE önce bir marj
ilan edilir, sonra farkın o marjın İÇİNDE olduğu gösterilir.
  H01: mu <= -delta   ->  t1 = (ort + delta)/SE,  p1 = P(T > t1)
  H02: mu >= +delta   ->  t2 = (ort - delta)/SE,  p2 = P(T < t2)
  p_TOST = max(p1, p2);  p_TOST < alpha ise EŞDEĞERLİK KURULDU.
Denk ifade: (1-2*alpha) güven aralığı tümüyle (-delta, +delta) içinde kalmalı.

MARJ, SONUÇ GÖRÜLMEDEN İLAN EDİLİYOR (prompt G3.4'ün önerisi):
    delta = 2 x (karşılaştırmanın kendi kontrol/referans kolunun tohum sd'si)
Bu, kampanyanın "established effect" ölçütünün eşiğiyle AYNI sayıdır — yani aynı büyüklük
hem "gerçek etki" hem "ihmal edilebilir fark" sınırı olarak kullanılıyor. Bu bilinçli:
iki iddia aynı cetveli paylaşmazsa biri diğerini yiyebilir.

BEKLENTİ, ÖNCEDEN YAZILIYOR: n=3 / df=2 ile TOST'un gücü çok düşüktür; testlerin çoğunun
eşdeğerlik KURAMAMASI beklenir. O durumda doğru cümle "eşdeğer" değil, **"eşdeğerlik için
kanıt yok"**tur ve makale öyle yazacaktır.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/equivalence_tests.{md,json}
Kullanım: python diagnostics/equivalence_tests.py
"""
import json
import statistics as st
import sys
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

A_CRIT = ROOT / "diagnostics" / "paper_tables" / "criterion_applied.json"
A_TS = ROOT / "diagnostics" / "paper_tables" / "student_ts_baseline.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
ALPHA = 0.05
SEEDS = ("42", "1", "43")

HONESTY = (
    "> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel "
    "report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is "
    "unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts."
)


def tost(diffs, delta, alpha=ALPHA):
    """İki tek-yanlı test. diffs = eşleştirilmiş farklar."""
    n = len(diffs)
    mean = st.mean(diffs)
    if n < 2 or delta is None or delta <= 0:
        return {"n": n, "mean": mean, "delta": delta, "equivalent": None,
                "reason": "n<2 veya marj tanımsız"}
    sd = sample_sd(diffs)
    se = sd / (n ** 0.5)
    df = n - 1
    if se == 0:
        eq = abs(mean) < delta
        return {"n": n, "mean": mean, "sd": sd, "se": se, "df": df, "delta": delta,
                "p_tost": 0.0 if eq else 1.0, "equivalent": eq,
                "ci90_lo": mean, "ci90_hi": mean, "reason": "sıfır varyans"}
    t1 = (mean + delta) / se
    t2 = (mean - delta) / se
    p1 = float(stats.t.sf(t1, df))
    p2 = float(stats.t.cdf(t2, df))
    p_tost = max(p1, p2)
    crit = float(stats.t.ppf(1 - alpha, df))         # (1-2a) CI -> tek yanlı kritik
    return {"n": n, "mean": mean, "sd": sd, "se": se, "df": df, "delta": delta,
            "t1": t1, "t2": t2, "p1": p1, "p2": p2, "p_tost": p_tost,
            "equivalent": p_tost < alpha,
            "ci90_lo": mean - crit * se, "ci90_hi": mean + crit * se}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tests = []

    # ---- (a) oracle kapısının DOĞRULUK null'ları, üç öğretmen
    crit = json.loads(A_CRIT.read_text(encoding="utf-8"))
    for cell, by_ck in sorted(crit["cells"].items()):
        if not cell.endswith("/gate:oracle_error"):
            continue
        c = (by_ck.get("swa") or {}).get("acc")
        if not c or (c.get("n") or 0) < 2:
            continue
        # eşleştirilmiş farklar tek tek saklanmıyor; ort + sd + n'den yeniden kurulamaz,
        # bu yüzden TOST doğrudan (ort, sd, n) üçlüsünden hesaplanır — matematiksel olarak
        # aynı şey, çünkü test yalnız bu üç sayıya bağlı.
        mean, sd, n = c["mean"], c["sd_paired"], c["n"]
        delta = 2 * c["sigma_control"]
        se = sd / (n ** 0.5)
        df = n - 1
        t1, t2 = (mean + delta) / se, (mean - delta) / se
        p1, p2 = float(stats.t.sf(t1, df)), float(stats.t.cdf(t2, df))
        p_tost = max(p1, p2)
        cr = float(stats.t.ppf(1 - ALPHA, df))
        tests.append({
            "group": "(a) oracle gate — accuracy null",
            "name": cell, "unit": "pp",
            "mean": mean, "sd": sd, "n": n, "se": se, "df": df,
            "delta": delta, "delta_source": "2 × control arm accuracy seed sd",
            "p_tost": p_tost, "equivalent": p_tost < ALPHA,
            "ci90_lo": mean - cr * se, "ci90_hi": mean + cr * se})

    # ---- (b) §5.7: öğrenci-tarafı TS vs öğretmen-tarafı T* kolu (FERPlus), ECE ve JSD
    ts = json.loads(A_TS.read_text(encoding="utf-8"))
    per = ts["per_seed"]
    for met, unit in (("ece", "ECE"), ("jsd", "JSD")):
        diffs = [per[s]["student_ts"][met] - per[s]["tstar_arm"][met] for s in SEEDS]
        # REFERANS KOL = ÖLÇEKLENMİŞ KONTROL KOLU (28 Ağu 2026). Önceki hâli T* kolunu
        # referans alıyordu ve §5.7 marjı "twice the scaled control arm's seed deviation"
        # diye BEYAN ediyor -- iki tanım aynı değil: T* kolu 2×0.0031764, ölçeklenmiş kontrol
        # 2×0.0034800. Ölçüldü, ayrışma gerçekti, ve basılan p_TOST eski paydadan geliyordu.
        # Beyan hangisiyse artefakt onu hesaplar; ters yön (metni artefakta uydurmak) marjı
        # sonuca göre seçmek olurdu. Sınıf ikisinde de aynı çıkıyor (inconclusive), yani
        # düzeltme hükmü değil, hükmün DAYANDIĞI paydayı yerine oturtuyor.
        # Aynı kural JSD ekseninde de uygulanır -- metin "the same margin" diyor, o yüzden
        # iki eksende iki farklı payda kuralı olamaz.
        ref = [per[s]["student_ts"][met] for s in SEEDS]
        delta = 2 * sample_sd(ref)
        r = tost(diffs, delta)
        r.update({"group": "(b) §5.7 student-side TS vs teacher-side T* arm",
                  "name": f"FERPlus {unit}: student-TS − T*-arm", "unit": unit,
                  "delta_source": f"2 × scaled control arm (student-TS) {unit} seed sd",
                  "per_seed": {s: d for s, d in zip(SEEDS, diffs)}})
        tests.append(r)

    # "Eşdeğerlik kurulamadı" İKİ farklı duruma uyuyor ve ikisi aynı cümleyle yazılamaz:
    #   · güçsüz  : CI marjı aşıyor, fark de sıfırdan ayrılamıyor -> gerçekten "kanıt yok"
    #   · fark var: CI tümüyle marjın DIŞINDA, tek yanda -> gösterilmiş bir fark
    # Ayrım yapılmazsa FERPlus JSD satırı (CI tamamen -delta'nın altında) diğer dördüyle aynı
    # kutuya düşer ve "belirsiz" diye okunur; oysa orada fark marjdan büyük ve yönü belli.
    for t in tests:
        d = t.get("delta")
        lo, hi = t.get("ci90_lo"), t.get("ci90_hi")
        if t.get("equivalent"):
            t["class"] = "equivalent"
        elif d and lo is not None and (hi < -d or lo > d):
            t["class"] = "difference beyond margin"
        else:
            t["class"] = "inconclusive"
    n_eq = sum(1 for t in tests if t.get("equivalent"))
    n_diff = sum(1 for t in tests if t["class"] == "difference beyond margin")
    n_inc = sum(1 for t in tests if t["class"] == "inconclusive")

    L = ["# G3.4 — Equivalence (TOST): auditing the \"indistinguishable\" claims", "",
         HONESTY, "",
         f"Producer: `diagnostics/equivalence_tests.py` · {SD_CONVENTION} · α = {ALPHA} · "
         "two one-sided tests, paired, df = n−1", "",
         "A large p-value is **not** evidence of equivalence; it only says a difference could "
         "not be demonstrated. At n = 3 that distinction is decisive, because power is low "
         "enough that almost nothing can be demonstrated. TOST asks the right question: is the "
         "difference demonstrably **inside** a margin declared in advance?", "",
         "**Margin, declared before reading any result:** δ = 2 × the seed sd of the "
         "comparison's own control/reference arm — deliberately the *same* number as the "
         "campaign's `established effect` threshold (G3.1), so that \"a real effect\" and "
         "\"a negligible difference\" are measured against one ruler rather than two.", "",
         "| test | mean diff | 90% CI | δ | p (TOST) | outcome |",
         "|---|---|---|---|---|---|"]
    for t in tests:
        digits = 3 if t["unit"] == "pp" else 4
        eq = {"equivalent": "**equivalence established**",
              "difference beyond margin": "**difference beyond margin**",
              "inconclusive": "inconclusive"}[t["class"]]
        L.append(f"| {t['name']} | {t['mean']:+.{digits}f} | "
                 f"[{t['ci90_lo']:+.{digits}f}, {t['ci90_hi']:+.{digits}f}] | "
                 f"±{t['delta']:.{digits}f} | {t['p_tost']:.4f} | {eq} |")

    L += ["",
          f"**{n_eq}** equivalence established · **{n_diff}** difference beyond the margin · "
          f"**{n_inc}** inconclusive (of {len(tests)}).", ""]
    if n_diff:
        L += ["### One row is not underpowered — it is a difference", "",
              "A failed TOST has two very different causes, and collapsing them would be the "
              "error this table exists to prevent. Where the 90% CI straddles ±δ the data are "
              "simply uninformative. But for "
              + ", ".join(f"**{t['name']}**" for t in tests
                          if t["class"] == "difference beyond margin")
              + " the interval lies **entirely outside** the margin, on one side: that is a "
                "demonstrated difference larger than δ, not an absence of evidence. It should "
                "be reported as a difference, with its direction.", ""]
    if n_inc:
        L += ["### What this means for the wording", "",
              "For every **inconclusive** test the defensible sentence is "
              "**\"no evidence for a difference\"**, not \"statistically indistinguishable\" and "
              "not \"equivalent\". The 90% CIs above show why: they extend beyond ±δ, so a "
              "difference as large as the margin cannot be excluded by these data.", "",
              "This is a power statement, not a claim that the arms differ. With n = 3 and "
              "df = 2, TOST is close to unable to certify equivalence at any margin a reader "
              "would find interesting; the honest report is the interval, not a verdict.", ""]
    L += ["Sources: `paper_tables/criterion_applied.json` (oracle cells and their control-arm "
          "sds) and `paper_tables/student_ts_baseline.json` (§5.7 per-seed values). Nothing is "
          "recomputed from checkpoints here.", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "equivalence_tests.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "equivalence_tests.json").write_text(json.dumps(
        {"note": "review-responsive, not pre-declared", "alpha": ALPHA,
         "margin_rule": "2 x seed sd of the comparison's own control/reference arm",
         "sd_convention": SD_CONVENTION, "n_equivalent": n_eq, "n_difference_beyond_margin": n_diff,
         "n_inconclusive": n_inc, "n_tests": len(tests),
         "tests": tests}, indent=2, ensure_ascii=False), encoding="utf-8")

    for t in tests:
        dg = 3 if t["unit"] == "pp" else 4
        print(f"  {t['name'][:48]:50s} ort {t['mean']:+.{dg}f} d ±{t['delta']:.{dg}f} "
              f"p_TOST {t['p_tost']:.4f} -> "
              f"{'ESDEGER' if t.get('equivalent') else 'kurulamadi'}")
    print(f"\n{n_eq}/{len(tests)} esdegerlik kuruldu")
    print(f"Wrote {OUT_DIR / 'equivalence_tests.md'}")


if __name__ == "__main__":
    main()
