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
# VICH-isolation + architecture-frontier ablation (2026-07-22).
# Two controls for the "does the student-side machinery earn its place" question,
# both at the EXACT T-C baseline recipe (VAE9182 teacher, 400e/swa200, plain KD),
# recipe copied verbatim from that run's run_args.json. Only the student differs.
#
#   Stream A = plus_linear   : same MobileNetV2Plus backbone + LightLE, head vich->linear.
#              Single-variable swap => isolates the VICH head alone.
#              Compare vs existing T-C baseline (vich) = 90.28+/-0.16, ECE 0.0273.
#   Stream B = vanilla_mnv2  : torchvision MobileNetV2 (no ECA/GeM/LightLE/VICH),
#              ImageNet-pretrained, linear 7-way head. Architecture frontier control
#              (2.233M params vs Plus 2.248M).
#
# GO/NO-GO logic lives on Stream A: if plus_linear (3-seed) does NOT clear the vich
# baseline's seed sd on acc OR ECE, the VICH-transfer novelty is dead and the width
# sweep is NOT run. width_mult is left at the script default 1.0 (matches T-C baseline;
# "b070" in the reference run names is a legacy tag, NOT width 0.7).
#
# train_rafdb_kd.py has NO --resume; on a mid-queue crash resume with
# -Stream <S> -StartIndex <n>. Runs AFTER F1.0 frees the GPU (do not launch concurrently).
# ============================================================================

$teacherCkpt = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt"  # VAE9182
$teacherHeadArgs = @("--teacher-vae-head")

$components = @{
    plus_linear  = @{
        Stem      = "RAFDB_vae9182_pluslinear_T6_224_400e_swa200"
        ExtraArgs = @(
            "--student-head-type", "linear",
            "--student-layer-embedding",
            "--student-lightweight-layer-embedding",
            "--student-layer-embedding-layers", "3"
        )
    }
    vanilla_mnv2 = @{
        Stem      = "RAFDB_vae9182_vanillamnv2_T6_224_400e_swa200"
        ExtraArgs = @(
            "--student-arch", "vanilla_mnv2",
            "--student-head-type", "linear"
        )
    }
}

$DataRoot = "data\rafdb_aligned"
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"

$streams = @{
    A = @(
        @{ CompKey = "plus_linear"; Seed = 42 },
        @{ CompKey = "plus_linear"; Seed = 1 },
        @{ CompKey = "plus_linear"; Seed = 43 }
    )
    B = @(
        @{ CompKey = "vanilla_mnv2"; Seed = 42 },
        @{ CompKey = "vanilla_mnv2"; Seed = 1 },
        @{ CompKey = "vanilla_mnv2"; Seed = 43 }
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
        "--epochs", "400",
        "--batch-size", "64",
        "--workers", "8",
        "--img-size", "224",
        "--resize-size", "0",
        "--augment-preset", "kd",
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
        Write-Host "########## VICH-ISO ${Stream} STAGE: $StageLabel ($runName), attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
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
Write-Host "=== VICH-isolation ablation, STREAM $Stream : $($stageList.Count) stages, starting at index $StartIndex ==="
for ($i = $StartIndex; $i -lt $stageList.Count; $i++) {
    $stage = $stageList[$i]
    $label = "$($stage.CompKey)_seed$($stage.Seed)"
    $ok = Invoke-Run -Stage $stage -StageLabel $label
    if (-not $ok) {
        Write-Host "=== STREAM ${Stream}: stage $label (index $i) failed after $MaxRetries attempts. Resume: -Stream $Stream -StartIndex $i ==="
        exit 1
    }
}
Write-Host ""
Write-Host "=== STREAM ${Stream} VICH-isolation ablation ($($stageList.Count) runs) completed successfully. ==="
exit 0
