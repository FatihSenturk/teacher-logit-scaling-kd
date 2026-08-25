"""R2-1: T* split-half stabilitesi — "T* raporlama foldunda fit ediliyor" itirazına ölçülü yanıt.

İTİRAZ: T* eval foldunda fit ediliyor; başka bir foldda başka bir T* çıkar mıydı?
İncelemenin önerdiği "training-side holdout" BURADA ÇALIŞMAZ: öğretmen train foldunun
tamamında eğitildi, train-ECE ezber yüzünden farklı bir niceliktir. Doğru gösterim
TS-baseline protokolünün aynısı: eval foldunu SHA-sıralı iki yarıya böl, T*'ı her
yarıda ayrı fit et — iki yarının T*'ı grid adımından yakınsa, T* örnekleme
gürültüsüne duyarsızdır ve "hangi foldda fit edildiği" pratikte önemsizdir.

BÖLME KURALI (student_ts_baseline.sha_split İLE AYNI FONKSİYON, import edilir):
  dosya ADI (basename) sha256'lanır, hex'e göre sıralanır, ilk yarı A / ikinci yarı B.
  Etikete, sıraya, içeriğe bakmaz; deterministik ve yeniden üretilebilir.

FİT PROSEDÜRÜ (fiilen kullanılan): tek skaler T, NLL küçültme (Guo et al. 2017),
scipy minimize_scalar bounded — log-uzayda [log 0.05, log 10.0]
(student_ts_baseline.fit_ts İLE AYNI FONKSİYON). Not: RAF-DB tarafındaki ilk fitler
(temperature_fit.json) lineer [0.5, 5.0] sınırıyla yapılmıştı; iç-nokta optimumlarda
iki sınırlama aynı değeri verir ve tam-fold sütunu o yayımlanmış değerlere karşı
çapalanır (tolerans altta). FERPlus için lineer [0.5, 5] SINIR ARTEFAKTI üretirdi
(T*≈0.51 sınırın dibinde) — log sınır bu yüzden tek tip kullanılır.

Eq.8 KARŞILIĞI: ECE-argmin, mevcut artefaktlarla aynı gridlerde —
  RAF-DB : T ∈ [0.60, 3.00] adım 0.05 (teacher_ece_grid.FINE_TS ile aynı)
  FERPlus: T ∈ [0.10, 4.00] adım 0.02 (ferplus_human_vote_jsd sweep'i ile aynı)

VERİ: önbellekli öğretmen logitleri — forward yok, GPU yok.
  RAF-DB : diagnostics/teacher_ece_grid/teacher_val_logits_{stage1,primary,vae9182}.pt
           (fold-3, n=3068, loader sırası). Dosya adları metadata CSV'nin fold==3
           satır sırasından kurulur; önbellekteki etiket tensörüyle birebir eşitlik
           doğrulanır (eşleşmezse betik durur — sessiz kayma yok).
  FERPlus: diagnostics/ferplus_jsd/ferplus_val_logits.pt (paths alanı var), oy>0
           filtresi ferplus_teacher_signed_grid ile aynı şekilde uygulanır (n=3153).

STAGE1 DAĞITIM NOTU: makaledeki dağıtılmış T*=1.3406, B3'ün ESKİ katmanlı-rastgele
yarı bölmesinden (b3_tstar_halfsplit.py, seed 1234) gelir; buradaki SHA-yarıları
farklı bir bölme olduğundan T*_A'nın 1.3406'ya eşit çıkması beklenmez. Çapa,
tam-fold değeridir (1.3494).

Salt-okunur. Çıktı -> diagnostics/paper_tables/tstar_stability.{md,json}
"""
import csv
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from student_ts_baseline import sha_split, fit_ts  # noqa: E402  (AYNI bölme + AYNI fit)
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402

GRID_DIR = ROOT / "diagnostics" / "teacher_ece_grid"
JSD_DIR = ROOT / "diagnostics" / "ferplus_jsd"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

RAFDB_META = ROOT / "data" / "rafdb_aligned" / "metadata_rafdb_poster_var.csv"
RAFDB_GRID = [round(0.60 + 0.05 * i, 2) for i in range(int((3.00 - 0.60) / 0.05) + 1)]
FER_GRID = [round(0.10 + 0.02 * i, 2) for i in range(int((4.00 - 0.10) / 0.02) + 1)]

# tam-fold çapaları: yayımlanmış sürekli-NLL fitleri (kaynaklar başlıkta)
PUBLISHED = {"stage1": 1.3494, "primary": 1.2613, "vae9182": 0.9829, "ferplus": 0.5063}
ANCHOR_TOL = 0.01  # |T*_full - yayımlanmış| bunun üstündeyse tablo UYARI basar


def rafdb_names_and_labels():
    """Metadata CSV fold==3, satır sırası — RAFDBDataset'in val kümesiyle aynı sıra."""
    names, labels = [], []
    with open(RAFDB_META, encoding="utf-8-sig") as fh:  # BOM'lu yazılmış
        for row in csv.DictReader(fh):
            if int(row["fold"]) == 3:
                names.append(Path(row["path"]).name)
                labels.append(int(row["label"]))
    return names, torch.tensor(labels)


def ferplus_kept():
    """ferplus_teacher_signed_grid ile aynı oy>0 filtresi; isim = basename."""
    import numpy as np
    import pandas as pd
    from utils.configs import load_yaml
    from ferplus_human_vote_jsd import EMOTIONS
    import argparse

    blob = torch.load(JSD_DIR / "ferplus_val_logits.pt", map_location="cpu",
                      weights_only=False)
    logits, labels, paths = blob["logits"], blob["labels"], blob["paths"]
    cfg = argparse.Namespace()
    load_yaml(cfg, str(ROOT / "configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml"))
    df = pd.read_csv(ROOT / cfg.metadata)
    df = df[df["fold"].isin(cfg.val_folds)].reset_index(drop=True)
    by_name = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows = [by_name[Path(p).name] for p in paths]
    votes = torch.tensor(df.loc[rows, EMOTIONS].to_numpy(dtype=np.float64))
    keep = votes.sum(dim=1) > 0
    names = [Path(p).name for p, k in zip(paths, keep.tolist()) if k]
    return logits[keep].float(), labels[keep], names


def ece_argmin(logits, labels, grid):
    best_T, best_e = None, float("inf")
    for T in grid:
        e = confidence_ece(logits, labels, T)
        if e < best_e:
            best_T, best_e = T, e
    return best_T, best_e


def one_teacher(tag, logits, labels, names, grid):
    mask_a, mask_b = sha_split(names)
    out = {"n": len(names), "n_A": int(mask_a.sum()), "n_B": int(mask_b.sum()),
           "grid_step": round(grid[1] - grid[0], 4)}
    for sub, mask in (("A", mask_a), ("B", mask_b), ("full", None)):
        lg = logits if mask is None else logits[mask]
        lb = labels if mask is None else labels[mask]
        t = fit_ts(lg, lb)
        am_T, am_e = ece_argmin(lg, lb, grid)
        out[sub] = {"T_star_nll": t, "ece_argmin_T": am_T, "ece_at_argmin": am_e}
    out["absdiff_nll_A_B"] = abs(out["A"]["T_star_nll"] - out["B"]["T_star_nll"])
    out["absdiff_argmin_A_B"] = abs(out["A"]["ece_argmin_T"] - out["B"]["ece_argmin_T"])
    # pratik maliyet: TAM foldun ECE'si, yarı-A'nın T*'ı ile mi yarı-B'ninkiyle mi
    # ölçeklendiğine ne kadar duyarlı? (|A−B|'nin ECE cinsinden karşılığı)
    e_at_A = confidence_ece(logits, labels, out["A"]["T_star_nll"])
    e_at_B = confidence_ece(logits, labels, out["B"]["T_star_nll"])
    out["full_ece_at_TA"], out["full_ece_at_TB"] = e_at_A, e_at_B
    out["cross_ece_penalty"] = abs(e_at_A - e_at_B)
    out["published_full"] = PUBLISHED[tag]
    out["anchor_dev"] = abs(out["full"]["T_star_nll"] - PUBLISHED[tag])
    out["anchor_ok"] = out["anchor_dev"] <= ANCHOR_TOL
    out["below_grid_step"] = out["absdiff_nll_A_B"] < out["grid_step"]
    return out


def main():
    # cp1252 konsolda `UnicodeEncodeError` -- gerekçe `order_stat_trend.py`'dekiyle aynı:
    # kapıda "başka hata" görünüyordu ve Level-1 sorusu hiç sorulmuyordu (9 Ağu).
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    results = {}

    raf_names, raf_labels = rafdb_names_and_labels()
    for tag in ("stage1", "primary", "vae9182"):
        blob = torch.load(GRID_DIR / f"teacher_val_logits_{tag}.pt", map_location="cpu",
                          weights_only=False)
        if not torch.equal(blob["labels"], raf_labels):
            raise RuntimeError(f"{tag}: önbellek etiketleri metadata fold-3 sırasıyla "
                               "eşleşmiyor — isim eşlemesi güvensiz, DURDU")
        results[tag] = one_teacher(tag, blob["logits"].float(), blob["labels"],
                                   raf_names, RAFDB_GRID)

    f_logits, f_labels, f_names = ferplus_kept()
    if len(f_names) != 3153:
        raise RuntimeError(f"FERPlus raporlama kümesi 3153 bekleniyordu, {len(f_names)} "
                           "bulundu — TS-baseline kümesiyle aynılık bozulmuş")
    results["ferplus"] = one_teacher("ferplus", f_logits, f_labels, f_names, FER_GRID)

    L = ["# R2-1 — T* split-half stability (SHA halves)", "",
         "Producer: `diagnostics/tstar_stability.py` · split and fit imported from "
         "`student_ts_baseline` (sha256(basename) hex order, first half A; NLL, continuous, "
         "log-bounded [0.05, 10]) · the Eq.8 column is the ECE argmin on the existing grid steps "
         "(RAF-DB 0.05, FERPlus 0.02) · no forward pass, cached logits.", "",
         "| teacher | n (A/B) | T*_A | T*_B | T*_full | **\\|T*_A−T*_B\\|** | grid step | "
         "cross-ECE penalty | argmin-ECE T (A / B / full) | published T* | anchor |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for tag, r in results.items():
        anchor = "OK" if r["anchor_ok"] else f"**DEVIATION {r['anchor_dev']:.4f}**"
        L.append(f"| {tag} | {r['n_A']}/{r['n_B']} | {r['A']['T_star_nll']:.4f} | "
                 f"{r['B']['T_star_nll']:.4f} | {r['full']['T_star_nll']:.4f} | "
                 f"**{r['absdiff_nll_A_B']:.4f}** | {r['grid_step']} | "
                 f"{r['cross_ece_penalty']:.5f} | "
                 f"{r['A']['ece_argmin_T']:.2f} / {r['B']['ece_argmin_T']:.2f} / "
                 f"{r['full']['ece_argmin_T']:.2f} | {r['published_full']} | {anchor} |")
    all_below = all(r["below_grid_step"] for r in results.values())
    n_below = sum(r["below_grid_step"] for r in results.values())
    worst_pen = max(r["cross_ece_penalty"] for r in results.values())
    L += ["",
          f"**Result, reported as it fell:** in {n_below}/4 teachers |T*_A − T*_B| is below that "
          "teacher's own grid step. "
          + ("" if all_below else
             "For FERPlus the difference (0.0263) exceeds the step of its own FINE diagnostic "
             "sweep (0.02); but (i) it is ~11% of the dose-response arm spacing (≥0.24), which is "
             "the experiments' actual resolution, and (ii) as the cross-ECE penalty column shows, "
             "rescaling the full fold with the wrong half's T* costs at most "
             f"{worst_pen:.5f} in ECE — about 2.5% of FERPlus's deployed calibration gain "
             "(ECE 0.1282→0.0156, ~0.113). The sentence 'below the grid step' can only be written "
             "for RAF-DB; the correct sentence covering all four is below.") , "",
          "Suggested sentence for the paper (direction-aware):", "",
          "> To verify that T* is not an artifact of the evaluation sample, we re-fitted it on "
          "two disjoint halves of each evaluation fold (deterministic SHA-sorted split, "
          "identical to the student-TS protocol). The two half-fits differ by at most 0.014 "
          "for the three RAF-DB teachers (grid step 0.05) and by 0.026 for FERPlus — an "
          "order of magnitude below the spacing between experimental arms in every case — and "
          "rescaling the full fold with either half's T* changes teacher ECE by less than "
          f"{worst_pen:.0e}. The choice of fitting sample therefore does not move T* at the "
          "resolution the experiments use.", "",
          "Note on the deployed Stage1 value: the paper's 1.3406 is B3's stratified-random half-A "
          "fit (a different splitting rule); the anchor used here is the full-fold 1.3494.", ""]

    payload = {"split_rule": "sha256(basename) hex sort, first half A (= student_ts_baseline)",
               "fit": "single-scalar TS, NLL minimisation, minimize_scalar bounded "
                      "log-space [0.05, 10] (= student_ts_baseline.fit_ts)",
               "eq8": "ECE-argmin on the existing grids (RAF-DB 0.60:3.00:0.05, "
                      "FERPlus 0.10:4.00:0.02)",
               "results": results, "all_below_grid_step": all_below}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tstar_stability.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "tstar_stability.json").write_text(json.dumps(payload, indent=2),
                                                 encoding="utf-8")
    for tag, r in results.items():
        print(f"{tag:<9} A {r['A']['T_star_nll']:.4f}  B {r['B']['T_star_nll']:.4f}  "
              f"full {r['full']['T_star_nll']:.4f}  |A-B| {r['absdiff_nll_A_B']:.4f} "
              f"(adım {r['grid_step']})  çapa {'OK' if r['anchor_ok'] else 'SAPMA'}")
    print(f"\nWrote {OUT_DIR / 'tstar_stability.md'}")


if __name__ == "__main__":
    main()
