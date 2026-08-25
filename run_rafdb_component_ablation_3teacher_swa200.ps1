param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [int]$WaitPollSeconds = 300,
    [switch]$SkipWaitForVichQueue,
    [ValidateSet(
        "stage1_gate", "stage1_g2g_kl", "stage1_logit_std", "stage1_adaptive_t", "stage1_ctkd",
        "primary_gate", "primary_g2g_kl"
    )]
    [string]$StartAt = "stage1_gate"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# STREAM A (2026-07-18, split for parallel execution -- see run_rafdb_
# component_ablation_streamB.ps1 for the other half). Together the two
# streams cover all 15 stage1/primary/vae9182 x gate/g2g_kl/logit_std/
# adaptive_t/ctkd combinations, each teacher's runs sharing --workers 8
# (16 total across both streams, matching the 7950X's 16 physical cores)
# instead of one stream at --workers 12, so the two streams can run
# concurrently on the GPU (each ~5GB VRAM, well under the 12GB card) rather
# than strictly sequentially -- roughly halves total wall-clock vs. running
# all 15 stages one after another.
#
# This stream (A) continues the existing run_rafdb_vichteacher_ablation_
# queue.ps1 chain (waits for it, like before) and handles: stage1's all 5
# components + primary's gate/g2g_kl (7 stages). Stream B covers primary's
# remaining 3 + vae9182's all 5 (8 stages) and starts immediately, no wait.
#
# Same caveat as the other queues: train_rafdb_kd.py has no --resume, so a
# crash restarts that run from epoch 0.

$teachers = @{
    stage1  = @{ Tag = "stage1";  Ckpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"; HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
    primary = @{ Tag = "primary"; Ckpt = "checkpoints\teacher_rafdb_vich_recipe_best.pt";                    HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0") }
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

if (-not $SkipWaitForVichQueue) {
    $vichLog = Join-Path $PSScriptRoot "rafdb_vichteacher_ablation_queue.log"
    Write-Host "Waiting for run_rafdb_vichteacher_ablation_queue.ps1 to finish (polling $vichLog every ${WaitPollSeconds}s)..."
    while ($true) {
        if ((Test-Path $vichLog) -and (Select-String -Path $vichLog -Pattern "VICH-teacher ablation queue completed successfully" -Quiet)) {
            Write-Host "Detected completion of the VICH-teacher vanilla-KD queue. Starting component ablation (Stream A)."
            break
        }
        Start-Sleep -Seconds $WaitPollSeconds
    }
}

$stageOrder = @(
    @{ TeacherKey = "stage1";  ComponentKey = "gate";       Name = "stage1_gate" },
    @{ TeacherKey = "stage1";  ComponentKey = "g2g_kl";     Name = "stage1_g2g_kl" },
    @{ TeacherKey = "stage1";  ComponentKey = "logit_std";  Name = "stage1_logit_std" },
    @{ TeacherKey = "stage1";  ComponentKey = "adaptive_t"; Name = "stage1_adaptive_t" },
    @{ TeacherKey = "stage1";  ComponentKey = "ctkd";       Name = "stage1_ctkd" },
    @{ TeacherKey = "primary"; ComponentKey = "gate";       Name = "primary_gate" },
    @{ TeacherKey = "primary"; ComponentKey = "g2g_kl";     Name = "primary_g2g_kl" }
)
$stageNames = $stageOrder | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stageOrder.Count; $i++) {
    $stage = $stageOrder[$i]
    $ok = Invoke-ComponentStage -Teacher $teachers[$stage.TeacherKey] -Component $components[$stage.ComponentKey] -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping Stream A: stage $($stage.Name) did not complete after $MaxRetries attempts. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== Stream A component ablation (7 runs) completed successfully. ==="
exit 0
