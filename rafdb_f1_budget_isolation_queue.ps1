param(
    [ValidateSet("A", "B")]
    [string]$Stream = "A",
    [int]$StartIndex = 0,
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# ============================================================================
# F1.0 (2026-07-22): isolate the SOURCE of the campaign-high student accuracy.
# combined_500e = VAE9182 teacher + g2g_kl + adaptive_t @ 500e/swa200 hit
# ~90.57 (3-seed mean 90.55/90.38/90.78). But NO 500e-budget plain or
# adaptive_t-alone baseline exists, so the height is unattributed. This queue
# runs the two missing cells at the SAME 500e/swa200 budget and the SAME 3
# seeds {42,1,43}, recipe copied verbatim from combined_500e's own run_args.json
# (only the component flags differ). Decomposition:
#   budget           = plain_500e        - plain_400e (mean 90.28+/-0.16)
#   adaptive_t effect = adaptive_t_500e  - plain_500e
#   g2g effect        = combined_500e(90.57) - adaptive_t_500e
# Stream A = plain (both components OFF); Stream B = adaptive_t-alone (g2g OFF).
# seed 42 runs FIRST in each stream -> early single-seed read at ~5h; the full
# 3-seed mean+/-sd is the noise-surviving verdict.
# train_rafdb_kd.py has NO --resume; on a mid-queue crash resume with
# -Stream <S> -StartIndex <n>.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"  # VAE9182
$teacherHeadArgs = @("--teacher-vae-head")

$components = @{
    plain      = @{ Stem = "RAFDB_vae9182_baseline_b070_T6_224_500e_swa200";   ExtraArgs = @() }
    adaptive_t = @{ Stem = "RAFDB_vae9182_adaptive_t_b070_T6_224_500e_swa200"; ExtraArgs = @("--adaptive-t-enable") }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

$streams = @{
    A = @(
        @{ CompKey = "plain"; Seed = 42 },
        @{ CompKey = "plain"; Seed = 1 },
        @{ CompKey = "plain"; Seed = 43 }
    )
    B = @(
        @{ CompKey = "adaptive_t"; Seed = 42 },
        @{ CompKey = "adaptive_t"; Seed = 1 },
        @{ CompKey = "adaptive_t"; Seed = 43 }
    )
}

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $component = $components[$Stage.CompKey]
    $runName   = "$($component.Stem)_seed$($Stage.Seed)"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$teacherCkpt",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "500",
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
    ) + $teacherHeadArgs + $component.ExtraArgs

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## F1.0 ${Stream} STAGE: $StageLabel ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
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
Write-Host "=== F1.0 budget-isolation, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    $label = "$($stage.CompKey)_500e_seed$($stage.Seed)"
    $ok = Invoke-Run -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} F1.0 budget-isolation ($($stageList.Count) runs) completed successfully. ==="
exit 0
