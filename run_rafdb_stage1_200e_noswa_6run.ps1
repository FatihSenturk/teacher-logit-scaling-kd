param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [ValidateSet("baseline", "gate", "g2g_kl", "logit_std", "adaptive_t", "ctkd")]
    [string]$StartAt = "baseline"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-19: 200e noSWA companion grid to the 400e_swa200 component ablation,
# using the Stage1-VICH teacher only (92.24% own-acc), chosen by the user over
# VAE9182/Primary. Mirrors run_rafdb_component_ablation_3teacher_swa200.ps1's
# stage1 recipe exactly, but --epochs 200 and no --swa. gate uses
# --class-weight-mode none (same fix as run_rafdb_gate_classweight_fix_backfill.ps1;
# gate + class-weighted CE is a hard ValueError, kd_common.py:190).
#
# No --resume in train_rafdb_kd.py: a crash restarts that stage from epoch 0.

$TeacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"
$TeacherHeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0")

$components = @{
    baseline    = @{ Name = "baseline";    ClassWeightMode = "effective_number"; ExtraArgs = @() }
    gate        = @{ Name = "gate";        ClassWeightMode = "none";             ExtraArgs = @("--gate-enable", "--gate-uncertainty-source", "mean_logvar") }
    g2g_kl      = @{ Name = "g2g_kl";      ClassWeightMode = "effective_number"; ExtraArgs = @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl") }
    logit_std   = @{ Name = "logit_std";   ClassWeightMode = "effective_number"; ExtraArgs = @("--logit-std-enable") }
    adaptive_t  = @{ Name = "adaptive_t";  ClassWeightMode = "effective_number"; ExtraArgs = @("--adaptive-t-enable") }
    ctkd        = @{ Name = "ctkd";        ClassWeightMode = "effective_number"; ExtraArgs = @("--mixup", "0", "--ctkd-enable") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

function Invoke-ComponentStage200 {
    param($Component, [string]$StageName)

    $runName = "RAFDB_stage1_$($Component.Name)_b070_T6_224_200e_noSWA"
    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$TeacherCkpt",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "200",
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
        "--class-weight-mode", "$($Component.ClassWeightMode)",
        "--class-weight-beta", "0.9999",
        "--scheduler-name", "cosine_warm_restarts",
        "--min-lr", "1e-6",
        "--gamma", "0.98",
        "--scheduler-t0", "10",
        "--scheduler-t-mult", "2",
        "--seed", "42"
    ) + $TeacherHeadArgs + $Component.ExtraArgs

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

$stageOrder = @("baseline", "gate", "g2g_kl", "logit_std", "adaptive_t", "ctkd")
$startIdx = [array]::IndexOf($stageOrder, $StartAt)

for ($i = $startIdx; $i -lt $stageOrder.Count; $i++) {
    $key = $stageOrder[$i]
    $ok = Invoke-ComponentStage200 -Component $components[$key] -StageName $key
    if (-not $ok) {
        Write-Host "=== Stopping stage1 200e_noSWA grid: stage $key did not complete after $MaxRetries attempts. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== Stage1 200e_noSWA 6-run grid completed successfully. ==="
exit 0
