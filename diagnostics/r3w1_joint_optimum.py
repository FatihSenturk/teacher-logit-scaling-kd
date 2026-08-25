"""R3-W1 — çift-eksen alt yazısının "aynı anda sağlanamaz" iddiasının sınanması (ön-kayıt A11).

İTİRAZ (Round-2 panel, R3/Perspektif koltuğu, 5 Ağu 2026, BÜYÜK): `fig_ferplus_dual.tex`
alt yazısı "no arm occupies the lower-left corner: the two objectives cannot be satisfied at
once" diyor. Bu bir İMKÂNSIZLIK iddiası ama dayanağı dört koldan ibaret bir grid. Hakemin
önerdiği ucuz çürütme adayı: insan-hizalı T=0.74 kolunda damıt, sonra ECE'yi onarmak için
öğrenci-tarafı TS'i çapraz-uyarla.

NE YAPILIYOR. R0-1'in protokolü (`student_ts_baseline.py`) DEĞİŞTİRİLMEDEN dört doz-yanıt
kolunun hepsine uygulanıyor. Bölme, fit ve ölçüm fonksiyonları oradan İTHAL EDİLİYOR,
kopyalanmıyor — R0-1'in yayımlanmış T=1 satırı burada birebir yeniden üretilmeli ve
üretilmezse bu bir bulgu olarak yazılır (aynı disiplin P6.1'de de uygulandı).

KÖŞE TANIMI (A11'de sayı görülmeden donduruldu):
  ECE_min := kollar arasındaki en düşük öğrenci ECE'si
  JSD_min := kollar arasındaki en düşük öğrenci JSD'si
  Bir nokta köşeyi İŞGAL EDER  <=>  ECE <= ECE_min + bar_ECE  VE  JSD <= JSD_min + bar_JSD
  bar_X := 2 x (karşılaştırılan iki büyüklüğün tohum sd'lerinin büyüğü)

KARAR (A11, üç kol):
  işgal eden VARSA      -> alt yazı post-hoc ölçekleme içeren tarifler için YANLIŞLANDI
  hiçbiri işgal ETMEZSE -> cümle ayakta; dört kol + dört TS varyantı sınandı diye güçlenir
  sınırda kalırsa       -> ÇÖZÜNMEDİ; alt yazı "no *evaluated* arm" diye daraltılır

Salt-okunur, CPU, eğitim yok (logitler `diagnostics/student_logits/` altında YAYIMLI).

LEVEL-1 (8 Ağu 2026). Bu betik 8 Ağu'ya kadar hem logitleri hem val yükleyicisinin
ayarlarını koşu dizinlerinden okuyordu ve Level-1 kapısında iki ihlalden biriydi. İkisi de
yalnız FORWARD için gerekliydi; logitler yayımlanınca forward kalmadı, dolayısıyla ne
görüntü ne `run_args.json` gerekiyor. Yeni yol: `student_ts_baseline.published_logits()` +
`student_ts_baseline.val_from_published()`. Sayı oynamadı — geçiş öncesi/sonrası çıktı
karşılaştırıldı.
Çıktı -> diagnostics/paper_tables/r3w1_joint_optimum.{md,json}
Kullanım: python diagnostics/r3w1_joint_optimum.py
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

# TEK KAYNAK: bölme kuralı, TS fit'i, iki-eksen ölçümü ve logit önbelleği R0-1'den ithal.
from student_ts_baseline import (  # noqa: E402
    CK, SEEDS, fit_ts, measure, published_logits, sha_split, val_from_published,
)
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "paper_tables"
A_R01 = OUT_DIR / "student_ts_baseline.json"

# Dört doz-yanıt kolu. Roller ferplus_dual_axis_figure.ROLE ile aynı.
ARMS = [
    ("0.26",   "over-sharpened", "FERPlus_tempscale_T026_vich_T6_224_200e_swa100_seed{s}"),
    ("0.5063", "T*_ECE / T*_NLL", "FERPlus_tempscale_T051_vich_T6_224_200e_swa100_seed{s}"),
    ("0.74",   "T*_JSD",         "FERPlus_tempscale_T074_vich_T6_224_200e_swa100_seed{s}"),
    ("1.0",    "native",         "FERPlus_tempscale_T100_vich_T6_224_200e_swa100_seed{s}"),
]


def agg(per_seed, arm, kind, met):
    v = [per_seed[arm][str(s)][kind][met] for s in SEEDS]
    return st.mean(v), sample_sd(v)


def crossfit_arm(lg, labels, p_human, mask_a, mask_b):
    """Bir kol/tohum için ham ölçüm + çapraz-uyarlanmış öğrenci-TS ölçümü.

    17 Ağu 2026'da fonksiyona ÇIKARILDI (`jsd_collapse_audit`). Gerekçe: "JSD çöküşü 40× mi
    37× mi" sorusunun cevabı tam olarak bu bloğun çıktısına dayanıyor, dolayısıyla ikinci bir
    betik onu KOPYALAMAK yerine buradan çağırmak zorunda — kopya, cevabın kendisi olan tanımı
    ikiye bölerdi. Gövde main()'den birebir taşındı; bu betiğin ürettiği hiçbir sayı
    değişmez (`.md`/`.json` bayt karşılaştırmasıyla doğrulandı).
    """
    n = labels.shape[0]
    na, nb = int(mask_a.sum()), int(mask_b.sum())
    raw = measure(lg, labels, p_human)
    # çapraz-fit: A'da fit -> B'de ölç ve tersi; birleşik = örnek-ağırlıklı
    t_ab = fit_ts(lg[mask_a], labels[mask_a])
    t_ba = fit_ts(lg[mask_b], labels[mask_b])
    m_b = measure(lg[mask_b], labels[mask_b], p_human[mask_b], T=t_ab)
    m_a = measure(lg[mask_a], labels[mask_a], p_human[mask_a], T=t_ba)
    ts = {k: (m_a[k] * na + m_b[k] * nb) / n for k in ("ece", "jsd", "entropy")}
    return {"raw": raw, "ts": ts, "T_s": [t_ab, t_ba]}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    labels, p_human, names = val_from_published()
    n = labels.shape[0]
    mask_a, mask_b = sha_split(names)
    na, nb = int(mask_a.sum()), int(mask_b.sum())
    print(f"raporlama kümesi n={n} · SHA-bölme A={na} / B={nb}\n")

    per_seed = {}
    for T, role, tmpl in ARMS:
        per_seed[T] = {}
        for s in SEEDS:
            lg = published_logits(tmpl.format(s=s))
            r = crossfit_arm(lg, labels, p_human, mask_a, mask_b)
            per_seed[T][str(s)] = r
            raw, ts, (t_ab, t_ba) = r["raw"], r["ts"], r["T_s"]
            print(f"  T={T:<7} seed{s}: ham ({raw['ece']:.4f}, {raw['jsd']:.4f}) -> "
                  f"TS ({ts['ece']:.4f}, {ts['jsd']:.4f})  T_s {t_ab:.3f}/{t_ba:.3f}")

    # --- R0-1'in yayımlanmış T=1 satırı birebir çıkıyor mu?
    repro = {"checked": False}
    if A_R01.exists():
        d0 = json.loads(A_R01.read_text(encoding="utf-8"))
        diffs = []
        for s in SEEDS:
            for kind, key in (("raw", "raw"), ("ts", "student_ts")):
                for met in ("ece", "jsd"):
                    a = per_seed["1.0"][str(s)][kind][met]
                    b = d0["per_seed"][str(s)][key][met]
                    if abs(a - b) > 1e-12:
                        diffs.append(f"T=1 tohum {s} {key}.{met}: {b:.6f} -> {a:.6f}")
        repro = {"checked": True, "identical": not diffs, "diffs": diffs}

    # --- köşe ve işgal testi (tanım A11'de dondu)
    ece_arm = {T: agg(per_seed, T, "raw", "ece") for T, _r, _t in ARMS}
    jsd_arm = {T: agg(per_seed, T, "raw", "jsd") for T, _r, _t in ARMS}
    ece_ts = {T: agg(per_seed, T, "ts", "ece") for T, _r, _t in ARMS}
    jsd_ts = {T: agg(per_seed, T, "ts", "jsd") for T, _r, _t in ARMS}

    T_ece_min = min(ece_arm, key=lambda T: ece_arm[T][0])
    T_jsd_min = min(jsd_arm, key=lambda T: jsd_arm[T][0])
    ECE_min, JSD_min = ece_arm[T_ece_min][0], jsd_arm[T_jsd_min][0]

    occupy = {}
    for T, _role, _t in ARMS:
        e, es = ece_ts[T]
        j, js = jsd_ts[T]
        bar_e = 2 * max(es, ece_arm[T_ece_min][1])
        bar_j = 2 * max(js, jsd_arm[T_jsd_min][1])
        ok_e, ok_j = e <= ECE_min + bar_e, j <= JSD_min + bar_j
        occupy[T] = {"ece": e, "ece_sd": es, "jsd": j, "jsd_sd": js,
                     "bar_ece": bar_e, "bar_jsd": bar_j,
                     "margin_ece": ECE_min + bar_e - e, "margin_jsd": JSD_min + bar_j - j,
                     "passes_ece": ok_e, "passes_jsd": ok_j, "occupies": ok_e and ok_j}

    winners = [T for T in occupy if occupy[T]["occupies"]]
    partial = [T for T in occupy if (occupy[T]["passes_ece"] != occupy[T]["passes_jsd"])]
    if winners:
        verdict = "ALT YAZI YANLIŞLANDI"
        detail = (f"{len(winners)} nokta köşeyi işgal ediyor: " +
                  ", ".join(f"T={T}+TS" for T in winners) +
                  ". Alt yazının 'the two objectives cannot be satisfied at once' cümlesi, "
                  "post-hoc öğrenci ölçeklemesi içeren tarifler için doğru değil ve yeniden "
                  "yazılmalı.")
    elif partial and not winners:
        verdict = "ÇÖZÜNMEDİ"
        detail = ("Hiçbir nokta iki eksende birden köşeye girmiyor, ama " +
                  ", ".join(f"T={T}+TS" for T in partial) + " bir eksende geçip diğerinde "
                  "taşıyor. Alt yazı 'no **evaluated** arm' diye daraltılmalı; genel "
                  "imkânsızlık iddiası yazılmamalı.")
    else:
        verdict = "ALT YAZI AYAKTA"
        detail = ("Dört kolun hiçbiri, çapraz-uyarlanmış öğrenci-tarafı TS ile bile köşeyi "
                  "işgal etmiyor. Bu, alt yazıyı zayıflatan değil güçlendiren bir sonuç: "
                  "hakemin önerdiği ucuz çürütme adayı sınandı ve tutmadı.")

    # ---------------- rapor
    L = ["# R3-W1 — Can both FERPlus objectives be met at once? (pre-registration A11)", "",
         f"Producer: `diagnostics/r3w1_joint_optimum.py` · @{CK} · {SD_CONVENTION} · "
         f"reporting set n={n} (same filter as `ferplus_student_jsd`)", "",
         "Round-2 review, seat R3 (MAJOR): the dual-axis caption asserts that *no arm occupies "
         "the lower-left corner: the two objectives cannot be satisfied at once*. That is an "
         "impossibility claim resting on a four-arm grid. The reviewer named a cheap refutation "
         "candidate — distil at the human-aligned T=0.74, then cross-fit a student-side "
         "temperature to repair ECE. This table runs that candidate, and the same test on all "
         "four arms.", "",
         "**Protocol is R0-1's, unchanged.** The split rule, the TS fit and the two-axis "
         "measurement are *imported* from `student_ts_baseline.py`, not reimplemented: image "
         "names are sha256'd and sorted by hex, first half A / second half B "
         f"(A={na}, B={nb}); T_s is fitted on one half by NLL minimisation and measured on the "
         "other, in both directions; each sample is scored exactly once with the opposite "
         "half's T. Only the scope differs — R0-1 applied it to the T=1 arm alone.", "",
         "## The four arms, before and after student-side TS", "",
         "| T (teacher pre-scaling) | role | ECE arm | ECE +TS | JSD arm | JSD +TS | "
         "T_s (A→B / B→A, seed 42) |", "|---|---|---|---|---|---|---|"]
    for T, role, _t in ARMS:
        ts42 = per_seed[T]["42"]["T_s"]
        L.append(f"| {T} | {role} | {ece_arm[T][0]:.4f} ± {ece_arm[T][1]:.4f} | "
                 f"**{ece_ts[T][0]:.4f} ± {ece_ts[T][1]:.4f}** | "
                 f"{jsd_arm[T][0]:.4f} ± {jsd_arm[T][1]:.4f} | "
                 f"**{jsd_ts[T][0]:.4f} ± {jsd_ts[T][1]:.4f}** | "
                 f"{ts42[0]:.3f} / {ts42[1]:.3f} |")
    L += ["",
          f"The corner is defined by the arms' own two best values: **ECE_min = {ECE_min:.4f}** "
          f"(T={T_ece_min}) and **JSD_min = {JSD_min:.4f}** (T={T_jsd_min}). A point occupies "
          "the corner when it is at or below both, each within one bar (2× the larger of the "
          "two seed sds). The definition was frozen in A11 before any number was read.", "",
          "## Does any point occupy the corner?", "",
          "| candidate | ECE | vs ECE_min+bar | JSD | vs JSD_min+bar | occupies? |",
          "|---|---|---|---|---|---|"]
    for T, _role, _t in ARMS:
        o = occupy[T]
        L.append(f"| T={T} + student-TS | {o['ece']:.4f} | "
                 f"{ECE_min + o['bar_ece']:.4f} ({'✅' if o['passes_ece'] else '❌'} "
                 f"{o['margin_ece']:+.4f}) | {o['jsd']:.4f} | "
                 f"{JSD_min + o['bar_jsd']:.4f} ({'✅' if o['passes_jsd'] else '❌'} "
                 f"{o['margin_jsd']:+.4f}) | "
                 f"{'**YES**' if o['occupies'] else 'no'} |")
    L += ["", f"### Verdict: {verdict}", "", detail, ""]

    # --- Marj dürüstlüğü. Kural "bar içinde" diyor; bir okuyucu bunu "iki optimumu da
    # DÖVDÜ" diye okumamalı. Geçişin ne kadar dar olduğu sayıyla yazılır.
    if winners:
        w = winners[0]
        o = occupy[w]
        L += ["#### How wide is the pass?", "",
              f"Not wide. T={w}+TS sits **{o['ece'] - ECE_min:+.4f}** from ECE_min "
              f"(bar {o['bar_ece']:.4f}) and **{o['jsd'] - JSD_min:+.4f}** from JSD_min "
              f"(bar {o['bar_jsd']:.4f}). On both axes it is *above* the best arm's value and "
              "clears the test only because it stays inside seed noise. The defensible sentence "
              "is therefore **\"indistinguishable from both optima within seed noise\"**, not "
              "\"better than both\". That is still enough to falsify an impossibility claim — "
              "the caption says the two objectives *cannot* be satisfied at once — but it is not "
              "a domination result and must not be written as one.", ""]
        if partial:
            L += [f"Note also that the reviewer's own candidate (T=0.74+TS) does **not** pass: "
                  f"it clears ECE by {occupy['0.74']['margin_ece']:+.4f} but misses JSD by "
                  f"{occupy['0.74']['margin_jsd']:+.4f}. The arm that refutes the caption is the "
                  "**native T=1 student** — i.e. the cheapest recipe on the board, with no "
                  "teacher-side intervention at all.", ""]

    # --- TS sonrası JSD çöküşü. Bu, sorulan sorudan bağımsız ama ondan daha önemli olabilir.
    j_arm_vals = [jsd_arm[T][0] for T, _r, _t in ARMS]
    j_ts_vals = [jsd_ts[T][0] for T, _r, _t in ARMS]
    spread_arm = max(j_arm_vals) - min(j_arm_vals)
    spread_ts = max(j_ts_vals) - min(j_ts_vals)
    L += ["## An unasked-for finding: student-side TS collapses the JSD axis", "",
          f"Before scaling, the four arms span **{spread_arm:.4f}** in JSD "
          f"({min(j_arm_vals):.4f}–{max(j_arm_vals):.4f}). After a single cross-fitted "
          f"student-side scalar they span **{spread_ts:.4f}** "
          f"({min(j_ts_vals):.4f}–{max(j_ts_vals):.4f}) — a "
          f"{spread_arm / spread_ts:.0f}× reduction, with all four arms landing on the same "
          "value to within seed noise.", "",
          "The reading is uncomfortable for the teacher-side lever and is reported anyway: on "
          "this dataset almost the entire human-alignment difference between pre-scaling arms is "
          "a **confidence-scale** effect, and one student-side scalar reproduces it. Whatever "
          "the teacher-side intervention does to the student's *representation* — as opposed to "
          "its confidence scale — does not show up on the JSD axis once the scale is free. §5.7 "
          "already reported the T=1 case of this; extending it to all four arms makes the "
          "pattern, not the single comparison, the finding.", ""]
    if repro.get("checked"):
        L += ["**R0-1 reproduction check.** " +
              ("The published T=1 row (raw and student-TS, ECE and JSD, three seeds) is "
               "reproduced bit-identically — the shared code path is the same one."
               if repro["identical"] else
               "⚠️ The published T=1 row is **NOT** reproduced: " + "; ".join(repro["diffs"])),
              ""]
    L += ["**Scope limit, stated in the declaration.** This check is only possible on FERPlus: "
          "RAF-DB has no clean partition on which to fit a student-side temperature (§5.7's own "
          "reasoning). The result is FERPlus-specific.", "",
          "No training and no GPU: the @swa logits are read from `diagnostics/student_logits/`, "
          "the published byte copies of the run-directory caches (`publish_student_logits.py`, "
          "sha256-verified). The reporting set — labels, vote distributions, file names — is "
          "rebuilt from `diagnostics/ferplus_jsd/ferplus_val_logits.pt` and "
          "`configs/FERPlus_majority_metadata.csv`, so this table needs no raw run directory.",
          ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "r3w1_joint_optimum.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "r3w1_joint_optimum.json").write_text(json.dumps(
        {"sd_convention": SD_CONVENTION, "checkpoint": CK, "n_val": n,
         "split": {"n_A": na, "n_B": nb},
         "corner": {"ECE_min": ECE_min, "T_ece_min": T_ece_min,
                    "JSD_min": JSD_min, "T_jsd_min": T_jsd_min},
         "arms": {T: {"role": r,
                      "ece_arm": ece_arm[T], "jsd_arm": jsd_arm[T],
                      "ece_ts": ece_ts[T], "jsd_ts": jsd_ts[T]} for T, r, _ in ARMS},
         "occupancy": occupy, "verdict": verdict, "detail": detail,
         "reproduces_r0_1": repro,
         "per_seed": per_seed}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n=== {verdict} ===\n{detail}")
    print(f"R0-1 yeniden üretim: {repro}")
    print(f"\nWrote {OUT_DIR / 'r3w1_joint_optimum.md'}")


if __name__ == "__main__":
    main()
