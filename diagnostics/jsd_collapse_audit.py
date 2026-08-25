"""N12 — JSD çöküşü: 40× mi 37× mi? TEK pay, İKİ payda; ikisi de 0.0005'e yuvarlanıyor.

ÇELİŞKİ (17 Ağu 2026). İki merci ters yönde hüküm verdi:
  · `paper_tables/number_audit_round3.md` kalem 7 (14 Ağu) -> "~40× doğru, 37× yeniden
    üretilemiyor"; ölçümü: açıklık 0.020083, ~39.8×.
  · Dış inceleme (17 Ağu) -> "37× doğru"; ölçümü: açıklık / TS-sonrası açıklık = 37.23×,
    40 ancak BASILI yuvarlak değerleri (0.0201 / 0.0005) bölerek çıkıyor.

ÖLÇÜLEN CEVAP: ikisi de kendi niceliği için doğru, ama İKİ AYRI NİCELİK var ve makale birinin
adını diğerine vermiş. Pay ortaktır (dört ham kolun JSD açıklığı). Payda değişir:
  · R_collapse := açıklık(ham kollar) / açıklık(çapraz-uyarlanmış TS sonrası kollar)
      -> "a NN× collapse onto a common value" cümlesinin niceliği (05_results_discussion.tex,
         sec:res_human içindeki "What post-hoc student scaling can and cannot do" paragrafı).
         Üreticisi `r3w1_joint_optimum.py`, kendi raporunda `{spread_arm/spread_ts:.0f}` basıyor.
  · R_noise    := açıklık(ham kollar) / tohum sd'si ("typical seed spread")
      -> "roughly forty times the noise" cümlesinin niceliği (AYNI alt bölümün gövdesi).
         `number_audit_round3` kalem 7 bunu ölçtü.
İki payda dört basamakta AYNI görünür (ikisi de 0.0005) ama eşit değildir; oran 37 ile 40
arasında oynar. Kalem 7, 37×'i ararken yalnız tohum sd paydalarını denedi ve
`r3w1_joint_optimum.json`'u hiç açmadı — 37× tam orada, üreticinin kendi çıktısında yazılı.

Bu betik hiçbir sayıyı yayımlı artefaktlardan okuyup yeniden yazmaz: dört kolu üç tohumda
YAYIMLANMIŞ logitlerden yeniden ölçer (bölme/fit/ölçüm fonksiyonları `student_ts_baseline`'dan,
çapraz-fit bloğu `r3w1_joint_optimum.crossfit_arm`'dan İTHAL — kopya değil), iki oranı da
kurar, beş tohum-sd konvansiyonunun hepsini basar ve yuvarlama tuzağını sayıyla gösterir.

Salt-okunur, CPU, eğitim yok, forward yok: yalnız `diagnostics/student_logits/` altındaki
yayımlanmış @swa logitleri.
Çıktı -> diagnostics/paper_tables/jsd_collapse_audit.{md,json}
Kullanım: python diagnostics/jsd_collapse_audit.py
"""
import argparse
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

# İTHAL, KOPYA DEGIL. Sorulan soru "iki sayı neden farklı" olduğu için, üçüncü bir tanım
# eklemek cevabı geçersiz kılardı: bölme kuralı, TS fit'i ve iki-eksen ölçümü R0-1'den,
# çapraz-fit bloğu ile dört kolun listesi R3-W1'in KENDİSİNDEN gelir.
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from student_ts_baseline import (CK, SEEDS, published_logits, sha_split,  # noqa: E402
                                 val_from_published)
from r3w1_joint_optimum import ARMS, crossfit_arm  # noqa: E402

D = ROOT / "diagnostics"
A_R3W1 = D / "paper_tables" / "r3w1_joint_optimum.json"
A_SJ = D / "ferplus_jsd" / "ferplus_student_jsd.json"
A_NA3 = D / "paper_tables" / "number_audit_round3.json"
OUT_DIR = D / "paper_tables"

# Aynı kod yolu + aynı önbellek => birebir beklenir. R3-W1'in kendi R0-1 kontrolü de 1e-12.
TOL = 1e-12


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def span(vals_by_arm):
    """(açıklık, argmax kolu, argmin kolu) — açıklık = en büyük eksi en küçük kol ortalaması."""
    hi = max(vals_by_arm, key=lambda k: vals_by_arm[k])
    lo = min(vals_by_arm, key=lambda k: vals_by_arm[k])
    return vals_by_arm[hi] - vals_by_arm[lo], hi, lo


def sd_conventions(sds):
    """`number_audit_round3` kalem 7'nin denediği beş "tipik tohum sd'si" okuması."""
    return {"mean sd": st.mean(sds), "median sd": st.median(sds),
            "largest sd": max(sds), "smallest sd": min(sds),
            "pooled sd": st.mean([s * s for s in sds]) ** 0.5}


def main():
    ap = argparse.ArgumentParser()
    # `parse_known_args` — ŞART: Level-1 kapısı üreticileri `runpy` ile çağırıp betiğin
    # yolunu argv'de bırakıyor; `parse_args` bunu tanımadığı argüman sayıp SystemExit atar.
    args, _unknown = ap.parse_known_args()
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")

    labels, p_human, names = val_from_published()
    n = labels.shape[0]
    mask_a, mask_b = sha_split(names)
    print(f"raporlama kümesi n={n} · SHA-bölme A={int(mask_a.sum())} / B={int(mask_b.sum())} "
          f"· checkpoint @{CK} · tohumlar {SEEDS}\n")

    per_seed = {}
    for T, _role, tmpl in ARMS:
        per_seed[T] = {}
        for s in SEEDS:
            per_seed[T][str(s)] = crossfit_arm(published_logits(tmpl.format(s=s)),
                                               labels, p_human, mask_a, mask_b)
        r = per_seed[T]
        print(f"  T={T:<7} ham JSD "
              + " / ".join(f"{r[str(s)]['raw']['jsd']:.6f}" for s in SEEDS)
              + "  ->  TS "
              + " / ".join(f"{r[str(s)]['ts']['jsd']:.6f}" for s in SEEDS))

    def col(kind, met):
        m = {T: st.mean([per_seed[T][str(s)][kind][met] for s in SEEDS]) for T, _r, _t in ARMS}
        sd = {T: sample_sd([per_seed[T][str(s)][kind][met] for s in SEEDS])
              for T, _r, _t in ARMS}
        return m, sd

    jsd_raw, jsd_raw_sd = col("raw", "jsd")
    jsd_ts, jsd_ts_sd = col("ts", "jsd")
    ece_raw, ece_raw_sd = col("raw", "ece")
    ece_ts, ece_ts_sd = col("ts", "ece")

    # ---------------- İKİ ORAN. Pay ortak, payda farklı.
    num, num_hi, num_lo = span(jsd_raw)                    # dört ham kolun JSD açıklığı
    den_c, den_c_hi, den_c_lo = span(jsd_ts)               # TS sonrası açıklık  -> "collapse"
    conv_raw = sd_conventions([jsd_raw_sd[T] for T, _r, _t in ARMS])   # tohum sd -> "noise"
    conv_ts = sd_conventions([jsd_ts_sd[T] for T, _r, _t in ARMS])

    R_collapse = num / den_c
    R_noise = {k: num / v for k, v in conv_raw.items()}

    print(f"\n  pay (ham açıklık)        {num:.8f}   [T={num_hi} − T={num_lo}]")
    print(f"  payda A (TS açıklığı)    {den_c:.8f}   [T={den_c_hi} − T={den_c_lo}]"
          f"  ->  R_collapse = {R_collapse:.4f}  (basılışı '{R_collapse:.0f}×')")
    for k, v in conv_raw.items():
        print(f"  payda B ({k:<11s})   {v:.8f}"
              f"   ->  R_noise    = {R_noise[k]:.4f}  (basılışı '{R_noise[k]:.0f}×')")

    # ---------------- "40" NASIL ÜRETİLİYOR: iki yol, ikisi de payda B'ye ait
    r4 = 4
    printed = {"span_raw": round(num, r4), "span_ts": round(den_c, r4),
               "seed_sd_mean": round(conv_raw["mean sd"], r4)}
    trap = {
        "printed_values": printed,
        "ratio_from_printed": printed["span_raw"] / printed["span_ts"],
        "denominator_that_gives_exactly_40": num / 40.0,
        "rel_gap_to_mean_seed_sd": abs(num / 40.0 - conv_raw["mean sd"]) / conv_raw["mean sd"],
        "rel_gap_to_ts_span": abs(num / 40.0 - den_c) / den_c,
        "both_denominators_print_as": (f"{den_c:.4f}", f"{conv_raw['mean sd']:.4f}"),
        "denominators_equal_at_4dp": f"{den_c:.4f}" == f"{conv_raw['mean sd']:.4f}"}
    print(f"\n  basılı bölme {printed['span_raw']:.4f}/{printed['span_ts']:.4f} = "
          f"{trap['ratio_from_printed']:.2f}  ·  tam 40 için gereken payda "
          f"{trap['denominator_that_gives_exactly_40']:.8f}  (ortalama tohum sd'sinden "
          f"%{100 * trap['rel_gap_to_mean_seed_sd']:.2f}, TS açıklığından "
          f"%{100 * trap['rel_gap_to_ts_span']:.2f} uzak)")

    # ---------------- SAĞLAMLIK: oran tohum başına ayrı ayrı
    per_seed_ratio = {}
    for s in SEEDS:
        a = {T: per_seed[T][str(s)]["raw"]["jsd"] for T, _r, _t in ARMS}
        b = {T: per_seed[T][str(s)]["ts"]["jsd"] for T, _r, _t in ARMS}
        per_seed_ratio[str(s)] = {"span_raw": span(a)[0], "span_ts": span(b)[0],
                                  "ratio": span(a)[0] / span(b)[0]}
    pr = [per_seed_ratio[str(s)]["ratio"] for s in SEEDS]
    print(f"  tohum başına R_collapse: " + " / ".join(f"{x:.2f}" for x in pr)
          + f"  -> {st.mean(pr):.2f} ± {sample_sd(pr):.2f}")

    # ---------------- PAYDANIN KENDİSİ GÜRÜLTÜ MÜ? (R_collapse'ın dürüstlük kaydı)
    bar_ts = 2 * max(jsd_ts_sd[T] for T, _r, _t in ARMS)   # R3-W1'in bar tanımı
    den_is_noise = den_c <= bar_ts
    print(f"  TS sonrası açıklık {den_c:.6f} vs bar (2× en büyük TS tohum sd'si) "
          f"{bar_ts:.6f}  ->  payda gürültü seviyesinde: {den_is_noise}")

    # ---------------- YAYIMLI ARTEFAKTLARLA ÇAPRAZ KONTROL
    a3, sj, na3 = jload(A_R3W1), jload(A_SJ), jload(A_NA3)
    swa = sj["by_checkpoint"][CK]
    it7 = next(i for i in na3["rows"] if i["claim"].startswith('"37×'))
    checks = []
    for T, _role, _t in ARMS:
        checks += [
            (f"r3w1.arms[{T}].jsd_arm mean", a3["arms"][T]["jsd_arm"][0], jsd_raw[T]),
            (f"r3w1.arms[{T}].jsd_arm sd", a3["arms"][T]["jsd_arm"][1], jsd_raw_sd[T]),
            (f"r3w1.arms[{T}].jsd_ts mean", a3["arms"][T]["jsd_ts"][0], jsd_ts[T]),
            (f"r3w1.arms[{T}].jsd_ts sd", a3["arms"][T]["jsd_ts"][1], jsd_ts_sd[T]),
            (f"r3w1.arms[{T}].ece_arm mean", a3["arms"][T]["ece_arm"][0], ece_raw[T]),
            (f"r3w1.arms[{T}].ece_ts mean", a3["arms"][T]["ece_ts"][0], ece_ts[T]),
            (f"ferplus_student_jsd.{CK}[{T}].jsd mean", swa[T]["jsd"][0], jsd_raw[T]),
            (f"ferplus_student_jsd.{CK}[{T}].jsd sd", swa[T]["jsd"][1], jsd_raw_sd[T])]
    checks += [("number_audit_round3 item7 span", it7["exact"]["span"], num),
               ("number_audit_round3 item7 ratio(mean sd)",
                it7["exact"]["ratios"]["ortalama sd"], R_noise["mean sd"]),
               ("number_audit_round3 item7 mean sd",
                it7["exact"]["sd_conventions"]["ortalama sd"], conv_raw["mean sd"])]
    xrows, worst = [], 0.0
    for name, published, remeasured in checks:
        dev = abs(published - remeasured)
        worst = max(worst, dev)
        xrows.append({"quantity": name, "published": published, "remeasured": remeasured,
                      "abs_dev": dev, "ok": dev < TOL})
    print(f"\n  {len(checks)} çapraz kontrol · en büyük sapma {worst:.2e} (eşik {TOL:g})")

    # ---------------- HÜKÜM
    verdict = {
        "R_collapse": R_collapse, "R_collapse_printed": f"{R_collapse:.0f}×",
        "R_noise_recommended": R_noise["mean sd"],
        "R_noise_printed": f"{R_noise['mean sd']:.0f}×",
        "numerator": num, "numerator_arms": [num_hi, num_lo],
        "denominator_collapse": den_c, "denominator_collapse_arms": [den_c_hi, den_c_lo],
        "denominator_noise_mean_sd": conv_raw["mean sd"],
        "two_distinct_quantities": True,
        "paper_line_693_should_read": f"{R_collapse:.0f}×",
        "paper_line_636_should_read": f"{R_noise['mean sd']:.0f}×",
        "rule": "türetilmiş oran DEFTERDEN hesaplanır, basılı yuvarlak değerlerden değil"}

    # ---------------- rapor
    L = ["# N12 — The JSD collapse: 37× or 40×? One numerator, two denominators", "",
         "> **Review-responsive, not pre-declared (17 Aug 2026).** Written to settle a "
         "contradiction between an internal audit and an external review; no prediction was "
         "frozen beforehand.", "",
         "Producer: `diagnostics/jsd_collapse_audit.py` · sources: published @swa student "
         "logits (`diagnostics/student_logits/`), `ferplus_jsd/ferplus_val_logits.pt`, "
         f"`configs/FERPlus_majority_metadata.csv` · reporting set n={n} · @{CK} · "
         f"seeds {SEEDS} · {SD_CONVENTION} · no forward pass, no GPU.", "",
         "The paper prints two ratios whose **numerator is the same number** and whose "
         "denominators both round to `0.0005` at four decimals. They are not the same "
         "denominator, and the two ratios are not the same quantity. Both sentences sit in the "
         "same subsection (`sections/05_results_discussion.tex`, `\\label{sec:res_human}`): the "
         "*noise* ratio in the subsection body and the *collapse* ratio in its "
         "`\\paragraph{What post-hoc student scaling can and cannot do}`.", "",
         "## 1 · The two ratios", "",
         "| ratio | definition | numerator | denominator | value | printed as |",
         "|---|---|---|---|---|---|",
         f"| `R_collapse` | span of the four **raw** arms ÷ span of the four arms **after one "
         f"cross-fitted student-side scalar** | {num:.6f} | {den_c:.6f} | **{R_collapse:.2f}** "
         f"| **{R_collapse:.0f}×** |",
         f"| `R_noise` | span of the four **raw** arms ÷ **typical seed sd** (mean over arms) "
         f"| {num:.6f} | {conv_raw['mean sd']:.6f} | **{R_noise['mean sd']:.2f}** | "
         f"**{R_noise['mean sd']:.0f}×** |", "",
         f"The numerator is the same in both rows: the raw JSD span between arm T={num_hi} "
         f"({jsd_raw[num_hi]:.6f}) and arm T={num_lo} ({jsd_raw[num_lo]:.6f}).", "",
         "### Where each field lives", "",
         "| quantity | artifact | field |", "|---|---|---|",
         f"| numerator | `paper_tables/r3w1_joint_optimum.json` | "
         f"`arms.{num_hi}.jsd_arm[0]` − `arms.{num_lo}.jsd_arm[0]` |",
         f"| numerator (same value, second artifact) | `ferplus_jsd/ferplus_student_jsd.json` | "
         f"`by_checkpoint.{CK}.{num_hi}.jsd[0]` − `by_checkpoint.{CK}.{num_lo}.jsd[0]` |",
         f"| `R_collapse` denominator | `paper_tables/r3w1_joint_optimum.json` | "
         f"`arms.{den_c_hi}.jsd_ts[0]` − `arms.{den_c_lo}.jsd_ts[0]` |",
         f"| `R_noise` denominator | `ferplus_jsd/ferplus_student_jsd.json` | mean of "
         f"`by_checkpoint.{CK}.*.jsd[1]` over the four arms |", "",
         "## 2 · The four arms, raw and after student-side TS", "",
         "| T (teacher pre-scaling) | role | JSD raw | JSD +TS | ECE raw | ECE +TS |",
         "|---|---|---|---|---|---|"]
    for T, role, _t in ARMS:
        L.append(f"| {T} | {role} | {jsd_raw[T]:.6f} ± {jsd_raw_sd[T]:.6f} | "
                 f"**{jsd_ts[T]:.6f} ± {jsd_ts_sd[T]:.6f}** | {ece_raw[T]:.4f} ± "
                 f"{ece_raw_sd[T]:.4f} | {ece_ts[T]:.4f} ± {ece_ts_sd[T]:.4f} |")
    L += ["",
          "## 3 · Where \"40\" comes from — two routes, both belonging to `R_noise`", "",
          f"**Route 1 — dividing the printed values.** The paper prints the numerator as "
          f"`{printed['span_raw']:.4f}` and the denominator as `{printed['span_ts']:.4f}`. "
          f"Divide those and you get **{trap['ratio_from_printed']:.2f}**, which rounds to 40. "
          f"Divide the ledger values and you get **{R_collapse:.2f}**. Four-decimal rounding on "
          f"a denominator of order 5e-4 moves the ratio by "
          f"{abs(trap['ratio_from_printed'] - R_collapse):.1f} — this is the same failure mode "
          f"as the \"13–14 times smaller\" case (`number_audit_round3` item 2), where both "
          f"sides divided rounded table cells.", "",
          f"**Route 2 — the other ratio is genuinely ≈40.** To make `R_collapse` equal exactly "
          f"40 the denominator would have to be **{trap['denominator_that_gives_exactly_40']:.6f}**. "
          f"The mean seed sd is **{conv_raw['mean sd']:.6f}** — "
          f"{100 * trap['rel_gap_to_mean_seed_sd']:.2f}% away. The post-TS span is "
          f"**{den_c:.6f}** — {100 * trap['rel_gap_to_ts_span']:.2f}% away. So \"40\" is not a "
          f"rounding of the collapse ratio; it is the *noise* ratio, correct in its own "
          f"sentence and wrong in this one. Both denominators print as "
          f"`{trap['both_denominators_print_as'][0]}` and "
          f"`{trap['both_denominators_print_as'][1]}` "
          f"({'identical' if trap['denominators_equal_at_4dp'] else 'different'} at 4 dp), which "
          f"is how one sentence's number could migrate into the other's without either author "
          f"noticing.", "",
          "**All five seed-sd conventions** (the choice `number_audit_round3` item 7 flagged as "
          "unresolved):", "",
          "| convention | typical seed sd | `R_noise` |", "|---|---|---|"]
    for k, v in conv_raw.items():
        L.append(f"| {k} | {v:.6f} | {R_noise[k]:.2f} |")
    L += ["",
          f"`R_noise` is between {min(R_noise.values()):.1f} and {max(R_noise.values()):.1f} "
          f"depending on which reduction of the four arms' seed sds is called \"typical\"; the "
          f"mean-sd reading ({R_noise['mean sd']:.2f}) is the one the published \"roughly forty\" "
          f"matches. The convention must be named in the text — the sd convention itself "
          f"(sample sd over seeds) is campaign-wide and fixed, but *which* reduction across arms "
          f"is \"typical\" is a free choice and currently unstated.", "",
          "## 4 · Honesty note: the collapse ratio's denominator is itself at noise level", "",
          f"After scaling, the four arms span {den_c:.6f}, while one bar — R3-W1's own "
          f"definition, 2× the largest post-TS seed sd — is {bar_ts:.6f}. The span is "
          + ("**inside** one bar" if den_is_noise else "**outside** one bar") +
          f", i.e. the four post-TS arms are not separable from each other at three seeds. That "
          f"is exactly what the sentence claims (\"onto a common value\"), but it also means "
          f"`R_collapse` is a ratio to a quantity that is itself indistinguishable from zero.", "",
          f"The consequence is visible if the ratio is formed inside each seed instead of from "
          f"the seed means: " + " / ".join(f"{x:.1f}" for x in pr) +
          f", i.e. {st.mean(pr):.1f} ± {sample_sd(pr):.1f} — all three below "
          f"{R_collapse:.1f}. The direction is expected and is not a defect of either estimator: "
          f"a span is a max minus a min, so it is biased upward by noise, and averaging three "
          f"seeds per arm first removes some of that noise from the denominator while the "
          f"between-arm signal it is measuring is already ~0. The published estimand (spans of "
          f"seed means) is the right one to report and is what both ratios use throughout this "
          f"table; the point is that **the multiplier carries no more than two significant "
          f"figures of information**. The defensible claim is *the axis collapses to within seed "
          f"noise* — for which 37 versus 40 changes nothing scientifically, and everything "
          f"about whether a reader who divides the printed numbers gets the paper's own value.",
          "",
          "## 5 · Cross-check against the published artifacts", "",
          f"All {len(checks)} checks below re-derive the published values from the published "
          f"logits through the *imported* R0-1/R3-W1 code path, not by reading them back:", "",
          "| quantity | published | re-measured here | |Δ| |", "|---|---|---|---|"]
    for r in xrows:
        L.append(f"| {r['quantity']} | {r['published']:.8f} | {r['remeasured']:.8f} | "
                 f"{r['abs_dev']:.1e} |")
    L += ["",
          f"Largest deviation {worst:.1e} (tolerance {TOL:g}). Both authorities' inputs are "
          f"reproduced exactly: R3-W1's four arms (raw and post-TS, JSD and ECE) and "
          f"`number_audit_round3` item 7's span and mean-sd ratio. **This script adds no third "
          f"definition** — the cross-fit block and the arm list are imported from "
          f"`r3w1_joint_optimum`, the split/fit/measure functions from `student_ts_baseline`.",
          "",
          "## 6 · Correction to the 14 Aug audit (`number_audit_round3`, item 7)", "",
          f"Item 7 asked which of the paper's two numbers was right and answered \"~40× "
          f"correct, 37× not reproducible\". Its measurement is arithmetically sound but it "
          f"only ever tried **seed-sd denominators** — five of them, listed above — and never "
          f"the post-TS span. It read `ferplus_jsd/ferplus_student_jsd.json`, which contains "
          f"the raw arms and their seed sds and nothing about student-side scaling; the "
          f"post-TS arms live in a different artifact, `paper_tables/r3w1_joint_optimum.json`, "
          f"which item 7 did not open. 37× is not unreproducible: its producer "
          f"`r3w1_joint_optimum.py` prints it directly from `spread_arm / spread_ts` and the "
          f"value is {R_collapse:.2f}. The external review's reading is the correct one for the "
          f"post-hoc-scaling paragraph's sentence, and item 7's is the correct one for the "
          f"subsection body's.", "",
          "The 14 Aug record stands as written — it is a dated declaration — and is corrected "
          "here, under today's date. The dangerous half of that verdict was not the arithmetic "
          "but the instruction it implied: \"37 is not reproducible\" invites editing 37 into "
          "40, which turns a correct sentence into an incorrect one. That the edit happened is "
          "on the record in the audit itself — item 7's `published` field, written on 14 Aug, "
          f"reads `{it7['published']}`, so the collapse sentence carried {R_collapse:.0f}× then "
          "and carries 40× now.", "",
          "## 7 · What the paper should carry", "",
          f"1. **The \"collapse onto a common value\" sentence: `{R_collapse:.0f}×`**, not 40×. "
          f"Numerator and denominator are both *spans across arms* — before and after scaling — "
          f"so the name \"collapse\" belongs here and nowhere else. Its producer already prints "
          f"{R_collapse:.0f}× in `paper_tables/r3w1_joint_optimum.md`; the paper and the "
          f"artifact disagree only because the paper's copy was changed.",
          f"2. **The \"times the noise\" sentence: `{R_noise['mean sd']:.0f}×` stands**, but "
          f"name the denominator and quote it to five decimals — \"a typical seed spread of "
          f"{conv_raw['mean sd']:.5f} (the mean of the four arms' seed sds), roughly forty times "
          f"the noise\" — so the two sentences stop sharing the string `0.0005`. Naming it is "
          f"not cosmetic: the reduction is a free choice and the ratio runs "
          f"{min(R_noise.values()):.0f}–{max(R_noise.values()):.0f} across the five readings "
          f"above. If a pooled estimator is preferred, it is "
          f"{conv_raw['pooled sd']:.5f} → {R_noise['pooled sd']:.1f}×, which the same prose "
          f"still covers. The word \"collapse\" must not appear in this sentence, and \"noise\" "
          f"must not appear in the other.",
          f"3. **Neither number may be re-derived from printed values.** "
          f"{printed['span_raw']:.4f}/{printed['span_ts']:.4f} = "
          f"{trap['ratio_from_printed']:.2f} is how 40 was produced for the wrong sentence; the "
          f"ledger value is {R_collapse:.2f}. Same rule, same failure mode as item 2's "
          f"\"13–14 times smaller\".", ""]

    payload = {"note": "review-responsive, not pre-declared",
               "sd_convention": SD_CONVENTION, "checkpoint": CK, "seeds": list(SEEDS),
               "n_val": n, "tol": TOL,
               "arms": {T: {"role": r,
                            "jsd_raw": [jsd_raw[T], jsd_raw_sd[T]],
                            "jsd_ts": [jsd_ts[T], jsd_ts_sd[T]],
                            "ece_raw": [ece_raw[T], ece_raw_sd[T]],
                            "ece_ts": [ece_ts[T], ece_ts_sd[T]]} for T, r, _ in ARMS},
               "numerator": {"value": num, "arm_hi": num_hi, "arm_lo": num_lo},
               "R_collapse": {"value": R_collapse, "denominator": den_c,
                              "denominator_arms": [den_c_hi, den_c_lo],
                              "per_seed": per_seed_ratio,
                              "per_seed_mean": st.mean(pr), "per_seed_sd": sample_sd(pr),
                              "denominator_bar": bar_ts,
                              "denominator_within_noise": den_is_noise},
               "R_noise": {"by_convention": R_noise, "seed_sd_by_convention": conv_raw,
                           "recommended": "mean sd"},
               "post_ts_seed_sd_by_convention": conv_ts,
               "rounding_trap": trap,
               "crosschecks": xrows, "max_abs_dev": worst,
               "verdict": verdict,
               "per_seed": per_seed}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "jsd_collapse_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "jsd_collapse_audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'jsd_collapse_audit.md'}")

    if worst >= TOL:
        print(f"\nDUR: yayımlı sayılar yeniden üretilemedi (en büyük sapma {worst:.3e}).")
        return 1
    if f"{R_collapse:.0f}" != "37":
        print(f"\nDUR: R_collapse {R_collapse:.4f} — R3-W1'in bastığı 37× ile uyuşmuyor.")
        return 1
    if f"{R_noise['mean sd']:.0f}" != "40":
        print(f"\nDUR: R_noise {R_noise['mean sd']:.4f} — yayımlı '~40×' ile uyuşmuyor.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
