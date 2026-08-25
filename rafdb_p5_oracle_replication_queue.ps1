param(
    [ValidateSet("S")]
    [string]$Stream = "S",
    [int]$StartIndex = 0,
    [int]$Workers = 12,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# P5 -- does the gate:oracle_error calibration harm REPLICATE on the two
# over-confident teachers? 6 runs: {stage1, primary} x {42, 1, 43}.
#
# *** PRE-DECLARED RESOLUTION ATTEMPT, NOT A PREDICTION. ***
# diagnostics/PREREGISTRATIONS.md, section "A8-tamamlama - P5", written before
# this file ran. No new prediction is attached. The DECISION THRESHOLD is fixed
# in that declaration in advance and is repeated here so it cannot drift:
#
#   3/3 seeds same sign AND |dECE| >= 2x that teacher's own cw=none control's
#   ECE seed sd  ->  ESTABLISHED (harm present on that teacher)
#   otherwise    ->  UNRESOLVED
#
#   bars, measured in P4 (n=3 each): stage1 0.0021, primary 0.0033
#
# ---------------------------------------------------------------------------
# WHAT THIS SEPARATES
#
# After P4: on VAE9182 the oracle gate degrades student ECE by +0.0056 (2.08x
# the control's seed sd, 3/3 seeds, pre-registered in A8). On stage1/primary the
# REAL learned-signal gate rows show nothing at n=1. Two readings survive:
#   (a) the harm is specific to VAE9182;
#   (b) the harm is there too, but stage1/primary students sit at ECE
#       0.0745/0.0755 -- 2.7x VAE9182's 0.0278 -- so the same absolute harm is
#       7.5% relative instead of 20% and hides inside a bigger, noisier base.
#
# WHY 6 RUNS AND NOT 4. An earlier note of mine said "4 runs"; that was an
# arithmetic slip. stage1 and primary have NO oracle_error run at all (their gate
# rows are mean_logvar and target_logvar), so 2 teachers x 3 seeds is 6 entirely
# new runs. And a replication has to repeat the SAME manipulation: testing an
# oracle-established finding against real-signal rows is not like for like --
# that asymmetry is exactly what made P4's null hard to read. Extending the
# existing real-signal cells to n=3 is a different question (10 runs); this queue
# does not ask it.
#
# The oracle signal is synthetic (1.0 exactly where the teacher's own top-1 is
# wrong) and kd_uncertainty.resolve_uncertainty dispatches it BEFORE the
# mu/logvar requirement, so it is available on any teacher head -- verified in
# code, not assumed.
#
# ---------------------------------------------------------------------------
# EXACTLY ONE VARIABLE MOVES vs. P4's controls: the two gate flags. Every other
# flag was read out of
#   RAFDB_vae9182_gate_oracle_error_b070_T6_224_400e_swa200_seed1/run_args.json
# and the teachers out of their own baselines, rather than reconstructed.
#
# train_rafdb_kd.py has NO --resume; on a crash resume with -StartIndex.
# Sequential at --workers 12: 2.33 h/run measured, ~14.0 h for six.
# ============================================================================

$teachers = @{
    stage1  = @{ Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt" }
    primary = @{ Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt" }
}
$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# Seed 42 on both teachers first: if the queue is cut short, two teachers at one
# shared seed is more informative than one teacher at three.
$stages = @(
    @{ Teacher = "stage1";  Seed = 42 },
    @{ Teacher = "primary"; Seed = 42 },
    @{ Teacher = "stage1";  Seed = 1 },
    @{ Teacher = "primary"; Seed = 1 },
    @{ Teacher = "stage1";  Seed = 43 },
    @{ Teacher = "primary"; Seed = 43 }
)
$streams = @{ S = $stages }

function Get-Build {
    param($Stage)
    $t = $teachers[$Stage.Teacher]
    $runName = "RAFDB_$($Stage.Teacher)_gate_oracle_error_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
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
        "--seed", "$($Stage.Seed)",
        # the only difference from P4's controls -- gate defaults match the
        # existing VAE9182 oracle run exactly (alpha_lo 0.1, alpha_hi 0.7, k 2.0,
        # tau 0.0, norm batch), so they are left at their defaults rather than
        # re-specified and risking a silent drift.
        "--gate-enable",
        "--gate-uncertainty-source", "oracle_error"
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
        Write-Host "########## P5 $Label ($($b.RunName)), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        # `| Out-Host` is REQUIRED: without it the native process's stdout leaks into this
        # function's return value as an array and `-not $result` is always false.
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
Write-Host "=== P5 oracle replication, $($queue.Count) run(s), from index $StartIndex ==="
for ($i = $StartIndex; $i -lt $queue.Count; $i++) {
    $st = $queue[$i]
    $label = "$($st.Teacher)_seed$($st.Seed)"
    if (-not (Invoke-Run -Stage $st -Label $label)) {
        Write-Host "!!! P5 FAILED at index $i ($label). Resume: -StartIndex $i"
        exit 1
    }
}
Write-Host ""
Write-Host "=== P5 completed successfully ($($queue.Count) runs). ==="
