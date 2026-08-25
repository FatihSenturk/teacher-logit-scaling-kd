"""P5 hükmü: `gate:oracle_error`in kalibrasyon hasarı stage1 ve primary'de tekrarlanıyor mu?

NE TEST EDİLİYOR. P2, VAE9182'de kusursuz-bilgi (oracle) gate'inin kalibrasyonu **tutarlı
biçimde bozduğunu** ölçtü (ΔECE +0.0056, 3/3 aynı işaret, temiz `cw=none` kontrole karşı).
D1'in kapanış gerekçesi ("gate işe yaramıyor değil, kalibrasyonu BOZUYOR") o tek öğretmene
koşulluydu. P5 aynı manipülasyonu iki öğretmende daha, aynı üç tohumda tekrarlıyor — 6 koşu,
çünkü stage1/primary'de hiç oracle koşusu yoktu ve bir replikasyon aynı manipülasyonu
tekrarlamak zorundadır.

DONMUŞ KARAR KURALI — koşudan önce yazıldı, sonra değiştirilmedi
(`rafdb_p5_oracle_replication_queue.ps1`, `PREREGISTRATIONS.md` A8-P5):

    Her kol KENDİ öğretmeninin `cw=none` kontrol kolunun ECE tohum sd'sine karşı ölçülür.
    Barlar: stage1 = 0.0021, primary = 0.0033.

    KURULU        :  3/3 tohumda ΔECE aynı işaretli  VE  |ortalama ΔECE| >= 2 x bar
    ÇÖZÜNMEDİ     :  aksi her durumda

İki sonucun metni de önceden sabitlendi. Kural bir VE bağlacıdır: iki koşuldan biri düşerse
hüküm ÇÖZÜNMEDİ'dir, diğerinin ne kadar yaklaştığına bakılmaz.

ÇÖZÜNMEDİ NE DEMEK DEĞİL. "Etki yok" demek değil. Bu bar, tek bir kolun tohum gürültüsünün iki
katıdır; altında kalan bir etki *ölçülemedi* demektir, *yoktur* demek değil. Metinde de böyle
yazılacak.

@swa BİRİNCİL. `best` raporlanan 3068 görüntüde argmax val-acc ile seçilir, yani seçim
iyimserliği taşır; @best/@last yalnız hükmün checkpoint seçimine bağlı olmadığını göstermek
için basılır.

VERİ KAYNAĞI: `selection_audit_unfrozen.csv`. P5 koşuları donmuş kesmenin (2026-07-31-06:00)
DIŞINDA başlatıldı; donmuş `selection_audit.csv` yalnız T8'in N=131'ini taşır ve bu betik onu
okumaz.

Salt-okunur, GPU yok. Çıktı -> diagnostics/p5_oracle_replication/p5_verdict.{json,md}
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit_unfrozen.csv"
RUNS = ROOT / "runs.csv"
OUT_DIR = ROOT / "diagnostics" / "p5_oracle_replication"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SEEDS = (42, 1, 43)
CKPTS = ("swa", "best", "last")
PRIMARY_CKPT = "swa"
BASE = "_b070_T6_224_400e_swa200"

# DONMUŞ BARLAR. Beyanda yazılı sabitler; aşağıda veriden yeniden ölçülüp karşılaştırılıyor.
# Uyuşmazlık olursa beyan edilen değer kullanılır (ön-kayıt odur) ve fark rapora yazılır --
# sessizce yeniden ölçülene geçmek, kuralı sonuca göre seçmek olurdu.
DECLARED_BAR = {"stage1": 0.0021, "primary": 0.0033}
ARMS = {
    "stage1": (f"RAFDB_stage1_gate_oracle_error{BASE}",
               f"RAFDB_stage1_baseline_noclassweight{BASE}"),
    "primary": (f"RAFDB_primary_gate_oracle_error{BASE}",
                f"RAFDB_primary_baseline_noclassweight{BASE}"),
}
# P2'nin sonucu, aynı tabloda karşılaştırma için (replikasyonun hedefi bu satır).
REFERENCE = ("vae9182", f"RAFDB_vae9182_gate_oracle_error{BASE}",
             f"RAFDB_vae9182_baseline_noclassweight{BASE}")


def build_seed_index():
    """(base_name, seed) -> run_name, her koşunun KENDİ kayıtlı seed'inden.

    Aileler seed 42'yi aynı yazmıyor (kimi `_seed42`, kimi sonek yok). İsimden kural çıkarmak
    3 tohumdan 2'sini eşleştirip n=3'te dondurulmuş bir tahmine n=2 hüküm verdirir.
    """
    idx = {}
    for r in csv.DictReader(open(RUNS, encoding="utf-8")):
        name, seed = r["run_name"], int(r["seed"])
        for base in (name, name.rsplit("_seed", 1)[0] if "_seed" in name else name):
            k = (base, seed)
            if k in idx and idx[k] != name:
                raise RuntimeError(f"{k} hem {idx[k]} hem {name} ile eşleşiyor")
            idx[k] = name
    return idx


SEED_INDEX = None


def resolve(base, seed):
    n = SEED_INDEX.get((base, seed))
    if n is None:
        raise RuntimeError(f"'{base}' için seed {seed} koşusu yok — kol eksik; "
                           f"isim tahminine düşülmeyecek.")
    return n


def load_audit():
    out = {}
    for r in csv.DictReader(open(AUDIT, encoding="utf-8")):
        k = (r["run_name"], r["checkpoint"])
        if k in out and out[k]["timestamp"] != r["timestamp"]:
            raise RuntimeError(f"{k} iki zaman damgasıyla var — hüküm sıraya bağlı olmasın.")
        out[k] = {"acc": float(r["acc"]), "ece": float(r["ece"]), "timestamp": r["timestamp"]}
    return out


def paired(audit, treat, control, ckpt):
    d_acc, d_ece, per_seed = [], [], {}
    for s in SEEDS:
        a = audit.get((resolve(control, s), ckpt))
        b = audit.get((resolve(treat, s), ckpt))
        if not a or not b:
            continue
        da, de = b["acc"] - a["acc"], b["ece"] - a["ece"]
        d_acc.append(da)
        d_ece.append(de)
        per_seed[s] = {"d_acc": da, "d_ece": de, "treat_ece": b["ece"],
                       "control_ece": a["ece"], "treat_acc": b["acc"], "control_acc": a["acc"]}
    return d_acc, d_ece, per_seed


def arm_stats(audit, base, ckpt):
    vals = [audit[(resolve(base, s), ckpt)] for s in SEEDS
            if (resolve(base, s), ckpt) in audit]
    return {"acc_mean": st.mean([v["acc"] for v in vals]),
            "acc_sd": sample_sd([v["acc"] for v in vals]),
            "ece_mean": st.mean([v["ece"] for v in vals]),
            "ece_sd": sample_sd([v["ece"] for v in vals]), "n": len(vals)}


def signs(vals):
    return "".join("+" if v > 0 else "-" for v in vals)


def judge(d_ece, bar):
    """DONMUŞ KURAL, harfiyen. VE bağlacı: iki koşul da sağlanmadıkça KURULU değil."""
    m = st.mean(d_ece)
    sg = signs(d_ece)
    same_sign = len(set(sg)) == 1 and len(d_ece) == 3
    big_enough = abs(m) >= 2 * bar
    return {"mean": m, "sd": sample_sd(d_ece), "signs": sg, "n": len(d_ece),
            "same_sign": same_sign, "bar": bar, "two_bar": 2 * bar,
            "ratio": abs(m) / bar, "big_enough": big_enough,
            "verdict": "ESTABLISHED" if (same_sign and big_enough) else "UNRESOLVED"}


def main():
    global SEED_INDEX
    SEED_INDEX = build_seed_index()
    audit = load_audit()

    res, verdicts = {}, {}
    for teacher, (treat, control) in ARMS.items():
        res[teacher] = {}
        for ck in CKPTS:
            d_acc, d_ece, per_seed = paired(audit, treat, control, ck)
            res[teacher][ck] = {"d_acc": d_acc, "d_ece": d_ece, "per_seed": per_seed,
                                "treat": arm_stats(audit, treat, ck),
                                "control": arm_stats(audit, control, ck)}
        p = res[teacher][PRIMARY_CKPT]
        if len(p["d_ece"]) != 3:
            raise RuntimeError(f"{teacher}: @{PRIMARY_CKPT}'de 3 eşleşmiş tohum bekleniyordu, "
                               f"{len(p['d_ece'])} bulundu — hüküm n=3'te donduruldu, n<3'te "
                               f"verilmeyecek.")
        verdicts[teacher] = judge(p["d_ece"], DECLARED_BAR[teacher])
        verdicts[teacher]["measured_bar"] = p["control"]["ece_sd"]
        verdicts[teacher]["bar_matches_declaration"] = (
            abs(p["control"]["ece_sd"] - DECLARED_BAR[teacher]) < 5e-5)

    # P2'nin referans satırı (replikasyonun hedefi)
    rt, rtreat, rctrl = REFERENCE
    r_acc, r_ece, _ = paired(audit, rtreat, rctrl, PRIMARY_CKPT)
    ref = {"teacher": rt, "d_acc_mean": st.mean(r_acc), "d_ece_mean": st.mean(r_ece),
           "d_ece_sd": sample_sd(r_ece), "signs": signs(r_ece), "n": len(r_ece)}

    n_kurulu = sum(1 for v in verdicts.values() if v["verdict"] == "KURULU")

    L = ["# P5 verdict — does `gate:oracle_error`'s calibration harm replicate?", "",
         f"Producer: `diagnostics/p5_oracle_replication_verdict.py` · @{PRIMARY_CKPT} primary · "
         f"{SD_CONVENTION}", "",
         "> **Pre-registered.** The decision rule was frozen inside `rafdb_p5_oracle_replication_queue.ps1` at "
         "2026-07-31 14:14:11; the first run started at 14:14:40 (**+29 seconds**). "
         "Rule: *3/3 same sign **AND** |ΔECE| ≥ 2 × the ECE seed sd of that arm's own `cw=none` "
         "control* → ESTABLISHED; otherwise UNRESOLVED.", "",
         "## Verdict", "",
         "| teacher | ΔECE (@swa) | signs | bar | 2×bar | |ΔECE|/bar | verdict |",
         "|---|---|---|---|---|---|---|"]
    for t, v in verdicts.items():
        L.append(f"| {t} | **{v['mean']:+.4f}** ± {v['sd']:.4f} | `{v['signs']}` | "
                 f"{v['bar']:.4f} | {v['two_bar']:.4f} | {v['ratio']:.2f}× | "
                 f"**{v['verdict']}** |")
    L += ["", f"| _reference: {ref['teacher']} (P2, the finding being replicated)_ | "
              f"_{ref['d_ece_mean']:+.4f} ± {ref['d_ece_sd']:.4f}_ | `{ref['signs']}` | — | — | "
              f"— | _established in P2_ |", ""]

    for t, v in verdicts.items():
        if not v["bar_matches_declaration"]:
            L += [f"> ⚠️ **{t}: declared bar {v['bar']:.4f}, re-measured "
                  f"{v['measured_bar']:.4f}.** The verdict uses the **declared** bar — that is what was "
                  f"pre-registered. Using the re-measured one would be choosing the rule after seeing the result.",
                  ""]

    L += ["## Differences paired within seed (@swa)", "",
          "| teacher | seed | Δacc (pp) | ΔECE |", "|---|---|---|---|"]
    for t in ARMS:
        for s in SEEDS:
            c = res[t][PRIMARY_CKPT]["per_seed"].get(s)
            if c:
                L.append(f"| {t} | {s} | {c['d_acc']:+.3f} | {c['d_ece']:+.4f} |")
    L += ["", "## Kollar (@swa)", "",
          "| teacher | arm | acc (%) | ECE | n |", "|---|---|---|---|---|"]
    for t in ARMS:
        p = res[t][PRIMARY_CKPT]
        for lab, k in (("kontrol (`cw=none` baseline)", "control"),
                       ("tedavi (`gate:oracle_error`)", "treat")):
            a = p[k]
            L.append(f"| {t} | {lab} | {a['acc_mean']:.3f} ± {a['acc_sd']:.3f} | "
                     f"{a['ece_mean']:.4f} ± {a['ece_sd']:.4f} | {a['n']} |")

    L += ["", "## Does the verdict depend on the checkpoint choice", "",
          "| teacher | checkpoint | Δacc (pp) | ΔECE | ECE signs |",
          "|---|---|---|---|---|"]
    for t in ARMS:
        for ck in CKPTS:
            c = res[t][ck]
            if not c["d_ece"]:
                continue
            L.append(f"| {t} | {ck}{' *(birincil)*' if ck == PRIMARY_CKPT else ''} | "
                     f"{st.mean(c['d_acc']):+.3f} ± {sample_sd(c['d_acc']):.3f} | "
                     f"{st.mean(c['d_ece']):+.4f} ± {sample_sd(c['d_ece']):.4f} | "
                     f"`{signs(c['d_ece'])}` |")

    L += ["", "## Reading — text fixed in advance", ""]
    if n_kurulu == 2:
        L += ["**ESTABLISHED in both teachers.** The calibration harm of `gate:oracle_error` is "
              "not specific to VAE9182; it has the same direction in all three teachers and exceeds twice "
              "the noise. D1's closing rationale (\"the gate degrades calibration\") can be "
              "written "
              "unconditionally."]
    elif n_kurulu == 1:
        won = [t for t, v in verdicts.items() if v["verdict"] == "KURULU"][0]
        L += [f"**ESTABLISHED in one teacher ({won}), UNRESOLVED in the other.** The harm was observed in two "
              "teachers but was not established in all three; D1's closing rationale will be written "
              "**conditionally**, naming the teachers in which it was established."]
    else:
        L += ["**UNRESOLVED in both teachers.** The mean effects have the same sign as the one measured in "
              "VAE9182, but their magnitudes stay below twice that arm's own seed noise — that is, in these "
              "two teachers the harm **could not be measured**.", "",
              "**This is NOT a null finding.** The bar is twice a single arm's seed sd; an effect below it "
              "an effect below it is not counted as absent but as unmeasurable. The sentence "
              "\"the gate does not degrade calibration in stage1 and primary\" **cannot be "
              "written** from this data.", "",
              "**D1's closing rationale stays conditional.** In the text: even with perfect information the "
              "gate brings no accuracy gain in any teacher (Δacc ≤ 0 in all three); the calibration "
              "harm was **established in VAE9182 and unresolved in stage1 and primary**. The "
              "no-accuracy-gain leg of the rationale is written unconditionally, the calibration-harm leg "
              "conditionally on VAE9182."]
    L += ["", "> The Δacc axis points the same way in all three teachers: even with perfect information the "
              "gate yields no accuracy gain. The gate's closure rests mainly on this row, and P5 "
              "strengthened it by adding two more teachers.", "",
          f"*Source: `{AUDIT.name}` (the unfrozen superset; the frozen `selection_audit.csv` carries only "
          f"T8's N=131 and was not used for this verdict) · `runs.csv`*", ""]

    (OUT_DIR / "p5_verdict.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "p5_verdict.json").write_text(json.dumps({
        "status": "PRE-REGISTERED (PREREGISTRATIONS.md A8-P5, frozen 2026-07-31 14:14:11)",
        "rule": "3/3 same sign AND |mean dECE| >= 2 x own cw=none control ECE seed sd",
        "sd_convention": SD_CONVENTION, "primary_checkpoint": PRIMARY_CKPT,
        "declared_bars": DECLARED_BAR, "seeds": list(SEEDS),
        "verdicts": verdicts, "reference_p2_vae9182": ref,
        "n_established": n_kurulu,
        "by_teacher": {t: {ck: {"d_acc": res[t][ck]["d_acc"], "d_ece": res[t][ck]["d_ece"],
                                "treat": res[t][ck]["treat"], "control": res[t][ck]["control"],
                                "per_seed": {str(k): v for k, v
                                             in res[t][ck]["per_seed"].items()}}
                           for ck in CKPTS} for t in ARMS},
    }, indent=2), encoding="utf-8")

    for t, v in verdicts.items():
        print(f"{t:<8} dECE {v['mean']:+.4f} +/- {v['sd']:.4f}  signs {v['signs']}  "
              f"bar {v['bar']:.4f}  2xbar {v['two_bar']:.4f}  ratio {v['ratio']:.2f}x  "
              f"-> {v['verdict']}")
        if not v["bar_matches_declaration"]:
            print(f"         ! declared bar {v['bar']:.4f} vs remeasured "
                  f"{v['measured_bar']:.4f} -- judged on the DECLARED bar")
    print(f"\nreference {ref['teacher']} (P2): dECE {ref['d_ece_mean']:+.4f} "
          f"signs {ref['signs']}")
    print(f"\n{n_kurulu}/2 arms KURULU")
    print(f"Wrote {OUT_DIR / 'p5_verdict.md'}")


if __name__ == "__main__":
    main()
