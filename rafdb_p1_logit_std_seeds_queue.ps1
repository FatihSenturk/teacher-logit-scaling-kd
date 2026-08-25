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
# P1 -- logit_std from n=1 to n=3.  *** PRE-REGISTERED ***
#
# ---------------------------------------------------------------------------
# FROZEN PREDICTION (written before any run in this queue starts; this file's
# mtime precedes the first run directory's timestamp, which train_rafdb_kd.py
# stamps at launch and cannot be back-dated -- the same evidence standard used
# for B-007, B-010 and B-015, see diagnostics/PREREGISTRATIONS.md).
#
#   P1.1  Delta_ECE > 0 for ALL THREE teachers (logit standardisation makes the
#         student's calibration WORSE, never better).
#   P1.2  Sign consistency 3/3 across seeds {42, 1, 43} within every teacher.
#   P1.3  The accuracy effect stays SMALLER than the calibration effect when
#         both are expressed in units of the matched baseline's seed sd
#         (|d_acc|/acc_sd  <  |d_ECE|/ece_sd), for every teacher.
#
# FALSIFICATION CONSEQUENCE, stated in advance: if any of P1.1-P1.3 fails, the
# phrase "the most destructive intervention" is WITHDRAWN from the paper and
# logit_std is reported as an inconsistent effect. Specifically:
#   - P1.1 or P1.2 fails -> the direction claim dies; report as null.
#   - P1.3 fails         -> the "accuracy-only ablation misleads" framing dies
#                           for this row, because the accuracy axis would then
#                           show the effect just as loudly. The row stays in
#                           T5 as an ordinary mechanism result.
#
# CURRENT n=1 EVIDENCE THIS IS TESTING (seed 42, @swa / @best / @last):
#   primary  d_ECE +0.0802 / +0.1195 / +0.1113   d_acc -0.59 / -0.55 / -0.49
#   stage1   d_ECE +0.0881 / +0.1255 / +0.1213   d_acc -0.23 / -0.36 / -0.95
#   vae9182  d_ECE +0.1381 / +0.1529 / +0.1720   d_acc -0.03 / -0.29 / -0.42
# ---------------------------------------------------------------------------
#
# SINGLE-VARIABLE DISCIPLINE. The command below is copied verbatim from
# run_rafdb_component_ablation_3teacher_swa200.ps1 (the queue that produced the
# seed-42 logit_std runs), including --class-weight-mode effective_number,
# --workers 8, --mixup 0.1 and --label-smoothing 0.1. Verified against the
# existing runs' own run_args.json. The ONLY difference is --seed.
#
# Each new run is differenced against the baseline of the SAME teacher and the
# SAME seed, which already exist at seeds 42/1/43 for all three teachers -- so
# this queue adds no control runs and the pairing stays within-seed.
#
# train_rafdb_kd.py has NO --resume; on a crash resume with -Stream/-StartIndex.
# ============================================================================

$teachers = @{
    stage1  = @{ Tag = "stage1";  Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"; HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    primary = @{ Tag = "primary"; Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt";                    HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    vae9182 = @{ Tag = "vae9182"; Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt";  HeadArgs = @("--teacher-vae-head") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
$seeds = @(1, 43)

$stages = @()
foreach ($t in @("stage1", "primary", "vae9182")) {
    foreach ($s in $seeds) { $stages += @{ TeacherKey = $t; Seed = $s } }
}
# Interleave so both streams carry one run of each teacher early; if the queue is
# cut short we still have partial coverage across teachers rather than all of one.
$streams = @{ A = @(); B = @() }
for ($i = 0; $i -lt $stages.Count; $i++) {
    if ($i % 2 -eq 0) { $streams.A += $stages[$i] } else { $streams.B += $stages[$i] }
}

function Get-Build {
    param($Stage)
    $t = $teachers[$Stage.TeacherKey]
    $runName = "RAFDB_$($t.Tag)_logit_std_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$($t.Ckpt)",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "400",
        "--batch-size", "64",
        "--workers", "8",
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
        "--class-weight-mode", "effective_number",
        "--class-weight-beta", "0.9999",
        "--scheduler-name", "cosine_warm_restarts",
        "--min-lr", "1e-6",
        "--gamma", "0.98",
        "--scheduler-t0", "10",
        "--scheduler-t-mult", "2",
        "--swa", "--swa-start", "200", "--swa-lr", "0.0001",
        "--seed", "$($Stage.Seed)",
        "--logit-std-enable"
    ) + $t.HeadArgs
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
        Write-Host "########## P1 ${Stream} $Label ($($b.RunName)), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        # `| Out-Host` is REQUIRED: without it the native process's stdout leaks into this
        # function's return value as an array, and `-not $array` is always $false, so a failed
        # run reads as success. This bit the campaign once already.
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
Write-Host "=== P1 logit_std seed replicates, stream $Stream : $($queue.Count) run(s), starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $queue.Count; $i++) {
    $st = $queue[$i]
    $label = "$($st.TeacherKey)_seed$($st.Seed)"
    if (-not (Invoke-Run -Stage $st -Label $label)) {
        Write-Host "!!! P1 stream $Stream FAILED at index $i ($label). Resume: -Stream $Stream -StartIndex $i"
        exit 1
    }
}
Write-Host ""
Write-Host "=== P1 logit_std stream $Stream completed successfully ($($queue.Count) runs). ==="
