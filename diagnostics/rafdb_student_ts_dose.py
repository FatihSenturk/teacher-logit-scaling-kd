# -*- coding: utf-8 -*-
"""K5 (Round-6, 27 Ağu 2026): RAF-DB student-side TS baseline — FERPlus protokolünün simetriği.

ÖN-BEYAN (bu docstring koşudan ÖNCE commit'lenir; S11 kültürü). İki bağımsız dış değerlendirme
aynı isteğe yakınsadı: FERPlus'ta kurulan sızıntısız öğrenci-TS karşılaştırması RAF-DB'de de
koşulmalı. Karar: SONUÇ NE ÇIKARSA basılır — doz-yanıt açıklığı öğrenci ölçeklemesiyle çökerse
de kalırsa da; §5.7'nin "clean partition" savunması sonuçla birlikte yeniden yazılacak. Başarı
ölçütü YOKTUR; bu bir envanter ölçümüdür.

PROTOKOL — FERPlus'takiyle (student_ts_baseline.py / r3w1_joint_optimum.py) bire bir:
  - raporlama kümesi: RAF-DB fold-3 (n=3068);
  - öğrenci logitleri YAYIMLANMIŞ bayt kopyalarından (diagnostics/student_logits/*.npz,
    @swa) — koşu dizini yok, forward yok, eğitim yok;
  - dosya adları metadata CSV'nin fold-3 satırlarından; satır sırası npz ile etiket-eşitliği
    KAPISIYLA doğrulanır (ayrışırsa sayı üretilmez, durulur);
  - bölme: sha256(dosya adı) hex sıralı, ilk yarı A / ikinci yarı B (FERPlus kuralının aynısı,
    `student_ts_baseline.sha_split` İTHAL edilir — iki kopya ayrışmasın);
  - T_s: yarı A'da NLL küçültme ile fit, yarı B'de ölçüm; yönler değişir; birleşik değer her
    örneği tam bir kez, karşı yarının T'siyle ölçer (`fit_ts` ithal);
  - kol eşlemesi: p1_two_teacher_overlay.CURVES (koşu→(öğretmen,T) için tek kaynak).

ALANLAR K1'in ECE-ekseni artefaktıyla (ferplus_scaled_ece_axis.json) simetrik: kol başına
raw/ts ECE (ortalama ± örneklem sd + tohum başına), öğretmen başına açıklıklar, çökme çarpanı
(payda adıyla), ölçekli sıralama, tohum tutarlılığı.

Çıktı -> diagnostics/paper_tables/rafdb_student_ts_dose.{json,md}
"""
import hashlib
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from student_ts_baseline import sha_split, fit_ts  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402
from p1_two_teacher_overlay import CURVES, SEEDS, TEACHER_GRID  # noqa: E402
from publish_student_logits import published_npz  # noqa: E402

META = ROOT / "data" / "rafdb_aligned" / "metadata_rafdb_poster_var.csv"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
CK = "swa"


def fold3_names_and_labels():
    """Metadata fold-3: (adlar, etiketler) — npz satır sırasıyla aynı olduğu KAPIDA doğrulanır."""
    import csv
    names, labels = [], []
    with open(META, encoding="utf-8-sig") as fh:   # dosya BOM'lu; düz utf-8 ilk kolonu 'ï»¿path' yapar
        for r in csv.DictReader(fh):
            if int(r["fold"]) == 3:
                names.append(Path(r["path"]).name)
                labels.append(int(r["label"]))
    return names, np.asarray(labels)


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    names, meta_labels = fold3_names_and_labels()
    n = len(names)
    mask_a, mask_b = sha_split(names)
    na, nb = int(mask_a.sum()), int(mask_b.sum())
    print(f"RAF-DB fold-3 n={n} · SHA-sıralı bölme A={na} / B={nb} · @{CK} · kaynak: "
          f"yayımlanmış logit kopyaları")

    out_arms = {}
    for teacher, by_T in CURVES.items():
        grid = TEACHER_GRID[teacher]["experiment_grid"]
        for T in sorted(by_T):
            raws, tss, per_seed = [], [], {}
            for s in SEEDS:
                run = by_T[T].get(s)
                if run is None:
                    continue
                z = np.load(published_npz(run, CK), allow_pickle=False)
                logits = torch.from_numpy(z["logits"]).float()
                labels = torch.from_numpy(z["labels"]).long()
                # KAPI: npz satır sırası == metadata fold-3 sırası (etiket-eşitliği).
                if labels.shape[0] != n or not (labels.numpy() == meta_labels).all():
                    raise RuntimeError(
                        f"{run}: yayımlanmış etiket vektörü metadata fold-3 sırasıyla "
                        f"uyuşmuyor — ad tabanlı bölme uygulanamaz, sayı üretilmez.")
                raw_ece = confidence_ece(logits, labels, 1.0)
                t_ab = fit_ts(logits[mask_a], labels[mask_a])
                t_ba = fit_ts(logits[mask_b], labels[mask_b])
                e_b = confidence_ece(logits[mask_b], labels[mask_b], t_ab)
                e_a = confidence_ece(logits[mask_a], labels[mask_a], t_ba)
                ts_ece = (e_a * na + e_b * nb) / n
                raws.append(raw_ece)
                tss.append(ts_ece)
                per_seed[str(s)] = {"run": run, "raw_ece": raw_ece, "ts_ece": ts_ece,
                                    "T_s_fitA_evalB": t_ab, "T_s_fitB_evalA": t_ba}
            key = f"{teacher}/{T:g}"
            out_arms[key] = {
                "teacher": teacher, "T": T,
                "teacher_ece": grid[f"{T:g}"]["teacher_ece"],
                "n": len(raws),
                "raw_ece": [st.mean(raws), sample_sd(raws)],
                "ts_ece": [st.mean(tss), sample_sd(tss)],
                "per_seed": per_seed,
            }
            print(f"  [{teacher}] T={T:<7g} raw {st.mean(raws):.4f}±{sample_sd(raws):.4f}  "
                  f"TS {st.mean(tss):.4f}±{sample_sd(tss):.4f}  n={len(raws)}")

    spans, collapse, ranking, consistency = {}, {}, {}, {}
    for teacher in CURVES:
        keys = [k for k in out_arms if out_arms[k]["teacher"] == teacher]
        for world in ("raw", "ts"):
            means = {k: out_arms[k][f"{world}_ece"][0] for k in keys}
            hi, lo = max(means, key=means.get), min(means, key=means.get)
            spans[f"{teacher}/{world}"] = {
                "span": means[hi] - means[lo], "max_arm": hi, "min_arm": lo,
                "numerator": f"max-arm mean minus min-arm mean, {world} ECE, "
                             f"{len(keys)} arms of {teacher}"}
        raw, ts = spans[f"{teacher}/raw"]["span"], spans[f"{teacher}/ts"]["span"]
        collapse[teacher] = {
            "factor": raw / ts,
            "spread_removed_frac": (raw - ts) / raw,
            "spread_surviving_frac": ts / raw,
            "numerator": f"raw between-arm ECE span of {teacher} ({raw:.5f})",
            "denominator": f"scaled between-arm ECE span of {teacher} ({ts:.5f})"}
        ranking[teacher] = sorted(keys, key=lambda k: out_arms[k]["ts_ece"][0])
        # tohum tutarlılığı: ölçekli dünyada en iyi kol, tohum tohum da en iyi mi
        best = ranking[teacher][0]
        wins = 0
        for s in map(str, SEEDS):
            if all(s in out_arms[k]["per_seed"] for k in keys):
                vals = {k: out_arms[k]["per_seed"][s]["ts_ece"] for k in keys}
                wins += min(vals, key=vals.get) == best
        # 28 Ağu 2026: §5.7'nin iki cümlesi ORTALAMA sıralamadan değil, TOHUM BAŞINA
        # sıralamadan konuşuyor ("stays dose-ordered in all three seeds"). Ortalama sıra ile
        # tohum başına sıra aynı şey değil (stage1'de ayrışıyorlar), o yüzden ikisi de alan.
        by_T = sorted(keys, key=lambda k: out_arms[k]["T"])          # doz sırası
        matched = dosed = 0
        for s in map(str, SEEDS):
            if not all(s in out_arms[k]["per_seed"] for k in keys):
                continue
            vals = {k: out_arms[k]["per_seed"][s]["ts_ece"] for k in keys}
            matched += sorted(keys, key=vals.get) == ranking[teacher]
            seq = [vals[k] for k in by_T]
            dosed += all(a < b for a, b in zip(seq, seq[1:]))
        consistency[teacher] = {
            "scaled_best_arm": best,
            "scaled_best_T": out_arms[best]["T"],
            "best_arm_wins_per_seed": f"{wins}/{len(SEEDS)}",
            "pooled_ranking_matched_per_seed": f"{matched}/{len(SEEDS)}",
            "dose_ordered_per_seed": f"{dosed}/{len(SEEDS)}",
            "dose_order_definition": "scaled ECE strictly increasing along the T grid "
                                     + " < ".join(k.split("/")[1] for k in by_T)}

    # T* ile işlenmemiş kol arasındaki ÖLÇEKLİ fark. §5.7 bunu "shrinks to 0.0011" diye
    # basıyor; iki alanın farkı olarak burada duruyor ki makale tarafı basılı yuvarlanmış
    # değerlerden türetme yapmak zorunda kalmasın. Payda değil, fark — pay iki kolun adıyla.
    tstar_vs_native = {}
    for teacher, tstar in (("stage1", 1.3406), ("vae9182", 1.3406)):
        a, b_ = f"{teacher}/{tstar:g}", f"{teacher}/1"
        if a not in out_arms or b_ not in out_arms:
            continue
        wins = sum(1 for s in map(str, SEEDS)
                   if s in out_arms[a]["per_seed"] and s in out_arms[b_]["per_seed"]
                   and out_arms[a]["per_seed"][s]["ts_ece"] < out_arms[b_]["per_seed"][s]["ts_ece"])
        tstar_vs_native[teacher] = {
            "tstar_arm": a, "native_arm": b_,
            "gap_scaled": out_arms[b_]["ts_ece"][0] - out_arms[a]["ts_ece"][0],
            "numerator": f"native-arm scaled ECE mean ({out_arms[b_]['ts_ece'][0]:.5f}) minus "
                         f"T*-arm scaled ECE mean ({out_arms[a]['ts_ece'][0]:.5f})",
            "tstar_beats_native_per_seed": f"{wins}/{len(SEEDS)}"}

    data = {"sd_convention": SD_CONVENTION, "checkpoint": CK, "n_val": n,
            "split": {"rule": "sha256(filename) hex sort, first half A", "n_A": na, "n_B": nb},
            "fit": "single-scalar TS, NLL minimisation (Guo et al. 2017), cross-fitted",
            "source": "published logit copies (diagnostics/student_logits/*.npz); "
                      "run->arm map: p1_two_teacher_overlay.CURVES; names: metadata fold-3 "
                      "(row order verified against npz labels, hard gate)",
            "arms": out_arms, "spans": spans, "collapse": collapse,
            "scaled_ranking_by_ece": ranking, "seed_consistency": consistency,
            "tstar_vs_native": tstar_vs_native}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "rafdb_student_ts_dose.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    L = ["# K5 — RAF-DB student-side TS across the dose arms (leak-free, published logits)", "",
         f"@{CK} · n={n} · A={na}/B={nb} · {SD_CONVENTION} · no training, no run dirs", "",
         "| arm | teacher ECE | raw student ECE | scaled student ECE | n |",
         "|---|---|---|---|---|"]
    for k in sorted(out_arms, key=lambda k: (out_arms[k]["teacher"], out_arms[k]["T"])):
        v = out_arms[k]
        L.append(f"| {k} | {v['teacher_ece']:.4f} | {v['raw_ece'][0]:.4f} ± "
                 f"{v['raw_ece'][1]:.4f} | {v['ts_ece'][0]:.4f} ± {v['ts_ece'][1]:.4f} | "
                 f"{v['n']} |")
    L.append("")
    for teacher in CURVES:
        c = collapse[teacher]
        L.append(f"- **{teacher}**: raw span {spans[f'{teacher}/raw']['span']:.4f} -> scaled "
                 f"span {spans[f'{teacher}/ts']['span']:.4f}; collapse {c['factor']:.1f}x, "
                 f"spread removed {c['spread_removed_frac']*100:.1f}% (denominator: raw span); "
                 f"scaled ranking {' < '.join(x.split('/')[1] for x in ranking[teacher])}; "
                 f"best arm per-seed {consistency[teacher]['best_arm_wins_per_seed']}.")
    L.append("")
    (OUT_DIR / "rafdb_student_ts_dose.md").write_text("\n".join(L), encoding="utf-8")
    print()
    for line in L[-1 - len(CURVES):-1]:
        print(line)
    print(f"-> {OUT_DIR / 'rafdb_student_ts_dose.json'}")


if __name__ == "__main__":
    main()
