"""R2-4/5: sıra-istatistiği penceresinde trend var mı? (K=50 → K=100 büyümesinin kaynağı)

SORU (R2 hakem turu): §5.6'nın saf sıra-istatistiği tahmini K=50'de +0.6445, K=100'de +0.7640 pp
(9 Ağu 2026'da donmuş denetim kümesine güncellendi; öncesi +0.642 / +0.768 idi ve geniş RAF-DB
popülasyonundan geliyordu -- bkz. PUBLISHED_A2'nin üstündeki kayıt).
Büyüme son-K penceresindeki bir TRENDDEN mi (doğruluk hâlâ tırmanıyor → max−ort şişer),
yoksa salt mekanik mi (daha çok çekilişin maksimumu büyür)? Trend varsa detrend'li değer,
yoksa "plato" teyidi.

İKİ REFERANS:
  * Mekanik büyüme (iid Gauss altında): E[max−ort] ≈ σ·E[max of K std normals];
    K=50→100 oranı ≈ %8–9. Gözlenen büyüme bundan büyükse fazlası trend kokar.
  * Detrend: pencere içinde OLS doğrusu (acc ~ epoch) çıkarılır; artıkların
    max−ort'u = saf gürültü sıra-istatistiği. Trend katkısı = ham − detrend'li.

KAPSAM DONMUŞ DENETİM KÜMESİ: selection_audit.csv'nin (N=131) run_dir sütunundan.
DİKKAT — selection_gain_estimator.py kesme filtresi UYGULAMIYOR; bugün yeniden koşulsa
P5/P6 koşularını da katar ve §5.6'daki sayılar kayardı. Bu betik bu yüzden denetim CSV'sine
sabitlenir ve ham a2'yi §5.6 değerlerine karşı çapalar (tolerans 0.001 pp: makaledeki 4 haneli
yuvarlamayı taşır, popülasyon kaymasını taşımaz; sapma bundan büyükse DUR).

Salt-okunur, GPU yok. Çıktı -> diagnostics/paper_tables/order_stat_trend.{md,json}
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from publish_epoch_curves import has, load  # noqa: E402
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
KS = (50, 100)
# §5.6/T8'in yayımlı değerleri (pp).
#
# 9 Ağu 2026, makale güncellemesinden SONRA: §5.6'nın ham a2 çifti ve iki argmax oranı donmuş
# kümeye çevrildi (T8 n=105 -> 131), dolayısıyla çapa da o değerlere çevrildi. Artık çapa BU
# BETİĞİN hesapladığı popülasyonun ta kendisinden geliyor; tek fark makaledeki 4 haneli
# yuvarlama, yani beklenen sapma ~5e-5.
#
# ÖNCEKİ HÂLİN KAYDI (silmiyorum, ders burada): çapa {50: 0.642, 100: 0.768} idi ve o iki sayı
# `selection_gain.json`'ın o günkü hâlinden, RAF-DB'nin BÜTÜN bitmiş koşularından (n=105)
# geliyordu. Donmuş 131'e karşı sapma 0.0025 / 0.0040, yani ANCHOR_TOL=0.02'nin ALTINDA -- çapa
# GEÇTİ ve popülasyon uyuşmazlığını **MASKELEDİ**. Gevşek bir çapa çapa değildir.
PUBLISHED_A2 = {50: 0.6445, 100: 0.7640}
POPULATION = "frozen selection audit set"
ANCHOR_POPULATION = POPULATION
# 0.02 -> 0.001: eşiğin taşıması gereken tek şey makaledeki yuvarlama (~5e-5); yakalaması gereken
# şey popülasyon kayması. Donmuş 131 ile geniş 199 arasındaki fark 0.0133 (K=50) ve 0.0198
# (K=100) pp -- ikisi de 0.001'in üstünde, yani bugün maskelenen olay bu eşikle DURDURULUR.
ANCHOR_TOL = 0.001


def frozen_runs():
    """Donmuş denetimin (koşu adı, zaman damgası) çiftleri — tekil, sıralı.

    LEVEL-1 (9 Ağu 2026). Eskiden `Path(r["run_dir"])` döndürüyordu ve eğri o dizinin
    `training_log.csv`'sinden okunuyordu; bu betik Level-1 kapısının iki ihlalinden biriydi.
    Denetim dosyası koşu DİZİNİNİ yazıyor ama buradan yalnız ad + zaman damgası alınır (saf
    metin işlemi) ve eğri `publish_epoch_curves` ile yayımlanan diziden okunur.
    """
    seen = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        seen[(r["run_name"], r["timestamp"])] = True
    return sorted(seen)


def val_acc_series(run):
    """Yayımlanan epok eğrisinden `val_acc` serisi. Koşu dizinine dokunmaz."""
    if not has(*run):
        return []
    _ep, va, _vl = load(*run)
    return [float(x) for x in va]


def ols_residual_stats(win):
    """OLS acc ~ epoch-indeksi; (eğim, pencere-boyu sürüklenme, artık max−ort)."""
    k = len(win)
    xs = list(range(k))
    xbar, ybar = st.mean(xs), st.mean(win)
    sxx = sum((x - xbar) ** 2 for x in xs)
    b = sum((x - xbar) * (y - ybar) for x, y in zip(xs, win)) / sxx
    resid = [y - (ybar + b * (x - xbar)) for x, y in zip(xs, win)]
    return b, b * (k - 1), max(resid) - st.mean(resid)


def main():
    # cp1252 konsolda Türkçe karakter `UnicodeEncodeError` atıyor ve betik SAYIYI ÜRETMEDEN
    # ilk satırı basarken düşüyordu; Level-1 kapısında "başka hata" görünüyordu, yani soru
    # hiç sorulmuyordu (9 Ağu). Deponun geri kalanındaki standart blok buraya da eklendi.
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    runs = frozen_runs()
    print(f"donmuş denetim kümesi: {len(runs)} koşu "
          f"(eğriler diagnostics/epoch_curves.npz'den — koşu dizini okunmuyor)")

    agg = {k: {"a2": [], "slope": [], "drift": [], "a2_detr": []} for k in KS}
    for rd in runs:
        acc = val_acc_series(rd)
        for k in KS:
            if len(acc) < k + 10:
                continue
            win = acc[-k:]
            a2 = max(win) - st.mean(win)
            b, drift, a2_detr = ols_residual_stats(win)
            d = agg[k]
            d["a2"].append(a2)
            d["slope"].append(b)
            d["drift"].append(drift)
            d["a2_detr"].append(a2_detr)

    res = {}
    for k in KS:
        d = agg[k]
        m_a2 = st.mean(d["a2"])
        anchor_dev = abs(m_a2 - PUBLISHED_A2[k])
        if anchor_dev > ANCHOR_TOL:
            raise RuntimeError(f"K={k}: ham a2 {m_a2:.4f}, §5.6 {PUBLISHED_A2[k]} — sapma "
                               f"{anchor_dev:.4f} > {ANCHOR_TOL}. Küme uyuşmuyor, DUR.")
        res[k] = {"n_runs": len(d["a2"]),
                  "population": POPULATION,
                  "a2_raw": {"mean": m_a2, "sd": sample_sd(d["a2"])},
                  "published_a2": PUBLISHED_A2[k], "anchor_dev": anchor_dev,
                  "anchor_population": ANCHOR_POPULATION,
                  # Elle çevrilen bir bayrak değil: iki tanımın karşılaştırması. Çapa başka bir
                  # popülasyona geri alınırsa bu alan kendiliğinden `false` olur.
                  "anchor_population_matches": ANCHOR_POPULATION == POPULATION,
                  "slope_pp_per_epoch": {"mean": st.mean(d["slope"]),
                                         "sd": sample_sd(d["slope"])},
                  "window_drift_pp": {"mean": st.mean(d["drift"]),
                                      "sd": sample_sd(d["drift"])},
                  "a2_detrended": {"mean": st.mean(d["a2_detr"]),
                                   "sd": sample_sd(d["a2_detr"])}}

    g_raw = res[100]["a2_raw"]["mean"] / res[50]["a2_raw"]["mean"]
    g_det = res[100]["a2_detrended"]["mean"] / res[50]["a2_detrended"]["mean"]

    L = ["# R2-4/5 — Trend analysis inside the order-statistic window", "",
         f"Producer: `diagnostics/order_stat_trend.py` · frozen audit set (N=131 runs, "
         f"those with a long enough log are in the table) · {SD_CONVENTION} · window = last K "
         f"epochs, OLS detrend.", "",
         "| K | n | raw a2 (max−mean) | §5.6 value | OLS drift (over the window) | "
         "**detrended a2** |",
         "|---|---|---|---|---|---|"]
    for k in KS:
        r = res[k]
        L.append(f"| {k} | {r['n_runs']} | {r['a2_raw']['mean']:+.3f} ± "
                 f"{r['a2_raw']['sd']:.3f} | +{r['published_a2']:.4f} | "
                 f"{r['window_drift_pp']['mean']:+.3f} ± {r['window_drift_pp']['sd']:.3f} pp | "
                 f"**{r['a2_detrended']['mean']:+.3f} ± {r['a2_detrended']['sd']:.3f}** |")
    L += ["",
          f"K=50→100 growth: raw {100 * (g_raw - 1):+.1f}% · detrended {100 * (g_det - 1):+.1f}% "
          "(the purely mechanical growth of an iid Gaussian maximum is ≈ +8–9%).", ""]
    payload = {"sd_convention": SD_CONVENTION, "results": {str(k): res[k] for k in KS},
               "growth_raw": g_raw, "growth_detrended": g_det}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "order_stat_trend.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "order_stat_trend.json").write_text(json.dumps(payload, indent=2),
                                                  encoding="utf-8")
    for k in KS:
        r = res[k]
        print(f"K={k:<4} n={r['n_runs']}  ham {r['a2_raw']['mean']:+.3f}±{r['a2_raw']['sd']:.3f}"
              f"  sürüklenme {r['window_drift_pp']['mean']:+.3f}"
              f"  detrend {r['a2_detrended']['mean']:+.3f}±{r['a2_detrended']['sd']:.3f}")
    print(f"büyüme: ham {100 * (g_raw - 1):+.1f}%  detrend {100 * (g_det - 1):+.1f}%")
    print(f"Wrote {OUT_DIR / 'order_stat_trend.md'}")


if __name__ == "__main__":
    main()
