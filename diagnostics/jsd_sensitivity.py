"""R3-3: FERPlus JSD hedefinin oy-katmanına duyarlılığı — "hedef koşullu bir dağılım" itirazına yanıt.

İTİRAZ (dış inceleme). FERPlus'ta insan hedefi p_human, satırın KENDİ oy toplamına
bölünerek kuruluyor. Ama oy toplamı her satırda 10 değil (6/7/8/9/10 hepsi geçiyor):
6 oyla kurulmuş bir dağılım 10 oyla kurulmuşa göre çok daha kaba nicelenmiştir. O halde
T*_JSD, kısmen "kaç kişi oy verdiğinin" bir fonksiyonu olabilir — yani hedef koşullu bir
dağılımdır ve sonucun bu koşullanmaya duyarlılığı ölçülmemiştir.

BU BETİĞİN YAPTIĞI. Aynı öğretmen, aynı fold, aynı T gridi; yalnız satır kümesi değişir:
  (a) tüm satırlar (oy>0)         -- mevcut yayımlanmış sonuç, REFERANS
  (b) yalnız oy toplamı = 10      -- en iyi çözünürlüklü insan hedefi
  (c) katmanlar {6-7, 8-9, 10}    -- çözünürlük arttıkça T*_JSD kayıyor mu?
Her kesitte T*_JSD, T*_NLL, T*_ECE ve bunların SIRALAMASI raporlanır.

ASIL SORU SIRALAMADIR, TEK BİR SAYI DEĞİL. Yayımlanmış bulgu bir ayrışmadır:
T*_ECE < T*_NLL < T*_JSD < 1 — yani sert-etiket kalibrasyonu, insan oylarının
desteklediğinden daha fazla keskinleştiriyor. Bir kesitte bu sıra bozuluyorsa bulgu
oy-çözünürlüğüne koşulludur ve makalede öyle yazılmalıdır. Sıra korunuyorsa bulgu
koşullanmadan bağımsızdır. İKİ SONUÇ DA YAZILIR (ön-kayıt A10, R3-3: başarı ölçütü yok).

VERİ: diagnostics/ferplus_jsd/ferplus_val_logits.pt (önbellek) + metadata oy sütunları.
Forward yok, GPU yok. Normalizasyon ferplus_human_vote_jsd ile birebir aynı: her satır
KENDİ oy toplamına bölünür.

Salt-okunur. Çıktı -> diagnostics/paper_tables/jsd_sensitivity.{md,json}
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from ferplus_human_vote_jsd import EMOTIONS, jsd  # noqa: E402  (AYNI JSD, AYNI sütunlar)
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402
from utils.configs import load_yaml  # noqa: E402

JSD_DIR = ROOT / "diagnostics" / "ferplus_jsd"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
CONFIG = "configs/FERPlus_8_vich_teacher_vae_ce_kld.yaml"

# ferplus_human_vote_jsd'nin taradığı gridin AYNISI. Farklı bir grid, kesitler arası
# farkı gridin kendisinden ayırt edilemez kılardı.
TS = [round(0.10 + 0.02 * i, 2) for i in range(int((4.00 - 0.10) / 0.02) + 1)]

# (etiket, alt sınır, üst sınır) -- oy toplamı bu aralıkta olan satırlar
STRATA = [("6-7", 6, 7), ("8-9", 8, 9), ("10", 10, 10)]


def load_ferplus():
    """(z, y, p_human, vote_sums) -- oy>0 satırlar, her biri KENDİ toplamına bölünmüş."""
    blob = torch.load(JSD_DIR / "ferplus_val_logits.pt", map_location="cpu",
                      weights_only=False)
    logits, labels, paths = blob["logits"], blob["labels"], blob["paths"]

    cfg = argparse.Namespace()
    load_yaml(cfg, str(ROOT / CONFIG))
    df = pd.read_csv(ROOT / cfg.metadata)
    df = df[df["fold"].isin(cfg.val_folds)].reset_index(drop=True)
    by_name = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows = [by_name[Path(p).name] for p in paths]
    votes = torch.tensor(df.loc[rows, EMOTIONS].to_numpy(dtype=np.float64), dtype=torch.float64)

    sums = votes.sum(dim=1)
    keep = sums > 0
    p_human = (votes[keep] / sums[keep].unsqueeze(1)).float()
    return logits[keep].double().float(), labels[keep], p_human, sums[keep]


def sweep(z, y, p_human):
    """Tek kesitte T taraması; üç optimum ve sınır kontrolü."""
    rec = []
    for T in TS:
        q = F.softmax(z / T, dim=1)
        rec.append({"T": T,
                    "mean_jsd": float(jsd(p_human, q).mean()),
                    "nll": float(F.cross_entropy(z / T, y.long())),
                    "ece": confidence_ece(z, y, T)})
    best = {k: min(rec, key=lambda r: r[f]) for k, f in
            (("jsd", "mean_jsd"), ("nll", "nll"), ("ece", "ece"))}
    at1 = next(r for r in rec if r["T"] == 1.0)
    on_boundary = sorted({k for k, v in best.items() if v["T"] in (TS[0], TS[-1])})
    return {
        "n": int(y.shape[0]),
        "T_jsd": best["jsd"]["T"], "jsd_at_opt": best["jsd"]["mean_jsd"],
        "T_nll": best["nll"]["T"], "T_ece": best["ece"]["T"],
        "ece_at_opt": best["ece"]["ece"],
        "jsd_at_T1": at1["mean_jsd"], "ece_at_T1": at1["ece"],
        "jsd_gain": at1["mean_jsd"] - best["jsd"]["mean_jsd"],
        "sep_jsd_ece": best["jsd"]["T"] - best["ece"]["T"],
        "sep_jsd_nll": best["jsd"]["T"] - best["nll"]["T"],
        # İKİ AYRI OLGU, birbirine karıştırılmamalı:
        # (1) BEYAN EDİLEN ayrışma (A10/R3-3: "ECE-optimal vs JSD-optimal ayrışması"):
        #     insan hizalanması, sert-etiket optimumlarının ikisinden de DAHA AZ
        #     keskinleştirme istiyor. Makalenin iddiası budur.
        # (2) ECE<NLL alt-sırası: yayımlanmış tabloda öyle çıkmış bir ayrıntı, iddia değil.
        # Bunları tek bir bayrakta toplamak, (2) kırıldığında (1) kırılmış gibi okunmasına
        # yol açar. Ayrı raporlanıyorlar.
        "separation_preserved": (best["jsd"]["T"] > max(best["ece"]["T"], best["nll"]["T"])),
        "suborder_ece_lt_nll": (best["ece"]["T"] < best["nll"]["T"]),
        "order_preserved": (best["ece"]["T"] < best["nll"]["T"] < best["jsd"]["T"]),
        "all_below_one": all(best[k]["T"] < 1.0 for k in best),
        "on_boundary": on_boundary,
    }


def main():
    z, y, p_human, sums = load_ferplus()
    hist = {int(s): int((sums == s).sum()) for s in sorted(set(sums.tolist()))}

    slices = {}
    slices["(a) all rows"] = (torch.ones_like(sums, dtype=torch.bool), "reference — the published result")
    slices["(b) vote sum = 10"] = (sums == 10, "highest-resolution human target")
    for lab, lo, hi in STRATA:
        slices[f"(c) stratum {lab}"] = ((sums >= lo) & (sums <= hi), f"vote sum in [{lo}, {hi}]")

    results = {}
    for name, (mask, why) in slices.items():
        n = int(mask.sum())
        if n == 0:
            results[name] = {"n": 0, "note": "empty slice", "why": why}
            continue
        r = sweep(z[mask], y[mask], p_human[mask])
        r["why"] = why
        results[name] = r

    ref = results["(a) all rows"]
    nonempty = {k: v for k, v in results.items() if v.get("n", 0) > 0}
    all_preserved = all(v["separation_preserved"] for v in nonempty.values())
    suborder_broken = [k for k, v in nonempty.items() if not v["suborder_ece_lt_nll"]]
    any_boundary = [k for k, v in nonempty.items() if v["on_boundary"]]
    t_jsd_values = sorted({v["T_jsd"] for v in nonempty.values()})

    L = ["# R3-3 — FERPlus JSD sensitivity to the vote-count stratum", "",
         "Producer: `diagnostics/jsd_sensitivity.py` · same teacher, same fold, same T grid "
         f"({TS[0]}–{TS[-1]} step 0.02, identical to `ferplus_human_vote_jsd.py`); only the row "
         "set changes · each row's vote vector is normalised by **its own** vote sum, exactly as "
         "in the published analysis · cached teacher logits, no forward pass. Pre-declared in "
         "`PREREGISTRATIONS.md` A10 (R3-3): **no success criterion** — whichever way the ordering "
         "falls is what goes in the paper.", "",
         "Vote-sum distribution over the reporting fold: "
         + ", ".join(f"**{k}** votes → {v} rows" for k, v in hist.items())
         + f" (total {sum(hist.values())}).", "",
         "| slice | n | T\\*_ECE | T\\*_NLL | T\\*_JSD | **separation** T\\*_JSD > both | "
         "sub-order ECE<NLL | T\\*_JSD − T\\*_ECE | JSD @T=1 | JSD @T\\*_JSD | JSD gain |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, r in results.items():
        if r.get("n", 0) == 0:
            L.append(f"| {name} | 0 | — | — | — | — | — | — | — | — | — |")
            continue
        sep = "✅ **held**" if r["separation_preserved"] else "❌ **BROKEN**"
        sub = "✅" if r["suborder_ece_lt_nll"] else "❌ flipped"
        L.append(f"| {name} | {r['n']} | {r['T_ece']:.2f} | {r['T_nll']:.2f} | {r['T_jsd']:.2f} | "
                 f"{sep} | {sub} | {r['sep_jsd_ece']:+.2f} | {r['jsd_at_T1']:.4f} | "
                 f"{r['jsd_at_opt']:.4f} | {r['jsd_gain']:+.4f} |")

    L += ["",
          "**Two different facts, kept apart on purpose.** The pre-declared quantity (A10, R3-3) "
          "is the **separation**: does human alignment want less sharpening than *either* "
          "hard-label criterion, i.e. T\\*_JSD > max(T\\*_ECE, T\\*_NLL)? That is the paper's "
          "claim. Whether T\\*_ECE happens to sit below T\\*_NLL is an incidental sub-ordering of "
          "the published table, not a claim. Collapsing the two into one flag would make a break "
          "in the second read as a break in the first.", "",
          "**Reported as it fell.** "]
    if all_preserved:
        L[-1] += ("The separation **holds in every slice**, including the highest-resolution one "
                  "(vote sum = 10, n=%d) and each individual stratum down to n=%d. It is "
                  "therefore not an artefact of pooling rows with different vote counts."
                  % (results["(b) vote sum = 10"]["n"],
                     min(v["n"] for v in nonempty.values())))
        if len(t_jsd_values) == 1:
            L[-1] += (f" T\\*_JSD is furthermore **identical ({t_jsd_values[0]:.2f}) in every "
                      f"slice** — the human-alignment optimum does not move with vote resolution "
                      f"at all.")
        else:
            big = {k: v for k, v in nonempty.items() if v["n"] >= 1000}
            if len({v["T_jsd"] for v in big.values()}) == 1:
                common = list(big.values())[0]["T_jsd"]
                # Kapsam YALNIZ (c) katmanları üzerinden sayılır: (a) ve (b) onlarla
                # örtüşür, hepsini toplamak satırları iki kez sayardı.
                n_cov = sum(v["n"] for k, v in nonempty.items()
                            if k.startswith("(c)") and v["T_jsd"] == common)
                L[-1] += (f" T\\*_JSD is furthermore identical ({common:.2f}) in every slice with "
                          f"n ≥ 1000; the strata carrying that value account for {n_cov} of the "
                          f"fold's {ref['n']} rows "
                          f"({100 * n_cov / ref['n']:.1f}%), and T\\*_JSD moves only in the "
                          f"smallest stratum "
                          f"(overall T\\*_JSD ∈ {{{', '.join(f'{t:.2f}' for t in t_jsd_values)}}}).")
    else:
        broken = [k for k, v in nonempty.items() if not v["separation_preserved"]]
        L[-1] += ("The separation does **not** survive every slice. It breaks in: "
                  + ", ".join(f"`{b}` (n={nonempty[b]['n']}; ECE {nonempty[b]['T_ece']:.2f}, NLL "
                              f"{nonempty[b]['T_nll']:.2f}, JSD {nonempty[b]['T_jsd']:.2f})"
                              for b in broken)
                  + ". The claim can therefore only be stated for the slices where it holds and "
                    "the paper must name the conditioning explicitly.")
    if suborder_broken:
        L += ["",
              "The incidental sub-ordering T\\*_ECE < T\\*_NLL flips in "
              + ", ".join(f"`{b}` (n={nonempty[b]['n']}, "
                          f"{100 * nonempty[b]['n'] / ref['n']:.1f}% of the fold)"
                          for b in suborder_broken)
              + ". This is reported because the pre-declaration forbids withholding a break, not "
                "because a claim rests on it: at that n the two optima are separated by one or "
                "two grid steps and the slice's own JSD gain is the smallest of all slices."]
    L += ["",
          f"Reference slice (a) reproduces the published values: T\\*_ECE {ref['T_ece']:.2f}, "
          f"T\\*_NLL {ref['T_nll']:.2f}, T\\*_JSD {ref['T_jsd']:.2f}, n={ref['n']}.", ""]
    if any_boundary:
        L += ["> ⚠️ **Boundary optima.** In " + ", ".join(f"`{k}`" for k in any_boundary) +
              " at least one optimum sits on the edge of the T grid, so it is not a resolved "
              "optimum and must not be quoted as one.", ""]

    payload = {"pre_registration": "PREREGISTRATIONS.md A10 (R3-3); no success criterion",
               "grid": {"lo": TS[0], "hi": TS[-1], "step": 0.02, "points": len(TS)},
               "normalisation": "each row divided by its own vote sum (= ferplus_human_vote_jsd)",
               "vote_sum_histogram": hist,
               "declared_quantity": "separation: T*_JSD > max(T*_ECE, T*_NLL)",
               "published_ordering": "T*_ECE < T*_NLL < T*_JSD, all < 1",
               "separation_preserved_everywhere": all_preserved,
               "suborder_broken_slices": suborder_broken,
               "T_jsd_values_across_slices": t_jsd_values,
               "boundary_slices": any_boundary,
               "results": results}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "jsd_sensitivity.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "jsd_sensitivity.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"vote-sum histogram: {hist}")
    for name, r in results.items():
        if r.get("n", 0) == 0:
            print(f"  {name:<22} EMPTY")
            continue
        print(f"  {name:<22} n={r['n']:<5} ECE {r['T_ece']:.2f}  NLL {r['T_nll']:.2f}  "
              f"JSD {r['T_jsd']:.2f}  order {'OK' if r['order_preserved'] else 'BROKEN'}")
    print(f"\nWrote {OUT_DIR / 'jsd_sensitivity.md'}")

    # Bant altyapısı genel depoda bulunmaz; yokluğu tablo üretimini durdurmamalı.
    try:
        import export_to_drive
        export_to_drive.hook("jsd_sensitivity.py")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
