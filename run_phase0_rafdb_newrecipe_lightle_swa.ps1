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
    "--swa", "--swa-start", "$SwaStart", "--swa-lr", "1e-4",
    "--use-amp"
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

# Restores the two components missing from every prior RAF-DB Phase 0 launcher
# (run_phase0_full_ablation_rafdb.ps1 and its newrecipe sibling never passed
# these, unlike the AffectNet+8 launcher and the historical 90.74%/91.00%
# "lightle_vich"/"posterhead" reference runs):
#   - LightLE (student_layer_embedding + lightweight variant, 3 taps)
#   - SWA (swa_start=100/150 ~= same 45-50% point as the reference's 90/200)
# Kept from the corrected-recipe track: teacher_rafdb_vich_recipe_best.pt
# (92.01%, no rotation/crop bug, native 224 res) instead of the historical
# run's teacher_ce9241_best.pt (92.41%, plain head -- incompatible with
# Gate/G2G which need teacher mu/logvar). img_size=224 (not 256) since RAF-DB
# aligned crops are native 100x100 -- 256 was pure upsampling for no benefit,
# validated by the no-erasing test run (89.28%, no regression from 256->224).
# random_erasing_p left at its default 0.1 (not overridden to 0 this time),
# matching the historical recipe -- our own A/B showed removing it didn't help.
Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_lightle_swa_150e" -ExtraArgs @()

Write-Host "RAF-DB newrecipe LightLE+SWA baseline test complete. Artifacts under: $SaveRoot"
