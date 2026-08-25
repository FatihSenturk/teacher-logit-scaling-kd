param(
    [int]$Epochs = 150,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int]$ImgSize = 224,
    [int]$SwaStart = 100
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherCkpt = "checkpoints/teacher_ce9241_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb_newrecipe_lightle_swa"

# NOTE: no --teacher-vich-head / --teacher-vae-head -- ce9241 is a plain classifier
# head + layer_embedding on the teacher side (matches reference_90_74/config.json:
# teacher_vae_head=false, teacher_vich_head=false, teacher_layer_embedding=true).
#
# DEAD REFERENCE, kept on purpose (8 Aug 2026 decision: comment, do not delete).
# `reference_90_74/` is NOT published in the public repository: it is a March-2026
# run directory from a different study, outside this paper's chain, and the scope
# criterion ("can I verify a number in the paper from this repo?") excludes it.
# The three flag values quoted above were read from that config at the time and are
# recorded here so the claim stays checkable even though the file is not shipped.
# A reader of the public repo will not find the path -- that is expected, not a bug.
$commonArgs = @(
    "--teacher-ckpt", $TeacherCkpt,
    "--teacher-layer-embedding",
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

# Diagnostic only (NOT the main study's teacher choice -- Gate/G2G-KL require a
# VICH/VAE-headed teacher and stay on teacher_rafdb_vich_recipe_best.pt). This
# isolates whether the ~1.7pp gap to the historical 90.74% "lightle_vich" run is
# attributable to teacher type (ce9241: plain head + layer_embedding, 92.41%) vs
# our VICH-headed teacher (92.01%). No --teacher-input-size override: ce9241 was
# trained at the student's own 224/256 pipeline resolution historically (no
# resolution-mismatch bug applied to this teacher). AMP included for speed --
# already shown to be a ~0.2pp (noise-level) effect, safe to keep on here.
Invoke-Phase0Run -Name "rafdb_ce9241_lightle_swa_150e_baseline" -ExtraArgs @()
Invoke-Phase0Run -Name "rafdb_ce9241_lightle_swa_150e_ctkd" -ExtraArgs @("--mixup", "0", "--ctkd-enable")

Write-Host "ce9241 teacher diagnostic complete. Artifacts under: $SaveRoot"
