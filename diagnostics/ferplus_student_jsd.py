"""Student-side human-alignment scorer: does distillation transfer the HUMAN-uncertainty match?

WHY THIS EXISTS, AND WHY SCORING ON HARD-LABEL ECE ALONE WOULD BE A RIGGED TEST.
The FERPlus arms differ only in the teacher's pre-scale temperature T. One of those arms (T=0.5063)
was chosen precisely because it MINIMISES the teacher's ECE/NLL against argmax labels. If the
students are then compared on hard-label ECE, that arm is favoured by construction -- the metric
and the arm selection share the same objective. Any "T*_ECE wins" conclusion would be circular.

FERPlus is one of the very few vision datasets that permits an independent second axis: it ships
the raw 10-rater vote distribution per image, i.e. a measured ground-truth DISTRIBUTION rather
than an argmax. So each student is scored on BOTH:
    hard-label axis   : ECE / NLL / Brier / accuracy / macro-F1   (already in ferplus_selection_audit.csv)
    human axis        : JSD( student softmax || 10-rater distribution ), plus the correlation
                        between per-sample student entropy and per-sample human entropy
and both results are reported whichever way they fall.

THE TEACHER-SIDE PICTURE IS ALREADY KNOWN AND THE TWO AXES DISAGREE THERE
(diagnostics/ferplus_jsd/ferplus_teacher_signed_grid.json):
    T=0.5063  teacher ECE 0.0156   JSD 0.0490   entropy 0.2562
    T=0.74    teacher ECE 0.0665   JSD 0.0440   entropy 0.4119   <- human entropy is 0.4401
    T=1.0     teacher ECE 0.1282   JSD 0.0492   entropy 0.6118
So on the teacher, moving to the human-aligned temperature costs +0.0508 ECE and buys -0.0050 JSD.

PRE-REGISTERED STUDENT-SIDE PREDICTIONS (fixed before the T=0.74 students finished):
  P1  hard-label student ECE stays monotone in teacher ECE, so the T=0.74 students land BETWEEN
      the T=0.26 and T=1.0 students (ordering 0.5063 < 0.26 < 0.74 < 1.0).
  P2  student JSD against the 10-rater distribution is MINIMISED at T=0.74.
  Both true  -> the two objectives are distinct and a real trade-off exists; a practitioner must
                choose which one to calibrate for.
  P1 true, P2 false -> human alignment does NOT survive distillation; it is a teacher-only
                property. Report as such.
  P1 false -> an interior counterexample to B-015's monotonicity; report as a restriction of the
                law, do not explain it away.

STUDENT SOFTMAX IS TAKEN AT T=1 (its deployed output). Rescaling the student would answer a
different question -- here we ask what the student actually emits after being taught by a
teacher at pre-scale T.

Defaults to CPU so the training queue keeps the GPU.
Usage:  python diagnostics/ferplus_student_jsd.py [--device cpu] [--force]
Outputs -> diagnostics/ferplus_jsd/ferplus_student_jsd.{csv,json}
"""
import argparse
import csv
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from dataset_utils.builder import build_dataloader  # noqa: E402
from kd_common import clean_state_dict, extract_logits  # noqa: E402
from ferplus_human_vote_jsd import EMOTIONS, entropy, jsd, spearman  # noqa: E402
from ferplus_selection_audit import VARIANTS, load_student  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402
from train_affectnetplus_kd import build_data_args  # noqa: E402
from utils.configs import load_yaml  # noqa: E402
from types import SimpleNamespace  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "ferplus_jsd"
STUDENTS = ROOT / "results" / "unified_students"
# LEVEL-1 SINIR DEFTERİ (17 Ağu 2026). Bu betik pahalı işi (öğrenci checkpoint'ini yükleyip
# skorlamak) koşu dizinindeki `student_jsd.json`da önbelleğe alıyordu -- yani önbellek `results/`
# ağacının İÇİNDE yaşıyordu ve üretici o ağaç olmadan HİÇ koşamıyordu. Artefaktı ihraç bandına
# aldığımız gün Level-1 kapısı bunu İHLAL olarak yakaladı (kapı bu üreticiye o güne kadar
# soruyu hiç soramamıştı, çünkü `parse_args` runpy altında düşüyordu).
# ÇÖZÜM `publish_epoch_curves`/`selection_gain_estimator` ile aynı desen: satırlar
# `diagnostics/` altına YAYIMLANIR, üretici koşu ağacı yokken onları okur. Böylece
# `tab_human`ın 29 basılı hücresi yayımlı depodan yeniden üretilebilir hale gelir --
# "yeniden üretilebilir" ile "denetlenebilir" arasındaki farkın tam olarak kapandığı yer.
PUBLISHED_ROWS = OUT_DIR / "ferplus_student_jsd_rows.json"
TEACHER_GRID = json.loads((OUT_DIR / "ferplus_teacher_signed_grid.json").read_text())


def build_val(run_args):
    """The student's OWN val pipeline (224 px via --img-size), plus the aligned human votes.

    The image order must match the vote order, so paths are carried through the loader and used
    to index the metadata rows -- never assume the loader and the CSV share an ordering.
    """
    a = SimpleNamespace(**run_args)
    a.device = torch.device("cpu")
    a.workers = 0
    a.cache_img = False
    cfg_path = Path(a.teacher_config)
    data_args = build_data_args(cfg_path if cfg_path.is_absolute() else ROOT / cfg_path, a)
    data_args.train_root = None
    data_args.train_shuffle = False
    _tr, val_loader = build_dataloader(data_args)
    ds = val_loader.dataset

    imgs, labs, idxs = [], [], []
    for batch in val_loader:
        index, img, label, _label_em, _path = batch
        imgs.append(img)
        labs.append(label)
        idxs.append(index)
    images = torch.cat(imgs)
    labels = torch.cat(labs)
    indices = torch.cat(idxs).numpy()
    names = [Path(ds.data_infos[i]["path"]).name for i in indices]

    cfg = argparse.Namespace()
    load_yaml(cfg, str(ROOT / a.teacher_config))
    df = pd.read_csv(ROOT / cfg.metadata)
    df = df[df["fold"].isin(cfg.val_folds)].reset_index(drop=True)
    by_name = {Path(p).name: i for i, p in enumerate(df["path"].tolist())}
    rows = [by_name[n] for n in names]
    votes = torch.tensor(df.loc[rows, EMOTIONS].to_numpy(dtype=np.float64), dtype=torch.float64)
    vsum = votes.sum(dim=1)
    keep = vsum > 0
    # normalise by each row's OWN vote sum: 37.3% of rows do not sum to 10 (see B-008)
    p_human = (votes[keep] / vsum[keep].unsqueeze(1)).float()
    return images[keep], labels[keep], p_human


@torch.no_grad()
def score(student, images, labels, p_human, h_human, device, batch=64):
    chunks = []
    for i in range(0, images.shape[0], batch):
        chunks.append(extract_logits(student(images[i:i + batch].to(device))).float().cpu())
    logits = torch.cat(chunks)
    probs = F.softmax(logits, dim=1)          # student's DEPLOYED distribution, T=1
    preds = logits.argmax(1)
    h_student = entropy(probs)
    k = probs.shape[1]
    onehot = F.one_hot(labels.long(), num_classes=k).float()
    return {
        # hard-label axis
        "acc": float((preds == labels).float().mean() * 100.0),
        "ece": confidence_ece(logits, labels, 1.0),
        "nll": float(F.cross_entropy(logits, labels.long())),
        "brier": float(((probs - onehot) ** 2).sum(dim=1).mean()),
        # human axis
        "jsd_vs_human": float(jsd(p_human, probs).mean()),
        "student_mean_entropy": float(h_student.mean()),
        "entropy_pearson_vs_human": float(np.corrcoef(h_human.numpy(), h_student.numpy())[0, 1]),
        "entropy_spearman_vs_human": spearman(h_human.numpy(), h_student.numpy()),
        "n_val": int(labels.shape[0]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--checkpoints", nargs="+", default=["swa", "best", "last"])
    ap.add_argument("--from-runs", action="store_true",
                    help="koşu ağacını tara ve yayımlı satırları TAZELE (Level-3 eylemi); "
                         "varsayılan yol yalnız yayımlı satırları okur")
    # `parse_known_args` -- deponun standart kuralı (bkz. bootstrap_cis.py): Level-1 kapısı
    # üreticileri `runpy` ile çağırıyor ve betiğin YOLU argv'de kalıyor; `parse_args` orada
    # SystemExit atıp kapıyı "başka hata"ya düşürüyor. DİKKAT: `--checkpoints` nargs="+" olduğu
    # için bilinmeyen konumsal argüman ona yutulabilirdi; `parse_known_args` onu `_unknown`a
    # bırakır. 17 Ağu 2026: artefakt ihraç bandına girince üreticisi ilk kez kapıya girdi.
    args, _unknown = ap.parse_known_args()
    # cp1252 konsolda Türkçe karakter `UnicodeEncodeError` atıyor; deponun standart bloğu.
    # Bu betiğin çıktısı bugüne kadar tümüyle İngilizceydi, o yüzden gerekmemişti; 17 Ağu'da
    # eklenen Türkçe satırlar Level-1 kapısının alt sürecinde hemen düşürdü.
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, "reconfigure"):
            s.reconfigure(encoding="utf-8", errors="replace")
    device = torch.device(args.device)

    # VARSAYILAN YOL KOŞU AĞACINA HİÇ DOKUNMAZ. Ağacı taramak `--from-runs` ile İSTENİR.
    # Bu bir tercih değil, kapının doğru sorulması meselesi: "hata olursa yayımlı satırlara
    # düş" biçiminde yazsaydık, betik ağaca YİNE dokunur ve Level-1 sorusunu geçmesi ancak
    # kapının kendi istisnasını yutmakla mümkün olurdu -- yani kapıyı oynatmakla. Tarama ayrı
    # bir eylemdir (`publish_epoch_curves` deseni), tablo üretimi Level-1 temizdir.
    if not args.from_runs:
        if not PUBLISHED_ROWS.exists():
            print(f"yayımlı satır yok ({PUBLISHED_ROWS.relative_to(ROOT)}); koşu ağacı olan "
                  f"makinede `--from-runs` ile bir kez üretilmeli. Hiçbir dosya yazılmadı.")
            return
        blob = json.loads(PUBLISHED_ROWS.read_text(encoding="utf-8"))
        rows, h_mean = blob["rows"], blob["human_mean_entropy"]
        print(f"yayımlı satırlar okundu: {len(rows)} satır "
              f"({PUBLISHED_ROWS.relative_to(ROOT)}) — koşu ağacına dokunulmadı")
    else:
        runs = []
        for rn in sorted(STUDENTS.iterdir()):
            if not (rn.is_dir() and rn.name.startswith("FERPlus_tempscale_")):
                continue
            for ts in sorted(rn.iterdir()):
                if (ts / "run_args.json").exists() and (ts / "metrics_best.json").exists():
                    runs.append(ts)
        if not runs:
            print("nothing to score yet")
            return
        print(f"device={device}   {len(runs)} finished FERPlus tempscale runs")
        images, labels, p_human = build_val(
            json.loads((runs[0] / "run_args.json").read_text()))
        h_human = entropy(p_human)
        h_mean = float(h_human.mean())
        print(f"FERPlus val n={images.shape[0]}  human mean entropy {h_mean:.4f} nat\n")

        rows = []
        for i, rd in enumerate(runs, 1):
            cache_p = rd / "student_jsd.json"
            cache = (json.loads(cache_p.read_text())
                     if (cache_p.exists() and not args.force) else {})
            ra = json.loads((rd / "run_args.json").read_text())
            changed = False
            for ck in args.checkpoints:
                fname = VARIANTS[ck][0]
                if not (rd / fname).exists():
                    continue
                if ck not in cache:
                    student, _ep = load_student(rd, fname, ra, device)
                    cache[ck] = score(student, images, labels, p_human, h_human, device)
                    changed = True
                    del student
                rows.append({"run_name": rd.parent.name, "checkpoint": ck,
                             "t_scale": float(ra.get("teacher_temperature_scale", 1.0)),
                             "seed": ra.get("seed"), **cache[ck]})
            if changed:
                cache_p.write_text(json.dumps(cache, indent=2), encoding="utf-8")
            print(f"  [{i}/{len(runs)}] {rd.parent.name}")

        # Satırları YAYIMLA: koşu dizinindeki önbellek `results/` ağacında kalır, bu kopya
        # depoda kalır ve üretici onsuz da koşabilir.
        PUBLISHED_ROWS.write_text(json.dumps(
            {"note": "published so the producer runs without results/ (Level-1)",
             "source": "results/unified_students/FERPlus_tempscale_*/*/student_jsd.json",
             "human_mean_entropy": h_mean, "n_rows": len(rows), "rows": rows},
            indent=2), encoding="utf-8")

    with open(OUT_DIR / "ferplus_student_jsd.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    tg = {round(g["T"], 4): g for g in TEACHER_GRID["grid"]}
    summary = {}
    for ck in args.checkpoints:
        sub = [r for r in rows if r["checkpoint"] == ck]
        if not sub:
            continue
        print(f"\n=== @{ck}: BOTH axes, per teacher pre-scale T ===")
        print(f"{'T':<9}{'n':<4}{'teachECE':<10}{'teachJSD':<10}"
              f"{'studECE':<18}{'studJSD':<18}{'studH':<9}{'rho(H,human)'}")
        by_T = {}
        for r in sub:
            by_T.setdefault(round(r["t_scale"], 4), []).append(r)
        for T in sorted(by_T):
            g = by_T[T]
            def ms(k):
                v = [x[k] for x in g]
                return st.mean(v), (st.stdev(v) if len(v) > 1 else 0.0)
            e_m, e_s = ms("ece")
            j_m, j_s = ms("jsd_vs_human")
            h_m, _ = ms("student_mean_entropy")
            rho_m, _ = ms("entropy_spearman_vs_human")
            t = tg.get(T, {})
            by_T[T] = {"n": len(g), "ece": (e_m, e_s), "jsd": (j_m, j_s),
                       "entropy": h_m, "rho": rho_m,
                       "teacher_ece": t.get("teacher_ece"), "teacher_jsd": t.get("mean_jsd_vs_human")}
            print(f"{T:<9g}{len(g):<4}{t.get('teacher_ece', float('nan')):<10.4f}"
                  f"{t.get('mean_jsd_vs_human', float('nan')):<10.4f}"
                  f"{e_m:.4f} +/- {e_s:.4f}   {j_m:.4f} +/- {j_s:.4f}   {h_m:<9.4f}{rho_m:.3f}")

        argmin_ece = min(by_T, key=lambda T: by_T[T]["ece"][0])
        argmin_jsd = min(by_T, key=lambda T: by_T[T]["jsd"][0])
        print(f"  argmin student ECE at T={argmin_ece:g}   "
              f"argmin student JSD at T={argmin_jsd:g}")
        if argmin_ece != argmin_jsd:
            a, b = by_T[argmin_ece], by_T[argmin_jsd]
            print(f"  >>> THE TWO OBJECTIVES DISAGREE ON THE STUDENT TOO. Moving from the "
                  f"ECE-optimal arm to the JSD-optimal arm costs "
                  f"{b['ece'][0] - a['ece'][0]:+.4f} ECE and buys "
                  f"{b['jsd'][0] - a['jsd'][0]:+.4f} JSD.")
        else:
            print(f"  >>> Both objectives are optimised by the SAME arm (T={argmin_ece:g}): "
                  f"no trade-off is visible at this grid resolution.")
        print(f"  human mean entropy {h_mean:.4f}; closest student entropy: "
              f"T={min(by_T, key=lambda T: abs(by_T[T]['entropy'] - h_mean)):g}")
        summary[ck] = {str(k): v for k, v in by_T.items()}
        summary[ck]["_argmin_ece_T"] = argmin_ece
        summary[ck]["_argmin_jsd_T"] = argmin_jsd

    (OUT_DIR / "ferplus_student_jsd.json").write_text(
        json.dumps({"human_mean_entropy": h_mean, "by_checkpoint": summary,
                    "per_run": rows}, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT_DIR / 'ferplus_student_jsd.csv'}")
    print(f"Wrote {OUT_DIR / 'ferplus_student_jsd.json'}")


if __name__ == "__main__":
    main()
