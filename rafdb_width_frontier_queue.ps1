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
# Student width sweep -> a PLOTTABLE efficiency frontier (P5's remaining hole)
#
# WHY. diagnostics/p5_efficiency_frontier.py currently reports is_frontier_plottable = FALSE.
# The three student variants measured so far (vich head / linear head / etc.) span only 1.005x in
# parameters, because the only thing that differed was head size -- that is not a capacity range,
# so no accuracy-vs-cost curve can be drawn. A real frontier needs a real capacity spread:
#
#     width_mult 0.50 -> 0.712 M params      (measured, not estimated)
#     width_mult 0.75 -> 1.380 M
#     width_mult 1.00 -> 2.248 M             = 3.16x spread, well over P5's 1.15x threshold
#
# ⚠️ THE CONFOUND THIS QUEUE EXISTS TO AVOID -- and the reason it is 9 runs, not 6.
# train_rafdb_kd.py:157-160 loads ImageNet weights ONLY when width_mult == 1.0:
#       if args.student_pretrained and args.width_mult == 1.0: student.load_pretrained_weights()
#       elif args.student_pretrained: print("Skipping ImageNet pretrained load because ...")
# torchvision ships MobileNetV2 weights at width 1.0 only, so 0.50 and 0.75 train FROM SCRATCH
# whether you ask for it or not. A naive {0.50, 0.75, 1.00} sweep would therefore vary capacity
# AND initialisation together: the small models would be penalised twice and the frontier would
# overstate the accuracy cost of shrinking -- an error in exactly the direction that matters for
# an efficiency claim.
#
# So width 1.00 is run a THIRD time with --no-student-pretrained, giving a frontier whose three
# points share one initialisation regime (all from scratch). The EXISTING pretrained width-1.0
# baseline runs stay in the analysis as a separate annotated point showing what ImageNet init is
# worth at fixed capacity -- a bonus contrast, not a frontier point.
#
#   frontier (from scratch, comparable) : w0.50, w0.75, w1.00-noimagenet   x 3 seeds = 9 runs
#   annotation (already done, free)     : w1.00 + ImageNet  (90.276 +/- 0.156 acc, 0.0330 ECE @swa)
#
# SINGLE-VARIABLE DISCIPLINE. Every flag below is copied from the existing VAE9182 baseline's own
# run_args.json (results/unified_students/RAFDB_vae9182_betaKD_b070_T6_224_best_400e_swa200/),
# so these runs differ from that baseline in exactly --width-mult and --no-student-pretrained.
# Teacher is VAE9182 (the best-calibrated teacher, B-001/B-007), unmanipulated: no
# --teacher-temperature-scale, no mechanism flags.
#
# BONUS THIS BUYS FOR FREE. The runs also produce ECE at three student capacities, which tests
# something B-007/B-015 never did: is the calibration law student-capacity dependent, or does a
# 0.7 M student inherit teacher calibration the same way a 2.2 M one does? Scored by the existing
# diagnostics/selection_audit_table.py (no new tooling).
#
# train_rafdb_kd.py has NO --resume; on a crash/outage resume with -Stream/-StartIndex.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"
$seeds = @(42, 1, 43)

# smallest-first so the cheapest runs validate the pipeline before the expensive ones,
# and seed 42 first within each width so a full 3-point seed-42 curve appears early.
$arms = @(
    @{ Tag = "w050"; Width = "0.5";  NoPre = $true },
    @{ Tag = "w075"; Width = "0.75"; NoPre = $true },
    @{ Tag = "w100ns"; Width = "1.0"; NoPre = $true }
)

$stages = @()
foreach ($a in $arms) { foreach ($s in $seeds) { $stages += @{ Arm = $a; Seed = $s } } }
# interleave into two streams so both widths progress in parallel rather than one stream
# finishing all the cheap runs while the other does all the expensive ones
$streams = @{ A = @(); B = @() }
for ($i = 0; $i -lt $stages.Count; $i++) {
    if ($i % 2 -eq 0) { $streams.A += $stages[$i] } else { $streams.B += $stages[$i] }
}

function Get-Cmd {
    param($Stage)
    $arm = $Stage.Arm
    $runName = "RAFDB_vae9182_frontier_$($arm.Tag)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"
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
        "--width-mult", "$($arm.Width)",
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
        "--seed", "$($Stage.Seed)"
    )
    if ($arm.NoPre) { $cmd += "--no-student-pretrained" }
    return @{ Cmd = $cmd; RunName = $runName; Width = $arm.Width }
}

function Invoke-Run {
    param($Stage, [string]$Label)
    $b = Get-Cmd -Stage $Stage
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        $t0 = Get-Date
        Write-Host ""
        Write-Host "########## FRONTIER ${Stream} $Label ($($b.RunName)), width=$($b.Width), attempt $attempt/$MaxRetries : $($t0.ToString('yyyy-MM-dd HH:mm:ss')) ##########"
        Write-Host "Command: python -u $($b.Cmd -join ' ')"
        & python -u @($b.Cmd) | Out-Host
        $exitCode = $LASTEXITCODE
        $elapsed = (Get-Date) - $t0
        Write-Host "[$Label] Exit code: $exitCode after $([math]::Round($elapsed.TotalHours,2))h at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) {
            Write-Host "[$Label] WALL-CLOCK $([math]::Round($elapsed.TotalHours,2))h/run (width $($b.Width))"
            return $true
        }
        Write-Host "[$Label] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

if ($DryRun) {
    Write-Host "=== DRY RUN: STREAM $Stream ($($streams[$Stream].Count) stages, nothing executed) ==="
    foreach ($st in $streams[$Stream]) {
        $b = Get-Cmd -Stage $st
        Write-Host ""
        Write-Host "--- $($b.RunName)   (width $($b.Width))"
        Write-Host "python -u $($b.Cmd -join ' ')"
    }
    exit 0
}

$list = $streams[$Stream]
Write-Host "=== RAF-DB width frontier, STREAM $Stream : $($list.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $list.Count; $i++) {
    $st = $list[$i]
    $label = "$($st.Arm.Tag)_seed$($st.Seed)"
    if (-not (Invoke-Run -Stage $st -Label $label)) {
        Write-Host "=== STREAM ${Stream}: $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} width frontier ($($list.Count) runs) completed successfully. ==="
exit 0
