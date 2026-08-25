"""Mark run directories that never finished, so no future scan can mistake them for results.

WHY A MARKER AND NOT A DELETE. Every analysis script in this campaign already requires
`metrics_best.json`, so these directories are inert today. The risk is a FUTURE script that
globs on `run_args.json` or on the directory name -- an unfinished 168-epoch run would then be
read as a completed one and silently averaged into a cell. A marker is the cheap insurance:
it is machine-readable, it explains itself, and unlike a delete it is reversible (one of these
directories is a power-outage casualty whose partial logs may still be worth reading).

The marker records WHY the run is abandoned, distinguishing:
  - "no epochs"   : the process died at startup (0 rows in training_log.csv). Zero information.
  - "interrupted" : real training happened, then stopped. The partial curve may be readable.

Idempotent: re-running refreshes markers and never touches a finished run. A directory that
LATER acquires metrics_best.json (e.g. an analysis writes it) has its marker removed, so the
marker can never outlive the condition it describes.

Read-only w.r.t. results; writes only ABANDONED.json. Outputs -> diagnostics/abandoned_runs.json
"""
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDENTS = ROOT / "results" / "unified_students"
OUT = ROOT / "diagnostics" / "abandoned_runs.json"
MARKER = "ABANDONED.json"
# Bu pencere icinde yazilmis bir dizin CANLI sayilir ve isaretlenmez.
LIVE_WINDOW_S = 15 * 60


def epochs_done(rd):
    tl = rd / "training_log.csv"
    if not tl.exists():
        return 0
    with open(tl, encoding="utf-8", errors="ignore") as fh:
        return max(0, sum(1 for _ in csv.reader(fh)) - 1)


def dir_size_mb(rd):
    return sum(f.stat().st_size for f in rd.iterdir() if f.is_file()) / 1e6


def main():
    apply = "--dry-run" not in sys.argv
    rows, cleared, live = [], [], []
    for rn in sorted(STUDENTS.iterdir()):
        if not rn.is_dir():
            continue
        for rd in sorted(rn.iterdir()):
            if not rd.is_dir():
                continue
            finished = (rd / "metrics_best.json").exists()
            marker = rd / MARKER
            if finished:
                # Never let a marker outlive the condition. A finished run must not carry one.
                if marker.exists():
                    cleared.append(str(rd.relative_to(ROOT)))
                    if apply:
                        marker.unlink()
                continue
            ep = epochs_done(rd)
            last = datetime.fromtimestamp(
                max((f.stat().st_mtime for f in rd.iterdir() if f.is_file()),
                    default=rd.stat().st_mtime))
            # CANLILIK KAPISI (6 Ağu 2026'da eklendi). "metrics_best.json yok" iki farklı
            # duruma uyuyor: koşu ÖLDÜ, ya da koşu HÂLÂ SÜRÜYOR. Ayrım yapılmazsa bu betik
            # çalışan bir koşuyu "terk edilmiş" diye işaretler; marker koşu bitince silinse
            # bile aradaki süre boyunca yanlış bilgi verir. Son yazma taze ise dokunulmaz.
            if (datetime.now() - last).total_seconds() < LIVE_WINDOW_S:
                live.append(f"{rn.name}/{rd.name} (son yazma {last:%H:%M:%S}, {ep} epoch)")
                continue
            rec = {
                "run_name": rn.name,
                "timestamp_dir": rd.name,
                "reason": "no epochs — process died at startup" if ep == 0
                          else f"interrupted after {ep} epochs (no metrics_best.json)",
                "epochs_completed": ep,
                "last_write": last.strftime("%Y-%m-%d %H:%M:%S"),
                "size_mb": round(dir_size_mb(rd), 2),
                "excluded_from": "every table and figure; T1-T10 require metrics_best.json",
                "marked_by": "diagnostics/mark_abandoned_runs.py",
                "marked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            rows.append(rec)
            if apply:
                marker.write_text(json.dumps(rec, indent=2), encoding="utf-8")

    if live:
        print(f"CANLI (isaretlenmedi): {len(live)}")
        for x in live:
            print("   ", x)
        print()
    dead = [r for r in rows if r["epochs_completed"] == 0]
    partial = [r for r in rows if r["epochs_completed"] > 0]
    print(f"{'DRY RUN — ' if not apply else ''}abandoned run directories: {len(rows)}"
          f"  ({len(dead)} never started, {len(partial)} interrupted mid-training)")
    print(f"disk held: {sum(r['size_mb'] for r in rows) / 1000:.2f} GB")
    if cleared:
        print(f"stale markers removed from now-finished runs: {len(cleared)}")
    print()
    print(f"{'epochs':>7}  {'last write':<17} {'MB':>7}  run")
    for r in sorted(rows, key=lambda x: x["last_write"]):
        print(f"{r['epochs_completed']:>7}  {r['last_write'][:16]:<17} {r['size_mb']:>7.1f}  "
              f"{r['run_name'][:44]}/{r['timestamp_dir']}")
    if apply:
        OUT.write_text(json.dumps({"marker_filename": MARKER, "count": len(rows),
                                   "runs": rows}, indent=2), encoding="utf-8")
        print(f"\nWrote {MARKER} into each directory above")
        print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
