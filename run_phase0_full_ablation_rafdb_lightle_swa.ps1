param(
    [int]$Epochs = 150,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int]$ImgSize = 224,
    [int]$SwaStart = 100,
    [ValidateSet("baseline", "gate", "g2g_kl", "logit_std", "adaptive_t", "ctkd")]
    [string]$StartAt = "baseline"
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

# Full 6-run RAF-DB Phase 0 grid, corrected: teacher_rafdb_vich_recipe_best.pt
# (92.01%, no rotation/crop bug, native 224 res) + LightLE + SWA (both missing
# from every prior RAF-DB launcher -- see run_phase0_full_ablation_rafdb.ps1 /
# run_phase0_full_ablation_rafdb_newrecipe.ps1, neither ever passed these) +
# img-size=224 + AMP. Naming matches run_phase0_rafdb_newrecipe_lightle_swa.ps1's
# baseline exactly so -StartAt gate resumes without re-running it.
$stageOrder = @("baseline", "gate", "g2g_kl", "logit_std", "adaptive_t", "ctkd")
$startIdx = $stageOrder.IndexOf($StartAt)

if ($startIdx -le 0) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_lightle_swa_150e" -ExtraArgs @()
}
if ($startIdx -le 1) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_gate_lightle_swa_150e" -ExtraArgs @("--gate-enable", "--gate-uncertainty-source", "mean_logvar")
}
if ($startIdx -le 2) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_g2g_kl_lightle_swa_150e" -ExtraArgs @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl")
}
if ($startIdx -le 3) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_logit_std_lightle_swa_150e" -ExtraArgs @("--logit-std-enable")
}
if ($startIdx -le 4) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_adaptive_t_lightle_swa_150e" -ExtraArgs @("--adaptive-t-enable")
}
if ($startIdx -le 5) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_ctkd_lightle_swa_150e" -ExtraArgs @("--mixup", "0", "--ctkd-enable")
}

Write-Host "All RAF-DB (LightLE+SWA, newrecipe) Phase 0 ablation runs completed successfully. Artifacts under: $SaveRoot"
