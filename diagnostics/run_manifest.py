"""Per-run provenance manifest: code state, config hash, dataset hash, seed.

HONEST SCOPE NOTE (read before citing these hashes in a paper):
`poster-var` is NOT a git repository -- there is no commit SHA to record. The
substitute is a content hash over the exact source files that determine a run's
numerics (CODE_FILES below). This is strictly weaker than a git SHA in one way and
stronger in another: weaker because it has no history, stronger because it hashes
what actually ran rather than what was committed.

Consequence for RETROACTIVE manifests: for a run that finished before this tool
existed, the code hash describes the code as it is NOW, which is only the code that
ran IF no source file was modified after the run completed. This tool therefore
compares each source file's mtime against the run's completion time and emits
`code_state_verified: false` plus the offending files when it cannot vouch for them.
Never silently present a retroactive hash as if it were recorded at run time.

Dataset hash: streaming SHA-256 over the metadata CSV followed by every image's bytes
in sorted-relative-path order. Expensive once (~15k files), so it is cached in
dataset_hash_cache.json keyed by (file count, total bytes) and only recomputed when
those change.

Usage:
  python diagnostics/run_manifest.py --run-dir results/unified_students/<RUN>/<TS>
  python diagnostics/run_manifest.py --all-matching "RAFDB_vae9182_tempscale_*"
Writes manifest.json INTO each run directory (additive; touches nothing existing).
"""
import argparse
import glob
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Source files whose contents determine a KD run's numerics. Anything not here is
# either inert at train time (diagnostics/tools) or a launcher whose settings are
# already captured verbatim in run_args.json.
CODE_FILES = [
    "train_rafdb_kd.py",
    "kd_common.py",
    "kd_g2g.py",
    "kd_uncertainty.py",
    "kd_baselines.py",
    "models/mobilenetv2_plus.py",
    "dataset_utils/transforms.py",
    "trails/posterv2/vit_vae_model.py",
]
DATA_ROOT = PROJECT_ROOT / "data" / "rafdb_aligned"
METADATA = DATA_ROOT / "metadata_rafdb_poster_var.csv"
CACHE = PROJECT_ROOT / "diagnostics" / "dataset_hash_cache.json"


_SHA_MEMO = {}


def sha256_file(path, chunk=1 << 20):
    """Memoized on (path, size, mtime). Without this, hashing N runs re-reads the same
    555 MB teacher checkpoint N times -- ~50 GB of disk I/O for the current 89 runs."""
    path = Path(path)
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key in _SHA_MEMO:
        return _SHA_MEMO[key]
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    _SHA_MEMO[key] = h.hexdigest()
    return _SHA_MEMO[key]


def code_state():
    out = {}
    for rel in CODE_FILES:
        p = PROJECT_ROOT / rel
        if not p.exists():
            out[rel] = {"present": False}
            continue
        out[rel] = {"present": True, "sha256": sha256_file(p),
                    "mtime_utc": datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).isoformat(),
                    "bytes": p.stat().st_size}
    combined = hashlib.sha256(
        "".join(f"{k}:{v.get('sha256','ABSENT')}" for k, v in sorted(out.items())).encode()
    ).hexdigest()
    return {"files": out, "combined_code_sha256": combined,
            "git_sha": None, "git_note": "poster-var is not a git repository; combined_code_sha256 replaces the commit SHA"}


def dataset_hash():
    images = sorted(p for p in DATA_ROOT.rglob("*.jpg"))
    total = sum(p.stat().st_size for p in images)
    key = f"{len(images)}:{total}:{METADATA.stat().st_size}"
    if CACHE.exists():
        cached = json.loads(CACHE.read_text())
        if cached.get("key") == key:
            return cached["value"]
    h = hashlib.sha256()
    h.update(METADATA.read_bytes())
    for p in images:
        h.update(p.relative_to(DATA_ROOT).as_posix().encode())
        h.update(p.read_bytes())
    value = {"dataset_sha256": h.hexdigest(), "n_images": len(images), "total_bytes": total,
             "metadata_sha256": sha256_file(METADATA), "root": str(DATA_ROOT)}
    CACHE.write_text(json.dumps({"key": key, "value": value}, indent=2), encoding="utf-8")
    return value


def run_completion_time(run_dir):
    """Best available 'this run finished' timestamp: metrics_best.json mtime."""
    mb = run_dir / "metrics_best.json"
    if mb.exists():
        return datetime.fromtimestamp(mb.stat().st_mtime, timezone.utc)
    return None


def build_manifest(run_dir, code, data):
    run_dir = Path(run_dir)
    run_args = json.loads((run_dir / "run_args.json").read_text())
    # Canonical form so logically identical configs hash identically regardless of key order.
    config_sha = hashlib.sha256(
        json.dumps(run_args, sort_keys=True, default=str).encode()
    ).hexdigest()

    finished = run_completion_time(run_dir)
    stale = []
    if finished is not None:
        for rel, info in code["files"].items():
            if info.get("present") and datetime.fromisoformat(info["mtime_utc"]) > finished:
                stale.append(rel)
        # None means "not yet answerable", not "fine" -- an unfinished run has no completion
        # time to compare mtimes against, so verified must NOT default to True.
        verified = len(stale) == 0
        verify_note = None
    else:
        verified = None
        verify_note = ("run has no metrics_best.json (still training or crashed); completion time "
                       "unknown, so the code-state check cannot be evaluated")

    teacher_ckpt = run_args.get("teacher_ckpt")
    teacher_info = None
    if teacher_ckpt:
        tp = Path(teacher_ckpt)
        if not tp.is_absolute():
            tp = PROJECT_ROOT / tp
        if tp.exists():
            teacher_info = {"path": str(tp), "sha256": sha256_file(tp), "bytes": tp.stat().st_size}
        else:
            teacher_info = {"path": str(tp), "sha256": None, "note": "checkpoint not found at manifest time"}

    return {
        "run_dir": str(run_dir),
        "run_name": run_dir.parent.name,
        "seed": run_args.get("seed"),
        "finished_utc": finished.isoformat() if finished else None,
        "config_sha256": config_sha,
        "code": code,
        "dataset": data,
        "teacher_checkpoint": teacher_info,
        "manifest_written_utc": datetime.now(timezone.utc).isoformat(),
        "retroactive": True,
        "code_state_verified": verified,
        "code_state_note": verify_note,
        "code_files_modified_after_run": stale,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=None)
    ap.add_argument("--all-matching", default=None,
                    help="glob over results/unified_students/<pattern>/*")
    ap.add_argument("--skip-dataset-hash", action="store_true",
                    help="skip the ~15k-file dataset hash (use only for a quick re-check)")
    args = ap.parse_args()

    print("Hashing source files...")
    code = code_state()
    print(f"  combined_code_sha256 = {code['combined_code_sha256'][:16]}...")
    if args.skip_dataset_hash:
        data = {"dataset_sha256": None, "note": "skipped via --skip-dataset-hash"}
    else:
        print("Hashing dataset (cached after first run)...")
        data = dataset_hash()
        print(f"  dataset_sha256 = {data['dataset_sha256'][:16]}...  n={data['n_images']}")

    targets = []
    if args.run_dir:
        targets.append(Path(args.run_dir))
    if args.all_matching:
        targets += [Path(p) for p in
                    sorted(glob.glob(str(PROJECT_ROOT / "results/unified_students" / args.all_matching / "*")))]
    if not targets:
        ap.error("give --run-dir or --all-matching")

    n_ok = n_stale = n_unknown = 0
    for t in targets:
        if not (t / "run_args.json").exists():
            print(f"  SKIP (no run_args.json): {t}")
            continue
        m = build_manifest(t, code, data)
        (t / "manifest.json").write_text(json.dumps(m, indent=2), encoding="utf-8")
        if m["code_state_verified"] is None:
            tag = "UNFINISHED"
            n_unknown += 1
        elif m["code_state_verified"]:
            tag = "OK"
            n_ok += 1
        else:
            tag = f"STALE({len(m['code_files_modified_after_run'])} file(s))"
            n_stale += 1
        print(f"  [{tag}] seed={m['seed']} cfg={m['config_sha256'][:12]} {m['run_name']}")

    print(f"\n{n_ok} verified, {n_stale} with post-run code edits, {n_unknown} unfinished (not evaluable).")
    if n_stale:
        print("For STALE runs the code hash is the CURRENT state, not provably the state that ran. "
              "Cite them as retroactive.")


if __name__ == "__main__":
    main()
