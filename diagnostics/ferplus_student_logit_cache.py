"""FERPlus öğrenci logit önbelleği — RAF-DB'deki student_logit_cache.py'nin FERPlus ikizi.

NEDEN GEREKLİ. R3-1 (ön-kayıt A10) yedi metriği örnek-başına dağılımdan hesaplıyor.
RAF-DB tarafında bu dağılım zaten koşu dizinlerinde <run>/logits_swa.npz olarak duruyor;
FERPlus tarafında YOKTU — ferplus_student_jsd.py yalnız SKALER özetleri (student_jsd.json)
önbelleğe alıyor. Skalerden eşit-kütle ECE ya da classwise ECE geri hesaplanamaz.

AYNI DOSYA BİÇİMİ, BİLEREK. Çıktı RAF-DB önbellekleriyle bit-uyumlu bir sözleşme taşır
(logits / labels / meta), böylece robustness_metrics.py 42 koşunun tamamını TEK bir
okuyucuyla gezer ve "FERPlus farklı yoldan geldi" diye bir ayrıksılık kalmaz.

DENETİM KAPISI — bu betiğin asıl gerekçesi. Sessizce yanlış bir checkpoint'ten üretilmiş
bir önbellek, aşağıdaki her tabloyu zehirler ve tamamen normal görünür. Bu yüzden her
yazımdan önce logitlerden acc ve 15-kutu ECE YENİDEN türetilir ve o koşunun
ferplus_selection_audit.csv satırıyla karşılaştırılır; tolerans aşılırsa dosya YAZILMAZ.
CSV başka bir gün, başka bir betikle üretildiği için bu gerçek bir çapraz doğrulamadır.

CİHAZ — VARSAYILAN CPU, ve bu bir gerileme değil, kapının kendi bulgusu. İlk deneme
CUDA'da yapıldı (RAF-DB önbellekleriyle aynı cihaz olsun diye) ve kapı DERHAL durdurdu:
doğruluk 88.9629 vs denetimin 88.9312'si, fark tam 0.0317 pp = 1/3153, yani TEK bir örnek
tahmin değiştirmişti. Sebep: ferplus_selection_audit.py varsayılan olarak CPU'da koşar
(kendi belgesi "Pass --device cuda only when the queue is idle" der), dolayısıyla
yayımlanmış FERPlus sayıları CPU sayılarıdır. CUDA'da üretilmiş bir önbellek, makalede
duran FERPlus tablosuyla dördüncü hanede çelişirdi.

Doğru kural şudur: HER SERİ, KENDİ YAYIMLANMIŞ DENETİMİNİN CİHAZINDA önbelleğe alınır --
RAF-DB CUDA'da denetlendi, CUDA'da; FERPlus CPU'da denetlendi, CPU'da. Karşılaştırmalar
zaten seri İÇİNDE yapılır (doz-cevap eğrisinin biçimi), seriler arası mutlak ECE farkı
bir büyüklük değildir. Bu düzeltme A10'a not olarak işlendi.

BATCH 64, keyfî değil: audit'in measure() fonksiyonu batch=64 kullanıyor. Farklı batch
farklı toplama sırası, o da kayan noktada farklı son hane demek; kapı bu yüzden aynı
batch'te karşılaştırma yapmalı (RAF-DB tarafında aynı gerekçeyle 256).

Kullanım:
  python diagnostics/ferplus_student_logit_cache.py            # 4 T x 3 tohum, @swa
  python diagnostics/ferplus_student_logit_cache.py --force
"""
import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "diagnostics"))

from kd_common import extract_logits  # noqa: E402
from ferplus_selection_audit import VARIANTS, build_val_images, load_student  # noqa: E402
from teacher_temperature_scaling_fit import confidence_ece  # noqa: E402

AUDIT_CSV = ROOT / "diagnostics" / "selection_audit" / "ferplus_selection_audit.csv"
EXPECTED_N = 3153


def audit_rows(ckpt):
    """{run_dir -> satır} — o checkpoint türü için denetim tablosunun kendisi."""
    out = {}
    with open(AUDIT_CSV, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["checkpoint"] == ckpt:
                out[Path(r["run_dir"])] = r
    return out


@torch.no_grad()
def forward_val(student, images, device, batch=64):   # = audit measure()
    chunks = []
    for i in range(0, images.shape[0], batch):
        chunks.append(extract_logits(student(images[i:i + batch].to(device))).float().cpu())
    return torch.cat(chunks)


def build_one(run_dir, row, ckpt, device, tol, force):
    p = run_dir / f"logits_{ckpt}.npz"
    if p.exists() and not force:
        return "cached", None

    run_args = json.loads((run_dir / "run_args.json").read_text())
    images, labels, _val_size = build_val_images(run_args)   # (imgs, labels, val_size)
    if int(labels.shape[0]) != EXPECTED_N:
        raise RuntimeError(f"{run_dir.parent.name}: val n={labels.shape[0]}, {EXPECTED_N} "
                           "bekleniyordu — rapor kümesi kaymış")

    fname = VARIANTS[ckpt][0]
    t0 = time.time()
    student, ckpt_epoch = load_student(run_dir, fname, run_args, device)
    logits = forward_val(student, images, device)
    dt = time.time() - t0
    del student

    acc = float((logits.argmax(1) == labels).float().mean() * 100.0)
    ece = confidence_ece(logits, labels, 1.0)
    d_acc, d_ece = abs(acc - float(row["acc"])), abs(ece - float(row["ece"]))
    if d_acc > tol["acc"] or d_ece > tol["ece"]:
        raise RuntimeError(
            f"{run_dir.parent.name} @{ckpt}: cached logits disagree with "
            f"ferplus_selection_audit.csv — acc {acc:.4f} vs {float(row['acc']):.4f} "
            f"(d={d_acc:.4f}), ECE {ece:.6f} vs {float(row['ece']):.6f} (d={d_ece:.6f}). "
            f"NOT writing the cache.")

    np.savez_compressed(
        p,
        logits=logits.numpy().astype(np.float32),
        labels=labels.numpy().astype(np.int64),
        meta=np.array(json.dumps({
            "run_name": run_dir.parent.name, "run_dir": str(run_dir), "checkpoint": ckpt,
            "n_val": int(labels.shape[0]), "acc_recomputed": acc, "ece_recomputed": ece,
            "audit_acc": float(row["acc"]), "audit_ece": float(row["ece"]),
            "d_acc": d_acc, "d_ece": d_ece, "ckpt_epoch": ckpt_epoch,
            "t_scale": float(row["t_scale"]), "seed": int(row["seed"]),
            "ece_method": "15-bin equal-width confidence ECE, FERPlus val fold, T=1",
            "device": str(device), "seconds": round(dt, 1),
        })))
    return "computed", dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="swa", choices=sorted(VARIANTS.keys()))
    ap.add_argument("--device", default="cpu",
                    help="the device the published FERPlus audit used; see module docstring")
    ap.add_argument("--threads", type=int, default=2)
    ap.add_argument("--tol-acc", type=float, default=1e-3, help="pp")
    ap.add_argument("--tol-ece", type=float, default=1e-4)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.device == "cpu":
        torch.set_num_threads(args.threads)
    device = torch.device(args.device)
    tol = {"acc": args.tol_acc, "ece": args.tol_ece}

    rows = audit_rows(args.ckpt)
    print(f"{len(rows)} FERPlus runs @{args.ckpt} on {device} "
          f"[tol acc {args.tol_acc} pp, ECE {args.tol_ece}]\n")

    n_new = 0
    for i, (run_dir, row) in enumerate(sorted(rows.items()), 1):
        status, dt = build_one(run_dir, row, args.ckpt, device, tol, args.force)
        n_new += status == "computed"
        t = f"{dt:5.1f}s" if dt else "   -- "
        print(f"  [{i:>2}/{len(rows)}] {status:<8} {t}  {run_dir.parent.name} @{args.ckpt}")

    print(f"\n{n_new} computed, {len(rows) - n_new} already cached. "
          f"Every written file matched ferplus_selection_audit.csv within tolerance.")


if __name__ == "__main__":
    main()
