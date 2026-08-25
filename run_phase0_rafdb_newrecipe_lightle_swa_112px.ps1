param(
    [int]$Epochs = 150,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int]$ImgSize = 112,
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

# Same LightLE+SWA recipe as run_phase0_rafdb_newrecipe_lightle_swa.ps1, but with
# --img-size 112 instead of 224. RAF-DB aligned crops are native 100x100, so 112 is
# barely any upsampling at all (vs 224's ~2.24x and 256's ~2.56x) -- tests whether the
# student needs anywhere near 224px, or if that's still wasted compute. Teacher still
# gets its own 224px copy via _prepare_teacher_images (resized independently from the
# student's 112px input), so teacher-side quality is unaffected -- only the student's
# own FLOPs/receptive field changes. Expected FLOPs: ~4x lower than 224px
# ((112/224)^2 = 0.25), ~0.082G vs 0.329G.
Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_lightle_swa_150e_112px" -ExtraArgs @()

Write-Host "RAF-DB newrecipe LightLE+SWA 112px baseline test complete. Artifacts under: $SaveRoot"
