"""G2.1 — seçim denetimi kontrastlarının çıkarım tablosu: SD ≠ SE.

İTİRAZ (Round-2 panel, R2/P0): `tab_selection_audit` sütunlarındaki ± değerleri koşular-arası
**SD**; ortalamanın belirsizliği ise SE = SD/√n. İkisi tabloda ayırt edilmediği için bir okuyucu
"±0.0092" görüp kontrastı gürültüde sanabiliyor, oysa n=131'de SE 0.0008 ve kontrast 3.6 SE.

NE ÜRETİLİYOR. T8'in DÖRT satırının (RAF-DB/FERPlus × best−last/best−swa) her biri için, iki
metrikte (doğruluk pp ve ECE): ortalama · SD · n · SE · t · df · iki-yanlı p · %95 CI.
Test, eşleştirilmiş farkların tek-örneklem t testidir (aynı koşunun iki checkpoint'i), df = n−1.

ÖLÇEĞE ORAN. ECE kontrastının büyüklüğü tek başına okunamaz; tabloya "tipik öğrenci ECE'sinin
yüzde kaçı" sütunu ekleniyor. Payda seçilebilir bir şey olduğu için ÜÇÜ BİRDEN raporlanır
(referans checkpoint'in ortalaması, medyanı ve best'in ortalaması) — tek bir payda seçip
"%7" demek, ölçütü sonradan seçmek olurdu.

VERİ: donmuş denetim dosyaları. `selection_audit.csv` (N=131, makalenin alıntıladığı küme) ve
`ferplus_selection_audit.csv` (N=12). Donmamış üst küme (179 koşu) KULLANILMAZ.

Salt-okunur, GPU yok.
Çıktı -> diagnostics/paper_tables/selection_audit_inference.{md,json}
Kullanım: python diagnostics/selection_audit_inference.py
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

A_RAFDB = ROOT / "diagnostics" / "selection_audit" / "selection_audit.csv"
A_FER = ROOT / "diagnostics" / "selection_audit" / "ferplus_selection_audit.csv"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

HONESTY = (
    "> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel "
    "report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is "
    "unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts."
)


def load_by_run(path):
    """(run_name, timestamp) -> {checkpoint: {acc, ece}}."""
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        out.setdefault((r["run_name"], r["timestamp"]), {})[r["checkpoint"]] = {
            "acc": float(r["acc"]), "ece": float(r["ece"])}
    return out


def one_sample_t(diffs):
    """Eşleştirilmiş farkların tek-örneklem t testi. n<2 ise test yok."""
    n = len(diffs)
    mean = st.mean(diffs)
    if n < 2:
        return {"mean": mean, "sd": None, "n": n, "se": None, "t": None, "df": None,
                "p": None, "ci_lo": None, "ci_hi": None}
    sd = sample_sd(diffs)
    se = sd / (n ** 0.5)
    df = n - 1
    if se == 0:
        return {"mean": mean, "sd": sd, "n": n, "se": se, "t": None, "df": df,
                "p": None, "ci_lo": mean, "ci_hi": mean}
    t = mean / se
    p = float(2 * stats.t.sf(abs(t), df))
    crit = float(stats.t.ppf(0.975, df))
    return {"mean": mean, "sd": sd, "n": n, "se": se, "t": t, "df": df, "p": p,
            "ci_lo": mean - crit * se, "ci_hi": mean + crit * se}


def fmt_p(p):
    if p is None:
        return "—"
    if p < 1e-4:
        return f"{p:.2e}"
    return f"{p:.4f}"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rows, payload = [], {}
    for label, path in (("RAF-DB", A_RAFDB), ("FERPlus", A_FER)):
        by_run = load_by_run(path)
        payload[label] = {"source": str(path.relative_to(ROOT)), "contrasts": {}}
        for ref in ("last", "swa"):
            pairs = [v for v in by_run.values() if "best" in v and ref in v]
            if not pairs:
                continue
            d_acc = [v["best"]["acc"] - v[ref]["acc"] for v in pairs]
            d_ece = [v["best"]["ece"] - v[ref]["ece"] for v in pairs]
            r_acc, r_ece = one_sample_t(d_acc), one_sample_t(d_ece)

            # --- ölçek paydaları: üçü birden, seçilmesin diye
            ece_ref = [v[ref]["ece"] for v in pairs]
            ece_best = [v["best"]["ece"] for v in pairs]
            scales = {f"mean ECE @{ref}": st.mean(ece_ref),
                      f"median ECE @{ref}": st.median(ece_ref),
                      "mean ECE @best": st.mean(ece_best)}
            rel = {k: (abs(r_ece["mean"]) / v if v else None) for k, v in scales.items()}

            payload[label]["contrasts"][f"best-{ref}"] = {
                "acc_pp": r_acc, "ece": r_ece,
                "ece_scale_denominators": scales, "ece_relative_to_scale": rel}
            rows.append((label, ref, r_acc, r_ece, scales, rel))
            print(f"{label:8s} best-{ref:4s} n={r_acc['n']:3d} | "
                  f"dacc {r_acc['mean']:+.3f} SE {r_acc['se']:.4f} t {r_acc['t']:+.2f} "
                  f"p {fmt_p(r_acc['p'])} | "
                  f"dece {r_ece['mean']:+.4f} SE {r_ece['se']:.5f} t {r_ece['t']:+.2f} "
                  f"p {fmt_p(r_ece['p'])}")

    L = ["# G2.1 — Selection-audit contrasts: SD vs SE, with inference", "", HONESTY, "",
         f"Producer: `diagnostics/selection_audit_inference.py` · {SD_CONVENTION} · "
         "paired one-sample t on within-run differences, df = n−1, two-sided", "",
         "The `±` in `tab_selection_audit` is the **between-run SD**, not the uncertainty of the "
         "mean. This table separates them: SE = SD/√n.", "",
         "## Accuracy contrasts (percentage points)", "",
         "| dataset | contrast | mean | SD | n | SE | t | df | p (two-sided) | 95% CI |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for label, ref, ra, _re, _s, _rl in rows:
        L.append(f"| {label} | best − {ref} | {ra['mean']:+.3f} | {ra['sd']:.3f} | {ra['n']} | "
                 f"{ra['se']:.4f} | {ra['t']:+.2f} | {ra['df']} | {fmt_p(ra['p'])} | "
                 f"[{ra['ci_lo']:+.3f}, {ra['ci_hi']:+.3f}] |")
    L += ["", "## ECE contrasts", "",
          "| dataset | contrast | mean | SD | n | SE | t | df | p (two-sided) | 95% CI |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for label, ref, _ra, re_, _s, _rl in rows:
        L.append(f"| {label} | best − {ref} | {re_['mean']:+.4f} | {re_['sd']:.4f} | {re_['n']} | "
                 f"{re_['se']:.5f} | {re_['t']:+.2f} | {re_['df']} | {fmt_p(re_['p'])} | "
                 f"[{re_['ci_lo']:+.4f}, {re_['ci_hi']:+.4f}] |")

    L += ["", "## ECE contrast relative to the scale of student ECE", "",
          "The magnitude of an ECE contrast cannot be read on its own. Three denominators are "
          "reported rather than one, because picking a single denominator after seeing the "
          "result would be choosing the yardstick to fit the number.", "",
          "| dataset | contrast | \\|mean ΔECE\\| | " +
          " | ".join(f"as % of {k}" for k in rows[0][4]) + " |",
          "|---|---|---|" + "---|" * len(rows[0][4])]
    for label, ref, _ra, re_, scales, rel in rows:
        cells = " | ".join(f"{100 * rel[k]:.1f}% ({scales[k]:.4f})" if rel[k] is not None else "—"
                           for k in scales)
        L.append(f"| {label} | best − {ref} | {abs(re_['mean']):.4f} | {cells} |")

    L += ["", "Source files: `diagnostics/selection_audit/selection_audit.csv` (the frozen "
              "N=131 inclusion set the paper quotes) and "
              "`diagnostics/selection_audit/ferplus_selection_audit.csv` (N=12). The unfrozen "
              "179-run superset is **not** used here.", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "selection_audit_inference.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "selection_audit_inference.json").write_text(json.dumps(
        {"sd_convention": SD_CONVENTION, "test": "paired one-sample t on within-run differences",
         "note": "review-responsive, not pre-declared", "datasets": payload},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'selection_audit_inference.md'}")


if __name__ == "__main__":
    main()
