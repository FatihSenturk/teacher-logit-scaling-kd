param(
    [ValidateSet("A", "B")]
    [string]$Stream = "A",
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 2026-07-20: Phase A seed replicates (matched {42,1,43} design).
#
# VAE9182 baseline already has all 3 seeds on disk (42/1/43 -> 90.06/90.35/
# 90.42%), so it needs NO new runs. This queue fills seeds {1,43} for the five
# conditions that currently have only seed 42, so every reported delta is
# computable at all three seeds:
#   VAE9182:  g2g_kl, adaptive_t, combined_500e   (baseline already 3 seeds)
#   Primary:  baseline, g2g_kl
# = 10 new runs, split into two concurrent streams (--workers 8 each, 16 total
# across both, matching the 16 physical cores; ~2x5GB VRAM under the 12GB card),
# per the user's explicit "2'li paralel" choice. Each stream carries one 500e
# combined run + four 400e runs so the long runs are load-balanced.
#
# Base recipe is copied verbatim from run_rafdb_component_ablation_3teacher_
# swa200.ps1 (verified identical across all existing seed-42 siblings via a
# full run_args.json field diff). Only seed / epochs(combined=500) / teacher
# ckpt+head-args / component flags differ per stage.
#
# train_rafdb_kd.py has NO --resume: a crash restarts that run from epoch 0.
# On a mid-queue crash, resume this stream with -StartIndex <n> (0-based index
# into the stage list below) to skip already-finished runs.

$teachers = @{
    vae9182 = @{
        Ckpt     = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"
        HeadArgs = @("--teacher-vae-head")
    }
    primary = @{
        Ckpt     = "checkpoints\teacher_rafdb_vich_recipe_best.pt"
        HeadArgs = @("--teacher-vich-head", "--teacher-vich-init-logvar-bias", "0")
    }
}

$components = @{
    baseline   = @{ Epochs = 400; ExtraArgs = @() }
    g2g_kl     = @{ Epochs = 400; ExtraArgs = @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl") }
    adaptive_t = @{ Epochs = 400; ExtraArgs = @("--adaptive-t-enable") }
    combined   = @{ Epochs = 500; ExtraArgs = @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl", "--adaptive-t-enable") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# Two balanced streams: each = one 500e combined + four 400e runs (equal epoch
# totals). Aggregation is by (teacher, condition, seed) read from run_args.json,
# so the run-name stems just need to be unique + greppable.
$streams = @{
    A = @(
        @{ TeacherKey = "vae9182"; CompKey = "combined";   Stem = "RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200"; Seed = 1 },
        @{ TeacherKey = "vae9182"; CompKey = "g2g_kl";     Stem = "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200";                  Seed = 1 },
        @{ TeacherKey = "vae9182"; CompKey = "g2g_kl";     Stem = "RAFDB_vae9182_g2g_kl_b070_T6_224_400e_swa200";                  Seed = 43 },
        @{ TeacherKey = "vae9182"; CompKey = "adaptive_t"; Stem = "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200";              Seed = 1 },
        @{ TeacherKey = "primary"; CompKey = "baseline";   Stem = "RAFDB_primary_baseline_b070_T6_224_400e_swa200";                Seed = 1 }
    )
    B = @(
        @{ TeacherKey = "vae9182"; CompKey = "combined";   Stem = "RAFDB_vae9182_combined_g2g_adaptive_t_b070_T6_224_500e_swa200"; Seed = 43 },
        @{ TeacherKey = "vae9182"; CompKey = "adaptive_t"; Stem = "RAFDB_vae9182_adaptive_t_b070_T6_224_400e_swa200";              Seed = 43 },
        @{ TeacherKey = "primary"; CompKey = "baseline";   Stem = "RAFDB_primary_baseline_b070_T6_224_400e_swa200";                Seed = 43 },
        @{ TeacherKey = "primary"; CompKey = "g2g_kl";     Stem = "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200";                  Seed = 1 },
        @{ TeacherKey = "primary"; CompKey = "g2g_kl";     Stem = "RAFDB_primary_g2g_kl_b070_T6_224_400e_swa200";                  Seed = 43 }
    )
}

function Invoke-SeedRun {
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
        Write-Host "########## STREAM ${Stream} STAGE: $StageLabel ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        & python -u @cmd | Out-Host
        $exitCode = $LASTEXITCODE
        Write-Host "[$StageLabel] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        if ($exitCode -eq 0) { return $true }
        Write-Host "[$StageLabel] Exited non-zero. No --resume support -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

$stageList = $streams[$Stream]
Write-Host "=== Phase A seed replicates, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="

for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    $label = "$($stage.TeacherKey)_$($stage.CompKey)_seed$($stage.Seed)"
    $ok = Invoke-SeedRun -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) did not complete after $MaxRetries attempts. Resume with -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}

Write-Host ""
Write-Host "=== STREAM ${Stream} seed replicates ($($stageList.Count) runs) completed successfully. ==="
exit 0
