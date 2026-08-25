"""Single source of truth for every finished RAF-DB student run -> runs.csv.

Design rule: EVERY field is derived from a run's own artifacts (run_args.json,
metrics_best.json, best_checkpoint.pth), never hand-typed. A hand-maintained results
table drifts from reality the moment a run is re-launched; this one cannot.

Accuracy comes from metrics_best.json (what the training loop recorded).
ECE is not recorded at train time, so it is computed post-hoc on the fold-3 val set
and CACHED into <run_dir>/calibration.json. First pass over a new run costs one CPU
forward; every later pass is a file read. Pass --no-compute-ece to skip uncached runs
(they land with ece empty and ece_source="uncached") when the machine is busy.

Columns are chosen so the paper's tables are pivots of this file, not new queries:
  family      which experiment block the run belongs to (dose_response, vich_isolation, ...)
  teacher     stage1 | primary | vae9182
  manipulation what single variable is being moved vs. that family's control
  t_scale     --teacher-temperature-scale (1.0 = unmanipulated teacher)

Usage:
  python diagnostics/build_runs_ledger.py                 # full rebuild (computes missing ECE)
  python diagnostics/build_runs_ledger.py --no-compute-ece
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

STUDENTS = ROOT / "results" / "unified_students"
OUT_CSV = ROOT / "runs.csv"

TEACHER_BY_CKPT = {
    "2026-07-17-04-41-04": "stage1",
    "2026-06-16-23-33-23": "vae9182",
    "teacher_rafdb_vich_recipe_best": "primary",
    "2026-07-11-04-10-08": "primary",
    "teacher_vich9237_best": "legacy9237",
}


def teacher_of(run_args):
    ckpt = str(run_args.get("teacher_ckpt", ""))
    for key, name in TEACHER_BY_CKPT.items():
        if key in ckpt:
            return name
    return "unknown"


PREREG_CSV = ROOT / "diagnostics" / "preregistration_blocks.csv"


def load_prereg_blocks():
    """prefix -> (block, declared_on, artifact), from a DECLARED registry rather than the flags.

    This is the single field in the ledger that cannot be derived from a run's own artifacts:
    which pre-registered block a run was launched to serve is intent, and intent is never written
    into run_args.json. See the header of preregistration_blocks.csv for why declaring it is not
    the same mistake as the lexical filters removed on 2026-07-30.
    """
    if not PREREG_CSV.exists():
        return []
    out = []
    with open(PREREG_CSV, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                out.append((parts[0], parts[1], parts[2], parts[3]))
    # longest prefix wins, so a specific rule can override a general one
    return sorted(out, key=lambda r: -len(r[0]))


def prereg_block_of(run_name, table):
    for prefix, block, _declared, _artifact in table:
        if run_name.startswith(prefix):
            return block
    return ""


def capacity_tag(width_mult, pretrained):
    """The capacity-sweep cell label, derived from FLAGS rather than parsed out of the run name.

    Every consumer of the capacity sweep used to recover this label with
    `run_name.split("_frontier_")[1].split("_")[0]`, which is how P3's
    RAFDB_vae9182_frontier_w050_tempscale_T220_* runs entered the fixed-teacher w050 cell.

    The returned strings reproduce the historical labels EXACTLY -- "w050", "w075", "w100ns",
    "w100" -- because those keys already appear in the exported figures' legends and in the
    paper's capacity table. The "ns" suffix only exists at width 1.0, which is the only width
    where a scratch and a pre-trained cell both exist and the label therefore has to disambiguate
    them. Widening the suffix to every scratch width would rename two cells for no gain; the job
    here is to take the run NAME out of the data path, not to rename anything.
    """
    w = float(width_mult)
    return f"w{int(round(w * 100)):03d}" + ("ns" if (w == 1.0 and not pretrained) else "")


# The B-010 miscalibration kill-switch block is identified by the temperature it injects. See the
# comment in classify(): experimental intent -- which pre-registered block a run belongs to -- is
# the one thing the flags do not record, so the manipulated VALUE stands in for it. 0.7311 is
# unique to that block (the dose-response sweep uses 0.85/1.0/1.3406/1.7/2.2).
MISCAL_T = 0.7311


def classify(run_name, run_args):
    """(family, manipulation) from the run's own flags -- not from its name, except
    where the name is the only record of intent (e.g. which ablation block it belongs to)."""
    n = run_name.lower()
    t_scale = float(run_args.get("teacher_temperature_scale", 1.0) or 1.0)
    mech = []
    if run_args.get("gate_enable"):
        mech.append("gate")
    if run_args.get("g2g_enable"):
        mech.append(f"g2g_{run_args.get('g2g_mode', 'kl')}")
    if run_args.get("adaptive_t_enable"):
        mech.append("adaptive_t")
    if run_args.get("logit_std_enable"):
        mech.append("logit_std")
    if run_args.get("ctkd_enable"):
        mech.append("ctkd")
    manipulation = "+".join(mech) if mech else "none"

    width_mult = float(run_args.get("width_mult", 1.0) or 1.0)
    pretrained = bool(run_args.get("student_pretrained"))

    # EVERY BRANCH BELOW KEYS ON FLAGS, NOT ON THE RUN NAME. Lexical tests were removed on
    # 2026-07-30 after `"frontier" in name` swept P3's temperature-scaled frontier runs into the
    # fixed-teacher capacity cell (see METHODS_DATA 5A.2). Two of the removed tests were dead --
    # `"tempscale" in name` never matched a run that `t_scale != 1.0` had not already caught, and
    # `"pluslinear" in name` was redundant with student_head_type -- but one was load-bearing:
    # the three `frontier_w100ns` runs have width_mult == 1.0 and were held in the capacity family
    # by their name alone. `not pretrained` is their exact semantic signature (verified: all 13
    # capacity runs are the only student_pretrained=False runs on disk, and every other family is
    # exclusively pretrained at width 1.0).
    if t_scale != 1.0:
        # A pre-scaled teacher is a different teacher; such a run must never sit in an unscaled
        # pool. T5 is independently protected (is_ablation_control requires t_scale == 1.0), but
        # any consumer trusting `family` alone would not be.
        # WHICH pre-scaled block a run belongs to is experimental intent, and intent is the one
        # thing no flag records -- so the manipulated VALUE stands in for it. This is the single
        # filter in this file that is not a pure flag test; if a future run reuses 0.7311 for a
        # different purpose, the ledger needs an explicit block field rather than this proxy.
        family = "miscal_causal" if abs(t_scale - MISCAL_T) < 1e-9 else "dose_response"
        manipulation = f"T={t_scale:g}" + (f"+{manipulation}" if mech else "")
    elif run_args.get("student_head_type") == "linear":
        family = "vich_isolation"
        manipulation = "head=linear"
    elif run_args.get("student_arch") == "vanilla_mnv2":
        family = "arch_frontier"
        manipulation = "arch=vanilla_mnv2"
    elif width_mult != 1.0 or not pretrained:
        # Capacity sweep. It MUST NOT fall through to family="baseline": every paired mechanism
        # table matches a treatment run to the baseline run with the same (teacher, seed), and a
        # 0.71 M-param frontier run sitting in that pool would silently become the control for a
        # 2.25 M-param treatment -- a capacity difference read as a mechanism effect.
        family = "width_frontier"
        manipulation = f"width={width_mult:g}" + ("" if pretrained else "+scratch")
    elif mech:
        family = "mechanism_ablation"
    else:
        family = "baseline"
    return family, manipulation, t_scale


def cached_ece(run_dir, compute):
    cal = run_dir / "calibration.json"
    if cal.exists():
        d = json.loads(cal.read_text())
        return d["ece"], d["acc_recomputed"], "cached"
    if not compute:
        return None, None, "uncached"
    from teacher_temperature_scaling_fit import build_val_images, confidence_ece
    from student_halfb_eval import eval_logits, student_from_run
    global _VAL
    if _VAL is None:
        _VAL = build_val_images()
    images, labels = _VAL
    logits = eval_logits(student_from_run(run_dir), images)
    ece = confidence_ece(logits, labels, 1.0)
    acc = float((logits.argmax(1) == labels).float().mean() * 100.0)
    cal.write_text(json.dumps({"ece": ece, "acc_recomputed": acc, "n_val": int(labels.shape[0]),
                               "method": "15-bin confidence ECE, fold-3 val, best_checkpoint.pth"},
                              indent=2), encoding="utf-8")
    return ece, acc, "computed"


_VAL = None


def is_rafdb(run_name):
    """This ledger is RAF-DB ONLY, and the filter is a CORRECTNESS guard, not tidiness.

    `cached_ece` scores every run on RAF-DB's fold-3 val set via `student_from_run`. Point that
    at a FERPlus or AffectNet+ student and one of two things happens, both bad:
      - it crashes (`train_rafdb_kd.build_student` reads `student_feature_adapter_dim`, a flag
        `train_affectnetplus_kd.py` does not have, so it is absent from those run_args.json) --
        this is what actually happened on the 2026-07-28 rebuild, once the 12 FERPlus tempscale
        runs existed; or
      - worse, for any run that happens to carry the flag, it silently emits an ECE computed on
        the WRONG dataset and writes it to that run's calibration.json, poisoning the cache.
    FERPlus runs are audited separately by diagnostics/ferplus_selection_audit.py, which builds
    the FERPlus val pipeline through the student's own `build_data_args`.
    """
    return run_name.upper().startswith("RAFDB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-compute-ece", action="store_true")
    args = ap.parse_args()
    PREREG_TABLE = load_prereg_blocks()

    rows, skipped = [], []
    for run_name_dir in sorted(STUDENTS.iterdir()):
        if not run_name_dir.is_dir():
            continue
        if not is_rafdb(run_name_dir.name):
            skipped.append(run_name_dir.name)
            continue
        for ts_dir in sorted(run_name_dir.iterdir()):
            ra_p, mb_p = ts_dir / "run_args.json", ts_dir / "metrics_best.json"
            if not (ra_p.exists() and mb_p.exists()):
                continue  # unfinished or not a run dir
            run_args = json.loads(ra_p.read_text())
            metrics = json.loads(mb_p.read_text())
            family, manipulation, t_scale = classify(run_name_dir.name, run_args)
            ece, acc_re, ece_src = cached_ece(ts_dir, not args.no_compute_ece)
            rows.append({
                "run_name": run_name_dir.name,
                "timestamp": ts_dir.name,
                "family": family,
                "teacher": teacher_of(run_args),
                "manipulation": manipulation,
                "t_scale": t_scale,
                "student_head": run_args.get("student_head_type"),
                "student_arch": run_args.get("student_arch", "plus"),
                # Semantic replacements for what consumers used to parse out of the run name.
                # capacity_tag() below turns these two into the "w050"/"w100ns" cell labels.
                "width_mult": float(run_args.get("width_mult", 1.0) or 1.0),
                "student_pretrained": bool(run_args.get("student_pretrained")),
                "capacity_tag": capacity_tag(run_args.get("width_mult", 1.0) or 1.0,
                                             bool(run_args.get("student_pretrained"))),
                # GATE SİNYALİ -- Level-1 DEĞİŞMEZİ İÇİN (8 Ağu, yalıtılmış adım).
                #
                # `manipulation` sütunu gate'in beş çeşidini tek bir "gate" değerine çöküyor,
                # o yüzden `paper_tables.gate_variant()` ayrımı her koşunun KENDİ
                # `run_args.json`'undan geri okuyordu. Bu, üç tablo üreticisini
                # (`paper_tables`, `t5_pairing_diff`, `section54_numbers`) koşu dizinlerine
                # bağımlı yapıyordu ve Level-1 kapısının 13 ihlalinin 8'i tam buydu: makaledeki
                # sayılar `results/unified_students/` olmadan türetilemiyordu.
                #
                # Defter zaten koşu dizinlerini okumak ZORUNDA (Level 3, `ALLOWED`'da beyanlı),
                # dolayısıyla ayrımı BURADA bir sütuna yazmak doğru yer: bilgi bir kez, en dışta,
                # okumaya izinli katmanda çıkarılır ve aşağı akış onu defterden okur.
                # Gate dışı koşularda boş kalır -- "gate" yazmak, gate olmayan bir koşuya gate
                # etiketi asmak olurdu.
                "gate_signal": (str(run_args.get("gate_uncertainty_source", "?"))
                                if run_args.get("gate_enable") else ""),
                # DECLARED, not inferred -- see load_prereg_blocks(). Empty means "no block
                # declared for this run", which is reported as a count below rather than defaulted.
                "preregistration_block": prereg_block_of(run_name_dir.name, PREREG_TABLE),
                "seed": run_args.get("seed"),
                "epochs": run_args.get("epochs"),
                "swa_start": run_args.get("swa_start") if run_args.get("swa") else "",
                "kd_temperature": run_args.get("temperature"),
                "alpha": run_args.get("alpha"),
                # Load-bearing for pairing, not descriptive. kd_common.py hard-errors on
                # gate + class-weighted CE, so EVERY gate run was forced to
                # --class-weight-mode none while the rest of the grid ran effective_number.
                # A control pool that ignores this field silently offers two legal controls
                # per (teacher, seed) and keeps whichever the dict happened to yield last.
                "class_weight_mode": run_args.get("class_weight_mode"),
                "best_epoch": metrics.get("best_epoch"),
                "acc": metrics.get("accuracy"),
                "ece": ece,
                "ece_source": ece_src,
                "macro_f1": metrics.get("macro_f1"),
                "params_m": metrics.get("params_m"),
                "flops_g": metrics.get("flops_g"),
                "run_dir": str(ts_dir),
            })
            print(f"  [{ece_src:<8}] {family:<20} {teacher_of(run_args):<10} "
                  f"seed={run_args.get('seed')} acc={metrics.get('accuracy')} {run_name_dir.name}")

    # MEKANİZMA HİPERPARAMETRE YAN DOSYASI -- Level-1 için (8 Ağu, yalıtılmış adım).
    #
    # `mechanism_specs.py` 14 ayrı `run_args` anahtarı okuyor (gate_norm, gate_alpha_lo/hi,
    # gate_k, gate_tau, adaptive_t_gamma, g2g_weight/mode/warmup_epochs, ctkd_t_min/t_max/
    # grl_lambda_max, lr) ve bunların hiçbiri defterde yoktu; dolayısıyla o tablo
    # yayımlanmayan koşu dizinleri olmadan üretilemiyordu.
    #
    # NEDEN CSV SÜTUNU DEĞİL. On iki sütunun tamamı tek bir tablo için ve çoğu koşuda boş
    # kalırdı; defterin 199 satırını on iki seyrek sütunla genişletmek okunabilirliği
    # bozardı. Yan dosya aynı katmanda üretiliyor (defter Level 3, koşu dizinlerini okumaya
    # BEYANLI izinli) ve tek bir tablonun ihtiyacını tek bir yerde topluyor.
    MECH_KEYS = ["gate_enable", "gate_uncertainty_source", "gate_norm", "gate_alpha_lo",
                 "gate_alpha_hi", "gate_k", "gate_tau", "adaptive_t_gamma", "g2g_weight",
                 "g2g_mode", "g2g_warmup_epochs", "ctkd_t_min", "ctkd_t_max",
                 "ctkd_grl_lambda_max", "lr", "temperature", "alpha",
                 "teacher_temperature_scale"]
    sidecar = {}
    for r in rows:
        ra_p = Path(r["run_dir"]) / "run_args.json"
        if not ra_p.exists():
            continue
        ra = json.loads(ra_p.read_text(encoding="utf-8"))
        sidecar[r["run_name"]] = {k: ra.get(k) for k in MECH_KEYS}
    OUT_MECH = ROOT / "diagnostics" / "paper_tables" / "run_mechanism_params.json"
    OUT_MECH.write_text(json.dumps(
        {"note": "Mekanizma hiperparametreleri, her koşunun kendi run_args.json'undan. "
                 "Level-1: tablo üreticileri koşu dizinlerine gitmesin diye burada.",
         "producer": "diagnostics/build_runs_ledger.py",
         "keys": MECH_KEYS, "runs": sidecar}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT_MECH}  ({len(sidecar)} kosu x {len(MECH_KEYS)} anahtar)")

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {OUT_CSV}  ({len(rows)} runs)")
    blocks = {}
    for r in rows:
        blocks[r["preregistration_block"] or "(none declared)"] = \
            blocks.get(r["preregistration_block"] or "(none declared)", 0) + 1
    assigned = sum(v for k, v in blocks.items() if k != "(none declared)")
    print(f"  pre-registration blocks: {assigned}/{len(rows)} runs declared "
          f"({', '.join(f'{k}={v}' for k, v in sorted(blocks.items()) if k != '(none declared)')})")
    print(f"    the remaining {len(rows) - assigned} predate the pre-registration discipline and "
          f"genuinely belong to no block -- that is a fact about the campaign, not a gap to fill")
    if skipped:
        print(f"  skipped {len(skipped)} non-RAF-DB run families (scored elsewhere): "
              f"{', '.join(sorted(skipped)[:4])}{' ...' if len(skipped) > 4 else ''}")
    fams = {}
    for r in rows:
        fams[r["family"]] = fams.get(r["family"], 0) + 1
    for k, v in sorted(fams.items()):
        print(f"  {k:<22} {v}")


if __name__ == "__main__":
    main()
