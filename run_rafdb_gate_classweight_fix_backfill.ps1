param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [int]$WaitPollSeconds = 300,
    [switch]$SkipWaitForStreams,
    [ValidateSet("stage1_gate", "primary_gate", "vae9182_gate")]
    [string]$StartAt = "stage1_gate"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# Backfill (2026-07-18): the component-ablation "gate" stage for all 3
# teachers crashed 3x and was silently skipped by both parallel streams
# (run_rafdb_component_ablation_3teacher_swa200.ps1 / ...streamB.ps1) due to
# a real, documented incompatibility -- kd_common.py:190 hard-errors
# gate_enable + class_weight_mode != "none" (class-weighted CE isn't exactly
# per-sample decomposable, so gate's per-sample alpha blend can't reproduce
# it). The base "best recipe" uses --class-weight-mode effective_number,
# which every other component tolerates but gate does not.
#
# Fix: same recipe as the other component-ablation runs, but
# --class-weight-mode none for these 3 gate runs specifically (the only
# viable way to get a valid gate result under this recipe family).
#
# Also fixed (2026-07-18): the two streams' retry loops had a latent bug --
# `& python -u @cmd` inside a function invoked via `$ok = Invoke-...`
# captured the native process's stdout into the function's own return value
# as an array (e.g. @("some output line", $false)), and `-not $array` is
# always $false for a non-empty array regardless of its last element --
# so a genuinely failed stage was never detected as failed. Fixed here (and
# backported into the other queue scripts) by piping the native call through
# `| Out-Host` (prints normally, does not leak into the return stream).

$teachers = @{
    stage1  = @{ Tag = "stage1";  Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"; HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    primary = @{ Tag = "primary"; Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt";                    HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    vae9182 = @{ Tag = "vae9182"; Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt";  HeadArgs = @("--teacher-vae-head") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

function Invoke-GateFixedStage {
    param($Teacher, [string]$StageName)

    $runName = "RAFDB_$($Teacher.Tag)_gate_noclassweight_b070_T6_224_400e_swa200"
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$($Teacher.Ckpt)",
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
        "--seed", "42",
        "--gate-enable", "--gate-uncertainty-source", "mean_logvar"
    ) + $Teacher.HeadArgs

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## STAGE: $StageName ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        & python -u @cmd | Out-Host
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageName] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

        if ($exitCode -eq 0) { return $true }
        Write-Host "[$StageName] Exited non-zero. No --resume support -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

if (-not $SkipWaitForStreams) {
    $logA = Join-Path $PSScriptRoot "rafdb_component_ablation_3teacher_swa200.log"
    $logB = Join-Path $PSScriptRoot "rafdb_component_ablation_streamB.log"
    Write-Host "Waiting for both Stream A and Stream B to finish (polling every ${WaitPollSeconds}s)..."
    while ($true) {
        $aDone = (Test-Path $logA) -and (Select-String -Path $logA -Pattern "Stream A component ablation .* completed successfully" -Quiet)
        $bDone = (Test-Path $logB) -and (Select-String -Path $logB -Pattern "Stream B component ablation .* completed successfully" -Quiet)
        if ($aDone -and $bDone) {
            Write-Host "Both streams done. Starting gate class-weight-fix backfill."
            break
        }
        Start-Sleep -Seconds $WaitPollSeconds
    }
}

$stageOrder = @(
    @{ TeacherKey = "stage1";  Name = "stage1_gate" },
    @{ TeacherKey = "primary"; Name = "primary_gate" },
    @{ TeacherKey = "vae9182"; Name = "vae9182_gate" }
)
$stageNames = $stageOrder | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stageOrder.Count; $i++) {
    $stage = $stageOrder[$i]
    $ok = Invoke-GateFixedStage -Teacher $teachers[$stage.TeacherKey] -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping gate backfill: stage $($stage.Name) did not complete after $MaxRetries attempts. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== Gate class-weight-fix backfill (3 runs) completed successfully. ==="
exit 0
