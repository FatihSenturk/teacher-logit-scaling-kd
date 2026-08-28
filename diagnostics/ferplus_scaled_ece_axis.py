# -*- coding: utf-8 -*-
"""K1 (Round-6, 27 Ağu 2026): student-side scaling'in ECE-EKSENİ özeti — JSD'nin 37×'iyle simetrik.

NEDEN VAR. §5.7 JSD ekseninde şunu kuruyor: dört ham kol JSD'de 0.0201 açılıyor, kol başına
tek çapraz-fit skalerden sonra 0.00054'e çöküyor — 37×. Aynı protokolün ECE eksenindeki
çıktısı artefakt olarak yapılandırılmamıştı: değerler `r3w1_joint_optimum.json`un per_seed
bloğunda duruyordu ama açıklık/çökme/sıralama alanları yoktu, yani makale tarafı bağlanacak
alan bulamıyordu. Bu üretici o alanları TÜRETİR — kaynak yayımlanmış artefakt, yeni
değerlendirme yok, koşu dizini yok, eğitim yok (Level-1 uyumlu).

ALAN SİMETRİSİ. JSD tarafının cümlesi span_raw→span_ts→collapse_factor üçlüsüyle kuruluyor;
ECE tarafı aynı üçlüyü taşır. Payda her oranda adıyla yazılır (kampanya kuralı): çökme
çarpanı = span_raw / span_ts; kaldırılan pay = (span_raw − span_ts) / span_raw.

Çıktı -> diagnostics/paper_tables/ferplus_scaled_ece_axis.{json,md}
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

SRC = ROOT / "diagnostics" / "paper_tables" / "r3w1_joint_optimum.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
SEEDS = ("42", "1", "43")
UNTREATED, TSTAR_ECE, TSTAR_JSD = "1.0", "0.5063", "0.74"


def main():
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    src = json.loads(SRC.read_text(encoding="utf-8"))
    ps = src["per_seed"]
    arms = sorted(ps, key=float)
    if set(arms) != {"0.26", "0.5063", "0.74", "1.0"}:
        raise RuntimeError(f"beklenmeyen kol kümesi: {arms}")

    out_arms, spans = {}, {}
    for metric in ("ece", "jsd"):
        for world in ("raw", "ts"):
            means = {}
            for arm in arms:
                vals = [ps[arm][s][world][metric] for s in SEEDS]
                means[arm] = st.mean(vals)
                a = out_arms.setdefault(arm, {})
                a[f"{world}_{metric}"] = [st.mean(vals), sample_sd(vals)]
                a.setdefault("per_seed", {})
                for s in SEEDS:
                    a["per_seed"].setdefault(s, {})[f"{world}_{metric}"] = ps[arm][s][world][metric]
            hi = max(means, key=means.get)
            lo = min(means, key=means.get)
            spans[f"{world}_{metric}"] = {
                "span": means[hi] - means[lo], "max_arm": hi, "min_arm": lo,
                "numerator": f"max-arm mean minus min-arm mean, {world} {metric}, 4 arms"}

    collapse = {}
    removal = {}
    for metric in ("ece", "jsd"):
        raw, ts = spans[f"raw_{metric}"]["span"], spans[f"ts_{metric}"]["span"]
        collapse[metric] = {
            "factor": raw / ts,
            "numerator": f"raw between-arm span of {metric} ({raw:.5f})",
            "denominator": f"scaled between-arm span of {metric} ({ts:.5f})"}
        removal[metric] = {
            "spread_removed_frac": (raw - ts) / raw,
            "spread_surviving_frac": ts / raw,
            "denominator": f"raw between-arm span of {metric} ({raw:.5f})"}

    ranking = sorted(arms, key=lambda a: out_arms[a]["ts_ece"][0])
    # tohum tutarlılığı: ölçekli dünyada işlenmemiş kol (T=1.0), T*_ECE kolunu tohum tohum
    # geçiyor mu — makalenin "3/3" tipi cümleleri ortalamayla değil bununla kurulur.
    beats = sum(1 for s in SEEDS
                if ps[UNTREATED][s]["ts"]["ece"] < ps[TSTAR_ECE][s]["ts"]["ece"])
    beats_all = sum(1 for s in SEEDS
                    if all(ps[UNTREATED][s]["ts"]["ece"] < ps[a][s]["ts"]["ece"]
                           for a in arms if a != UNTREATED))
    # 28 Agu 2026: §5.7 "the T*_ECE arm worst (0.0296, all three seeds)" diyor. Bu, yukaridaki
    # `untreated_beats_tstar_ece_scaled` DEGIL -- o "islenmemis kol T*'i geciyor mu" sorusu.
    # Ikisi de 3/3 cikiyor ve tam bu yuzden alan gerekiyordu: cumlenin bagi, degeri tesadufen
    # esit olan baska bir alana dusmesin.
    worst_all = sum(1 for s in SEEDS
                    if all(ps[TSTAR_ECE][s]["ts"]["ece"] > ps[a][s]["ts"]["ece"]
                           for a in arms if a != TSTAR_ECE))

    data = {
        "source": "diagnostics/paper_tables/r3w1_joint_optimum.json (per_seed; published "
                  "artifact -- no run dirs, no new evaluation)",
        "protocol": src.get("split", {}),
        "checkpoint": src.get("checkpoint"), "n_val": src.get("n_val"),
        "sd_convention": SD_CONVENTION,
        "arms": out_arms, "spans": spans,
        "collapse": collapse, "removal": removal,
        "scaled_ranking_by_ece": ranking,
        "scaled_best_arm": {"arm": ranking[0], "ts_ece": out_arms[ranking[0]]["ts_ece"]},
        "scaled_worst_arm": {"arm": ranking[-1], "ts_ece": out_arms[ranking[-1]]["ts_ece"]},
        "seed_consistency": {
            "untreated_beats_tstar_ece_scaled": f"{beats}/{len(SEEDS)}",
            "untreated_best_of_all_scaled": f"{beats_all}/{len(SEEDS)}",
            "tstar_ece_worst_of_all_scaled": f"{worst_all}/{len(SEEDS)}"},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "ferplus_scaled_ece_axis.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    L = ["# K1 — FERPlus student-side scaling, ECE axis (derived from r3w1, no new eval)", "",
         f"Source: `r3w1_joint_optimum.json` per_seed · @{data['checkpoint']} · "
         f"n={data['n_val']} · {SD_CONVENTION}", "",
         "| arm (teacher pre-scale T) | raw ECE | scaled ECE | raw JSD | scaled JSD |",
         "|---|---|---|---|---|"]
    for a in arms:
        v = out_arms[a]
        L.append(f"| {a} | {v['raw_ece'][0]:.4f} ± {v['raw_ece'][1]:.4f} | "
                 f"{v['ts_ece'][0]:.4f} ± {v['ts_ece'][1]:.4f} | "
                 f"{v['raw_jsd'][0]:.4f} ± {v['raw_jsd'][1]:.4f} | "
                 f"{v['ts_jsd'][0]:.4f} ± {v['ts_jsd'][1]:.4f} |")
    e, j = collapse["ece"], collapse["jsd"]
    L += ["",
          f"- ECE: raw span **{spans['raw_ece']['span']:.4f}** "
          f"({spans['raw_ece']['min_arm']}..{spans['raw_ece']['max_arm']}) -> scaled span "
          f"**{spans['ts_ece']['span']:.4f}** ({spans['ts_ece']['min_arm']}.."
          f"{spans['ts_ece']['max_arm']}); collapse **{e['factor']:.1f}x**, spread removed "
          f"**{removal['ece']['spread_removed_frac']*100:.1f}%** (denominator: raw span).",
          f"- JSD: raw span {spans['raw_jsd']['span']:.4f} -> scaled span "
          f"{spans['ts_jsd']['span']:.5f}; collapse **{j['factor']:.0f}x** (the printed 37x).",
          f"- Scaled ranking by ECE: {' < '.join(ranking)}; untreated beats T*_ECE "
          f"{data['seed_consistency']['untreated_beats_tstar_ece_scaled']} seeds, "
          f"best-of-all {data['seed_consistency']['untreated_best_of_all_scaled']}.", ""]
    (OUT_DIR / "ferplus_scaled_ece_axis.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L[4:]))
    print(f"-> {OUT_DIR / 'ferplus_scaled_ece_axis.json'}")


if __name__ == "__main__":
    main()
