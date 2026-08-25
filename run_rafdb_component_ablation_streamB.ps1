param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [ValidateSet(
        "primary_logit_std", "primary_adaptive_t", "primary_ctkd",
        "vae9182_gate", "vae9182_g2g_kl", "vae9182_logit_std", "vae9182_adaptive_t", "vae9182_ctkd"
    )]
    [string]$StartAt = "primary_logit_std"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# STREAM B (2026-07-18) -- runs concurrently with run_rafdb_component_
# ablation_3teacher_swa200.ps1 (Stream A) and the tail end of run_rafdb_
# vichteacher_ablation_queue.ps1. No wait-loop: starts immediately. Covers
# primary's remaining 3 components (logit_std/adaptive_t/ctkd) + vae9182's
# all 5, --workers 8 (paired with Stream A's --workers 8 = 16 total across
# both streams, matching the 7950X's 16 physical cores). Each stream's
# training process uses ~5GB VRAM, well under the 12GB card, so two
# concurrent processes fit comfortably.
#
# Same caveat as the other queues: train_rafdb_kd.py has no --resume, so a
# crash restarts that run from epoch 0.

$teachers = @{
    primary = @{ Tag = "primary"; Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt";                   HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    vae9182 = @{ Tag = "vae9182"; Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"; HeadArgs = @("--teacher-vae-head") }
}

$components = @{
    gate        = @{ Name = "gate";        ExtraArgs = @("--gate-enable", "--gate-uncertainty-source", "mean_logvar") }
    g2g_kl      = @{ Name = "g2g_kl";      ExtraArgs = @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl") }
    logit_std   = @{ Name = "logit_std";   ExtraArgs = @("--logit-std-enable") }
    adaptive_t  = @{ Name = "adaptive_t";  ExtraArgs = @("--adaptive-t-enable") }
    ctkd        = @{ Name = "ctkd";        ExtraArgs = @("--mixup", "0", "--ctkd-enable") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

function Invoke-ComponentStage {
    param($Teacher, $Component, [string]$StageName)

    $runName = "RAFDB_$($Teacher.Tag)_$($Component.Name)_b070_T6_224_400e_swa200"
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
        "--seed", "42"
    ) + $Teacher.HeadArgs + $Component.ExtraArgs
    # Component ExtraArgs appended last so ctkd's "--mixup 0" overrides the
    # base "--mixup 0.1" above (argparse keeps the last value for a repeated flag).

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

$stageOrder = @(
    @{ TeacherKey = "primary"; ComponentKey = "logit_std";  Name = "primary_logit_std" },
    @{ TeacherKey = "primary"; ComponentKey = "adaptive_t"; Name = "primary_adaptive_t" },
    @{ TeacherKey = "primary"; ComponentKey = "ctkd";       Name = "primary_ctkd" },
    @{ TeacherKey = "vae9182"; ComponentKey = "gate";       Name = "vae9182_gate" },
    @{ TeacherKey = "vae9182"; ComponentKey = "g2g_kl";     Name = "vae9182_g2g_kl" },
    @{ TeacherKey = "vae9182"; ComponentKey = "logit_std";  Name = "vae9182_logit_std" },
    @{ TeacherKey = "vae9182"; ComponentKey = "adaptive_t"; Name = "vae9182_adaptive_t" },
    @{ TeacherKey = "vae9182"; ComponentKey = "ctkd";       Name = "vae9182_ctkd" }
)
$stageNames = $stageOrder | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stageOrder.Count; $i++) {
    $stage = $stageOrder[$i]
    $ok = Invoke-ComponentStage -Teacher $teachers[$stage.TeacherKey] -Component $components[$stage.ComponentKey] -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping Stream B: stage $($stage.Name) did not complete after $MaxRetries attempts. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== Stream B component ablation (8 runs) completed successfully. ==="
exit 0
