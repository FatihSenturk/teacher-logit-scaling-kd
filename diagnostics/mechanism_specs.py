"""R2-3: Mekanizma spec eki — makine-üretimli, appendix tablosunun kaynağı.

Her mekanizma kolunun hiperparametreleri DEFTERDEKİ koşuların kendi `run_args.json`
dökümlerinden okunur (elle sayı yok); formül metinleri kod referanslıdır ve şu
dosyalardan doğrulanmıştır:

  kd_common.py        (DistillationLoss.forward: sabit harman satır 440,
                       gate harmanı 406-438, G2G ekleme noktası 453)
  kd_uncertainty.py   (gate: kaynaklar 14-92, normalizer 95-137, gate_alpha 140-146)
  kd_baselines.py     (logit_std 12-20, adaptive_t 23-38, GRL 41-52, CTKD 55-92)
  kd_g2g.py           (KL 16-36, W2 39-48, clamp 12-13, warmup 83-92)

Kapsam: runs.csv'deki RAF-DB kolları (mekanizma başına koşu sayısı tabloda).
Aynı koldaki koşular arasında bir anahtar farklı değer alıyorsa hepsi listelenir —
tekilleştirme yok, çeşitlilik görünür kalır.

Salt-okunur. Çıktı -> diagnostics/paper_tables/mechanism_specs.{md,json}
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A_RUNS = ROOT / "runs.csv"
# Level-1: mekanizma hiperparametreleri defterin yan dosyasından, koşu dizinlerinden değil.
A_MECH = ROOT / "diagnostics" / "paper_tables" / "run_mechanism_params.json"
MECH_PARAMS = (json.loads(A_MECH.read_text(encoding="utf-8"))["runs"]
               if A_MECH.exists() else {})
OUT_DIR = ROOT / "diagnostics" / "paper_tables"

# mekanizma -> (runs.csv manipulation eşleşmesi, run_args anahtarları)
MECHS = {
    "gate": (lambda m: m.startswith("gate"),
             ["gate_uncertainty_source", "gate_norm", "gate_alpha_lo", "gate_alpha_hi",
              "gate_k", "gate_tau"]),
    "adaptive_t": (lambda m: m == "adaptive_t" or m.endswith("+adaptive_t"),
                   ["adaptive_t_gamma"]),
    "g2g": (lambda m: m.startswith("g2g"),
            ["g2g_weight", "g2g_mode", "g2g_warmup_epochs"]),
    "logit_std": (lambda m: m == "logit_std", []),
    "ctkd": (lambda m: m == "ctkd",
             ["ctkd_t_min", "ctkd_t_max", "ctkd_grl_lambda_max", "lr"]),
}
COMMON_KEYS = ["temperature", "alpha", "teacher_temperature_scale"]

FORMULAS = {
    "gate": ("α_i = α_lo + (α_hi−α_lo)·sigmoid(k·(û_i − τ_g)); û_i = z-score(u_i) "
             "(gate_norm=batch: batch mean/std, eps 1e-6; running: EMA momentum 0.99, frozen "
             "at eval). Blend: loss_i = α_i·CE_i + (1−α_i)·KD_i — α_i is the HARD-label "
             "weight. Sources: mean/target/top2_logvar, entropy, oracle_error. "
             "ORACLE DIRECTION: if the teacher's top-1 is wrong then u_i=1 → û_i high → "
             "α_i→α_hi → on that sample the TEACHER's WEIGHT (1−α_i) is MINIMISED (a sample "
             "the teacher gets wrong is listened to less). "
             "[kd_uncertainty.py:51-66,140-146; kd_common.py:406-438]"),
    "adaptive_t": ("Per sample T_i = τ·(1 + γ·(H̃_i − mean(H̃))), H̃_i = H_i/log C, with H_i "
                   "computed at T=1 (so the definition is not circular); "
                   "clamp [1.0, 2τ]. [kd_baselines.py:23-38]"),
    "g2g": ("Additional term: loss += w·ramp(epoch)·mean_i KL(N(μ_t,σ_t²) ‖ N(μ_s,σ_s²)); "
            "CLASS-SPACE diagonal Gaussians (the head's 7/8-dimensional μ, logvar output — not "
            "an intermediate layer), summed over classes independently; logvar clamped to ±10; "
            "KL direction teacher‖student; STATELESS (no EMA or running statistics — the "
            "batch/running question does not arise). Where w applies: additively to the total "
            "loss, AFTER the α blend. [kd_g2g.py:16-36; kd_common.py:453]"),
    "logit_std": ("ẑ = (z − mean_c z)/(std_c z + ε), ε=1e-6, std unbiased=False, taken per "
                  "sample over the CLASS axis (dim=1); in the KD term ONLY, BEFORE the division "
                  "by T, on both the teacher and the student side (Sun et al. CVPR 2024). The "
                  "supervision term is untouched. [kd_baselines.py:12-20]"),
    "ctkd": ("A single GLOBAL learnable temperature: T = t_min + (t_max−t_min)·sigmoid(GRL(θ,λ)); "
             "θ initialised at 0 (so T starts mid-range), λ cosine-ramped 0→λ_max over epochs; "
             "the GRL flips the gradient by −λ in the backward pass (the direction that makes KD "
             "harder = the curriculum). θ is added to the main optimiser → the 'adversarial lr' "
             "is the run's own lr (in the table), AdamW, no separate optimiser. A single-scalar "
             "simplification of Li et al. AAAI 2023 (no per-sample MLP). [kd_baselines.py:41-92]"),
}


def fmt(v):
    if isinstance(v, float) and v == int(v):
        return str(int(v)) if abs(v) >= 1 else f"{v:g}"
    return f"{v:g}" if isinstance(v, float) else str(v)


def main():
    rows = [r for r in csv.DictReader(open(A_RUNS, encoding="utf-8"))]
    out, common_vals = {}, {k: {} for k in COMMON_KEYS}
    for mech, (match, keys) in MECHS.items():
        runs = [r for r in rows if match(r["manipulation"])]
        vals = {k: {} for k in keys}
        for r in runs:
            # Level-1 (8 Ağu): hiperparametreler artık defterin yan dosyasından okunuyor,
            # koşu dizininden DEĞİL. Değerler birebir aynı (`build_runs_ledger.py` onları
            # aynı `run_args.json`'lardan çıkarıyor), ama okuma yayımlanan bir artefakttan.
            ra = MECH_PARAMS.get(r["run_name"])
            if ra is None:
                raise RuntimeError(
                    f"{r['run_name']}: `paper_tables/run_mechanism_params.json` içinde yok. "
                    f"Defter bu yan dosya eklenmeden önce kurulmuş; "
                    f"`python diagnostics/build_runs_ledger.py` ile yeniden kurun.")
            for k in keys:
                vals[k].setdefault(fmt(ra.get(k)), []).append(r["run_name"])
            for k in COMMON_KEYS:
                common_vals[k].setdefault(fmt(ra.get(k, 1.0)), set()).add(mech)
        out[mech] = {"n_runs": len(runs),
                     "params": {k: sorted(v.keys()) for k, v in vals.items()},
                     "param_variants": {k: {vv: len(names) for vv, names in v.items()}
                                        for k, v in vals.items()},
                     "formula": FORMULAS[mech]}

    L = ["# R2-3 — Mechanism specification appendix (machine-generated)", "",
         "Producer: `diagnostics/mechanism_specs.py` · values read from the runs' own "
         "`run_args.json` dumps (no number is typed by hand) · formulas carry code references "
         "(file:line in every cell) · scope: the RAF-DB arms in runs.csv.", ""]
    for mech, o in out.items():
        L += [f"## {mech}  (n={o['n_runs']} runs)", "", o["formula"], ""]
        if o["params"]:
            L += ["| parameter | value(s) [n runs] |", "|---|---|"]
            for k, variants in o["param_variants"].items():
                vtxt = " · ".join(f"`{v}` [{n}]" for v, n in sorted(variants.items()))
                L.append(f"| `{k}` | {vtxt} |")
            L.append("")
        else:
            L += ["No tunable hyperparameter (ε=1e-6 is fixed in the code).", ""]

    L += ["## Common check (all mechanism runs)", "",
          "| key | value(s) → in which mechanisms |", "|---|---|"]
    for k, vals in common_vals.items():
        vtxt = " · ".join(f"`{v}` ({', '.join(sorted(m))})" for v, m in sorted(vals.items()))
        L.append(f"| `{k}` | {vtxt} |")
    exceptions = {k: {v: sorted(m) for v, m in vals.items() if len(vals) > 1}
                  for k, vals in common_vals.items() if len(vals) > 1}
    L += ["",
          "τ=6 and α=0.3 are expected throughout, as is `teacher_temperature_scale` 1.0 — the "
          "only known exception is the T0=0.7311 arms of the B-010 deliberate-miscalibration "
          "pilot (visible on the adaptive_t row; intentional, see BULGULAR B-010). If the table "
          "shows any other variation, that row must be carried into the appendix as an "
          "exception.", ""]

    payload = {"mechanisms": out,
               "common": {k: {v: sorted(m) for v, m in vals.items()}
                          for k, vals in common_vals.items()},
               "common_exceptions": exceptions}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "mechanism_specs.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (OUT_DIR / "mechanism_specs.json").write_text(json.dumps(payload, indent=2,
                                                             ensure_ascii=False),
                                                  encoding="utf-8")
    for mech, o in out.items():
        print(f"{mech:<11} n={o['n_runs']:<3} " +
              "  ".join(f"{k}={'/'.join(v)}" for k, v in o["params"].items()))
    print("ortak: " + "  ".join(f"{k}={'/'.join(sorted(v))}" for k, v in common_vals.items()))
    print(f"Wrote {OUT_DIR / 'mechanism_specs.md'}")


if __name__ == "__main__":
    main()
