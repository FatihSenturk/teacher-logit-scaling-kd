param(
    [int]$Epochs = 150,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int]$ImgSize = 224,
    [int]$SwaStart = 100
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherCkpt = "checkpoints/teacher_rafdb_vich_recipe_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb_newrecipe_lightle_swa"

$commonArgs = @(
    "--teacher-ckpt", $TeacherCkpt,
    "--teacher-vich-head",
    "--teacher-vich-init-logvar-bias", "0.0",
    "--aligned-dir", $AlignedDir,
    "--metadata", $Metadata,
    "--student-head-type", "vich",
    "--student-layer-embedding",
    "--student-lightweight-layer-embedding",
    "--student-layer-embedding-layers", "3",
    "--no-vich-sampling",
    "--save-root", $SaveRoot,
    "--epochs", "$Epochs",
    "--batch-size", "$BatchSize",
    "--workers", "$Workers",
    "--img-size", "$ImgSize",
    "--teacher-input-size", "224",
    "--swa", "--swa-start", "$SwaStart", "--swa-lr", "1e-4"
)

function Invoke-Phase0Run {
    param([string]$Name, [string[]]$ExtraArgs)
    $cmd = @("train_rafdb_kd.py") + $commonArgs + @("--name", $Name) + $ExtraArgs
    Write-Host "=== Phase 0 full run: $Name ==="
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd
    if ($LASTEXITCODE -ne 0) { throw "Phase 0 run failed: $Name" }
    Write-Host "Finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

# Isolated diagnostic: identical to run_phase0_full_ablation_rafdb_lightle_swa.ps1's
# baseline EXCEPT no --use-amp. Tests whether AMP is the reason our LightLE+SWA runs
# (88.5-89.5%) undershoot the historical 90.74% "lightle_vich" reference, which predates
# the --use-amp flag entirely (fp32 training only). VICH's exp(logvar) computation is a
# plausible source of fp16 precision loss under autocast.
Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_lightle_swa_150e_noamp" -ExtraArgs @()

Write-Host "RAF-DB LightLE+SWA no-AMP diagnostic test complete. Artifacts under: $SaveRoot"
