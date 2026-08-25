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
# P3 -- does the teacher-ECE -> student-ECE slope change with student capacity?
#
# *** EXPLORATORY. NO PREDICTION IS MADE OR CLAIMED. ***
#
# This file deliberately contains NO frozen prediction, and the paper will
# report this analysis as exploratory. It is recorded here anyway, before the
# runs, so that the QUESTION and the ANALYSIS PLAN are on record and cannot be
# reverse-engineered from the result afterwards. Pre-registering a question is
# not the same as pre-registering a prediction, and only the latter would let
# us write "pre-registered" next to the outcome.
#
# THE QUESTION. B-007/B-015 established that student ECE is governed by teacher
# calibration, measured entirely at one student capacity (2.248 M). The dose-
# response slope there is
#       student_ECE = +0.0237 + 0.7137 * teacher_ECE     (R^2 = 0.999, n = 5)
# Nothing is known about whether that slope is a property of the law or of that
# particular student. A 0.71 M student has less capacity to represent a soft
# target; the slope could plausibly flatten (small student cannot follow the
# teacher's miscalibration) or steepen (small student is dominated by it).
#
# WHY THESE FOUR RUNS. w050 already has T=1.0 at seeds {42, 1, 43}. Adding
# T=1.7 and T=2.2 at two of those seeds gives three temperatures at matched
# seeds -- the minimum for a slope. T=1.7 and T=2.2 are chosen because at
# 2.248 M they move student ECE from 0.0330 to 0.1282 and 0.2109 respectively:
# the widest available lever, so a capacity-dependent slope shows up most
# clearly. Small-T points are NOT run: the 2.248 M curve is already nearly
# linear over 0.0136-0.2622 teacher ECE, so the information is at the far end.
#
#   w050 (0.712 M, scratch)  x  T in {1.7, 2.2}  x  seeds {42, 1}  =  4 runs
#
# ANALYSIS PLAN, fixed in advance (so the fit cannot be chosen after seeing it):
#   - Fit student_ECE = a + b * teacher_ECE by ordinary least squares on the
#     three w050 points (T = 1.0, 1.7, 2.2), teacher ECE taken from
#     diagnostics/teacher_ece_grid (closed form, already computed).
#   - Compare b_w050 against b_2248 = 0.7137 fitted on the SAME three
#     temperatures, not on all five -- comparing a 3-point fit against a
#     5-point fit would confound capacity with the fit's support.
#   - Report both slopes with their R^2 and n. With one seed pair per point the
#     slope has no error bar; state that, do not manufacture one.
#   - @swa is primary, @best/@last reported alongside.
#
# CONFOUND ALREADY HANDLED. w050 is scratch-init (train_rafdb_kd.py loads
# ImageNet weights only at width_mult == 1.0), while the 2.248 M dose-response
# curve is pre-trained. So b_w050 vs b_2248 mixes capacity with initialisation.
# The scratch 2.248 M runs at T=1.0 pin the initialisation offset at one point,
# but NOT the slope -- an honest comparison must say that the two slopes differ
# in two respects, and that separating them needs a scratch dose-response at
# 2.248 M (4 more runs, not launched).
#
# SINGLE-VARIABLE DISCIPLINE. Command copied verbatim from
# rafdb_width_frontier_queue.ps1 (which produced the w050 T=1.0 runs); the only
# addition is --teacher-temperature-scale.
#
# train_rafdb_kd.py has NO --resume; on a crash resume with -Stream/-StartIndex.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"

$stages = @(
    @{ T = "1.7"; Tag = "T170"; Seed = 42 },
    @{ T = "2.2"; Tag = "T220"; Seed = 42 },
    @{ T = "1.7"; Tag = "T170"; Seed = 1 },
    @{ T = "2.2"; Tag = "T220"; Seed = 1 }
)
# Seed 42 first on both streams so a complete single-seed 3-point curve exists
# early; if the queue is cut short that is still a usable (if n=1) slope.
$streams = @{ A = @(); B = @() }
for ($i = 0; $i -lt $stages.Count; $i++) {
    if ($i % 2 -eq 0) { $streams.A += $stages[$i] } else { $streams.B += $stages[$i] }
}

function Get-Build {
    param($Stage)
    $runName = "RAFDB_vae9182_frontier_w050_tempscale_$($Stage.Tag)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$teacherCkpt",
        "--teacher-vae-head",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--aligned-dir", "data\rafdb_aligned",
        "--metadata", "data\rafdb_aligned\metadata_rafdb_poster_var.csv",
        "--train-folds", "2", "--val-folds", "3",
        "--epochs", "400",
        "--batch-size", "64",
        "--workers", "8",
        "--img-size", "224",
        "--resize-size", "0",
        "--augment-preset", "kd",
        "--ra-mag", "7",
        "--random-erasing-p", "0.1",
        "--student-head-type", "vich",
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3",
        "--student-embedding-dim", "768",
        "--no-vich-sampling",
        "--vich-init-logvar-bias", "-5.0",
        "--beta-vich", "0.0001",
        "--dropout", "0.5",
        "--width-mult", "0.5",
        "--alpha", "0.3",
        "--temperature", "6",
        "--label-smoothing", "0.1",
        "--mixup", "0.1",
        "--class-weight-mode", "effective_number",
        "--class-weight-beta", "0.9999",
        "--use-amp",
        "--lr", "3e-4",
        "--weight-decay", "1e-4",
        "--scheduler-name", "cosine_warm_restarts",
        "--min-lr", "1e-6",
        "--scheduler-t0", "10",
        "--scheduler-t-mult", "2",
        "--gamma", "0.98",
        "--swa", "--swa-start", "200", "--swa-lr", "0.0001",
        "--seed", "$($Stage.Seed)",
        "--no-student-pretrained",
        "--teacher-temperature-scale", "$($Stage.T)"
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
        Write-Host "########## P3 ${Stream} $Label ($($b.RunName)), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
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
Write-Host "=== P3 capacity-slope (w050 tempscale), stream $Stream : $($queue.Count) run(s), from index $StartIndex ==="
for ($i = $StartIndex; $i -lt $queue.Count; $i++) {
    $st = $queue[$i]
    $label = "$($st.Tag)_seed$($st.Seed)"
    if (-not (Invoke-Run -Stage $st -Label $label)) {
        Write-Host "!!! P3 stream $Stream FAILED at index $i ($label). Resume: -Stream $Stream -StartIndex $i"
        exit 1
    }
}
Write-Host ""
Write-Host "=== P3 stream $Stream completed successfully ($($queue.Count) runs). ==="
