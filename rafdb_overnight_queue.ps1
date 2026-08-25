param(
    [ValidateSet("A", "B")]
    [string]$Stream = "A",
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-21 overnight batch (6 runs, 2 concurrent streams, --workers 8 each):
#   (1) bridge->student baseline -- directly measure the bridge teacher's TRANSFER
#       (VAE head + VICH recipe, ECE 0.0391/T*1.25 => predicted to transfer POORLY,
#       ~89.6%/ECE~0.058 like the VICH teachers, NOT like VAE9182's 90.06/0.0285).
#   (2) T-A (Stage1) seed completion: baseline + g2g_kl at seeds {1,43} -> makes
#       those two T-A cells n=3, matching T-C/T-B; + adaptive_t seed 1 (partial).
# Base recipe copied verbatim from rafdb_seed_replicates_queue.ps1 (verified).
# train_rafdb_kd.py has no --resume; on a mid-queue crash resume with
# -Stream <S> -StartIndex <n>.

$teachers = @{
    stage1 = @{
        Ckpt     = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"
        HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0")
    }
    bridge = @{
        # Phase C2 bridge teacher: VAE head + VICH recipe.
        Ckpt     = "results\teacher_logs\RAFDB\POSTERv2\2026-07-21-13-36-38\best.pt"
        HeadArgs = @("--teacher-vae-head")
    }
}

$components = @{
    baseline   = @{ Epochs = 400; ExtraArgs = @() }
    g2g_kl     = @{ Epochs = 400; ExtraArgs = @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl") }
    adaptive_t = @{ Epochs = 400; ExtraArgs = @("--adaptive-t-enable") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

$streams = @{
    A = @(
        @{ TeacherKey = "bridge"; CompKey = "baseline"; Stem = "RAFDB_bridge_baseline_b070_T6_224_400e_swa200"; Seed = 42 },
        @{ TeacherKey = "stage1"; CompKey = "g2g_kl";   Stem = "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200";   Seed = 1 },
        @{ TeacherKey = "stage1"; CompKey = "g2g_kl";   Stem = "RAFDB_stage1_g2g_kl_b070_T6_224_400e_swa200";   Seed = 43 }
    )
    B = @(
        @{ TeacherKey = "stage1"; CompKey = "baseline";   Stem = "RAFDB_stage1_baseline_b070_T6_224_400e_swa200";   Seed = 1 },
        @{ TeacherKey = "stage1"; CompKey = "baseline";   Stem = "RAFDB_stage1_baseline_b070_T6_224_400e_swa200";   Seed = 43 },
        @{ TeacherKey = "stage1"; CompKey = "adaptive_t"; Stem = "RAFDB_stage1_adaptive_t_b070_T6_224_400e_swa200"; Seed = 1 }
    )
}

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $teacher   = $teachers[$Stage.TeacherKey]
    $component = $components[$Stage.CompKey]
    $runName   = "$($Stage.Stem)_seed$($Stage.Seed)"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$($teacher.Ckpt)",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "$($component.Epochs)",
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
        "--seed", "$($Stage.Seed)"
    ) + $teacher.HeadArgs + $component.ExtraArgs

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## OVERNIGHT ${Stream} STAGE: $StageLabel ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        & python -u @cmd | Out-Host
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageLabel] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) { return $true }
        Write-Host "[$StageLabel] Exited non-zero. No --resume -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

$stageList = $streams[$Stream]
Write-Host "=== OVERNIGHT batch, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    $label = "$($stage.TeacherKey)_$($stage.CompKey)_seed$($stage.Seed)"
    $ok = Invoke-Run -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} overnight batch ($($stageList.Count) runs) completed successfully. ==="
exit 0
