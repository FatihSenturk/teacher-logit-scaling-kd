param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [int]$WaitPollSeconds = 300,
    [switch]$SkipWait,
    [ValidateSet("stage1_gate_target_logvar", "primary_gate_target_logvar", "vae9182_gate_oracle_error")]
    [string]$StartAt = "stage1_gate_target_logvar"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-19/20: gate signal follow-up, motivated by diagnostics/
# rafdb_signal_quality_table.py's finding that gate's default
# `mean_logvar` source is inversely correlated with teacher error for all
# 3 teachers, but `target_logvar` is strongly and CORRECTLY signed for the
# two VICH teachers (AUROC 0.700 Stage1, 0.843 Primary -- vs. 0.458 for
# VAE9182, near chance). Real, non-synthetic signal choice (not a post-hoc
# sign flip) -- tests whether gate actually helps once given a signal that
# is known to track error in the right direction.
#
# vae9182_gate_oracle_error uses the new (2026-07-20) `oracle_error` gate
# source (kd_uncertainty.py) -- a synthetic perfect-information signal
# (1.0 iff the teacher's own top-1 prediction is wrong) used to upper-bound
# how much per-sample gating could help on this dataset at all, independent
# of whether any real proxy is good enough. VAE9182 chosen for the oracle
# run since none of its real logvar-derived signals (mean/target/top2/max)
# were usefully signed (all <=0.46 AUROC) -- the oracle isolates "is gating
# structurally useful here" from "is there a good real signal for VAE9182."
#
# Waits for BOTH concurrently-running jobs to finish before starting:
#   - run_rafdb_stage1_200e_noswa_6run.ps1 (rafdb_stage1_200e_noswa_6run.log)
#   - run_rafdb_vae9182_combined_g2g_adaptive_t.ps1 (rafdb_vae9182_combined_g2g_adaptive_t.log)
# Same no-resume caveat as every other queue this session.

$teachers = @{
    stage1  = @{ Tag = "stage1";  Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"; HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    primary = @{ Tag = "primary"; Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt";                    HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    vae9182 = @{ Tag = "vae9182"; Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt";  HeadArgs = @("--teacher-vae-head") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

function Invoke-GateSignalStage {
    param($Teacher, [string]$GateSource, [string]$StageName)

    $runName = "RAFDB_$($Teacher.Tag)_gate_${GateSource}_b070_T6_224_400e_swa200"
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
        "--gate-enable", "--gate-uncertainty-source", "$GateSource"
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

if (-not $SkipWait) {
    $logA = Join-Path $PSScriptRoot "rafdb_stage1_200e_noswa_6run.log"
    $logB = Join-Path $PSScriptRoot "rafdb_vae9182_combined_g2g_adaptive_t.log"
    Write-Host "Waiting for both the 200e_noSWA grid and the combined g2g+adaptive_t run to finish (polling every ${WaitPollSeconds}s)..."
    while ($true) {
        $aDone = (Test-Path $logA) -and (Select-String -Path $logA -Pattern "200e_noSWA 6-run grid completed successfully" -Quiet)
        $bDone = (Test-Path $logB) -and (Select-String -Path $logB -Pattern "vae9182_combined_g2g_adaptive_t completed successfully" -Quiet)
        if ($aDone -and $bDone) {
            Write-Host "Both jobs done. Starting gate signal follow-up queue."
            break
        }
        Start-Sleep -Seconds $WaitPollSeconds
    }
}

$stageOrder = @(
    @{ TeacherKey = "stage1";  GateSource = "target_logvar"; Name = "stage1_gate_target_logvar" },
    @{ TeacherKey = "primary"; GateSource = "target_logvar"; Name = "primary_gate_target_logvar" },
    @{ TeacherKey = "vae9182"; GateSource = "oracle_error";  Name = "vae9182_gate_oracle_error" }
)
$stageNames = $stageOrder | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stageOrder.Count; $i++) {
    $stage = $stageOrder[$i]
    $ok = Invoke-GateSignalStage -Teacher $teachers[$stage.TeacherKey] -GateSource $stage.GateSource -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping gate signal follow-up queue: stage $($stage.Name) did not complete after $MaxRetries attempts. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== Gate signal follow-up queue (3 runs) completed successfully. ==="
exit 0
