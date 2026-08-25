param(
    # "S" = all six runs in ONE sequential queue (the mode actually used -- see the timing note
    # below). "A"/"B" keep the two-concurrent-stream layout available for a future machine.
    [ValidateSet("A", "B", "S")]
    [string]$Stream = "S",
    [int]$StartIndex = 0,
    # 12 suits sequential (one trainer owns the machine); drop to 8 when running A and B together,
    # or the paging file cannot back both sets of dataloader workers (Windows error 1455,
    # ERROR_COMMITMENT_LIMIT, which is what forced P2 sequential).
    [int]$Workers = 12,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# P4 -- the missing `class_weight_mode=none` baseline for the stage1 and primary
# teachers, 3 seeds each. Finishes the control repair A8 started.
#
# *** PRE-DECLARED CONTROL COMPLETION, NOT A PRE-REGISTERED PREDICTION. ***
# See diagnostics/PREREGISTRATIONS.md, section "A8-tamamlama - P4", written
# before this file ran. No new prediction is attached to these six runs, and
# the declaration commits in advance to putting the four repaired gate rows
# into T5 whichever way the numbers come out. That commitment is the point:
# it is what keeps a control completion from turning into a result hunt.
#
# ---------------------------------------------------------------------------
# WHY THESE SIX RUNS EXIST
#
# kd_common.py hard-errors on gate_enable + class_weight_mode != "none" (the
# class-weighted CE normalises by sum(w_i) batch-wide and is therefore not
# exactly decomposable per sample, which the gate's per-sample alpha blend
# requires). So EVERY gate run in this campaign was launched with
# --class-weight-mode none while the standard baseline used effective_number.
#
# P2 produced the matched control for VAE9182 and it changed the answer: against
# the contaminated control gate:oracle read as ECE-neutral (+0.0004 +/- 0.0011,
# signs +-+); against the clean one it is +0.0056 +/- 0.0040 with 3/3 agreeing
# signs. Class weighting was degrading the control's own ECE by 0.0052 and
# cancelling the gate's harm almost exactly.
#
# But P2 only covered ONE teacher. The four remaining 400e/SWA@200 gate rows --
# {stage1, primary} x {mean_logvar, target_logvar} -- still have no control at
# their own class weighting and were dropped from T5 on 2026-07-30 rather than
# differenced against the wrong one. These six runs are those controls.
#
# ---------------------------------------------------------------------------
# EXACTLY ONE VARIABLE MOVES vs. the existing baselines.
#
# Every flag below was read out of the run_args.json of
#   RAFDB_stage1_baseline_b070_T6_224_400e_swa200_seed1   and
#   RAFDB_primary_baseline_b070_T6_224_400e_swa200_seed1
# rather than reconstructed from memory, and the ONLY difference is
#   --class-weight-mode none      (those runs used effective_number)
# Note primary's teacher is the promoted checkpoint file, not a timestamp dir;
# that is what its own baselines used and copying it keeps the pairing exact.
#
# train_rafdb_kd.py has NO --resume; on a crash resume with -Stream/-StartIndex.
# ============================================================================

$teachers = @{
    stage1  = @{ Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt" }
    primary = @{ Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt" }
}
$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# SEQUENTIAL, NOT PAIRED -- and the honest reason is RISK, not throughput.
#
# The throughput argument I first wrote here was wrong, because both of my early rate measurements
# were taken over too few epochs and were dominated by process startup (a 556 MB teacher load plus
# cudnn warmup and dataloader spin-up, ~100 s, which over 9 epochs inflates the apparent rate by
# ~11 s/epoch). Measured properly, as a two-point wall-clock difference over 20 epochs (6 -> 26):
#
#   sequential, --workers 12 : 21.0 s/epoch -> 2.33 h/run -> 14.0 h for six   [MEASURED, and
#                              independently consistent with P2's four solo runs: 2.34 / 2.29 /
#                              2.31 / 2.28 h]
#   paired,     --workers 8  : ~38 s/epoch  -> ~4.2 h/run -> ~12.7 h for six, since the two
#                              streams advance concurrently (3 runs each)   [INFERRED from tqdm's
#                              36 s train loop plus ~2 s validation; never validated over a long
#                              window, because the paired launch was stopped. Weaker evidence than
#                              the sequential figure -- do not treat the two as equally solid.]
#
# So pairing was about 1.5 h FASTER, not 2.8 h slower as I first claimed. Sequential is kept anyway
# because on a 14 h job that margin does not justify switching the layout a second time, discarding
# work already done, and re-inviting the error-1455 (ERROR_COMMITMENT_LIMIT) paging failure that
# pairing actually caused in P2 -- with no --resume in train_rafdb_kd.py to recover from it.
#
# The paired launch was stopped 10 epochs in and its two partial run directories were deleted.
#
# Seed 42 first on both teachers: if the queue is cut short, two teachers at one shared seed still
# repairs all four gate rows at n=1, whereas three seeds of one teacher would leave the other two
# rows with no control at all.
$stages = @(
    @{ Teacher = "stage1";  Seed = 42 },
    @{ Teacher = "primary"; Seed = 42 },
    @{ Teacher = "stage1";  Seed = 1 },
    @{ Teacher = "primary"; Seed = 1 },
    @{ Teacher = "stage1";  Seed = 43 },
    @{ Teacher = "primary"; Seed = 43 }
)
$streams = @{ A = @(); B = @(); S = $stages }
for ($i = 0; $i -lt $stages.Count; $i++) {
    if ($i % 2 -eq 0) { $streams.A += $stages[$i] } else { $streams.B += $stages[$i] }
}

function Get-Build {
    param($Stage)
    $t = $teachers[$Stage.Teacher]
    $runName = "RAFDB_$($Stage.Teacher)_baseline_noclassweight_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$($t.Ckpt)",
        "--teacher-vich-head",
        "--teacher-vich-init-logvar-bias", "0.0",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "400",
        "--batch-size", "64",
        "--workers", "$Workers",
        "--img-size", "224",
        "--resize-size", "0",
        "--augment-preset", "kd",
        "--student-head-type", "vich",
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3",
        "--no-vich-sampling",
        "--alpha", "0.3",
        "--temperature", "6",
        "--label-smoothing", "0.1",
        "--mixup", "0.1",
        "--use-amp",
        "--class-weight-mode", "none",
        "--scheduler-name", "cosine_warm_restarts",
        "--min-lr", "1e-6",
        "--gamma", "0.98",
        "--scheduler-t0", "10",
        "--scheduler-t-mult", "2",
        "--swa", "--swa-start", "200", "--swa-lr", "0.0001",
        "--seed", "$($Stage.Seed)"
    )
    return @{ Cmd = $cmd; RunName = $runName }
}

function Invoke-Run {
    param($Stage, [string]$Label)
    $b = Get-Build -Stage $Stage
    if ($DryRun) {
        Write-Host "[DRYRUN $Label] $($b.RunName)"
        Write-Host "  python -u $($b.Cmd -join ' ')"
        return $true
    }
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        $t0 = Get-Date
        Write-Host ""
        Write-Host "########## P4 ${Stream} $Label ($($b.RunName)), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        # `| Out-Host` is REQUIRED: without it the native process's stdout leaks into this
        # function's return value as an array and `-not $result` is always false, so a failed
        # run reads as a success.
        & python -u @($b.Cmd) | Out-Host
        $exitCode = $LASTEXITCODE
        $elapsed = (Get-Date) - $t0
        Write-Host "[$Label] Exit code: $exitCode after $([math]::Round($elapsed.TotalHours,2))h at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) { return $true }
        Write-Host "[$Label] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

$queue = $streams[$Stream]
Write-Host "=== P4 no-classweight controls, stream $Stream : $($queue.Count) run(s), from index $StartIndex ==="
for ($i = $StartIndex; $i -lt $queue.Count; $i++) {
    $st = $queue[$i]
    $label = "$($st.Teacher)_seed$($st.Seed)"
    if (-not (Invoke-Run -Stage $st -Label $label)) {
        Write-Host "!!! P4 stream $Stream FAILED at index $i ($label). Resume: -Stream $Stream -StartIndex $i"
        exit 1
    }
}
Write-Host ""
Write-Host "=== P4 stream $Stream completed successfully ($($queue.Count) runs). ==="
