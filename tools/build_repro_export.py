"""Repro deposu kurucusu: git'ten temiz export -> teacher-logit-scaling-kd/ (+ zip).

NİYE ÇALIŞMA AĞACINDAN DEĞİL GİT'TEN. §6'nın vaadi "run manifests, pre-registration records,
analysis scripts". Çalışma ağacı her an kirli olabilir (koşan kuyruğun logları, geçici dosyalar,
henüz commit'lenmemiş düzenlemeler); `git archive HEAD` ise tarihli, tekrarlanabilir ve junk'sız
bir kesittir. Deponun README'si hangi commit'ten üretildiğini yazar — kopya ile tarih arasındaki
bağ koparılamaz.

İÇERİK (beyan; joker yalnız uzantıyla sınırlı):
  kod        : train_*.py, kd_*.py, main_encoder.py, valid_encoder.py, loss_encoder.py,
               models/, utils/, dataset_utils/, tools/, configs/
  analiz     : diagnostics/*.py (fark kapısı dahil) + stats_convention
  kayıtlar   : runs.csv, diagnostics/PREREGISTRATIONS.md, diagnostics/claims.md,
               diagnostics/preregistration_blocks.csv, diagnostics/paper_tables/RESULTS_TABLES.*,
               diagnostics/selection_audit/*.csv+json+README, METHODS_DATA.md
  kuyruklar  : rafdb_*.ps1 / ferplus_*.ps1 (ön-kayıt artefaktlarının kendileri)
DIŞARIDA (bilinçli): veri kümeleri (lisans — README'de edinme linkleri), checkpoint'ler (boyut;
istek üzerine), results/, _greyscale/, paper/, geçici çıktılar. `git archive` zaten yalnız
izlenen dosyaları verir; buradaki ALLOW listesi onu bir kez daha daraltır.

Kullanım:  python tools/build_repro_export.py [--dest <klasör>] [--ref HEAD]
Çıktı:     <dest>/teacher-logit-scaling-kd/  +  teacher-logit-scaling-kd_<commit>.zip
Yayınlama kararı ve zamanı Fatih'te — bu betik yalnız yerel bir kesit üretir.
"""
import argparse
import fnmatch
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "teacher-logit-scaling-kd"   # ad önerisi — Fatih onaylayacak

ALLOW = [
    "train_*.py", "kd_*.py", "main_encoder.py", "valid_encoder.py", "loss_encoder.py",
    "beta_weighted_kd.py", "generate_kd_figure.py",
    # trails/ = POSTERv2 öğretmen paketi: onsuz train_*.py import'ta düşer ve hiçbir koşu
    # yeniden üretilemez. İlk sürüm bunu atlamıştı — kesit "çalışan kod" vaadi taşıyor.
    "models/*", "utils/*", "dataset_utils/*", "tools/*", "configs/*", "trails/*", "trials/*",
    # diagnostics/ TAMAMI (2 Agu'da genisletildi). Onceki surum paper_tables altindaki dosyalari
    # tek tek sayiyordu; R0/R1/R2 paketleri gelince (student_ts_baseline, inferential_tests,
    # headroom_review, tstar_stability, order_stat_trend, mechanism_specs) liste sessizce eksik
    # kaldi -- makaledeki sayinin ureticisi kesitte yoksa "her tablo yeniden uretilebilir" vaadi
    # delinir. Artik joker + guclu DENY: yeni bir tablo eklendiginde kendiliginden kapsanir.
    "diagnostics/*",
    "runs.csv", "METHODS_DATA.md", "BULGULAR.md",
    "rafdb_*.ps1", "ferplus_*.ps1", "run_*.ps1",
    "requirements*.txt", ".gitignore",
]
# Ikili/veri artefaktlari: logit cache (.npz -- rafdb_calibration_backfill, 2.8 MB), FERPlus JSD
# ara dizileri (.npy), checkpoint'ler ve figur ikilileri. Figurler bilincli olarak disarida:
# hepsi export_paper_figures.py ile yeniden uretilir ve verify_paper_figures.py ile dogrulanir,
# yani kesit "kod + kayit" kalir, ikili artefakt tasimaz.
DENY = ["**/_greyscale/*", "paper/*",
        "*.npz", "*.npy", "*.pt", "*.pth", "*.pth.tar", "*.tar", "*.pdf", "*.png", "*.jpg",
        # Yazar-yerel bant altyapisi: yazarin ozel Drive yolunu ve gonderim takvimini
        # tasiyor, makalede hicbir tabloyu/figuru/beyani uretmiyor. Kesitin disinda. Bunlari
        # import eden uc betikte (paper_tables, export_paper_figures, verify_paper_figures)
        # kanca try/except ImportError ile korunur -- yoklugu uretimi durdurmaz.
        "diagnostics/export_to_drive.py"]


def keep(rel):
    r = rel.replace("\\", "/")
    if any(fnmatch.fnmatch(r, d) for d in DENY):
        return False
    return any(fnmatch.fnmatch(r, a) for a in ALLOW)


def git(*a):
    r = subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()


README = """# {name}

Reproducibility package for **"{title}"** — run manifests, pre-registration
records and analysis scripts, exported from git commit `{commit}` ({cdate}).

> Datasets (RAF-DB, FERPlus, AffectNet) are NOT included for licensing reasons —
> obtain them from their maintainers (RAF-DB: http://www.whdeng.cn/raf/model1.html ·
> FERPlus: https://github.com/microsoft/FERPlus · AffectNet: http://mohammadmahoor.com/affectnet/).
> Model checkpoints are excluded for size and are available on request.

## What can be reproduced, at which level

1. **Every table and number in the paper, without a GPU.** The run ledger
   (`runs.csv`, one row per finished run, every field derived from the run's own
   artifacts) and the frozen selection audit (`diagnostics/selection_audit/`,
   N=131) are included. `python diagnostics/paper_tables.py` regenerates
   `RESULTS_TABLES.{{md,json}}` from them; `python diagnostics/table_diff_gate.py`
   verifies the result cell-by-cell against the accepted baseline (also included).
   Which table comes from which script is listed below.
2. **Every training run, with a GPU and the datasets.** The exact launcher for
   each campaign is a `*.ps1` queue at the repo root; each embeds the full
   `train_*.py` command line. The pre-registration record
   (`diagnostics/PREREGISTRATIONS.md`) maps each queue to its frozen prediction
   and decision rule, declared before the runs.

## Table -> producing script

| output | script |
|---|---|
| RESULTS_TABLES (T1-T10) | `diagnostics/paper_tables.py` |
| T5 pairing diff | `diagnostics/t5_pairing_diff.py` |
| denominator conventions | `diagnostics/denominator_table.py` |
| section 5.4 numbers | `diagnostics/section54_numbers.py` |
| selection audit @131 | `diagnostics/selection_audit_table.py` (frozen cutoff inside) |
| P2 / P5 verdicts | `diagnostics/p2_gate_oracle_verdict.py` / `diagnostics/p5_oracle_replication_verdict.py` |
| paper figures | `diagnostics/export_paper_figures.py` + producers it imports |
| figure gate | `diagnostics/verify_paper_figures.py` |
| run ledger | `diagnostics/build_runs_ledger.py` (needs run directories) |

## Setup

```
python -m venv .venv && .venv\\Scripts\\activate   # Windows
pip install -r requirements.txt
```

PyTorch + CUDA are only needed to retrain; the analysis layer is CPU-only.

## Integrity notes

- The selection audit's inclusion set is FROZEN (N=131, cutoff inside
  `selection_audit_table.py`); the script raises if the set drifts.
- `diagnostics/preregistration_blocks.csv` is a human-authored declaration of
  experimental intent, not an inference — see its header.
- Sample sd (n-1) throughout: `diagnostics/stats_convention.py`.

Exported {now} by `tools/build_repro_export.py`.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default=str(ROOT.parent))
    ap.add_argument("--ref", default="HEAD")
    args = ap.parse_args()

    if git("status", "--porcelain"):
        print("UYARI: calisma agaci kirli -- export yine de", args.ref,
              "commit'inden yapilir (kirli dosyalar KESITTE YOK).")
    commit = git("rev-parse", "--short=12", args.ref)
    cdate = git("log", "-1", "--format=%ci", args.ref)

    dest = Path(args.dest) / NAME
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as td:
        tar_p = Path(td) / "archive.tar"
        with open(tar_p, "wb") as fh:
            subprocess.run(["git", "-C", str(ROOT), "archive", args.ref],
                           stdout=fh, check=True)
        n_all, n_kept = 0, 0
        with tarfile.open(tar_p) as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                n_all += 1
                if keep(m.name):
                    tf.extract(m, dest, filter="data")
                    n_kept += 1

    (dest / "README.md").write_text(
        README.format(name=NAME, commit=commit, cdate=cdate,
                      title="calibration-conditioned knowledge distillation for FER",
                      now=datetime.now().strftime("%Y-%m-%d %H:%M")),
        encoding="utf-8")

    zip_base = Path(args.dest) / f"{NAME}_{commit}"
    zip_p = shutil.make_archive(str(zip_base), "zip", root_dir=dest.parent,
                                base_dir=NAME)
    total = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
    print(f"commit   : {commit} ({cdate})")
    print(f"kesit    : {n_kept}/{n_all} izlenen dosya -> {dest}")
    print(f"boyut    : {total / 1e6:.1f} MB  |  zip: {Path(zip_p).name} "
          f"({Path(zip_p).stat().st_size / 1e6:.1f} MB)")
    print("YAYINLANMADI: ad + zaman karari Fatih'te.")


if __name__ == "__main__":
    main()
