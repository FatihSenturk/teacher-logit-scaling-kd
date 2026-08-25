param(
    [ValidateSet("A", "B")]
    [string]$Stream = "A",
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# P2 -- gate:oracle_error from n=1 to n=3, WITH ITS OWN MATCHED CONTROL.
# *** PRE-REGISTERED ***
#
# ---------------------------------------------------------------------------
# FROZEN PREDICTION (frozen before any run in this queue starts; this file's
# mtime precedes the first run directory's timestamp, which train_rafdb_kd.py
# stamps at launch and cannot be back-dated).
#
#   P2.1  NULL on accuracy:    |mean d_acc| <= the control's own seed sd.
#   P2.2  NULL on calibration: |mean d_ECE| <= the control's own seed sd.
#   P2.3  Sign inconsistency:  the 3 per-seed signs are NOT all equal, on at
#         least one of the two axes.
#
# WHY A NULL IS THE STRONG RESULT HERE. `oracle_error` is a synthetic
# perfect-information gate signal (1.0 exactly when the teacher's own top-1 is
# wrong). It is an UPPER BOUND on what any per-sample weighting scheme could
# achieve on this dataset. If even perfect information does not beat the
# control, the weighting axis is closed on its own terms -- not merely "we
# could not find a good signal". Confirming P2.1-P2.3 therefore STRENGTHENS
# the D1=B closure rather than being an absence of evidence.
#
# FALSIFICATION CONSEQUENCE, stated in advance: if the oracle wins
# consistently (both axes, 3/3 same sign, beyond the control's seed sd), the
# claim "the weighting axis is closed" is FALSE and the paper is re-framed
# around per-sample weighting with a realisable-signal gap as the open problem.
# ---------------------------------------------------------------------------
#
# *** WHY THIS QUEUE RUNS 5 JOBS AND NOT 2 -- A CONTROL DEFECT BEING FIXED ***
#
# kd_common.py hard-errors on gate_enable + class_weight_mode != "none": the
# class-weighted CE normalises by sum(w_i) batch-wide, so it is not exactly
# decomposable per sample and the gate's per-sample alpha blend cannot
# reproduce it. Consequently EVERY gate run in this campaign was launched with
# --class-weight-mode none, while the standard baseline uses
# --class-weight-mode effective_number.
#
# T5 currently differences those gate runs against the effective_number
# baseline. That comparison changes TWO things at once (the gate AND the class
# weighting), so every gate delta in T5 is confounded -- including the seed-42
# oracle row this queue is extending. Adding two more seeds to a confounded
# contrast would produce a confounded n=3 instead of a confounded n=1.
#
# So this queue also runs the missing control: a plain baseline, same teacher,
# same recipe, --class-weight-mode none, at all three seeds. Then
#     delta = gate(cw=none) - baseline(cw=none)
# varies exactly one thing. The new control also repairs the other five gate
# rows in T5, which can be re-differenced against it at seed 42 with no extra
# GPU cost.
#
#   gate:oracle_error   vae9182  seeds {1, 43}       2 runs  (seed 42 exists)
#   baseline cw=none    vae9182  seeds {42, 1, 43}   3 runs  (NEW control)
#
# SINGLE-VARIABLE DISCIPLINE. The command is copied verbatim from
# run_rafdb_gate_signal_followup_queue.ps1 (which produced the seed-42 oracle
# run), including --workers 12 and --class-weight-mode none, verified against
# that run's own run_args.json. Control rows are the identical command with the
# two gate flags removed -- nothing else differs.
#
# train_rafdb_kd.py has NO --resume; on a crash resume with -Stream/-StartIndex.
# ============================================================================

$teacher = @{ Tag = "vae9182"; Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"; HeadArgs = @("--teacher-vae-head") }
$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# Controls first: if the queue is cut short, a complete 3-seed control is worth
# more than a complete treatment with nothing to difference it against.
$stages = @(
    @{ Kind = "control"; Seed = 42 },
    @{ Kind = "control"; Seed = 1 },
    @{ Kind = "control"; Seed = 43 },
    @{ Kind = "gate";    Seed = 1 },
    @{ Kind = "gate";    Seed = 43 }
)
$streams = @{ A = @(); B = @() }
for ($i = 0; $i -lt $stages.Count; $i++) {
    if ($i % 2 -eq 0) { $streams.A += $stages[$i] } else { $streams.B += $stages[$i] }
}

function Get-Build {
    param($Stage)
    if ($Stage.Kind -eq "gate") {
        $runName = "RAFDB_$($teacher.Tag)_gate_oracle_error_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
    } else {
        $runName = "RAFDB_$($teacher.Tag)_baseline_noclassweight_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
    }
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$($teacher.Ckpt)",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "400",
        "--batch-size", "64",
        "--workers", "12",
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
    if ($Stage.Kind -eq "gate") {
        $cmd += @("--gate-enable", "--gate-uncertainty-source", "oracle_error")
    }
    $cmd += $teacher.HeadArgs
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
        Write-Host "########## P2 ${Stream} $Label ($($b.RunName)), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        # `| Out-Host` is REQUIRED -- see the note in rafdb_p1_logit_std_seeds_queue.ps1.
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
Write-Host "=== P2 gate:oracle_error + matched control, stream $Stream : $($queue.Count) run(s), from index $StartIndex ==="
for ($i = $StartIndex; $i -lt $queue.Count; $i++) {
    $st = $queue[$i]
    $label = "$($st.Kind)_seed$($st.Seed)"
    if (-not (Invoke-Run -Stage $st -Label $label)) {
        Write-Host "!!! P2 stream $Stream FAILED at index $i ($label). Resume: -Stream $Stream -StartIndex $i"
        exit 1
    }
}
Write-Host ""
Write-Host "=== P2 stream $Stream completed successfully ($($queue.Count) runs). ==="
