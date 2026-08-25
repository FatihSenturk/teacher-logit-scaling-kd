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
# P1 flat-control (2026-07-24): VAE9182 teacher dose-response.
# VAE9182 is the WELL-calibrated teacher (own ECE 0.0136, fitted T*=0.983). Same
# T-grid as the Stage1 dose-response so the two curves overlay on one x-axis.
# Prediction (calibration-conditioned headroom law, B-007): because there is little
# miscalibration to correct, this curve should be FLAT/shallow with its minimum near
# T=1.0 -- NO deep dip like Stage1's (which improved -46% ECE at T*=1.34). If VAE9182
# at T=1.34 does NOT improve (or worsens), that is the headroom-proportional-to-
# miscalibration evidence that unifies gate-dead + G2G-null + F1.0-null.
# Recipe = T-C baseline (VAE9182 teacher, 400e/swa200, plain KD); only
# --teacher-temperature-scale and --seed vary. T=1.0 is FREE (T-C baseline = 90.276
# +/-0.156, ECE 0.0273, 3-seed). 4 new T x 3 seed = 12 runs.
# train_rafdb_kd.py has NO --resume; on a mid-queue crash resume with -Stream/-StartIndex.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"  # VAE9182 (VAE head)
$teacherHeadArgs = @("--teacher-vae-head")

$Tvals = @{ "T085" = "0.85"; "T134" = "1.3406"; "T170" = "1.70"; "T220" = "2.20" }

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# seed42-first on Stream A -> full 5-point seed42 curve early (with free T=1.0).
$streams = @{
    A = @(
        @{ Tag = "T085"; Seed = 42 },
        @{ Tag = "T134"; Seed = 42 },
        @{ Tag = "T170"; Seed = 42 },
        @{ Tag = "T220"; Seed = 42 },
        @{ Tag = "T085"; Seed = 1 },
        @{ Tag = "T134"; Seed = 1 }
    )
    B = @(
        @{ Tag = "T170"; Seed = 1 },
        @{ Tag = "T220"; Seed = 1 },
        @{ Tag = "T085"; Seed = 43 },
        @{ Tag = "T134"; Seed = 43 },
        @{ Tag = "T170"; Seed = 43 },
        @{ Tag = "T220"; Seed = 43 }
    )
}

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $tval    = $Tvals[$Stage.Tag]
    $runName = "RAFDB_vae9182_tempscale_$($Stage.Tag)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$teacherCkpt",
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
        "--teacher-temperature-scale", "$tval",
        "--seed", "$($Stage.Seed)"
    ) + $teacherHeadArgs

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## P1-VAE ${Stream} STAGE: $StageLabel ($runName), T=$tval, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
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
Write-Host "=== P1 VAE9182 flat-control, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    $label = "$($stage.Tag)_seed$($stage.Seed)"
    $ok = Invoke-Run -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} P1 VAE9182 flat-control ($($stageList.Count) runs) completed successfully. ==="
exit 0
