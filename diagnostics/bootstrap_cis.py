"""G3.5 — Bootstrap güven aralıkları: öğretmen ECE, T*, headroom, T*_JSD, havuzlanmış ρ.

İTİRAZ (Round-2 panel). Makalenin taşıyıcı skalerleri tek nokta tahmini olarak veriliyor:
öğretmen ECE'leri, fit edilmiş T* değerleri, headroom, T*_JSD ve havuzlanmış ρ=0.789. Hiçbiri
belirsizlik taşımıyor. Özellikle ρ için DA-8 haklı: 14 nokta 14 bağımsız gözlem DEĞİL, üç
eğridir; nokta düzeyinde bootstrap bu bağımlılığı yok sayıp aralığı yapay olarak daraltır.

İKİ FARKLI BOOTSTRAP, BİLEREK:
  · Örneklem bootstrap'i (öğretmen ECE, T*, headroom, T*_JSD): belirsizlik kaynağı doğrulama
    kümesinin sonlu olması. Değerlendirme örnekleri yeniden örneklenir.
  · KÜMELENMİŞ bootstrap (havuzlanmış ρ): belirsizlik kaynağı yalnız üç seri olması. SERİLER
    yeniden örneklenir, noktalar değil.
    ÖLÇÜM SONRASI NOT: kümelenmiş aralığın naif aralıktan GENİŞ çıkması bekleniyordu; çıkmadı
    (bkz. üretilen tablo). Her seri kendi içinde neredeyse monoton olduğu için seri düzeyinde
    yeniden örnekleme bu yapıyı korur, nokta düzeyinde örnekleme ise bozar. Asıl sınırlama
    genişlik değil ÇÖZÜNÜRLÜK: üç kümeden tekrarlı üç seçmenin yalnız 10 farklı çoklu-kümesi
    var, dolayısıyla kümelenmiş ρ sonlu sayıda değer alıyor. Rapor bunu sayıyla yazıyor.

HIZ NOTU. Sıcaklık ölçekleme argmax'ı değiştirmez, dolayısıyla DOĞRULUK ve örnek-başına
DOĞRULUK göstergesi T'den bağımsızdır. Güven ve NLL ise T'ye bağlı ama örnek başına bir kez,
tüm T ızgarası için önceden hesaplanabilir. Bootstrap sonra yalnız AĞIRLIKLI TOPLAM'a iner
(multinom ağırlıklar), yani her tekrarda softmax yeniden hesaplanmaz.

Veri: önbellekli öğretmen logitleri — teacher_ece_grid/teacher_val_logits_*.pt (RAF-DB) ve
ferplus_jsd/ferplus_val_logits.pt (FERPlus). Forward pass YOK, GPU YOK.
Çıktı -> diagnostics/paper_tables/bootstrap_cis.{md,json}
Kullanım: python diagnostics/bootstrap_cis.py [--b 2000]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION  # noqa: E402

TG = ROOT / "diagnostics" / "teacher_ece_grid"
FJ = ROOT / "diagnostics" / "ferplus_jsd"
OV = ROOT / "diagnostics" / "p1_dose_response" / "two_dataset_overlay.json"
ROB = ROOT / "diagnostics" / "paper_tables" / "robustness_metrics.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

N_BINS = 15
T_GRID = np.round(np.arange(0.50, 2.501, 0.02), 4)      # T* aramasi icin
RNG_SEED = 20260806
TEACHERS = {"stage1": TG / "teacher_val_logits_stage1.pt",
            "primary": TG / "teacher_val_logits_primary.pt",
            "vae9182": TG / "teacher_val_logits_vae9182.pt"}
ARM_TO_SERIES = {"rafdb_stage1": "RAF-DB stage1", "rafdb_vae9182": "RAF-DB vae9182",
                 "ferplus": "FERPlus"}

HONESTY = (
    "> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel "
    "report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is "
    "unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts."
)


def precompute(logits, labels, t_grid=None):
    """Örnek başına, T ızgarası boyunca: güven, doğru-mu, NLL, ECE bin indeksi.

    `t_grid` 15 Ağu 2026'da eklendi (headroom_grid_audit): ızgara artık bir PARAMETRE, çünkü
    Eq.8 `min_{T∈G}` ve dolayısıyla G'nin kendisi estimand'ın parçası. Varsayılan bu modülün
    kendi T_GRID'i — bu betiğin ürettiği hiçbir sayı değişmez (kapı ile doğrulandı).
    """
    t_grid = T_GRID if t_grid is None else np.asarray(t_grid, dtype=np.float64)
    lg = logits.astype(np.float64)
    n = lg.shape[0]
    correct = (lg.argmax(1) == labels).astype(np.float64)       # T'den BAGIMSIZ
    conf = np.empty((n, len(t_grid)))
    nll = np.empty((n, len(t_grid)))
    for j, T in enumerate(t_grid):
        z = lg / T
        z = z - z.max(1, keepdims=True)
        e = np.exp(z)
        p = e / e.sum(1, keepdims=True)
        conf[:, j] = p.max(1)
        nll[:, j] = -np.log(np.clip(p[np.arange(n), labels], 1e-12, None))
    binidx = np.clip((conf * N_BINS).astype(np.int64), 0, N_BINS - 1)
    return correct, conf, nll, binidx


def ece_weighted(w, correct, conf, binidx):
    """15-bin eşit-genişlik ECE, ağırlıklı. w: (n,) multinom ağırlıklar. Tüm T için vektörel."""
    nT = conf.shape[1]
    key = binidx + N_BINS * np.arange(nT)[None, :]              # (n, nT)
    tot = np.bincount(key.ravel(), weights=np.repeat(w, nT), minlength=N_BINS * nT)
    sc = np.bincount(key.ravel(), weights=np.repeat(w * correct, nT), minlength=N_BINS * nT)
    scf = np.bincount(key.ravel(), weights=(w[:, None] * conf).ravel(), minlength=N_BINS * nT)
    tot = tot.reshape(nT, N_BINS, order="F") if False else tot.reshape(N_BINS, nT, order="F")
    sc = sc.reshape(N_BINS, nT, order="F")
    scf = scf.reshape(N_BINS, nT, order="F")
    nz = tot > 0
    gap = np.zeros_like(tot)
    gap[nz] = np.abs(sc[nz] / tot[nz] - scf[nz] / tot[nz])
    return (gap * tot).sum(0) / w.sum()                          # (nT,)


def pct(a, lo=2.5, hi=97.5):
    return float(np.percentile(a, lo)), float(np.percentile(a, hi))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--b", type=int, default=2000)
    # `parse_known_args` -- Level-1 kapısı üreticileri `runpy` ile çağırıp betiğin yolunu
    # argv'de bırakıyor; `parse_args` bunu tanımadığı argüman sayıp SystemExit atıyor ve kapı
    # "başka hata" yazıyordu, yani Level-1 sorusu bu betiğe hiç sorulmuyordu. (Aynı arıza
    # `student_ts_baseline.py`'de GERÇEK bir ihlali saklıyordu -- 9 Ağu.)
    args, _unknown = ap.parse_known_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = np.random.default_rng(RNG_SEED)
    B = args.b
    i_T1 = int(np.argmin(np.abs(T_GRID - 1.0)))
    out = {}

    # ---------- örneklem bootstrap'i: öğretmenler
    for name, path in list(TEACHERS.items()) + [("ferplus", FJ / "ferplus_val_logits.pt")]:
        d = torch.load(path, map_location="cpu", weights_only=False)
        lg = d["logits"].numpy()
        lb = d["labels"].numpy()
        correct, conf, nll, binidx = precompute(lg, lb)
        n = lg.shape[0]

        w0 = np.ones(n)
        e0 = ece_weighted(w0, correct, conf, binidx)
        nll0 = (nll * w0[:, None]).sum(0) / n
        t_nll0 = float(T_GRID[int(np.argmin(nll0))])
        t_ece0 = float(T_GRID[int(np.argmin(e0))])
        point = {"ece_T1": float(e0[i_T1]), "T_star_nll": t_nll0, "T_star_ece": t_ece0,
                 "ece_at_T_star_nll": float(e0[int(np.argmin(nll0))]),
                 "headroom_nllstar": float(e0[i_T1] - e0[int(np.argmin(nll0))]),
                 "headroom_eq8": float(e0[i_T1] - e0.min()), "n_val": n}

        bs = {k: np.empty(B) for k in ("ece_T1", "T_star_nll", "T_star_ece",
                                       "headroom_nllstar", "headroom_eq8")}
        for b in range(B):
            w = rng.multinomial(n, np.full(n, 1.0 / n)).astype(np.float64)
            e = ece_weighted(w, correct, conf, binidx)
            nl = (nll * w[:, None]).sum(0) / w.sum()
            j_n, j_e = int(np.argmin(nl)), int(np.argmin(e))
            bs["ece_T1"][b] = e[i_T1]
            bs["T_star_nll"][b] = T_GRID[j_n]
            bs["T_star_ece"][b] = T_GRID[j_e]
            bs["headroom_nllstar"][b] = e[i_T1] - e[j_n]
            bs["headroom_eq8"][b] = e[i_T1] - e.min()
        out[name] = {"point": point,
                     "ci95": {k: pct(v) for k, v in bs.items()},
                     "B": B}
        print(f"  {name:9s} ECE(T=1) {point['ece_T1']:.4f} "
              f"[{out[name]['ci95']['ece_T1'][0]:.4f},{out[name]['ci95']['ece_T1'][1]:.4f}] · "
              f"T*_NLL {t_nll0:.3f} "
              f"[{out[name]['ci95']['T_star_nll'][0]:.2f},"
              f"{out[name]['ci95']['T_star_nll'][1]:.2f}] · "
              f"headroom_eq8 {point['headroom_eq8']:+.4f} "
              f"[{out[name]['ci95']['headroom_eq8'][0]:+.4f},"
              f"{out[name]['ci95']['headroom_eq8'][1]:+.4f}]")

    # ---------- KÜMELENMİŞ bootstrap: havuzlanmış ρ
    ov = json.loads(OV.read_text(encoding="utf-8"))
    rob = json.loads(ROB.read_text(encoding="utf-8"))
    series_pts = {}
    for arm, sname in ARM_TO_SERIES.items():
        s = rob["series"][sname]
        Ts, mean = s["T"], s["metrics"]["ece_ew_15"]["mean"]
        pts = []
        for p in ov["arms"][arm]["points"]:
            k = [kk for kk in mean if abs(float(kk) - p["T"]) < 1e-9]
            if k:
                pts.append((abs(p["signed_gap"]), mean[k[0]]))
        series_pts[arm] = pts

    def spearman(xy):
        x = np.array([a for a, _ in xy]); y = np.array([b for _, b in xy])
        rx = np.argsort(np.argsort(x)).astype(float)
        ry = np.argsort(np.argsort(y)).astype(float)
        rx -= rx.mean(); ry -= ry.mean()
        den = np.sqrt((rx ** 2).sum() * (ry ** 2).sum())
        return float((rx * ry).sum() / den) if den else float("nan")

    all_pts = [p for v in series_pts.values() for p in v]
    rho_point = spearman(all_pts)
    keys = list(series_pts)
    rho_cluster, rho_naive = np.empty(B), np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(keys), len(keys))
        pooled = [p for i in pick for p in series_pts[keys[i]]]
        rho_cluster[b] = spearman(pooled)
        idx = rng.integers(0, len(all_pts), len(all_pts))
        rho_naive[b] = spearman([all_pts[i] for i in idx])
    rho_cluster = rho_cluster[~np.isnan(rho_cluster)]
    rho_naive = rho_naive[~np.isnan(rho_naive)]

    # Üç kümeyle kümelenmiş bootstrap KABA bir nesnedir: 3 seriden tekrarlı 3 seçmenin
    # yalnız C(5,3)=10 farklı çoklu-kümesi var, dolayısıyla rho da sonlu sayıda değer alır.
    # Bunu sayıyla göstermek, aralığın genişliğinden daha bilgilendirici.
    n_distinct = int(len(np.unique(np.round(rho_cluster, 10))))
    ci_c, ci_n = pct(rho_cluster), pct(rho_naive)
    out["pooled_rho"] = {"point": rho_point, "n_points": len(all_pts),
                         "n_clusters": len(keys),
                         "ci95_cluster_bootstrap": ci_c,
                         "ci95_naive_point_bootstrap": ci_n,
                         "width_cluster": ci_c[1] - ci_c[0],
                         "width_naive": ci_n[1] - ci_n[0],
                         "n_distinct_cluster_values": n_distinct, "B": B}
    print(f"  pooled rho {rho_point:.3f} | kumelenmis CI "
          f"[{out['pooled_rho']['ci95_cluster_bootstrap'][0]:.3f},"
          f"{out['pooled_rho']['ci95_cluster_bootstrap'][1]:.3f}] | naif CI "
          f"[{out['pooled_rho']['ci95_naive_point_bootstrap'][0]:.3f},"
          f"{out['pooled_rho']['ci95_naive_point_bootstrap'][1]:.3f}]")

    # ---------- rapor
    L = ["# G3.5 — Bootstrap confidence intervals", "", HONESTY, "",
         f"Producer: `diagnostics/bootstrap_cis.py` · {SD_CONVENTION} · B = {B} · "
         f"percentile CIs · RNG seed {RNG_SEED} · ECE = {N_BINS}-bin equal-width · "
         f"T grid {T_GRID[0]:g}–{T_GRID[-1]:g} step {T_GRID[1] - T_GRID[0]:g}", "",
         "Two different resampling units, chosen deliberately:", "",
         "- **Sample bootstrap** for teacher ECE, T\\*, headroom and T\\*_JSD — the uncertainty "
         "there comes from a finite validation set, so evaluation samples are resampled.",
         "- **Cluster bootstrap** for the pooled ρ — the uncertainty there is that there are "
         "only three curves. Series are resampled, not points.", "",
         "## Teacher-side quantities (sample bootstrap)", "",
         "| teacher | n | ECE(T=1) | T\\*_NLL | T\\*_ECE | headroom (Eq. 8) |",
         "|---|---|---|---|---|---|"]
    for name in list(TEACHERS) + ["ferplus"]:
        o = out[name]
        p, c = o["point"], o["ci95"]
        L.append(f"| {name} | {p['n_val']} | {p['ece_T1']:.4f} "
                 f"[{c['ece_T1'][0]:.4f}, {c['ece_T1'][1]:.4f}] | "
                 f"{p['T_star_nll']:.3f} [{c['T_star_nll'][0]:.2f}, {c['T_star_nll'][1]:.2f}] | "
                 f"{p['T_star_ece']:.3f} [{c['T_star_ece'][0]:.2f}, {c['T_star_ece'][1]:.2f}] | "
                 f"{p['headroom_eq8']:+.4f} "
                 f"[{c['headroom_eq8'][0]:+.4f}, {c['headroom_eq8'][1]:+.4f}] |")
    L += ["",
          "Headroom is reported in the Eq. 8 sense (ECE at T=1 minus the grid minimum), which is "
          "non-negative by construction. The alternative definition used in earlier text "
          "(ECE(T=1) − ECE at T\\*_NLL) is in the JSON as `headroom_nllstar`; it can be "
          "negative, which is what `headroom_review` flagged.", "",
          "## Pooled ρ — and why the resampling unit changes the answer", "",
          "| resampling unit | ρ | 95% CI |", "|---|---|---|",
          f"| **series (clustered, {out['pooled_rho']['n_clusters']} clusters)** | "
          f"{rho_point:.3f} | [{out['pooled_rho']['ci95_cluster_bootstrap'][0]:.3f}, "
          f"{out['pooled_rho']['ci95_cluster_bootstrap'][1]:.3f}] |",
          f"| points (naive, {out['pooled_rho']['n_points']} points) | {rho_point:.3f} | "
          f"[{out['pooled_rho']['ci95_naive_point_bootstrap'][0]:.3f}, "
          f"{out['pooled_rho']['ci95_naive_point_bootstrap'][1]:.3f}] |", "",
          f"**The clustered interval is not simply wider — and that is worth stating plainly, "
          f"because the expected result was that it would be.** Its width is "
          f"{out['pooled_rho']['width_cluster']:.3f} against the naive "
          f"{out['pooled_rho']['width_naive']:.3f}, and it sits higher. The reason is "
          "structural: each series is individually near-monotone in \|gap\|, so resampling "
          "whole series preserves that monotonicity (and duplicates it), whereas resampling "
          "individual points can break it. Clustering does not add noise here; it removes the "
          "one source of noise the naive scheme was manufacturing.", "",
          f"**The real limitation is resolution, not width.** With three clusters there are only "
          f"ten distinct multisets to draw, so the clustered ρ takes at most a handful of "
          f"values — {out['pooled_rho']['n_distinct_cluster_values']} distinct values across "
          f"{B} replicates. The upper bound sitting exactly at "
          f"{out['pooled_rho']['ci95_cluster_bootstrap'][1]:.3f} is a symptom of that "
          "granularity, not a claim that ρ could be 1. Neither interval should be read as a "
          "smooth 95% region; what n = 3 teachers buys is a direction, not a calibrated "
          "uncertainty.", "",
          "Sources: cached teacher logits (`teacher_ece_grid/teacher_val_logits_*.pt`, "
          "`ferplus_jsd/ferplus_val_logits.pt`), `p1_dose_response/two_dataset_overlay.json` "
          "and `paper_tables/robustness_metrics.json`. No forward pass, no GPU.", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "bootstrap_cis.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "bootstrap_cis.json").write_text(json.dumps(
        {"note": "review-responsive, not pre-declared", "B": B, "rng_seed": RNG_SEED,
         "n_bins": N_BINS, "results": out}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'bootstrap_cis.md'}")


if __name__ == "__main__":
    main()
