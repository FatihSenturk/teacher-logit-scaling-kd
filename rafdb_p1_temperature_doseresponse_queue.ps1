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
# P1 (2026-07-23): causal teacher-calibration dose-response.
# The over-confident Stage1 teacher (own ECE 0.0378, fitted T*=1.3406) is post-hoc
# temperature-scaled across a grid; architecture/recipe/teacher-accuracy are FIXED,
# only teacher calibration (softmax sharpness) changes. Student acc + ECE are then
# measured at each T => a controlled dose-response of "teacher calibration -> student
# outcome", the causal upgrade of the observational 3-teacher ECE correlation.
# Recipe copied verbatim from B3's own run_args.json (the T=1.3406 pilot, student acc
# 89.928 seed42); only --teacher-temperature-scale and --seed vary.
#
# Grid T in {0.85, 1.0, 1.3406, 1.70, 2.20}. Two points are FREE:
#   T=1.0  -> existing Stage1 baseline (T-A baseline) = 89.744+/-0.055, ECE 0.0631 (3 seed)
#   T=1.34 -> B3 pilot seed42 = 89.928 (reused; only seed1/seed43 run here)
# Prediction (calibration thesis): student ECE is a U in T with a minimum near T*=1.34;
# T<1 (sharpening an already-overconfident teacher) hurts, T>>T* (over-softening) hurts.
# GO test: does student ECE track teacher T monotonically toward the T* minimum, 3-seed,
# clearing seed sd (~0.005 ECE)? B3 suggested a large effect, so 3 seeds should resolve it.
#
# Stream A runs seed42 across the new T first => a full 5-point seed42 curve emerges early
# (combined with the free T=1.0 and T=1.34 seed42 points). train_rafdb_kd.py has NO
# --resume; on a mid-queue crash resume with -Stream <S> -StartIndex <n>.
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-07-17-04-41-04\best.pt"  # Stage1 (VICH head)

# tag -> exact temperature-scale value
$Tvals = @{ "T085" = "0.85"; "T134" = "1.3406"; "T170" = "1.70"; "T220" = "2.20" }

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

# seed42-first on Stream A -> early full seed42 dose-response curve.
$streams = @{
    A = @(
        @{ Tag = "T085"; Seed = 42 },
        @{ Tag = "T170"; Seed = 42 },
        @{ Tag = "T220"; Seed = 42 },
        @{ Tag = "T085"; Seed = 1 },
        @{ Tag = "T170"; Seed = 1 },
        @{ Tag = "T220"; Seed = 1 }
    )
    B = @(
        @{ Tag = "T134"; Seed = 1 },
        @{ Tag = "T085"; Seed = 43 },
        @{ Tag = "T170"; Seed = 43 },
        @{ Tag = "T220"; Seed = 43 },
        @{ Tag = "T134"; Seed = 43 }
    )
}

function Invoke-Run {
    param($Stage, [string]$StageLabel)
    $tval    = $Tvals[$Stage.Tag]
    $runName = "RAFDB_stage1_tempscale_$($Stage.Tag)_b070_T6_224_400e_swa200_seed$($Stage.Seed)"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$teacherCkpt",
        "--teacher-vich-head",
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
    )

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## P1 ${Stream} STAGE: $StageLabel ($runName), T=$tval, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
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
Write-Host "=== P1 temperature dose-response, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
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
Write-Host "=== STREAM ${Stream} P1 dose-response ($($stageList.Count) runs) completed successfully. ==="
exit 0
