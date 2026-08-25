"""P5 completion: latency measured under a controlled protocol on an idle machine.

WHY THIS REPLACES THE OLD NUMBERS. The three pre-existing latency CSVs measured the SAME
teacher architecture (58.34 M params, 8.4827 GMACs) at 249.8 / 89.2 / 47.5 ms -- a 5.3x spread.
Identical FLOPs cannot produce that; the spread was machine contention, because those
measurements were taken while the KD training queues were running. Those numbers are discarded.

PROTOCOL (fixed, per configuration):
  - 50 warmup iterations, then 200 measured iterations (CPU uses reduced counts, recorded below,
    because a batch-32 POSTERv2 forward on CPU is ~1-2 s and 200 of those is not a good use of
    an idle window; the deviation is recorded per row rather than hidden).
  - torch.cuda.synchronize() before starting the timer and before stopping it, so the measured
    interval contains the completed GPU work rather than just the launch.
  - torch.inference_mode(), model.eval().
  - MEDIAN and IQR reported, never the mean: latency distributions are right-skewed (occasional
    scheduler/driver hiccups) so the mean is dragged by outliers the median ignores.
  - Batch 1 (deployment / single-face latency) and batch 32 (throughput) reported separately;
    per-image time for batch 32 is median/32.
  - fp32 always; fp16 via autocast on CUDA (skipped on CPU, where fp16 conv is not accelerated).

Both models are measured so the speed-up ratio is apples-to-apples on one machine, one session.

Outputs -> diagnostics/p5_efficiency/latency_benchmark.{csv,json}
"""
import argparse
import csv
import json
import platform
import statistics as st
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from train_rafdb_kd import build_student, build_teacher  # noqa: E402

OUT_DIR = ROOT / "diagnostics" / "p5_efficiency"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STUDENT_RUN = ROOT / "results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200"
TEACHER_CKPT = ROOT / "results/teacher_logs/RAFDB/POSTERv2/2026-06-16-23-33-23/best.pt"


def env_manifest():
    def sh(cmd):
        try:
            return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                                  timeout=25).stdout.strip() or None
        except Exception:
            return None
    m = {
        "torch": torch.__version__,
        "torch_cuda_build": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "python": platform.python_version(),
        "os": platform.platform(),
        "cpu": platform.processor(),
        "measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
        "note": "measured on an idle machine; no training queue running (verified before start)",
    }
    if torch.cuda.is_available():
        m["gpu"] = torch.cuda.get_device_name(0)
        p = torch.cuda.get_device_properties(0)
        m["gpu_total_mem_gb"] = round(p.total_memory / 1024 ** 3, 2)
        m["gpu_sm"] = f"{p.major}.{p.minor}"
        m["nvidia_smi_driver"] = sh("nvidia-smi --query-gpu=driver_version --format=csv,noheader")
        m["nvidia_smi_power_limit_w"] = sh(
            "nvidia-smi --query-gpu=power.limit --format=csv,noheader")
        # Sampled BEFORE any work, so this is the IDLE clock, not the clock the timings were
        # taken at. Labelled accordingly -- reporting an idle clock as if it characterised the
        # measurement would misrepresent the conditions. The under-load sample is taken later.
        m["nvidia_smi_clocks_mhz_IDLE_before_run"] = sh(
            "nvidia-smi --query-gpu=clocks.sm,clocks.mem --format=csv,noheader")
    m["windows_power_plan"] = sh("powercfg /getactivescheme")
    return m


def clocks_under_load(model, device, seconds=4.0):
    """The clock that actually applies to the reported timings: sampled while the GPU is busy.
    An idle-state reading (240 MHz here) would badly misrepresent the measurement conditions."""
    if device.type != "cuda":
        return None
    x = torch.randn(32, 3, 224, 224, device=device)
    samples = []
    t_end = time.perf_counter() + seconds
    with torch.inference_mode():
        while time.perf_counter() < t_end:
            for _ in range(5):
                model(x)
            torch.cuda.synchronize()
            try:
                out = subprocess.run(
                    "nvidia-smi --query-gpu=clocks.sm,clocks.mem,power.draw,temperature.gpu "
                    "--format=csv,noheader", shell=True, capture_output=True, text=True, timeout=10)
                if out.stdout.strip():
                    samples.append(out.stdout.strip())
            except Exception:
                pass
    return samples


def build_models(device):
    args = SimpleNamespace(**json.loads(
        sorted(STUDENT_RUN.glob("*/run_args.json"))[-1].read_text()))
    args.student_pretrained = False
    args.use_vich_sampling = False
    student = build_student(args, device).eval()
    targs = SimpleNamespace(
        teacher_vae_head=True, teacher_layer_embedding=True, teacher_votes_sum=0,
        teacher_vich_head=False, teacher_vich_use_sampling=False,
        teacher_vich_logvar_min=-10.0, teacher_vich_logvar_max=10.0,
        teacher_vich_init_logvar_bias=-5.0)
    teacher = build_teacher(TEACHER_CKPT, device, targs).eval()
    return {"student_MobileNetV2Plus_VICH": student, "teacher_POSTERv2_VAE": teacher}


def bench(model, device, batch, dtype, warmup, iters):
    x = torch.randn(batch, 3, 224, 224, device=device)
    use_amp = dtype == "fp16"
    if use_amp and device.type != "cuda":
        return None
    samples = []
    with torch.inference_mode():
        for i in range(warmup + iters):
            if device.type == "cuda":
                torch.cuda.synchronize()
            t0 = time.perf_counter()
            if use_amp:
                with torch.autocast("cuda", dtype=torch.float16):
                    model(x)
            else:
                model(x)
            if device.type == "cuda":
                torch.cuda.synchronize()
            dt = (time.perf_counter() - t0) * 1000.0
            if i >= warmup:
                samples.append(dt)
    samples.sort()
    q1 = samples[len(samples) // 4]
    q3 = samples[(3 * len(samples)) // 4]
    med = st.median(samples)
    return {"median_ms": med, "q1_ms": q1, "q3_ms": q3, "iqr_ms": q3 - q1,
            "min_ms": samples[0], "max_ms": samples[-1], "mean_ms": st.mean(samples),
            "per_image_median_ms": med / batch, "fps_from_median": 1000.0 * batch / med,
            "warmup": warmup, "iters": iters}


IDLE_MEM_MIB = 1500


def _run(cmd, timeout=25):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              timeout=timeout).stdout or ""
    except Exception:
        return ""


def gpu_busy():
    """Return a reason string if the machine is NOT idle, else "". Guard for the timing protocol.

    Two independent signals, because each one alone has a failure mode that reads as "idle":

      1. TOTAL GPU memory in use (`--query-gpu=memory.used`). Deliberately NOT
         `--query-compute-apps=used_memory`: on this machine (Windows / WDDM) that per-process
         field returns literal `[N/A]` for every row, so a naive sum is always 0 and the guard
         silently passes while two trainings are running. That is exactly what the first version
         of this function did.
      2. Any live `train_*.py` process. Covers the window where a run has been launched but has
         not yet allocated, and the case where the driver reports memory oddly.

    Utilisation % is used by neither: it is an instantaneous sample and reads near zero between
    a training step's kernels, so a busy GPU can genuinely report 0% at the moment you look.
    """
    reasons = []
    mem = _run("nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits").strip()
    mib = next((int(x) for x in mem.splitlines() if x.strip().isdigit()), 0)
    if mib > IDLE_MEM_MIB:
        reasons.append(f"{mib} MiB GPU memory in use (idle threshold {IDLE_MEM_MIB})")
    procs = _run('powershell -NoProfile -Command "Get-CimInstance Win32_Process '
                 "-Filter \\\"Name='python.exe'\\\" | Select-Object -ExpandProperty CommandLine\"")
    training = [ln for ln in procs.splitlines() if "train_" in ln and "_kd.py" in ln]
    if training:
        reasons.append(f"{len(training)} training process(es) alive")
    return " + ".join(reasons)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu-warmup", type=int, default=50)
    ap.add_argument("--gpu-iters", type=int, default=200)
    ap.add_argument("--cpu-warmup", type=int, default=5)
    ap.add_argument("--cpu-iters", type=int, default=20)
    ap.add_argument("--devices", nargs="+", default=["cuda", "cpu"])
    ap.add_argument("--tag", default="",
                    help="suffix for the output files, e.g. --tag session2. REQUIRED for a "
                         "replication run: without it the second session OVERWRITES the first, "
                         "destroying the very baseline it exists to be compared against.")
    ap.add_argument("--allow-busy-gpu", action="store_true",
                    help="run even if training processes are alive. Only for smoke tests -- the "
                         "resulting numbers are contended and must never be reported.")
    args = ap.parse_args()

    busy = gpu_busy()
    if busy and not args.allow_busy_gpu:
        raise SystemExit(
            f"REFUSING TO MEASURE -- machine is not idle: {busy}.\n"
            "Every timing in this file is defined as an idle-machine measurement; taken under a "
            "training queue it is unfalsifiably contended, and the fp16-vs-fp32 question this "
            "benchmark exists to settle is exactly the kind of small effect contention fakes.\n"
            "Wait for the queue to drain, or pass --allow-busy-gpu for a throwaway smoke test.")

    manifest = env_manifest()
    manifest["idle_check"] = busy or "idle (no training process, GPU memory below threshold)"
    manifest["session_tag"] = args.tag or "session1"
    print(json.dumps(manifest, indent=2))
    print()

    rows = []
    for dev_name in args.devices:
        if dev_name == "cuda" and not torch.cuda.is_available():
            print("cuda unavailable, skipping")
            continue
        device = torch.device(dev_name)
        warmup = args.gpu_warmup if dev_name == "cuda" else args.cpu_warmup
        iters = args.gpu_iters if dev_name == "cuda" else args.cpu_iters
        models = build_models(device)
        if dev_name == "cuda":
            manifest["nvidia_smi_UNDER_LOAD_sm,mem,power,temp"] = clocks_under_load(
                models["teacher_POSTERv2_VAE"], device)
            print(f"  clocks under load: {manifest['nvidia_smi_UNDER_LOAD_sm,mem,power,temp']}")
        for mname, model in models.items():
            for batch in (1, 32):
                for dtype in ("fp32", "fp16"):
                    r = bench(model, device, batch, dtype, warmup, iters)
                    if r is None:
                        print(f"  {dev_name:<5} {mname:<32} b{batch:<3} {dtype}  SKIPPED "
                              f"(fp16 not benchmarked on CPU)")
                        continue
                    rows.append({"device": dev_name, "model": mname, "batch": batch,
                                 "dtype": dtype, **r})
                    print(f"  {dev_name:<5} {mname:<32} b{batch:<3} {dtype}  "
                          f"median {r['median_ms']:8.3f} ms  IQR {r['iqr_ms']:6.3f}  "
                          f"per-img {r['per_image_median_ms']:7.3f} ms  "
                          f"{r['fps_from_median']:8.1f} img/s  (n={iters})")
        del models
        if dev_name == "cuda":
            torch.cuda.empty_cache()

    # speed-up ratios, matched on (device, batch, dtype)
    print("\n=== teacher -> student speed-up (median-based, matched config) ===")
    ratios = []
    for dev in {r["device"] for r in rows}:
        for batch in (1, 32):
            for dtype in ("fp32", "fp16"):
                t = next((r for r in rows if r["device"] == dev and r["batch"] == batch
                          and r["dtype"] == dtype and "teacher" in r["model"]), None)
                s = next((r for r in rows if r["device"] == dev and r["batch"] == batch
                          and r["dtype"] == dtype and "student" in r["model"]), None)
                if not (t and s):
                    continue
                ratio = t["median_ms"] / s["median_ms"]
                ratios.append({"device": dev, "batch": batch, "dtype": dtype,
                               "teacher_median_ms": t["median_ms"],
                               "student_median_ms": s["median_ms"], "speedup": ratio})
                print(f"  {dev:<5} b{batch:<3} {dtype}: {t['median_ms']:8.3f} -> "
                      f"{s['median_ms']:7.3f} ms  = {ratio:5.2f}x faster")

    suffix = f"_{args.tag}" if args.tag else ""
    with open(OUT_DIR / f"latency_benchmark{suffix}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (OUT_DIR / f"latency_benchmark{suffix}.json").write_text(
        json.dumps({"manifest": manifest, "measurements": rows, "speedups": ratios}, indent=2),
        encoding="utf-8")
    print(f"\nWrote {OUT_DIR / f'latency_benchmark{suffix}.csv'}")
    print(f"Wrote {OUT_DIR / f'latency_benchmark{suffix}.json'}")


if __name__ == "__main__":
    main()
