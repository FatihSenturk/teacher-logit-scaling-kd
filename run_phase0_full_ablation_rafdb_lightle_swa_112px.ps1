param(
    [int]$Epochs = 150,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [int]$ImgSize = 112,
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

# 112px sibling of run_phase0_full_ablation_rafdb_lightle_swa.ps1's full 6-run grid --
# same corrected teacher + LightLE + SWA + AMP, only --img-size differs (112 vs 224).
# RAF-DB aligned crops are native 100x100, so 112 is barely any upsampling at all.
# Teacher still gets its own 224px copy via _prepare_teacher_images regardless of
# student img_size, so teacher-side quality is unaffected -- only student FLOPs/
# receptive field changes (~4x lower FLOPs than 224px).
$stageOrder = @("baseline", "gate", "g2g_kl", "logit_std", "adaptive_t", "ctkd")
$startIdx = $stageOrder.IndexOf($StartAt)

if ($startIdx -le 0) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_lightle_swa_150e_112px" -ExtraArgs @()
}
if ($startIdx -le 1) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_gate_lightle_swa_150e_112px" -ExtraArgs @("--gate-enable", "--gate-uncertainty-source", "mean_logvar")
}
if ($startIdx -le 2) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_g2g_kl_lightle_swa_150e_112px" -ExtraArgs @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl")
}
if ($startIdx -le 3) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_logit_std_lightle_swa_150e_112px" -ExtraArgs @("--logit-std-enable")
}
if ($startIdx -le 4) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_adaptive_t_lightle_swa_150e_112px" -ExtraArgs @("--adaptive-t-enable")
}
if ($startIdx -le 5) {
    Invoke-Phase0Run -Name "rafdb_newrecipe_ctkd_lightle_swa_150e_112px" -ExtraArgs @("--mixup", "0", "--ctkd-enable")
}

Write-Host "All RAF-DB (LightLE+SWA, 112px) Phase 0 ablation runs completed successfully. Artifacts under: $SaveRoot"
