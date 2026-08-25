param(
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15,
    [ValidateSet("stage1_noswa", "stage1_swa200", "primary_noswa", "primary_swa200")]
    [string]$StartAt = "stage1_noswa"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# VICH-headed-teacher ablation (2026-07-18): the "best recipe" (alpha=0.3,
# T=6, label_smoothing=0.1, mixup=0.1, class-weighted CE, cosine_warm_
# restarts, kd preset) proved out at 90.06-90.45% with a VAE-headed teacher
# (vae9182). This queue repeats the same two recipe shapes (200e_noSWA,
# best_400e_swa200) with a VICH-headed teacher instead, since the student
# must pair with a VICH-headed teacher per project requirement. Two teacher
# candidates, both VICH-headed:
#   stage1   : results/teacher_logs/RAFDB/POSTERv2/2026-07-17-04-41-04/best.pt
#              (92.24%, this session's retrain, ce_kld_beta=1e-4, RAFDB_RECIPE)
#   primary  : checkpoints/teacher_rafdb_vich_recipe_best.pt (92.01%, the
#              project's long-established VICH teacher)
# All runs use --workers 12 (confirmed ~1.8x+ speedup over workers=0 earlier
# this session; 7950X has 16 cores/32 threads, PC otherwise idle).
#
# Same caveat as run_rafdb_priority1_queue.ps1: train_rafdb_kd.py has no
# --resume, so a crash restarts that stage from epoch 0.
$stages = @(
    @{ Bat = "run_rafdb_vichteacher_stage1_224_vich_200e_noSWA.bat";          Name = "stage1_noswa" },
    @{ Bat = "run_rafdb_vichteacher_stage1_224_vich_best_400e_swa200.bat";    Name = "stage1_swa200" },
    @{ Bat = "run_rafdb_vichteacher_primary_224_vich_200e_noSWA.bat";        Name = "primary_noswa" },
    @{ Bat = "run_rafdb_vichteacher_primary_224_vich_best_400e_swa200.bat";  Name = "primary_swa200" }
)

function Invoke-VichTeacherStage {
    param([string]$BatFile, [string]$StageName)

    Write-Host ""
    Write-Host "########## STAGE: $StageName ($BatFile) : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host "=== [$StageName] Attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
        $fullBatPath = Join-Path $PSScriptRoot $BatFile
        cmd /c "`"$fullBatPath`" < NUL" | Out-Host
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageName] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

        if ($exitCode -eq 0) {
            Write-Host "=== [$StageName] Completed successfully. ==="
            return $true
        }

        Write-Host "[$StageName] Exited non-zero. No --resume support in train_rafdb_kd.py -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }

    Write-Host "=== [$StageName] Exhausted $MaxRetries attempts without completing. ==="
    return $false
}

$stageNames = $stages | ForEach-Object { $_.Name }
$startIdx = [array]::IndexOf($stageNames, $StartAt)

for ($i = $startIdx; $i -lt $stages.Count; $i++) {
    $stage = $stages[$i]
    $ok = Invoke-VichTeacherStage -BatFile $stage.Bat -StageName $stage.Name
    if (-not $ok) {
        Write-Host "=== Stopping queue: stage $($stage.Name) did not complete. ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== VICH-teacher ablation queue completed successfully (all 4 runs done). ==="
exit 0
