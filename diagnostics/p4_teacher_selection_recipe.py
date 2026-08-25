"""P4: an actionable teacher-SELECTION recipe based on teacher ECE, not teacher accuracy.

THE PRACTICAL PROBLEM. You have K candidate teachers and one GPU. Choosing by distilling a
student from each costs K x (4h+). Choosing by teacher accuracy is free -- and, on this
benchmark, WRONG: the most accurate teacher is not the best teacher.

THE RECIPE (all steps inference-only, no student training):
  1. Forward each candidate over the val split ONCE; cache logits.
  2. Compute ECE(T=1) and fit T* (NLL-optimal) from the cached logits -- closed form, free.
  3. RANK BY ECE, NOT ACCURACY.
  4. Read off the teacher-side headroom ECE(T=1) - ECE(T*). If it is meaningfully positive,
     distil with --teacher-temperature-scale T*: a free student-calibration gain that costs
     nothing at train time and does not touch architecture or recipe.
  5. Optionally predict the student's ECE before training it, via the fitted transfer relation
     below, to decide whether the candidate is worth a run at all.

This file quantifies steps 3 and 5 and reports the GPU cost the recipe avoids.

HONEST SCOPE: fitted on RAF-DB only, K=3 teachers for the ranking claim and 10 (teacher-ECE,
student-ECE) pairs from 2 teachers for the predictor. These are small n. The ranking claim is
reported as a rank correlation with its exact n, and the predictor is reported with
leave-one-out error, not in-sample error. Cross-dataset validation is NOT claimed.

Outputs -> diagnostics/p4_teacher_selection/
"""
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "diagnostics"))
from paper_tables import (A_AUDIT_MECH, CKPTS, TEACHERS, is_ablation_control,  # noqa: E402
                          load_audit, load_runs)
from stats_convention import SD_CONVENTION, sample_sd  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "p4_teacher_selection"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TEACHER_GRID = json.loads((ROOT / "diagnostics" / "teacher_ece_grid" / "teacher_ece_grid.json").read_text())
OVERLAY = ROOT / "diagnostics" / "p1_dose_response" / "two_teacher_overlay.json"

# ÖĞRENCİ SAYILARI ARTIK DEFTERDEN, ÜÇ CHECKPOINT'TE (N5, 13 Ağu 2026).
#
# ÖNCEKİ HÂL VE NEDEN DEĞİŞTİ. Bu dosya öğrenci doğruluğunu
# `seed_variance/seed_variance_table.json`'dan okuyordu (`T-A/T-B/T-C baseline` anahtarlarıyla).
# O tablonun üç kusuru vardı ve üçü birden N5'in sorduğu çelişkiyi üretti:
#   1. TEK CHECKPOINT. İçindeki sayılar `best_checkpoint.pth`ten, yani @best. Makale ise
#      birincil checkpoint olarak @swa kullanıyor. "Seçim maliyeti 0.53 pp" @best'in değeri;
#      @swa'da aynı büyüklük 0.35. İki sayı da doğruydu, ikisi de aynı isimle anılıyordu.
#   2. BAYAT. mtime 2026-07-28, yani P1/P2/P3/P4'ten önce; stage1 hücresi 89.7436 diyor,
#      defterin aynı kolu @best'te 89.7545 -- 0.011 pp fark, ve yayımlı 0.53 tam bu farktan
#      geliyor (doğrusu 0.5215).
#   3. ANONİM ETİKET. `T-A/T-B/T-C` hangi öğretmen olduğu dosyadan geri kurtarılamıyordu;
#      eşleme burada elle yapılıyordu. Aynı gerekçeyle `paper_tables.py` 2026-07-31'de T5a'nın
#      paydasını bu dosyadan koparmıştı -- P4 o temizlikte atlanmış.
#
# Yeni kaynak: kanonik defter (`runs.csv`) + seçim denetimi, kolun tanımı
# `paper_tables.is_ablation_control` ile İTHAL (yeniden yazılmıyor) + `cw=effective_number`.
# Bu kural doğrulandı: stage1 ve vae9182 için ürettiği koşu kümesi `p1_two_teacher_overlay`in
# T=1.00 satırlarıyla BİREBİR aynı, dolayısıyla T1/T2'nin yayımlı @swa değerlerini
# (89.60±0.34 / 89.95±0.37) tam olarak yeniden üretiyor. primary'nin aynı biçimli kolu da
# üç tohumlu ve T1/T2 tablolarında olmadığı için N5'te eksik olan sayı buydu.
CW_MODE = "effective_number"
# Measured wall-clock for one 400e student KD run on this machine (RTX 5070), from the
# dose-response queue timings: ~4.3 h solo-equivalent per run.
HOURS_PER_STUDENT_RUN = 4.3


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    dx, dy = [a - mx for a in x], [b - my for b in y]
    den = (sum(a * a for a in dx) * sum(b * b for b in dy)) ** 0.5
    return sum(a * b for a, b in zip(dx, dy)) / den if den else float("nan")


def spearman(x, y):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        i = 0
        while i < len(order):           # average ranks over ties
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r
    return pearson(rank(x), rank(y))


def linfit(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((a - mx) ** 2 for a in x)
    b = sum((a - mx) * (c - my) for a, c in zip(x, y)) / sxx
    return my - b * mx, b            # intercept, slope


def student_by_ckpt():
    """teacher -> checkpoint -> {acc/ece mean, sd, n} for the T=1 baseline arm, from the ledger."""
    runs, audit = load_runs(), load_audit(A_AUDIT_MECH)
    out = {}
    for t in TEACHERS:
        keys = [k for k, r in runs.items()
                if r["teacher"] == t and is_ablation_control(r)
                and r["class_weight_mode"] == CW_MODE]
        if not keys:
            raise RuntimeError(f"{t}: no T=1 baseline arm in the ledger — the selection rule or "
                               f"the ledger changed; DO NOT fall back to a second source.")
        cells = {}
        for ck in CKPTS:
            accs = [audit[k + (ck,)]["acc"] for k in keys if k + (ck,) in audit]
            eces = [audit[k + (ck,)]["ece"] for k in keys if k + (ck,) in audit]
            if not accs:
                continue
            cells[ck] = {"acc_mean": st.mean(accs), "acc_sd": sample_sd(accs),
                         "ece_mean": st.mean(eces), "ece_sd": sample_sd(eces), "n": len(accs)}
        out[t] = {"by_ckpt": cells,
                  "runs": sorted(k[0] for k in keys)}
    return out


def per_checkpoint_verdict(rows, students):
    """N5: the same three questions asked at EVERY checkpoint, not just at @best.

    The T6 note used to ASSERT "the ranking is identical at all three checkpoints" with nothing
    computing it. It is now computed, ties included -- a tie is not an identical ranking and the
    difference has to be visible rather than rounded away.
    """
    t_acc = {r["teacher"]: r["teacher_acc"] for r in rows}
    t_ece = {r["teacher"]: r["teacher_ece"] for r in rows}
    pick_acc = max(t_acc, key=t_acc.get)          # what teacher-accuracy would choose
    pick_ece = min(t_ece, key=t_ece.get)          # what teacher-ECE would choose
    out = {"picked_by_accuracy": pick_acc, "picked_by_ece": pick_ece, "by_ckpt": {}}
    for ck in CKPTS:
        got = {t: students[t]["by_ckpt"][ck] for t in TEACHERS if ck in students[t]["by_ckpt"]}
        if len(got) < len(TEACHERS):
            continue
        s_acc = {t: v["acc_mean"] for t, v in got.items()}
        order = sorted(s_acc, key=lambda t: -s_acc[t])
        best = order[0]
        # Beraberlik SESSİZ GEÇMEZ: iki ortalama tam eşitse sıralama bir tam sıra değildir.
        ties = [(a, b) for i, a in enumerate(order) for b in order[i + 1:]
                if s_acc[a] == s_acc[b]]
        out["by_ckpt"][ck] = {
            "student_acc": s_acc,
            "ranking": order,
            "ties": [list(p) for p in ties],
            "strict_total_order": not ties,
            "best_teacher": best,
            "spearman_teacherACC_vs_studentACC":
                spearman([t_acc[t] for t in TEACHERS], [s_acc[t] for t in TEACHERS]),
            "spearman_negTeacherECE_vs_studentACC":
                spearman([-t_ece[t] for t in TEACHERS], [s_acc[t] for t in TEACHERS]),
            "accuracy_criterion_correct": pick_acc == best,
            "ece_criterion_correct": pick_ece == best,
            "cost_of_wrong_pick_pp": s_acc[best] - s_acc[pick_acc],
        }
    cks = list(out["by_ckpt"])
    # "SIRALAMA ÜÇÜNDE DE AYNI" BERABERLİK VARKEN SÖYLENEMEZ. `sorted` beraberlikte girdi
    # sırasını koruduğu için tam eşit iki ortalama YİNE de bir sıra üretir -- ama o sıra
    # keyfîdir. Bu yüzden iddia iki parçaya ayrılıyor: (a) sıralama her checkpoint'te TAM SIRA
    # mı, (b) tam sıra olanlar birbirinin aynısı mı. Makaledeki "identical at all three
    # checkpoints" cümlesi tam olarak burada kırılıyor.
    strict = [c for c in cks if out["by_ckpt"][c]["strict_total_order"]]
    out["ckpts_with_ties"] = [c for c in cks if c not in strict]
    out["ranking_identical_among_strict_ckpts"] = (
        len({tuple(out["by_ckpt"][c]["ranking"]) for c in strict}) == 1 if strict else None)
    out["ranking_identical_across_ckpts"] = (
        len(strict) == len(cks) and out["ranking_identical_among_strict_ckpts"] is True)
    # Beraberlik keyfî sırayı gizlemesin diye okunabilir gösterim: eşitler küme içinde.
    for c in cks:
        v = out["by_ckpt"][c]
        acc = v["student_acc"]
        groups, seen = [], set()
        for t in v["ranking"]:
            if t in seen:
                continue
            eq = [u for u in v["ranking"] if acc[u] == acc[t]]
            seen.update(eq)
            groups.append(eq[0] if len(eq) == 1 else "{" + " = ".join(eq) + "}")
        v["ranking_display"] = " > ".join(groups)
    out["best_teacher_identical_across_ckpts"] = (
        len({out["by_ckpt"][c]["best_teacher"] for c in cks}) == 1)
    # Bir ikili karşılaştırma checkpoint'ler arasında YÖN DEĞİŞTİRİYOR MU? Dış denetimin
    # iddiası buydu; mekanik olarak sınanır, elle göz kararı değil.
    rev = []
    for i, a in enumerate(TEACHERS):
        for b in TEACHERS[i + 1:]:
            signs = {(1 if out["by_ckpt"][c]["student_acc"][a] > out["by_ckpt"][c]["student_acc"][b]
                      else -1 if out["by_ckpt"][c]["student_acc"][a] < out["by_ckpt"][c]["student_acc"][b]
                      else 0) for c in cks}
            if {1, -1} <= signs:
                rev.append([a, b])
    out["pairwise_reversals"] = rev
    return out


def step3_ranking():
    """Would accuracy-ranking or ECE-ranking have picked the right teacher?"""
    students = student_by_ckpt()
    rows = []
    for t in TEACHERS:
        g = TEACHER_GRID[t]
        # T6'nın mevcut sütunları @best; geriye uyumluluk için o değerler bu adlarla kalıyor,
        # üç checkpoint'in tamamı `by_ckpt` altında.
        b = students[t]["by_ckpt"]["best"]
        rows.append({"teacher": t, "teacher_acc": g["own_acc_pct"], "teacher_ece": g["ece_T1"],
                     "T_star": g["T_star"],
                     "teacher_headroom": g["ece_T1"] - min(g["fine_sweep"].values()),
                     "student_acc": b["acc_mean"], "student_ece": b["ece_mean"],
                     "student_acc_sd": b["acc_sd"], "n_seeds": b["n"],
                     "student_by_ckpt": students[t]["by_ckpt"],
                     "arm_runs": students[t]["runs"]})
    t_acc = [r["teacher_acc"] for r in rows]
    t_ece = [r["teacher_ece"] for r in rows]
    s_acc = [r["student_acc"] for r in rows]
    s_ece = [r["student_ece"] for r in rows]
    # Higher teacher acc should mean higher student acc; LOWER teacher ECE should mean higher
    # student acc, so negate ECE to make "bigger = predicted better" for both criteria.
    out = {
        "rows": rows,
        "spearman_teacherACC_vs_studentACC": spearman(t_acc, s_acc),
        "spearman_negTeacherECE_vs_studentACC": spearman([-e for e in t_ece], s_acc),
        "spearman_teacherECE_vs_studentECE": spearman(t_ece, s_ece),
        "n_teachers": len(rows),
    }
    best_by_acc = max(rows, key=lambda r: r["teacher_acc"])["teacher"]
    best_by_ece = min(rows, key=lambda r: r["teacher_ece"])["teacher"]
    truly_best = max(rows, key=lambda r: r["student_acc"])["teacher"]
    out.update({"picked_by_accuracy": best_by_acc, "picked_by_ece": best_by_ece,
                "actually_best": truly_best,
                "accuracy_criterion_correct": best_by_acc == truly_best,
                "ece_criterion_correct": best_by_ece == truly_best,
                "cost_of_wrong_pick_pp": max(r["student_acc"] for r in rows)
                                         - next(r["student_acc"] for r in rows if r["teacher"] == best_by_acc),
                "student_source": "runs.csv + selection audit, T=1 baseline arm "
                                  f"(is_ablation_control, cw={CW_MODE}); columns above are @best",
                "primary_checkpoint": "swa"})
    out["per_checkpoint"] = per_checkpoint_verdict(rows, {r["teacher"]: {"by_ckpt": r["student_by_ckpt"]}
                                                          for r in rows})
    return out


def step5_predictor():
    """Predict student ECE from teacher ECE, leave-one-out. Uses the dose-response points,
    where teacher ECE was MANIPULATED rather than merely observed."""
    if not OVERLAY.exists():
        return {"available": False, "reason": "two_teacher_overlay.json not built yet"}
    curves = json.loads(OVERLAY.read_text())["curves"]
    pts = [(p["teacher_ece"], p["student_ece_mean"], t, p["T"], p["n"])
           for t, ps in curves.items() for p in ps]
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]
    a, b = linfit(x, y)

    loo_err = []
    for i in range(len(pts)):
        xi = x[:i] + x[i + 1:]
        yi = y[:i] + y[i + 1:]
        ai, bi = linfit(xi, yi)
        loo_err.append(abs((ai + bi * x[i]) - y[i]))
    return {
        "available": True, "n_points": len(pts),
        "intercept": a, "slope": b,
        "pearson": pearson(x, y), "spearman": spearman(x, y),
        "loo_mean_abs_error": st.mean(loo_err), "loo_max_abs_error": max(loo_err),
        "student_ece_range": [min(y), max(y)],
        "loo_error_as_pct_of_range": 100 * st.mean(loo_err) / (max(y) - min(y)),
        "points": [{"teacher": t, "T": T, "teacher_ece": xe, "student_ece": ye, "n_seeds": n}
                   for xe, ye, t, T, n in pts],
    }


def rows_sorted(rank):
    return sorted(rank["rows"], key=lambda r: -r["student_acc"])


def main():
    rank = step3_ranking()
    pred = step5_predictor()

    print("=== P4 step 3: which selection criterion picks the right teacher? ===")
    print(f"{'teacher':<10}{'teacher acc':<13}{'teacher ECE':<13}{'T*':<8}{'headroom':<11}"
          f"{'student acc':<14}{'student ECE'}")
    for r in sorted(rank["rows"], key=lambda r: -r["student_acc"]):
        print(f"{r['teacher']:<10}{r['teacher_acc']:<13.2f}{r['teacher_ece']:<13.4f}"
              f"{r['T_star']:<8.3f}{r['teacher_headroom']:<11.4f}"
              f"{r['student_acc']:<14.3f}{r['student_ece']:.4f}")
    print(f"\n  rank corr (teacher ACC  -> student ACC): {rank['spearman_teacherACC_vs_studentACC']:+.3f}")
    print(f"  rank corr (teacher ECE  -> student ACC): {rank['spearman_negTeacherECE_vs_studentACC']:+.3f}  (ECE negated)")
    print(f"  rank corr (teacher ECE  -> student ECE): {rank['spearman_teacherECE_vs_studentECE']:+.3f}")
    print(f"\n  pick by ACCURACY -> {rank['picked_by_accuracy']}  (correct: {rank['accuracy_criterion_correct']})")
    print(f"  pick by ECE      -> {rank['picked_by_ece']}  (correct: {rank['ece_criterion_correct']})")
    print(f"  actually best    -> {rank['actually_best']}")
    print(f"  cost of the accuracy-criterion mistake: {rank['cost_of_wrong_pick_pp']:.3f} pp student accuracy")

    pc = rank["per_checkpoint"]
    print("\n=== N5: the same question at ALL THREE checkpoints (student acc, pp) ===")
    print(f"{'teacher':<10}" + "".join(f"{'@' + ck:<22}" for ck in CKPTS))
    for r in rows_sorted(rank):
        cells = r["student_by_ckpt"]
        print(f"{r['teacher']:<10}" + "".join(
            f"{cells[ck]['acc_mean']:.2f} ± {cells[ck]['acc_sd']:.2f} (n={cells[ck]['n']})   "
            if ck in cells else f"{'-':<22}" for ck in CKPTS))
    print(f"\n{'ckpt':<7}{'ranking':<34}{'rho(tACC)':<12}{'rho(-tECE)':<13}{'wrong-pick cost'}")
    for ck in CKPTS:
        v = pc["by_ckpt"].get(ck)
        if not v:
            continue
        rk = v["ranking_display"]
        print(f"@{ck:<6}{rk:<34}{v['spearman_teacherACC_vs_studentACC']:+.3f}       "
              f"{v['spearman_negTeacherECE_vs_studentACC']:+.3f}        "
              f"{v['cost_of_wrong_pick_pp']:.4f} pp")
    print(f"\n  best teacher identical at all three : {pc['best_teacher_identical_across_ckpts']}")
    print(f"  full ranking identical at all three : {pc['ranking_identical_across_ckpts']}")
    for ck, v in pc["by_ckpt"].items():
        for a, b in v["ties"]:
            print(f"  TIE @{ck}: {a} and {b} at {v['student_acc'][a]:.6f} pp — "
                  f"the ranking is NOT a strict total order there")
    print(f"  pairwise reversals across checkpoints: "
          f"{pc['pairwise_reversals'] or 'NONE'}")
    print(f"  GPU cost avoided vs. distilling all {rank['n_teachers']} candidates: "
          f"{rank['n_teachers'] * 3 * HOURS_PER_STUDENT_RUN:.0f} h "
          f"({rank['n_teachers']} teachers x 3 seeds x {HOURS_PER_STUDENT_RUN} h) -> "
          f"replaced by {rank['n_teachers']} inference passes (~15 min each, CPU)")

    print("\n=== P4 step 5: predict student ECE from teacher ECE (leave-one-out) ===")
    if not pred["available"]:
        print(f"  unavailable: {pred['reason']}")
    else:
        print(f"  fit on n={pred['n_points']} manipulated points: "
              f"student_ECE = {pred['intercept']:+.4f} + {pred['slope']:.4f} * teacher_ECE")
        print(f"  Pearson {pred['pearson']:+.3f}   Spearman {pred['spearman']:+.3f}")
        print(f"  LOO mean |err| = {pred['loo_mean_abs_error']:.4f}  (max {pred['loo_max_abs_error']:.4f}); "
              f"student ECE spans {pred['student_ece_range'][0]:.4f}-{pred['student_ece_range'][1]:.4f}")
        print(f"  => LOO error is {pred['loo_error_as_pct_of_range']:.1f}% of the spanned range")
        n_partial = sum(1 for p in pred["points"] if p["n_seeds"] < 3)
        if n_partial:
            print(f"  NOTE: {n_partial}/{pred['n_points']} points are still <3 seeds; refit when complete.")

    # This file only PASSES THROUGH sds computed upstream (two_teacher_overlay.json), so the
    # stamp records the convention those numbers were produced under -- it does not re-derive it.
    payload = {"sd_convention": SD_CONVENTION,
               "recipe_step3_ranking": rank, "recipe_step5_predictor": pred,
               "hours_per_student_run": HOURS_PER_STUDENT_RUN}
    (OUT_DIR / "p4_teacher_selection.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'p4_teacher_selection.json'}")


if __name__ == "__main__":
    main()
