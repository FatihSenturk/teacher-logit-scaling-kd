"""C2: refuse to ship a silently-changed table number.

WHAT THIS EXISTS TO CATCH, STATED PRECISELY. On 2026-07-30 a filter change moved T10's headline
ratio from 76x to 3x. No internal check could have caught it: 3x is a perfectly plausible ratio,
every cell was internally consistent, every sd was finite, and no exception was raised. The only
thing that identified it was comparison against a REMEMBERED EARLIER VALUE. Self-validation cannot
detect a plausible wrong answer; only a baseline can. So the baseline is made explicit and
mechanical here instead of living in whoever happens to remember last week's number.

THE TWO TRIGGERS (the second was the actual tell in the T10 case):
  1. VALUE MOVED beyond the cell's own seed sd. The cell's sd is the natural yardstick: a shift
     smaller than the noise the cell already carries is not a finding, and a shift larger than it
     is either a new result or a bug -- either way a human should look. Cells with no sd (n=1, or
     a derived scalar like an axis ratio) fall back to REL_TOL.
  2. n CHANGED. Unconditional, no threshold. In the T10 case n went 3 -> 7 and that alone was
     sufficient signal; a cell silently gaining samples means its membership predicate changed.
     A cell appearing or disappearing is reported the same way.

This gate does NOT decide whether a change is right -- it only guarantees nobody finds out later.
Adding runs legitimately moves numbers; the workflow is: regenerate, read the diff, then
`--accept` to move the baseline forward with a note saying why.

Usage:
  python diagnostics/table_diff_gate.py                    # compare, exit 1 on any deviation
  python diagnostics/table_diff_gate.py --accept "P2/P3 runs added; deltas reviewed"
  python diagnostics/table_diff_gate.py --show             # print the current baseline's provenance

Outputs -> diagnostics/table_diff_gate/baseline.json  (+ last_diff.md on every comparison)
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

# This script echoes Turkish reasons and cell labels; the Windows console defaults to cp1252 and
# would raise UnicodeEncodeError on the first "ş" -- after the baseline file had already been
# written, i.e. it would fail loudly while having half-succeeded.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "diagnostics"
OUT_DIR = D / "table_diff_gate"
OUT_DIR.mkdir(parents=True, exist_ok=True)
BASELINE = OUT_DIR / "baseline.json"
LAST_DIFF = OUT_DIR / "last_diff.md"

REL_TOL = 0.02   # fallback for cells with no sd: 2% relative, or 1e-4 absolute, whichever is larger
ABS_FLOOR = 1e-4


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def cells_from_tables(p):
    """T5 mechanism cells and T10 capacity cells + axis spans."""
    out = {}
    if not p.exists():
        return out
    d = json.loads(p.read_text(encoding="utf-8"))
    for key, row in d.get("T5_mechanisms", {}).items():
        for ck in ("swa", "best", "last"):
            c = row.get(ck)
            if not c or c.get("d_ece_mean") is None:
                continue
            out[f"T5/{key}/{ck}/d_acc"] = (c.get("d_acc_mean"), c.get("d_acc_sd"), c.get("n"))
            out[f"T5/{key}/{ck}/d_ece"] = (c.get("d_ece_mean"), c.get("d_ece_sd"), c.get("n"))
    for ck, cells in d.get("T10_capacity_cells", {}).items():
        for name, c in cells.items():
            out[f"T10/{name}/{ck}/acc"] = (c["acc_mean"], c["acc_sd"], c["n"])
            out[f"T10/{name}/{ck}/ece"] = (c["ece_mean"], c["ece_sd"], c["n"])
    for ck, s in d.get("T10_axis_spans", {}).items():
        for k, v in s.items():
            out[f"T10/axis/{ck}/{k}"] = (v, None, None)
    return out


def cells_from_capacity_law(p):
    out = {}
    if not p.exists():
        return out
    d = json.loads(p.read_text(encoding="utf-8"))
    sc = d.get("slope_comparison", {})
    for side in ("big", "small"):
        c = sc.get(side)
        if c:
            out[f"capacity_law/{side}/slope"] = (c["slope"], c.get("seed_noise_envelope"), None)
            out[f"capacity_law/{side}/r2"] = (c["r2"], None, None)
    if "slope_difference" in sc:
        out["capacity_law/slope_difference"] = (sc["slope_difference"],
                                               sc.get("combined_envelope"), None)
    return out


def cells_from_p2(p):
    out = {}
    if not p.exists():
        return out
    d = json.loads(p.read_text(encoding="utf-8"))
    for ck, c in d.get("by_checkpoint", {}).items():
        for arm in ("treat", "control"):
            a = c.get(arm, {})
            if a:
                out[f"P2/{arm}/{ck}/acc"] = (a["acc_mean"], a["acc_sd"], a["n"])
                out[f"P2/{arm}/{ck}/ece"] = (a["ece_mean"], a["ece_sd"], a["n"])
    for name, v in d.get("verdict", {}).items():
        if _num(v.get("measured")):
            out[f"P2/verdict/{name}/measured"] = (v["measured"], v.get("bar"), None)
    return out


def cells_from_headline(p):
    out = {}
    if not p.exists():
        return out
    h = json.loads(p.read_text(encoding="utf-8")).get("headline", {})
    if h:
        out["abstract/selection_optimism/d_acc"] = (h["d_acc_mean"], h["d_acc_sd"], h["n"])
        out["abstract/selection_optimism/d_ece"] = (h["d_ece_mean"], h["d_ece_sd"], h["n"])
    return out


def cells_from_dose_response(p):
    """T1-T4: the dose-response curves, i.e. the paper's central law.

    These were the first thing that should have been baselined and the last thing added -- the
    gate initially watched T5/T10 (where the two known defects happened) and left the core law
    unwatched, which is exactly the wrong bias: a gate should cover what matters most, not only
    where the last bug was.
    """
    out = {}
    if not p.exists():
        return out
    d = json.loads(p.read_text(encoding="utf-8"))
    for arm, a in d.get("arms", {}).items():
        for pt in a.get("points", []):
            T = pt.get("T")
            out[f"dose/{arm}/T={T:g}/teacher_ece"] = (pt["teacher_ece"], None, None)
            for ck, b in pt.get("by_ckpt", {}).items():
                out[f"dose/{arm}/T={T:g}/{ck}/student_ece"] = (b["ece_mean"], b.get("ece_sd"),
                                                               b.get("n"))
                if _num(b.get("acc_mean")):
                    out[f"dose/{arm}/T={T:g}/{ck}/student_acc"] = (b["acc_mean"], b.get("acc_sd"),
                                                                   b.get("n"))
    # HAVUZ ISTATISTIKLERI (17 Agu 2026, N14). `tab_pooled`'un uc sutunu da buradan basiliyor
    # ama kapi yalniz kol noktalarini izliyordu -- yani makalede duran alti korelasyon
    # korumasizdi. Pearson sutunu bugun uretildi; ayni gun kapiya da giriyor, cunku kayitsiz
    # artefakt korumasiz artefakttir.
    for ck, s in (d.get("pooled_stats") or {}).items():
        if not isinstance(s, dict):
            continue
        for stat in ("spearman_abs_signed_gap", "spearman_signed_gap",
                     "pearson_abs_signed_gap", "pearson_signed_gap"):
            if _num(s.get(stat)):
                out[f"dose/pooled/{ck}/{stat}"] = (s[stat], None, s.get("n_points"))
    return out


def cells_from_split_identity(p):
    """Bolme kimligi: her veri kumesinin egitim/raporlama orneklem sayilari.

    Bu sayilar makalenin §4'unde basili (15.339 / 12.271 / 3.068 / 28.259 / 3.153). Kapiya
    girmeleri gerekir: bir gun bir fold beyani degisirse tablo sessizce kaymasin.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for name, s in d.get("datasets", {}).items():
        tag = name.replace(" ", "_")
        out[f"split/{tag}/n_train"] = (s.get("n_train"), None, None)
        out[f"split/{tag}/n_reporting"] = (s.get("n_reporting"), None, None)
        out[f"split/{tag}/rows_total"] = (s.get("rows_total"), None, None)
        out[f"split/{tag}/n_partitions"] = (s.get("n_partitions_in_metadata"), None, None)
        for k, v in (s.get("reporting_per_class") or {}).items():
            out[f"split/{tag}/per_class/{k}"] = (v, None, None)
    return out


def cells_from_r3_robustness(p):
    """R3-1: yedi metriğin doz-cevap değerleri (kol ortalamaları) + adım tutarlılığı.

    Bu blok olmadan R3 sayıları kapının DIŞINDA kalırdı: tablo yeniden üretildiğinde
    bir metrik sessizce kayabilir ve hiçbir şey bağırmazdı. Yeni bir tablo eklemek,
    onu buraya da eklemek demektir.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for sname, s in d.get("series", {}).items():
        tag = sname.replace(" ", "_")
        for met, pm in s.get("metrics", {}).items():
            for T, mu in pm.get("mean", {}).items():
                out[f"R3-1/{tag}/{met}/T={T}"] = (mu, pm.get("sd", {}).get(T),
                                                 len(pm.get("by_seed", {})))
            out[f"R3-1/{tag}/{met}/steps"] = (pm.get("steps_consistent"), None,
                                              pm.get("steps_total"))
            # 18 Agu: minimumun YERI de kapiya girdi. `argmin_T_modal` cogunlugun,
            # `argmin_T_all_seeds` HER tohumun koydugu yer (oybirligi yoksa None ve hucre
            # dusurulur -- bir sonraki kosuda VANISHED olarak bagirir, sessizce kaymaz).
            out[f"R3-1/{tag}/{met}/argmin_T_modal"] = (pm.get("argmin_T_modal"), None, None)
            if pm.get("argmin_T_all_seeds") is not None:
                out[f"R3-1/{tag}/{met}/argmin_T_all_seeds"] = (pm["argmin_T_all_seeds"],
                                                               None, None)
        # Uzlasi sayaci: makalede `tab:app_argmin`'in "7/7" sutunu.
        out[f"R3-1/{tag}/consensus_T"] = (s.get("_consensus_T"), None, None)
        out[f"R3-1/{tag}/metrics_agreeing"] = (s.get("_consensus_metrics_agreeing"), None,
                                               s.get("_n_metrics"))
    return out


def cells_from_r3_tstar(p):
    """R3-2: dört öğretmenin iki T* değeri ve iki ECE farkı."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for tag, r in d.get("results", {}).items():
        for k in ("T_star_nll", "T_star_ece", "abs_dT", "d_ece", "ece_removed_by_ts"):
            out[f"R3-2/{tag}/{k}"] = (r.get(k), None, None)
        # KANONIK vs TEYIT blogu (17 Agu, N14): ayni niceligi hesaplayan ikinci uygulama ile
        # farki, ve AMAC FONKSIYONUNDAKI fark. Kayitli olmasi sart -- teyidin kendisi kayar da
        # kimse gormezse teyit degil gozlem olur.
        x = r.get("cross_fit") or {}
        for k in ("confirm_T_star", "abs_dT", "d_nll", "d_ece"):
            if k in x:
                out[f"R3-2/{tag}/cross_fit/{k}"] = (x[k], None, None)
    return out


def cells_from_r3_jsd(p):
    """R3-3: her kesitin üç optimumu ve n'i."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for name, r in d.get("results", {}).items():
        if not r.get("n"):
            continue
        tag = name.replace(" ", "_")
        for k in ("T_ece", "T_nll", "T_jsd"):
            out[f"R3-3/{tag}/{k}"] = (r.get(k), None, r.get("n"))
    return out


def cells_from_p6(p):
    """P6 resmî hükmü: çift ΔECE'leri (T11) ve α gap'leri (T12) + üç hüküm.

    P6.1 hücreleri erken okumanın (2 Ağu) sayılarıyla aynı olmalı; kapı bunu ayrıca
    kayıt altına alır — biri ileride önbelleği tazelerse APPEARED değil MOVED görünür.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for pname, v in d.get("p6_1", {}).get("pairs", {}).items():
        tag = pname.replace(" ", "_").replace("·", "x")
        out[f"P6.1/{tag}/mean_dECE"] = (v.get("mean"), v.get("sd"),
                                        len(v.get("per_seed", {})))
        for s, ps in v.get("per_seed", {}).items():
            out[f"P6.1/{tag}/seed{s}/dECE"] = (ps.get("d_ece"), None, None)
        out[f"P6.1/{tag}/status"] = (v.get("status"), None, None)
    for a, row in d.get("grid2_cells", {}).items():
        for s, c in row.items():
            out[f"P6.2/alpha={a}/seed{s}/gap"] = (c.get("gap"), None, None)
    out["P6.2/verdict"] = (d.get("p6_2", {}).get("verdict"), None,
                           d.get("p6_2", {}).get("n_seeds_ok"))
    out["P6.3/verdict"] = (d.get("p6_3", {}).get("verdict"), None,
                           d.get("p6_3", {}).get("n_seeds_ok"))
    return out


def cells_from_r3w1(p):
    """R3-W1: dört kolun TS öncesi/sonrası iki ekseni + köşe işgali (ön-kayıt A11)."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for T, a in d.get("arms", {}).items():
        for k in ("ece_arm", "jsd_arm", "ece_ts", "jsd_ts"):
            mean, sd = a[k]
            out[f"R3W1/T={T}/{k}"] = (mean, sd, 3)
    for T, o in d.get("occupancy", {}).items():
        out[f"R3W1/T={T}/occupies"] = (o.get("occupies"), None, None)
    c = d.get("corner", {})
    out["R3W1/corner/ECE_min"] = (c.get("ECE_min"), None, None)
    out["R3W1/corner/JSD_min"] = (c.get("JSD_min"), None, None)
    out["R3W1/verdict"] = (d.get("verdict"), None, None)
    return out


def cells_from_selection_inference(p):
    """G2.1: dört kontrastın iki metrikte ortalama/SE/t/p'si."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for ds, dv in d.get("datasets", {}).items():
        for con, cv in dv.get("contrasts", {}).items():
            for met in ("acc_pp", "ece"):
                r = cv[met]
                out[f"G2.1/{ds}/{con}/{met}/mean"] = (r.get("mean"), r.get("sd"), r.get("n"))
                out[f"G2.1/{ds}/{con}/{met}/t"] = (r.get("t"), None, r.get("df"))
                out[f"G2.1/{ds}/{con}/{met}/p"] = (r.get("p"), None, None)
    return out


def cells_from_monotonicity(p):
    """G2.2: üç eksenin geçen-tohum sayıları + hücre başına ✓/✗."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for axis, (ok, tot) in d.get("summary", {}).items():
        out[f"G2.2/summary/{axis}"] = (ok, None, tot)
    for sname, s in d.get("series", {}).items():
        tag = sname.replace(" ", "_")
        for sd, cell in s.get("seeds", {}).items():
            out[f"G2.2/{tag}/seed{sd}/a"] = (cell["a_T_axis"]["ok"], None, None)
            out[f"G2.2/{tag}/seed{sd}/b"] = (cell["b_signed_gap_within_branch"]["ok"], None, None)
            out[f"G2.2/{tag}/seed{sd}/c"] = (cell["c_unsigned_gap_pooled"]["ok"], None, None)
    return out


def cells_from_criterion(p):
    """G3.1/G3.2: her hücrenin iki paydayla oranı ve hükmü + aile-bazlı FPR."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for cell, by_ck in d.get("cells", {}).items():
        v = (by_ck.get("swa") or {}).get("ece")
        if not v or not v.get("n"):
            continue
        out[f"G3.1/{cell}/ratio_ctrl"] = (v.get("ratio_vs_control_sd"), None, v.get("n"))
        out[f"G3.1/{cell}/ratio_paired"] = (v.get("ratio_vs_paired_sd"), None, v.get("n"))
        out[f"G3.1/{cell}/verdict"] = (v.get("verdict"), None, None)
    f = d.get("fpr", {})
    out["G3.2/k_observed_median"] = (f.get("k_observed_median"), None, f.get("n_cells"))
    out["G3.2/per_cell_fpr"] = (f.get("per_cell_at_observed_k"), None, None)
    out["G3.2/family_wise"] = (f.get("family_wise_upper_bound"), None, f.get("n_cells"))
    # N19b (20 Agu): §4.7'nin bes sayisi. Bunlar makalede BASILI ve artik kapali formdan
    # geliyor -- yani bir daha degisirlerse sebep MC gurultusu OLAMAZ, ya aile degismistir
    # ya olcut. Ikisi de sessiz gecmemeli.
    s = d.get("false_positive_simulation", {})
    for key in ("per_cell_rate_at_median_k", "family_wise_at_median_k", "family_wise_at_own_k",
                "family_wise_with_shared_component", "independence_gap_own_k_minus_shared",
                "rho_shared_control", "rho_other_pairs"):
        out[f"G3.2/sim/{key}"] = (s.get(key), None, s.get("n_family_cells"))
    out["G3.2/sim/n_family_cells"] = (s.get("n_family_cells"), None, None)
    return out


def cells_from_run_manifest_census(p):
    """§4.8'in dort sayisi + PENCERE ETIKETI. Etiket de hucre: sayim degisip etiket
    degismezse (ya da tersi) sapma olarak gorunsun."""
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {f"RMC/{k}": (d.get(k), None, d.get("n_manifests"))
           for k in ("n_manifests", "n_code_state_verified", "n_retroactive_unverified",
                     "n_unfinished")}
    out["RMC/window_label"] = ((d.get("window") or {}).get("label"), None, None)
    out["RMC/checksum_ok"] = (str(d.get("checksum_ok")), None, None)
    return out


def cells_from_prereg_lead(p):
    """S11 Lead sutununun alti degeri + iki saglama sayaci. Lead'ler HAM saniye olarak
    hucre olur; makale tarafi floor'lanmis halini basar, sapma burada gorunur."""
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {f"PL/{b}_lead_s": (d["items"][b]["lead_seconds"], None, None)
           for b in d["lead_bearing_rows"]}
    out["PL/n_annotation_checked"] = (d["summary"]["n_annotation_checked"], None, None)
    out["PL/n_runs_csv_checked"] = (d["summary"]["n_runs_csv_checked"], None, None)
    return out


def cells_from_reliability(p):
    """§5.1'in iki sayisi: en yuksek guven kutusundaki kutle, iki kosulda."""
    d = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for cond, v in (d.get("conditions") or {}).items():
        tb = v.get("top_bin") or {}
        out[f"REL/{cond}/top_bin_share_pct"] = (tb.get("share_pct"), None, tb.get("n_pooled"))
        out[f"REL/{cond}/top_bin_n"] = (tb.get("n"), None, tb.get("n_pooled"))
    return out


def cells_from_g3(p):
    """G3.3/G3.4/G3.5: Holm p'leri, TOST hukumleri, bootstrap CI ucları."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for r in d.get("rows", []):                      # holm_family
        out[f"G3.3/{r['name']}/p_raw"] = (r.get("p_raw"), None, r.get("n"))
        out[f"G3.3/{r['name']}/p_holm"] = (r.get("p_holm"), None, r.get("n"))
    for t in d.get("tests", []):                     # equivalence_tests
        out[f"G3.4/{t['name']}/mean"] = (t.get("mean"), t.get("sd"), t.get("n"))
        out[f"G3.4/{t['name']}/p_tost"] = (t.get("p_tost"), None, None)
        out[f"G3.4/{t['name']}/class"] = (t.get("class"), None, None)
    for k, v in (d.get("results") or {}).items():    # bootstrap_cis
        if k == "pooled_rho":
            out["G3.5/rho/point"] = (v.get("point"), None, v.get("n_points"))
            for tag in ("ci95_cluster_bootstrap", "ci95_naive_point_bootstrap"):
                lo, hi = v[tag]
                out[f"G3.5/rho/{tag}/lo"] = (lo, None, None)
                out[f"G3.5/rho/{tag}/hi"] = (hi, None, None)
            continue
        for q, val in (v.get("point") or {}).items():
            if isinstance(val, (int, float)):
                out[f"G3.5/{k}/{q}"] = (val, None, v.get("point", {}).get("n_val"))
        for q, (lo, hi) in (v.get("ci95") or {}).items():
            out[f"G3.5/{k}/{q}/ci_lo"] = (lo, None, None)
            out[f"G3.5/{k}/{q}/ci_hi"] = (hi, None, None)
    return out


def cells_from_g4(p):
    """G4.1/4.4/4.5/4.6/4.7 -- panel tablo ve sayi duzeltmeleri.

    NEDEN SONRADAN EKLENDI (7 Agu 2026). Bu bes artefakt 7 Agu'da uretildi ama SOURCES'a
    kaydedilmedi; kapi her kosuda "702/702 sapma yok" dedi ve bu DOGRUYDU -- ama yeni tablolar
    icin BOSTU, cunku hic okunmuyorlardi. Kapinin var olma sebebi tam olarak buydu (76x -> 3x
    olayinda hicbir ic kontrol hatayi gormemisti); kayitsiz bir tablo korumasiz bir tablodur.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    item = d.get("item", p.stem)

    for c in d.get("comparisons", []):                       # G4.1 asimetri
        tag = f"{c['arm']}/{c['idx']}"
        out[f"G4.1/{tag}/ratio_absolute"] = (c.get("ratio_absolute"), None, None)
        out[f"G4.1/{tag}/ratio_excess"] = (c.get("ratio_excess"), None, None)
        for k in ("ci_absolute", "ci_excess"):
            if c.get(k):
                out[f"G4.1/{tag}/{k}/lo"] = (c[k][0], None, None)
                out[f"G4.1/{tag}/{k}/hi"] = (c[k][1], None, None)

    for ck, r in (d.get("by_checkpoint") or {}).items():     # G4.4 verim
        out[f"G4.4/{ck}/acc_mean"] = (r.get("acc_mean"), r.get("acc_sd"), r.get("n"))
        out[f"G4.4/{ck}/retention_pct"] = (r.get("retention_pct"), None, r.get("n"))

    for k, g in (d.get("nine_cell_grid") or {}).items():     # G4.5 gurultu birimi
        if not g:
            continue
        out[f"G4.5/{k}/ratio"] = (g.get("ratio"), None, g.get("n"))
        out[f"G4.5/{k}/d_ece_mean"] = (g.get("d_ece_mean"), g.get("d_ece_sd"), g.get("n"))
    for ck, q in (d.get("pooled") or {}).items():
        for stat in ("median", "mean", "min"):
            out[f"G4.5/pooled/{ck}/{stat}"] = (q.get(stat), None, q.get("n_cells"))
    # OZET ISTATISTIKLER (17 Agu 2026, N14). `tab_logitstd` alt yazisinin bastigi 27x (medyan),
    # 52x (ortalama) ve 2.6x (taban) tam olarak bu blokta yasiyor; kapi dokuz hucreyi izlerken
    # OZETI izlemiyordu, yani makaleye giren uc sayi korumasizdi.
    if item == "G4.5" and isinstance(d.get("summary"), dict):   # G4.5 dokuz hucrenin ozeti
        for stat in ("median", "mean", "min", "max"):
            out[f"G4.5/summary/{stat}"] = (d["summary"].get(stat), None,
                                           d["summary"].get("n_cells"))
    if item == "G4.1":                                       # G4.1 asimetri ozeti
        for grp, gv in (d.get("summary") or {}).items():
            for est, ev in (gv or {}).items():
                for stat in ("mean", "sd", "min", "max"):
                    out[f"G4.1/summary/{grp}/{est}/{stat}"] = (ev.get(stat), None, ev.get("n"))

    if item == "G4.6":                                       # G4.6 denetim populasyonu
        out["G4.6/off_standard_count"] = (d.get("off_standard_count"), None, d.get("n_total"))
        for b, s in (d.get("selection_optimism_by_budget") or {}).items():
            out[f"G4.6/{b}/d_acc_mean"] = (s.get("d_acc_mean"), s.get("d_acc_sd"), s.get("n"))
            out[f"G4.6/{b}/d_ece_mean"] = (s.get("d_ece_mean"), s.get("d_ece_sd"), s.get("n"))

    # G4.7'nin OLCULEN fitleri (17 Agu, N14). `tab_dose_response` blok basliklari ve alt yazisi
    # tam bu iki sozlukten basiliyor (1.35 / 1.3494 / 1.3406 / 0.98); kapi bugune kadar yalniz
    # `deployed` satirlarini okuyordu.
    for blk in ("full_fold_fits", "half_fold_fits"):
        for t, v in (d.get(blk) or {}).items():
            out[f"G4.7/{blk}/{t}"] = (v, None, None)
    for r in d.get("deployed", []):                          # G4.7 T* kokeni
        if r.get("kind", "").startswith("FİT") and r.get("fit_value") is not None:
            out[f"G4.7/T={r['T']:g}/fit_value"] = (r["fit_value"], None, r.get("n_runs"))
            out[f"G4.7/T={r['T']:g}/source"] = (r.get("source_key"), None, None)
    return out


def cells_from_a12(p):
    """A12 -- gercek-sinyal gate hucreleri n=3.

    NEDEN KAYITLI (8 Agu). A12'nin hukmu EXPORTS'ta yayimlanan bir artefakt ama SOURCES'a
    girmemisti; yani bes hucrenin orani ve ortalamasi kapinin gormedigi sayilardi. G4'te
    tam bu olmustu ("702/702 sapma yok" dogru ama bos). Kayitsiz tablo korumasiz tablodur.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for c in d.get("cells", []):
        tag = f"{c['teacher']}/{c['signal']}"
        for ck in ("swa", "best", "last"):
            blk = c.get(ck) or {}
            for axis in ("ece", "acc"):
                j = blk.get(axis) or {}
                if j.get("mean") is None:
                    continue
                out[f"A12/{tag}/{ck}/{axis}/mean"] = (j.get("mean"), j.get("sd"), j.get("n"))
                out[f"A12/{tag}/{ck}/{axis}/ratio"] = (j.get("ratio"), None, j.get("n"))
    for b in d.get("bar_check", []):
        out[f"A12/bar/{b['teacher']}/ece_sd"] = (b.get("ece_measured"), None, b.get("n"))
        out[f"A12/bar/{b['teacher']}/acc_sd"] = (b.get("acc_measured"), None, b.get("n"))
    return out


def cells_from_a13(p):
    """A13 -- 2.248 M scratch doz-yanitinin uc egimi ve uc karsilastirmasi."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for name, f in (d.get("fits") or {}).items():
        out[f"A13/fit/{name}/slope"] = (f.get("slope"), None, None)
        out[f"A13/fit/{name}/envelope"] = (f.get("envelope"), None, None)
        out[f"A13/fit/{name}/r2"] = (f.get("r2"), None, None)
        for i, (m, s) in enumerate(zip(f.get("cell_ece_mean") or [],
                                       f.get("cell_ece_sd") or [])):
            out[f"A13/fit/{name}/cell{i}/ece"] = (m, s, None)
    for c in d.get("comparisons", []):
        key = c["name"].replace(" ", "_")
        out[f"A13/cmp/{key}/d_slope"] = (c.get("d_slope"), None, None)
        out[f"A13/cmp/{key}/envelope"] = (c.get("combined_envelope"), None, None)
    return out


def cells_from_g42(p):
    """G4.2 -- kaldirac orani, baslatma eslestirilmis. Iki oran da korunur."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for r in d.get("rows", []):
        if r.get("status") != "tam":
            continue
        ck = r["ckpt"]
        for k in ("capacity_span", "teacher_span_pretrained", "teacher_span_scratch",
                  "ratio_published", "ratio_init_matched"):
            out[f"G4.2/{ck}/{k}"] = (r.get(k), None, None)
    return out


def cells_from_mechanism_specs(p):
    """Mekanizma spesifikasyonları: her mekanizmanın n'i ve her parametrenin varyant dağılımı.

    NEDEN SONRADAN EKLENDI (8 Agu 2026, T3). `run_mechanism_params.json` yan dosyasi ayni gun
    dogdu: defter koşu dizinlerinden 199 kosu x 18 anahtar cikariyor, `mechanism_specs.py` de
    artik onu okuyor. Yani YENI bir artefakt yayima girdi ve hicbir kapi onu okumuyordu -- 7
    Agu'da G4'te ve ayni gun A12/A13/G4.2'de yasanan bosluğun aynisi ("kayitsiz bir tablo
    korumasiz bir tablodur").

    HAM YAN DOSYA DEGIL, TUREVI kaydedildi. 199 x 18 ham hucre kapinin hucre sayisini 885'ten
    ~4500'e cikarir ve denetim sayisini seyreltirdi; makaleye giren buyukluk zaten bu turev
    tablodur. SINIR ACIKCA: yan dosyada, mekanizma tablosunda GECMEYEN bir kosunun degeri
    sessizce degisirse bu kapi kimildamaz -- ama oyle bir degisiklik makalede hicbir sayiyi da
    oynatmaz, ki kapinin gorevi orasi.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for mech, m in d.get("mechanisms", {}).items():
        out[f"MECH/{mech}/n_runs"] = (m.get("n_runs"), None, None)
        for param, variants in (m.get("param_variants") or {}).items():
            for val, k in variants.items():
                out[f"MECH/{mech}/{param}={val}"] = (k, None, m.get("n_runs"))
    for param, by_val in (d.get("common") or {}).items():
        for val, mechs in by_val.items():
            out[f"MECH/common/{param}={val}"] = (len(mechs), None, None)
    return out


def cells_from_logit_manifest(p):
    """42 yayımlanmış logit önbelleğinin sha256'sı + defterin özdeşlik sayacı.

    NEDEN (8 Agu 2026). Bu 42 dosya bugun yayima girdi ve R3-1 ile R3-W1'in butun sayilari
    onlardan uretiliyor. Bir kopya sessizce degisirse iki tablonun hucreleri de kayar (kapi
    onu zaten yakalar), ama o zaman NEDENI aramak gerekir. sha256'lari birer hucre olarak
    kaydetmek nedeni dogrudan gosterir: dosya mi degisti, boru hatti mi.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    out["LOGITS/total"] = (d.get("total"), None, d.get("total_bytes"))
    out["LOGITS/identical"] = (d.get("identical"), None, d.get("total"))
    for run, r in (d.get("runs") or {}).items():
        out[f"LOGITS/{run}/sha256"] = (r.get("sha256"), None, r.get("bytes"))
    return out


def cells_from_selection_gain(p):
    """T8'in sıra-istatistiği kolonları (K=50/100) + denetim delta özetleri.

    NEDEN SONRADAN EKLENDI (9 Agu 2026). Bu artefakt yayimliydi, `RESULTS_TABLES.md` T8'in
    kaynak satirinda aniliyordu, ama SOURCES'a kayitli DEGILDI -- ve BAYAT cikti: icindeki
    sayilar 105 kosuluk bir populasyondan uretilmisti, kampanya 199'a buyumustu ve hicbir sey
    bagirmadi. Kapinin kendi kurali ("kayitsiz bir tablo korumasiz bir tablodur") burada
    ikinci kez, bu kez BAYATLIK uzerinden dogrulandi: kayitli olsaydi populasyon 105'ten
    199'a ciktigi gun MOVED verirdi.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    # İKİ POPÜLASYON DA KAYITLI (9 Ağu). `per_k` birincil (donmuş denetim kümesi),
    # `per_k_rafdb_all` robustluk satırı. İkisi de yayımlanıyor, dolayısıyla ikisi de
    # kapıya girer -- yayımlanan ama izlenmeyen blok bırakmıyoruz.
    for blk, tag in (("per_k", "T8"), ("per_k_rafdb_all", "T8w")):
        for k, r in (d.get(blk) or {}).items():
            out[f"{tag}/K={k}/n_runs"] = (r.get("n_runs"), None, None)
            out[f"{tag}/K={k}/argmax_in_last_K"] = (r.get("argmax_in_last_K_frac"), None,
                                                    r.get("n_runs"))
            # 20 Agu: oranin PAYI da hucre. Oran ayni kalip pay/payda birlikte kayabilir
            # (populasyon degisirse); ikisini ayri izlemek o hali gorunur kilar.
            out[f"{tag}/K={k}/argmax_in_last_K_count"] = (
                r.get("argmax_in_last_K_count"), None, r.get("argmax_in_last_K_denominator"))
            for met in ("a1_max_all_minus_mean_lastK", "a2_pure_order_statistic",
                        "val_loss_at_selected_minus_mean_lastK"):
                v = r.get(met) or {}
                out[f"{tag}/K={k}/{met}"] = (v.get("mean"), v.get("sd"), r.get("n_runs"))
    for name, r in (d.get("audit_deltas") or {}).items():
        for met in ("d_acc", "d_ece"):
            v = r.get(met) or {}
            out[f"T8/{name}/{met}"] = (v.get("mean"), v.get("sd"), r.get("n"))
    return out


def cells_from_p4(p):
    """T6/T6a: öğretmen-seçim tarifesi -- üç checkpoint'te öğrenci doğruluğu, ρ'lar, maliyet.

    NEDEN SONRADAN EKLENDI (13 Agu 2026, N5). Bu artefakt T6'yi besliyor ve T6 makalede
    "teacher selection recipe" olarak geciyor -- ama SOURCES'a kayitli DEGILDI. Sonucu somut:
    ogrenci sayilari BAYAT bir yan tablodan (`seed_variance_table.json`, mtime 2026-07-28,
    anonim T-A/T-B/T-C etiketli) geliyordu ve stage1 hucresi defterden 0.011 pp sapiyordu;
    yayimlanan "0.53 pp" tam bu sapmadan dogdu. Hucreler kayitli olsaydi defter degistigi gun
    MOVED verirdi. Ucuncu kez ayni ders: kayitsiz bir tablo korumasiz bir tablodur.

    CHECKPOINT BASINA AYRI HUCRE. "Maliyet" tek bir sayi degil: @swa 0.35 / @best 0.52 /
    @last 0.83. Tek hucreye sikistirmak, N5'in acmak zorunda kaldigi karisikligin ta kendisi
    olurdu -- hangi checkpoint'in kaydigi gorunmez kalirdi.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    r3 = d.get("recipe_step3_ranking") or {}
    for row in r3.get("rows", []):
        t = row["teacher"]
        for k in ("teacher_acc", "teacher_ece", "T_star", "teacher_headroom"):
            out[f"T6/{t}/{k}"] = (row.get(k), None, None)
        for ck, c in (row.get("student_by_ckpt") or {}).items():
            out[f"T6a/{t}/{ck}/student_acc"] = (c.get("acc_mean"), c.get("acc_sd"), c.get("n"))
            out[f"T6a/{t}/{ck}/student_ece"] = (c.get("ece_mean"), c.get("ece_sd"), c.get("n"))
    pc = r3.get("per_checkpoint") or {}
    for ck, v in (pc.get("by_ckpt") or {}).items():
        out[f"T6a/{ck}/cost_wrong_pick"] = (v.get("cost_of_wrong_pick_pp"), None, None)
        out[f"T6a/{ck}/rho_teacherACC"] = (v.get("spearman_teacherACC_vs_studentACC"), None, None)
        out[f"T6a/{ck}/rho_negTeacherECE"] = (v.get("spearman_negTeacherECE_vs_studentACC"),
                                              None, None)
        out[f"T6a/{ck}/ranking"] = (v.get("ranking_display"), None, None)
        out[f"T6a/{ck}/best_teacher"] = (v.get("best_teacher"), None, None)
        out[f"T6a/{ck}/strict_total_order"] = (v.get("strict_total_order"), None, None)
    out["T6a/best_identical_all_ckpts"] = (pc.get("best_teacher_identical_across_ckpts"),
                                           None, None)
    out["T6a/ranking_identical_all_ckpts"] = (pc.get("ranking_identical_across_ckpts"), None, None)
    out["T6a/n_pairwise_reversals"] = (len(pc.get("pairwise_reversals") or []), None, None)
    return out


def cells_from_order_stat_trend(p):
    """R2-4/5: pencere içi trend -- ham/de-trend a2, eğim, sürüklenme, VE ÇAPANIN KENDİSİ.

    NEDEN SONRADAN EKLENDI (9 Agu 2026, ayni gunun ikinci vakasi). Bu artefakt §5.6'nin
    DE-TREND edilmis a2 cift'ini tasiyor, `export_to_drive` ile Drive'a gidiyor ve genel depoda
    yayimlaniyor -- ama SOURCES'a kayitli DEGILDI. `selection_gain.json` ile birebir ayni sinif:
    yayimli, makalede alintilanan, korumasiz. Bugun capa yeniden hedeflenirken ortaya cikti:
    "capayi cevirince kapida 1 MOVED gorurum" beklentisi TUTMADI, cunku kapi bu dosyayi hic
    okumuyordu. Kapinin kendi kurali ucuncu kez dogrulandi: kayitsiz bir tablo korumasiz bir
    tablodur.

    CAPA HUCRELERI DE KAYITLI (`published_a2`, `anchor_dev`, `anchor_population_matches`).
    Sebep somut: 9 Agu'da capa ANCHOR_TOL=0.02 ile bir populasyon uyusmazligini maskeledi. Bir
    esik gevsetilirse ya da capa baska bir populasyona geri alinirsa, bunlar artik hucre olarak
    kayar -- yani "denetim aracinin kendisi sessizce zayiflatildi" olayi da MOVED verir.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for k, r in (d.get("results") or {}).items():
        n = r.get("n_runs")
        for key, blk in (("a2_raw", "a2_raw"), ("a2_detrended", "a2_detrended"),
                         ("slope", "slope_pp_per_epoch"), ("drift", "window_drift_pp")):
            v = r.get(blk) or {}
            out[f"OST/K={k}/{key}"] = (v.get("mean"), v.get("sd"), n)
        out[f"OST/K={k}/published_a2"] = (r.get("published_a2"), None, n)
        out[f"OST/K={k}/anchor_dev"] = (r.get("anchor_dev"), None, n)
        out[f"OST/K={k}/anchor_pop_matches"] = (r.get("anchor_population_matches"), None, None)
    out["OST/growth_raw"] = (d.get("growth_raw"), None, None)
    out["OST/growth_detrended"] = (d.get("growth_detrended"), None, None)
    return out


def cells_from_epoch_curves(p):
    """Epok-eğrisi yan dosyasının bütünlük sayaçları -- 4 hücre, koşu başına satır DEĞİL.

    NEDEN SADECE 4 (9 Agu). 199 kosu icin ayri hucre acmak kapinin hucre sayisini ~200
    artirip denetim sayisini seyreltirdi ve hicbir sey kazandirmazdi: bir egri degisirse
    `order_stat_trend` ve `selection_gain` hucreleri zaten kayar. Buradaki dort sayi NEDENI
    gosterir -- dosya mi degisti (sha256/bayt), populasyon mu degisti (kosu/satir sayisi).
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for k in ("n_runs", "n_epoch_rows", "npz_bytes"):
        out[f"CURVES/{k}"] = (d.get(k), None, None)
    out["CURVES/npz_sha256"] = (d.get("npz_sha256"), None, d.get("n_runs"))
    return out


# Okunamayan kaynaklar icin BEYAN listesi -- bkz. main()'deki hata-sinifi blogu. Bos kalmasi
# hedeftir: bir kaynak eksikse ya uretilecek ya SOURCES'tan cikarilacak.
DECLARED_MISSING = set()

def cells_from_round3(p):
    """Round-3 (14 Agu) artefaktlari: B2/B3/B4/B6/B7/B8/B9/B10.

    NEDEN AYNI GUN KAYDEDILIYOR. Bu turun kendi bulgusu tam olarak buydu: N5'te bayat bir
    yan tablo haftalarca yasadi cunku kapiya kayitli degildi. Yeni uretilen yedi artefakt
    ayni gun kaydediliyor -- kayit, uretimin bir sonraki adimi degil, PARCASI.

    Tek fonksiyon, dosya adina gore dagitim: yedi ayri cikarici yazmak ayni deseni yedi kez
    tekrarlardi ve biri gunun birinde digerlerinden ayrilirdi.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    name = p.stem

    if name == "control_sd_mde":                              # B3(a) + B6
        for r in d.get("rows", []):
            tag = f"{r['checkpoint']}/{r['teacher']}/{r['class_weight_mode']}/{r['axis']}"
            out[f"B3/{tag}/control_sd"] = (r.get("control_sd"), None, r.get("n"))
            out[f"B6/{tag}/mde_2sd"] = (r.get("mde_2sd"), None, r.get("n"))
            out[f"B6/{tag}/mde_pct"] = (r.get("mde_pct_of_level"), None, r.get("n"))
        out["B3/n_family_denominators"] = (d.get("n_family_denominators"), None, None)

    elif name == "tau_t_factorial":                           # B4
        for k, a in (d.get("arms") or {}).items():
            out[f"B4/{k}/ece_mean"] = (a.get("ece_mean"), a.get("ece_sd"), a.get("n"))
            out[f"B4/{k}/acc_mean"] = (a.get("acc_mean"), a.get("acc_sd"), a.get("n"))
        for c in (d.get("matched_pairs") or []) + (d.get("marginal_contrasts") or []):
            out[f"B4/{c['label']}/d_ece"] = (c.get("d_ece_mean"), c.get("d_ece_sd"),
                                             c.get("n"))
            out[f"B4/{c['label']}/d_acc"] = (c.get("d_acc_mean"), c.get("d_acc_sd"),
                                             c.get("n"))
            out[f"B4/{c['label']}/ece_signs"] = (c.get("ece_signs"), None, c.get("n"))

    elif name == "mechanism_grid_gaps":                       # B9
        out["B9/n_cells"] = (d.get("n_cells"), None, None)
        out["B9/n_empty"] = (d.get("n_empty"), None, None)
        for g in d.get("gaps", []):
            out[f"B9/{g['teacher']}/{g['mechanism']}/class"] = (g.get("class"), None, None)
        for s in d.get("outside_budget", []):
            out[f"B9/{s['teacher']}/{s['mechanism']}/n_in_grid"] = (
                s.get("n_in_grid"), None, None)
            out[f"B9/{s['teacher']}/{s['mechanism']}/n_in_ledger"] = (
                s.get("n_in_ledger"), None, None)

    elif name == "dose_response_per_seed":                    # B8
        out["B8/n_curves"] = (d.get("n_curves"), None, None)
        out["B8/n_rho_positive"] = (d.get("n_rho_positive"), None, None)
        out["B8/n_strictly_monotone_in_T"] = (d.get("n_strictly_monotone_in_T"), None, None)
        for c in d.get("seed_curves", []):
            tag = f"{c['arm']}/seed{c['seed']}"
            out[f"B8/{tag}/rho_T"] = (c.get("rho_T_vs_ece"), None, c.get("n_points"))
            out[f"B8/{tag}/span"] = (c.get("span"), None, c.get("n_points"))

    elif name == "ferplus_abstention_entropy":                # B7
        out["B7/mean_entropy_conditional_8"] = (d.get("mean_entropy_conditional_8"),
                                                None, d.get("n_val"))
        out["B7/mean_entropy_with_abstention_10"] = (
            d.get("mean_entropy_with_abstention_10"), None, d.get("n_val"))
        out["B7/rows_with_abstention"] = (d.get("rows_with_abstention"), None,
                                          d.get("n_val"))
        for tag, key in (("conditional_8", "T_star_jsd_conditional_8"),
                         ("abstention_10", "T_star_jsd_with_abstention_10")):
            b = d.get(key) or {}
            out[f"B7/{tag}/T_star_jsd"] = (b.get("T"), None, d.get("n_val"))
            out[f"B7/{tag}/mean_jsd"] = (b.get("mean_jsd"), None, d.get("n_val"))

    elif name == "regression_line_provenance":                # B2
        for ck, v in (d.get("ferplus") or {}).items():
            out[f"B2/ferplus/{ck}/slope"] = (v.get("slope"), None, v.get("n_runs"))
            out[f"B2/ferplus/{ck}/intercept"] = (v.get("intercept"), None, v.get("n_runs"))
            out[f"B2/ferplus/{ck}/pearson"] = (v.get("pearson"), None, v.get("n_runs"))
            out[f"B2/ferplus/{ck}/r2_9runs"] = (
                (v.get("fit_on_9_runs") or {}).get("r2"), None, v.get("n_runs"))
        r = d.get("rafdb") or {}
        out["B2/rafdb/producer_found"] = (r.get("producer_found"), None, None)
        out["B2/rafdb/slope_range_lo"] = ((r.get("slope_range") or [None])[0], None, None)
        out["B2/rafdb/slope_range_hi"] = ((r.get("slope_range") or [None, None])[1],
                                          None, None)

    elif name == "number_audit_round3":                       # B10
        for i, r in enumerate(d.get("rows", []), 1):
            out[f"B10/{i:02d}/verdict"] = (r.get("verdict"), None, None)
            out[f"B10/{i:02d}/measured"] = (r.get("measured"), None, None)

    return out


def cells_from_headroom_audit(p):
    """N11 (15 Agu) — FERPlus headroom'un UC izgaradaki degeri, CI'lari ve sinir tanisi.

    Neden kayitli: bu tablo "hangi sayi makaleye girer"i belirliyor. Izgaralardan biri
    (bootstrap_cis.T_GRID) degisirse headroom sessizce kayar; kapinin gormesi gereken tam
    olarak budur.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for gk, r in (d.get("grids") or {}).items():
        out[f"N11/{gk}/headroom"] = (r.get("headroom"), None, r["grid"]["n"])
        out[f"N11/{gk}/T_argmin"] = (r.get("T_argmin"), None, r["grid"]["n"])
        out[f"N11/{gk}/ece_at_argmin"] = (r.get("ece_at_argmin"), None, r["grid"]["n"])
        out[f"N11/{gk}/ci_lo"] = (r["ci95"][0], None, None)
        out[f"N11/{gk}/ci_hi"] = (r["ci95"][1], None, None)
        out[f"N11/{gk}/grid_lo"] = (r["grid"]["lo"], None, None)
        out[f"N11/{gk}/grid_hi"] = (r["grid"]["hi"], None, None)
        out[f"N11/{gk}/on_bound"] = (str(r.get("argmin_at_lower_bound")
                                         or r.get("argmin_at_upper_bound")), None, None)
        out[f"N11/{gk}/boot_frac_lo"] = (r.get("boot_frac_argmin_at_lower_bound"), None, None)
    for name, b in (d.get("boot_grid_boundary_by_teacher") or {}).items():
        out[f"N11/boundary/{name}/T"] = (b.get("T_argmin_on_boot_grid"), None, b.get("n_val"))
        out[f"N11/boundary/{name}/at_bound"] = (str(b.get("at_lower_bound")
                                                    or b.get("at_upper_bound")), None, None)
    t = d.get("ferplus_T_star_ece") or {}
    for k in ("continuous_argmin", "fine_grid_argmin", "boot_grid_point"):
        out[f"N11/tstar/{k}"] = (t.get(k), None, None)
    out["N11/tstar/truncated"] = (str(t.get("truncated")), None, None)
    out["N11/max_abs_dev"] = (d.get("max_abs_dev"), None, None)
    v = d.get("verdict") or {}
    out["N11/verdict/primary_number"] = (v.get("primary_number"), None, None)
    out["N11/verdict/primary_T"] = (v.get("primary_T"), None, None)
    return out


def cells_from_number_ledger(p):
    """N13 (17 Agu) — sayi provenans defterinin SAYIMLARI ve turetilmis nicelikleri.

    Neden kayitli: defterin kapsami sessizce daralirsa (bir tablo kapsam disina kayar, bir
    muafiyet genisler) makale korumasiz kalir ama hicbir sey hata vermez. Kapida duran sey
    tek tek 590 hucre degil -- KAPSAMIN KENDISI: jeton/bagli/muaf/KAYITSIZ sayilari ve her
    turetilmis niceligin yeniden hesaplanmis degeri.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for k, v in (d.get("counts") or {}).items():
        out[f"N13/count/{k}"] = (v, None, None)
    for e in d.get("prose_entries") or []:
        out[f"N13/prose/{e['id']}"] = (e.get("exact"), None, None)
    # TEYIT KAYITLARI (17 Agu, N14): iki kaynagin degeri, ayrismasi ve ESIGI. Esik makalenin
    # kendi hassasiyetinden turetiliyor, yani tablolar daha cok basamak basmaya baslarsa esik
    # KENDILIGINDEN siklasir -- o degisimin kapida gorunmesi gerekir.
    for e in d.get("cross_checks") or []:
        out[f"N13/xcheck/{e['id']}/canonical"] = (e["canonical"]["value"], None, None)
        out[f"N13/xcheck/{e['id']}/confirm"] = (e["confirm"]["value"], None, None)
        out[f"N13/xcheck/{e['id']}/abs_diff"] = (e.get("abs_diff"), None, None)
        out[f"N13/xcheck/{e['id']}/tolerance"] = (e.get("tolerance"), None, None)
        out[f"N13/xcheck/{e['id']}/ok"] = (int(bool(e.get("matches"))), None, None)
    out["N13/unbound_ids"] = (len(d.get("unbound") or []), None, None)
    return out


def cells_from_derived_registry(p):
    """N13 turetilmis nicelikler: her oran/fark yeniden hesaplanmis degeriyle kapida."""
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    for e in d.get("entries") or []:
        out[f"N13/derived/{e['id']}"] = (e.get("exact"), None, None)
        out[f"N13/derived/{e['id']}/ok"] = (str(e.get("matches")), None, None)
    return out


def cells_from_jsd_collapse(p):
    """N12 (17 Agu) — JSD çöküşü: tek pay, iki payda (TS-sonrası açıklık ve tohum sd'si).

    Neden kayıtlı: makalede iki cümle var, paylari ayni, paydalari FARKLI ve ikisi de dort
    basamakta 0.0005 basiliyor. Payda sessizce kayarsa (kol eklenir, tohum eklenir, TS
    protokolu degisir) iki oran birbirine daha da yaklasir ya da uzaklasir ve metindeki 37/40
    ayrimi kapiya gorunmeden bozulur. Kapinin gormesi gereken tam olarak bu iki paydadir.
    """
    out = {}
    d = json.loads(p.read_text(encoding="utf-8"))
    n = d.get("n_val")
    for T, a in (d.get("arms") or {}).items():
        for k in ("jsd_raw", "jsd_ts", "ece_raw", "ece_ts"):
            out[f"N12/arm/{T}/{k}"] = (a[k][0], a[k][1], n)
    num = d.get("numerator") or {}
    out["N12/numerator"] = (num.get("value"), None, n)
    out["N12/numerator/arms"] = (f"{num.get('arm_hi')}-{num.get('arm_lo')}", None, None)
    rc = d.get("R_collapse") or {}
    out["N12/R_collapse"] = (rc.get("value"), None, n)
    out["N12/R_collapse/denominator"] = (rc.get("denominator"), None, n)
    out["N12/R_collapse/per_seed_mean"] = (rc.get("per_seed_mean"), rc.get("per_seed_sd"), 3)
    out["N12/R_collapse/denominator_bar"] = (rc.get("denominator_bar"), None, None)
    out["N12/R_collapse/denom_within_noise"] = (str(rc.get("denominator_within_noise")),
                                                None, None)
    rn = d.get("R_noise") or {}
    for k, v in (rn.get("by_convention") or {}).items():
        out[f"N12/R_noise/{k}"] = (v, None, n)
    for k, v in (rn.get("seed_sd_by_convention") or {}).items():
        out[f"N12/seed_sd/{k}"] = (v, None, n)
    tr = d.get("rounding_trap") or {}
    out["N12/trap/ratio_from_printed"] = (tr.get("ratio_from_printed"), None, None)
    out["N12/trap/denom_for_exactly_40"] = (tr.get("denominator_that_gives_exactly_40"),
                                            None, None)
    out["N12/max_abs_dev"] = (d.get("max_abs_dev"), None, None)
    v = d.get("verdict") or {}
    out["N12/verdict/collapse_printed"] = (v.get("R_collapse_printed"), None, None)
    out["N12/verdict/noise_printed"] = (v.get("R_noise_printed"), None, None)
    return out


SOURCES = [
    (D / "epoch_curves_MANIFEST.json", cells_from_epoch_curves),
    (D / "paper_tables" / "headroom_grid_audit.json", cells_from_headroom_audit),
    (D / "paper_tables" / "jsd_collapse_audit.json", cells_from_jsd_collapse),
    (D / "paper_tables" / "number_ledger.json", cells_from_number_ledger),
    (D / "paper_tables" / "derived_registry.json", cells_from_derived_registry),
    (D / "paper_tables" / "prereg_lead_audit.json", cells_from_prereg_lead),
    (D / "paper_tables" / "control_sd_mde.json", cells_from_round3),
    (D / "paper_tables" / "tau_t_factorial.json", cells_from_round3),
    (D / "paper_tables" / "mechanism_grid_gaps.json", cells_from_round3),
    (D / "paper_tables" / "dose_response_per_seed.json", cells_from_round3),
    (D / "paper_tables" / "ferplus_abstention_entropy.json", cells_from_round3),
    (D / "paper_tables" / "regression_line_provenance.json", cells_from_round3),
    (D / "paper_tables" / "number_audit_round3.json", cells_from_round3),
    (D / "selection_audit" / "selection_gain.json", cells_from_selection_gain),
    (D / "paper_tables" / "order_stat_trend.json", cells_from_order_stat_trend),
    (D / "p4_teacher_selection" / "p4_teacher_selection.json", cells_from_p4),
    (D / "paper_tables" / "mechanism_specs.json", cells_from_mechanism_specs),
    (D / "student_logits" / "MANIFEST.json", cells_from_logit_manifest),
    (D / "p1_dose_response" / "two_dataset_overlay.json", cells_from_dose_response),
    (D / "a12_realsignal_gate" / "a12_verdict.json", cells_from_a12),
    (D / "a13_scratch_dose" / "a13_verdict.json", cells_from_a13),
    (D / "paper_tables" / "g42_init_matched_lever.json", cells_from_g42),
    (D / "paper_tables" / "RESULTS_TABLES.json", cells_from_tables),
    (D / "paper_tables" / "robustness_metrics.json", cells_from_r3_robustness),
    (D / "paper_tables" / "split_identity.json", cells_from_split_identity),
    (D / "paper_tables" / "tstar_sensitivity.json", cells_from_r3_tstar),
    (D / "paper_tables" / "jsd_sensitivity.json", cells_from_r3_jsd),
    (D / "paper_tables" / "p6_collapse_test.json", cells_from_p6),
    (D / "paper_tables" / "r3w1_joint_optimum.json", cells_from_r3w1),
    (D / "paper_tables" / "selection_audit_inference.json", cells_from_selection_inference),
    (D / "paper_tables" / "monotonicity_test.json", cells_from_monotonicity),
    (D / "paper_tables" / "criterion_applied.json", cells_from_criterion),
    (D / "paper_tables" / "holm_family.json", cells_from_g3),
    (D / "paper_tables" / "equivalence_tests.json", cells_from_g3),
    (D / "paper_tables" / "bootstrap_cis.json", cells_from_g3),
    (D / "paper_tables" / "asymmetry_estimand.json", cells_from_g4),
    (D / "paper_tables" / "efficiency_retention.json", cells_from_g4),
    (D / "paper_tables" / "noise_units.json", cells_from_g4),
    (D / "paper_tables" / "audit_population.json", cells_from_g4),
    (D / "paper_tables" / "tstar_provenance.json", cells_from_g4),
    (D / "p5_efficiency" / "capacity_law_check.json", cells_from_capacity_law),
    (D / "p2_gate_oracle" / "p2_verdict.json", cells_from_p2),
    (D / "selection_audit" / "selection_optimism_headline.json", cells_from_headline),
    # --- N19b (20 Agu): son 23 kayitsizin bagi acilan iki artefakt. "Kayitsiz bir tablo
    # korumasiz bir tablodur" -- yayima girdikleri gun kapiya da giriyorlar.
    (D / "paper_tables" / "run_manifest_census.json", cells_from_run_manifest_census),
    (D / "reliability" / "reliability_diagram.json", cells_from_reliability),
]


def collect():
    cells, missing = {}, []
    for path, fn in SOURCES:
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
            continue
        cells.update(fn(path))
    return cells, missing


def tolerance(sd, value):
    """The cell's own seed sd, or a relative fallback when it has none."""
    if _num(sd) and sd > 0:
        return sd, "1x cell sd"
    return max(abs(value) * REL_TOL, ABS_FLOOR), f"{REL_TOL:.0%} rel (no sd)"


def compare(cur, base):
    changed, n_changed, appeared, vanished = [], [], [], []
    for k, (v, sd, n) in sorted(cur.items()):
        if k not in base:
            appeared.append(k)
            continue
        bv, bsd, bn = base[k]
        if n != bn:
            n_changed.append((k, bn, n, bv, v))
            continue
        if _num(v) and _num(bv):
            tol, why = tolerance(sd if _num(sd) else bsd, v)
            if abs(v - bv) > tol:
                changed.append((k, bv, v, v - bv, tol, why))
        elif v != bv:
            # SAYI OLMAYAN HÜCRELER DE KARŞILAŞTIRILIR (9 Ağu 2026).
            #
            # Eski koşul `_num(v) and _num(bv)` ile başlıyordu, yani hüküm/durum hücreleri
            # (`P6.2/verdict`, `G3.4/.../class`, `P6.1/.../status`, sha256 dizgileri) tabana
            # YAZILIYOR ama hiç KIYASLANMIYORDU: "GEÇTİ" -> "DÜŞTÜ" dönmesi kapıyı
            # kımıldatmazdı. Kaydedilip kıyaslanmayan hücre yalnızca görünüşte korunur --
            # bu turun kuralının ("hata sınıfı boş değilken GEÇTİ raporlanmaz") aynı ailesi.
            # Bugün somut gerekçesi var: `anchor_population_matches` bir bool ve çapanın
            # popülasyonu geri alınırsa değişecek tek alan o.
            changed.append((k, bv, v, None, None, "tam eşitlik (sayı olmayan hücre)"))
    for k in sorted(base):
        if k not in cur:
            vanished.append(k)
    return changed, n_changed, appeared, vanished


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accept", metavar="REASON",
                    help="bless the current numbers as the new baseline, recording why")
    ap.add_argument("--show", action="store_true", help="print the baseline's provenance and exit")
    args = ap.parse_args()

    cur, missing = collect()
    if not cur:
        raise SystemExit("no numbers collected -- are the table artifacts generated?")

    if args.show:
        if not BASELINE.exists():
            raise SystemExit("no baseline yet")
        b = json.loads(BASELINE.read_text(encoding="utf-8"))
        print(f"baseline accepted {b['accepted_at']}\n  reason: {b['reason']}\n"
              f"  cells : {len(b['cells'])}")
        return

    if args.accept or not BASELINE.exists():
        reason = args.accept or "initial baseline (no prior version on disk)"
        BASELINE.write_text(json.dumps({
            "accepted_at": dt.datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "sources": [str(p.relative_to(ROOT)) for p, _ in SOURCES],
            "cells": {k: list(v) for k, v in cur.items()},
        }, indent=2), encoding="utf-8")
        print(f"baseline written: {len(cur)} cells\n  reason: {reason}")
        if missing:
            print("  NOTE missing sources (not in baseline): " + ", ".join(missing))
        return

    b = json.loads(BASELINE.read_text(encoding="utf-8"))
    base = {k: tuple(v) for k, v in b["cells"].items()}
    changed, n_changed, appeared, vanished = compare(cur, base)

    L = ["# Table diff gate — last comparison", "",
         f"Baseline: **{b['accepted_at']}** — {b['reason']}  ",
         f"Cells compared: {len(cur)} ({len(base)} in the baseline)", ""]
    # A cell can legitimately carry no value (a verdict-only row, or an axis that was
    # "EKSİK" when the baseline was taken). Formatting that as a float raised TypeError and
    # killed the whole gate -- i.e. a reporting bug in the gate silently became "the gate
    # cannot run", which is the worst failure mode for a stop-gate. Render None as "—".
    def num(x, prec=4, sign=False):
        if x is None:
            return "—"
        if not _num(x):
            return str(x)          # hüküm/durum/sha256 hücreleri artık kıyaslanıyor (bkz. compare)
        return f"{x:{'+' if sign else ''}.{prec}f}"

    if n_changed:
        L += ["## ⚠️ n CHANGED (unconditional warning — a cell's membership rule may have moved)",
              "", "| cell | n old→new | value old | value new |", "|---|---|---|---|"]
        for k, bn, n, bv, v in n_changed:
            L.append(f"| `{k}` | {bn}→{n} | {num(bv)} | {num(v)} |")
        L.append("")
    if changed:
        L += ["## Value moved by more than its own seed sd", "",
              "| cell | old | new | diff | threshold | source of the threshold |",
              "|---|---|---|---|---|---|"]
        for k, bv, v, d, tol, why in changed:
            L.append(f"| `{k}` | {num(bv)} | {num(v)} | {num(d, sign=True)} | "
                     f"{num(tol)} | {why} |")
        L.append("")
    if appeared or vanished:
        L += ["## Cells appeared / vanished", ""]
        if appeared:
            L.append("**appeared:** " + ", ".join(f"`{k}`" for k in appeared))
        if vanished:
            L.append("**vanished:** " + ", ".join(f"`{k}`" for k in vanished))
        L.append("")
    if not (changed or n_changed or appeared or vanished):
        L.append("✅ No deviation — every cell is at its baseline value.")
    LAST_DIFF.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"baseline {b['accepted_at']}  ({b['reason']})")
    print(f"cells: {len(cur)} now, {len(base)} in baseline")
    for k, bn, n, bv, v in n_changed:
        print(f"  n CHANGED  {k}: n {bn}->{n}, value {num(bv)} -> {num(v)}")
    for k, bv, v, d, tol, why in changed:
        print(f"  MOVED      {k}: {num(bv)} -> {num(v)}  "
              f"({num(d, sign=True)}, tol {num(tol)} = {why})")
    for k in appeared:
        print(f"  APPEARED   {k}")
    for k in vanished:
        print(f"  VANISHED   {k}")
    # HATA SINIFI BOŞ DEĞİLKEN GEÇTİ RAPORLANMAZ (9 Ağu 2026 kuralı, Fatih).
    #
    # Bu blok eskiden `NOTE missing sources: ...` yazıp ARDINDAN "No deviation: every cell
    # matches the accepted baseline" diyor ve çıkış kodu 0 döndürüyordu. Eksik bir kaynak
    # "sapma yok" DEĞİL, "o kaynağın hücreleri hiç okunmadı" demek -- Level-1 kapısındaki
    # `başka hata` sütununun tam eşdeğeri, ve orada 8 Ağu'da tam bu yüzden üç gerçek ihlal
    # gizlenmişti. Kayıtsız artefakt korumasız artefakttır; OKUNAMAYAN artefakt da öyle.
    #
    # DECLARED_MISSING bilerek boş: bir kaynak eksikse ya üretilecek ya SOURCES'tan
    # çıkarılacak. "Şimdilik yok" gerekçe değildir.
    undeclared_missing = [m for m in missing if m not in DECLARED_MISSING]
    if missing:
        print("  NOTE missing sources: " + ", ".join(missing))

    total = len(changed) + len(n_changed) + len(appeared) + len(vanished)
    if total:
        print(f"\n{total} deviation(s). Read {LAST_DIFF.relative_to(ROOT)}, then re-run with "
              f'--accept "why" once you have checked each one.')
        sys.exit(1)
    if undeclared_missing:
        print(f"\n!! {len(undeclared_missing)} SOURCES entry could not be read, and none is "
              f"declared. The gate does NOT report a pass:")
        for m in undeclared_missing:
            print(f"     {m}")
        print("   Either produce the artefact or remove it from SOURCES. A source that cannot "
              "be read is a source whose cells were never checked.")
        sys.exit(1)
    print("\nNo deviation: every cell matches the accepted baseline.")


if __name__ == "__main__":
    main()
