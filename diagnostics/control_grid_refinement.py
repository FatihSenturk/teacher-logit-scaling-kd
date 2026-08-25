"""G0 — kontrol öğretmeni grid inceltmesi: çıkış kontrolü + beş noktalı seri.

ÖN-BEYAN DURUMU: BU KOŞULAR ÖN-BEYANLI DEĞİL (PREREGISTRATIONS B8). Round-2 hakem raporu
(5 Ağu) görülmüşken planlandılar. §4.5 envanterine GİRMEZLER.

NEDEN. Panel R1-W11: kontrol öğretmeninin (VAE9182) kendi optimumu T*_NLL=0.983 /
T*_ECE=1.057 aralığında, ama A1'in ön-beyanlı falsifikasyon grid'i {0.85, 1.00, 1.3406,
1.70, 2.20} — en yakın aralık 0.15. "İyi kalibre öğretmen iç optimum göstermez" tahmini
başarısız olabileceği ölçekte sınanamamıştı. T=0.95 ve T=1.10 bunu sınanabilir yapıyor.

ÇIKIŞ KONTROLÜ — ÇOKLU-ATTEMPT MADDESİ AYRICA RAPORLANIR (Fatih'in 6 Ağu talimatı).
G0'ın bütün değeri "mevcut kontrol kollarıyla birebir aynı tarif, tek fark T" olmasında.
Kesilip DEVAM ETTİRİLEN bir koşu, optimizer durumu ve veri sırası bakımından temiz koşuyla
aynı değildir ve o karşılaştırılabilirliği bozar. Bu yüzden:
  · her koşu adının kaç DENEME dizini taşıdığı sayılır ve raporlanır;
  · yarım kalan denemeler `metrics_best.json` yokluğuyla ELENİR (analiz onları görmez);
  · elenen her deneme, kaç epoch'ta öldüğüyle birlikte tabloda GÖRÜNÜR — sessizce atılmaz.
6 Ağu ~05:43 elektrik kesintisi T110_seed42'yi 399/400'de öldürdü; kurtarma DENENMEDİ
(swa_student.pth yazılmamıştı, ayrıca train_rafdb_kd.py'de --resume yok), koşu sıfırdan
yeniden koşuldu. Bu tablo o olayı gizlemez, sayar.

AD -> PARAMETRE KAPISI: hiçbir hücre adından çıkarılmaz; her koşunun kendi run_args.json'u
okunup (alpha, tau, t_scale, seed, epochs, swa_start) referans kolla karşılaştırılır.

ÇIKTI: beş noktalı tam seri (0.85 / 0.95 / 1.00 / 1.10 / 1.3406) — tohum başına ECE ve
doğruluk, arm ortalamaları ± sd, T=1'e karşı tohum-içi eşleştirilmiş farklar, ve
2×-kontrol-sd ölçütünün (G3.1) uygulanmış hâli.

Veri: selection_audit_unfrozen.csv @swa. GPU yok, salt-okunur.
Çıktı -> diagnostics/paper_tables/control_grid_refinement.{md,json}
Kullanım: python diagnostics/control_grid_refinement.py
"""
import csv
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))

from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402
from p1_two_teacher_overlay import CURVES  # noqa: E402  -- TEK KAYNAK: mevcut kol adları

STUDENTS = ROOT / "results" / "unified_students"
AUDIT = ROOT / "diagnostics" / "selection_audit" / "selection_audit_unfrozen.csv"
DENOM = ROOT / "diagnostics" / "paper_tables" / "denominator_table.json"
OUT_DIR = ROOT / "diagnostics" / "paper_tables"
SEEDS = (42, 1, 43)
CK = "swa"

# Beş nokta: üçü mevcut (CURVES'ten), ikisi G0'ın yeni koşuları.
NEW = {0.95: "RAFDB_vae9182_tempscale_T095_b070_T6_224_400e_swa200_seed{s}",
       1.10: "RAFDB_vae9182_tempscale_T110_b070_T6_224_400e_swa200_seed{s}"}
GRID = [0.85, 0.95, 1.0, 1.10, 1.3406]

HONESTY = (
    "> **Review-responsive, not pre-declared (5 Aug 2026).** Computed after the Round-2 panel "
    "report; no prediction was frozen beforehand. The pre-declaration inventory of §4.5 is "
    "unaffected — these analyses are reported as post-hoc re-analyses of existing artifacts."
)
GRID_NOTE = (
    "> The original pre-declared test was run at grid resolution 0.15 and held; these two "
    "points were added afterwards, in response to review, to test at the scale of the "
    "teacher's own optimum."
)


def curve_at(T):
    ks = [k for k in CURVES["vae9182"] if abs(float(k) - T) < 1e-9]
    return CURVES["vae9182"][ks[0]] if len(ks) == 1 else None


def run_name(T, s):
    if T in NEW:
        return NEW[T].format(s=s)
    c = curve_at(T)
    return c.get(s) if c else None


def attempts(name):
    """Bu koşu adının deneme dizinleri: (toplam, bitmiş, yarım listesi)."""
    d = STUDENTS / name
    if not d.is_dir():
        return 0, [], []
    subs = sorted(x for x in d.iterdir() if x.is_dir())
    done, part = [], []
    for x in subs:
        tl = x / "training_log.csv"
        ep = (sum(1 for _ in tl.open(encoding="utf-8", errors="replace")) - 1) if tl.exists() else 0
        (done if (x / "metrics_best.json").exists() else part).append((x.name, ep))
    return len(subs), done, part


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    swa, args_by_run = {}, {}
    for r in csv.DictReader(AUDIT.open(encoding="utf-8")):
        if r["checkpoint"] == CK:
            swa[r["run_name"]] = {"ece": float(r["ece"]), "acc": float(r["acc"]),
                                  "run_dir": r["run_dir"]}

    # ---- çıkış kontrolü
    exit_rows, missing = [], []
    for T in GRID:
        for s in SEEDS:
            nm = run_name(T, s)
            if not nm:
                missing.append(f"T={T:g} seed{s}: ad çözülemedi")
                continue
            n_att, done, part = attempts(nm)
            exit_rows.append({"T": T, "seed": s, "run": nm, "n_attempts": n_att,
                              "finished": [a for a, _ in done], "partial": part,
                              "in_audit": nm in swa})
            if nm not in swa:
                missing.append(f"T={T:g} seed{s}: {nm} denetimde yok")

    multi = [r for r in exit_rows if r["n_attempts"] > 1]
    partial_all = [(r, a, e) for r in exit_rows for a, e in r["partial"]]

    # ---- ad -> parametre kapısı (yalnız denetimde olanlar)
    param_bad, param_default = [], []
    for r in exit_rows:
        if not r["in_audit"]:
            continue
        ra = json.loads((Path(swa[r["run"]]["run_dir"]) / "run_args.json")
                        .read_text(encoding="utf-8"))
        want = {"alpha": 0.3, "temperature": 6.0, "epochs": 400, "swa_start": 200,
                "teacher_temperature_scale": r["T"], "seed": r["seed"]}
        # EKSİK ANAHTAR ≠ YANLIŞ DEĞER. T=1.0 kolları Haziran'da, `--teacher-temperature-scale`
        # bayrağı eklenmeden önce koşuldu; run_args.json'larında anahtar HİÇ YOK. Yokluğu
        # uyuşmazlık saymak üç yanlış alarm üretiyordu. Yokluk, bayrağın belgelenmiş
        # VARSAYILANI kabul edilir — ama sessizce değil: hangi koşuda hangi anahtarın
        # varsayılana düştüğü ayrıca listelenir, çünkü "varsayılan kabul edildi" bir okuyucunun
        # görmesi gereken bir varsayımdır.
        DEFAULTS = {"teacher_temperature_scale": 1.0}
        for k, v in want.items():
            got = ra.get(k)
            if got is None and k in DEFAULTS:
                if abs(DEFAULTS[k] - float(v)) > 1e-9:
                    param_bad.append(f"{r['run']}: {k} beklenen {v}, anahtar yok ve varsayılan "
                                     f"{DEFAULTS[k]} de uymuyor")
                else:
                    param_default.append(f"{r['run']}: `{k}` anahtarı yok → belgelenmiş "
                                         f"varsayılan {DEFAULTS[k]:g} kabul edildi "
                                         f"(bayrak bu koşudan sonra eklendi)")
                continue
            if got is None or abs(float(got) - float(v)) > 1e-9:
                param_bad.append(f"{r['run']}: {k} beklenen {v}, run_args {got}")

    # ---- seri
    series, gaps = {}, {}
    ref = {}
    for T in GRID:
        cells = {}
        for s in SEEDS:
            nm = run_name(T, s)
            if nm and nm in swa:
                cells[s] = swa[nm]
        if cells:
            series[T] = {"n": len(cells),
                         "ece_mean": st.mean(c["ece"] for c in cells.values()),
                         "ece_sd": sample_sd([c["ece"] for c in cells.values()]),
                         "acc_mean": st.mean(c["acc"] for c in cells.values()),
                         "acc_sd": sample_sd([c["acc"] for c in cells.values()]),
                         "by_seed": {str(s): cells[s] for s in cells}}
        if abs(T - 1.0) < 1e-9:
            ref = cells
    for T in GRID:
        if abs(T - 1.0) < 1e-9 or T not in series:
            continue
        d = [swa[run_name(T, s)]["ece"] - ref[s]["ece"]
             for s in SEEDS if run_name(T, s) in swa and s in ref]
        if d:
            gaps[T] = {"n": len(d), "mean": st.mean(d), "sd": sample_sd(d),
                       "signs": "".join("-" if x < 0 else "+" for x in d), "per_seed": d}

    # ---- 2×-kontrol-sd ölçütü (G3.1)
    dn = json.loads(DENOM.read_text(encoding="utf-8"))
    sigma = dn["control_arms"]["vae9182/effective_number"]["ece_sd"]
    for T, g in gaps.items():
        ratio = abs(g["mean"]) / sigma
        same = len(set(g["signs"])) == 1 and len(g["signs"]) == g["n"]
        g.update({"sigma_control": sigma, "ratio": ratio, "same_sign": same,
                  "verdict": "established" if (ratio >= 2 and same) else "unresolved"})

    complete = not missing and not param_bad
    L = ["# G0 — Control-teacher grid refinement (T = 0.95 and 1.10)", "", HONESTY, "",
         GRID_NOTE, "",
         f"Producer: `diagnostics/control_grid_refinement.py` · @{CK} · {SD_CONVENTION} · "
         "pre-registration status: **not pre-declared** (PREREGISTRATIONS §B8)", "",
         "## Exit check", "",
         "| check | result |", "|---|---|",
         f"| grid points × seeds expected | {len(GRID)} × {len(SEEDS)} = {len(GRID) * len(SEEDS)} |",
         f"| present in the audit | {sum(1 for r in exit_rows if r['in_audit'])} |",
         f"| **runs with more than one attempt (crash evidence)** | **{len(multi)}** |",
         f"| partial attempts excluded (no `metrics_best.json`) | {len(partial_all)} |",
         f"| name → parameter mismatches | {len(param_bad)} |",
         f"| keys absent, documented default assumed | {len(param_default)} |", ""]

    L += ["**Why the multi-attempt line is reported separately.** G0's entire value is that the "
          "recipe is byte-for-byte the existing control arm with only T changed. A run that was "
          "interrupted and *continued* would not be equivalent to a clean one — optimizer state "
          "and data order would differ — so it would break exactly the comparability the "
          "experiment depends on. No G0 run was resumed: the campaign's training script has no "
          "`--resume`, and the one casualty was restarted from epoch 0 rather than continued.", ""]
    if partial_all:
        L += ["| excluded attempt | epochs reached | reason |", "|---|---|---|"]
        for r, a, e in partial_all:
            L.append(f"| `{r['run']}` / {a} | {e}/400 | no `metrics_best.json` — "
                     "interrupted, restarted clean |")
        L += [""]
    if multi:
        L += ["Runs carrying more than one attempt directory: "
              + ", ".join(f"`{r['run']}` ({r['n_attempts']})" for r in multi)
              + ". Each such run's **finished** attempt is the one used; the partial is marked "
                "`ABANDONED.json` and is invisible to every table.", ""]
    if missing:
        L += ["> ⚠️ **Incomplete.** The series below is missing runs and must not be read as "
              "final:", ""] + [f"> - {m}" for m in missing] + [""]
    if param_bad:
        L += ["> ⚠️ **Name/parameter mismatch — verdict withheld:**", ""] + \
             [f"> - {m}" for m in param_bad] + [""]

    if param_default:
        L += ["**Keys absent, default assumed** (stated rather than silently accepted — the "
              "T = 1 arms predate the `--teacher-temperature-scale` flag, so the key is missing "
              "from their `run_args.json` rather than set):", ""]
        L += [f"- {m}" for m in param_default] + [""]

    L += ["## The five-point control series", "",
          "| T | role | n | student ECE | student acc (pp) |", "|---|---|---|---|---|"]
    role = {0.85: "pre-declared grid", 0.95: "**added (G0)**", 1.0: "native / pre-declared",
            1.10: "**added (G0)**", 1.3406: "pre-declared grid"}
    for T in GRID:
        if T not in series:
            L.append(f"| {T:g} | {role[T]} | — | *(missing)* | — |")
            continue
        v = series[T]
        L.append(f"| {T:g} | {role[T]} | {v['n']} | {v['ece_mean']:.4f} ± {v['ece_sd']:.4f} | "
                 f"{v['acc_mean']:.2f} ± {v['acc_sd']:.2f} |")

    if gaps:
        L += ["", "## Paired differences against T = 1, within seed", "",
              f"Criterion (G3.1): |mean ΔECE| ÷ σ_control ≥ 2 **and** all seeds share the sign. "
              f"σ_control = {sigma:.4f} (vae9182 `effective_number` control arm @swa).", "",
              "| T | mean ΔECE | signs | ratio | verdict |", "|---|---|---|---|---|"]
        for T in GRID:
            if T not in gaps:
                continue
            g = gaps[T]
            L.append(f"| {T:g} | {g['mean']:+.4f} ± {g['sd']:.4f} | {g['signs']} | "
                     f"{g['ratio']:.2f}× | {g['verdict']} |")
        L += [""]

    L += ["Source: `diagnostics/selection_audit/selection_audit_unfrozen.csv` @swa. The frozen "
          "audit (`selection_audit.csv`, N=131) is a different file and is untouched.", ""]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "control_grid_refinement.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "control_grid_refinement.json").write_text(json.dumps(
        {"note": "review-responsive, not pre-declared (B8)", "checkpoint": CK,
         "sd_convention": SD_CONVENTION, "complete": complete,
         "exit_check": {"rows": exit_rows, "n_multi_attempt": len(multi),
                        "partial_excluded": [{"run": r["run"], "attempt": a, "epochs": e}
                                             for r, a, e in partial_all],
                        "missing": missing, "param_mismatches": param_bad,
                        "param_defaults_assumed": param_default},
         "series": {str(k): v for k, v in series.items()},
         "gaps_vs_T1": {str(k): v for k, v in gaps.items()},
         "sigma_control": sigma}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"cikis: {sum(1 for r in exit_rows if r['in_audit'])}/{len(exit_rows)} denetimde · "
          f"coklu-attempt {len(multi)} · elenen yarim {len(partial_all)} · "
          f"parametre uyusmazligi {len(param_bad)} "
          f"(varsayilana dusen {len(param_default)})")
    if missing:
        print(f"EKSIK ({len(missing)}): seri final DEGIL")
    print(f"Wrote {OUT_DIR / 'control_grid_refinement.md'}")


if __name__ == "__main__":
    main()
