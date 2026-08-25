param(
    [int]$Epochs = 250,
    [int]$BatchSize = 64,
    [int]$Workers = 8,
    [switch]$Cpu
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherCkpt = "checkpoints/teacher_rafdb_vich_recipe_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb_newrecipe"

$commonArgs = @(
    "--teacher-ckpt", $TeacherCkpt,
    "--teacher-vich-head",
    "--teacher-vich-init-logvar-bias", "0.0",
    "--aligned-dir", $AlignedDir,
    "--metadata", $Metadata,
    "--student-head-type", "vich",
    "--save-root", $SaveRoot,
    "--epochs", "$Epochs",
    "--batch-size", "$BatchSize",
    "--workers", "$Workers",
    "--teacher-input-size", "224"
)
if ($Cpu) { $commonArgs += "--cpu" }

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

# Same 6-run grid as run_phase0_full_ablation_rafdb.ps1, but against the
# corrected-recipe RAF-DB teacher (teacher_rafdb_vich_recipe_best.pt, 92.01%,
# no rotation/crop) instead of the untraceable-provenance teacher_vich9237.
Invoke-Phase0Run -Name "rafdb_newrecipe_baseline_250e" -ExtraArgs @()
Invoke-Phase0Run -Name "rafdb_newrecipe_gate_250e" -ExtraArgs @("--gate-enable", "--gate-uncertainty-source", "mean_logvar")
Invoke-Phase0Run -Name "rafdb_newrecipe_g2g_kl_250e" -ExtraArgs @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl")
Invoke-Phase0Run -Name "rafdb_newrecipe_logit_std_250e" -ExtraArgs @("--logit-std-enable")
Invoke-Phase0Run -Name "rafdb_newrecipe_adaptive_t_250e" -ExtraArgs @("--adaptive-t-enable")
Invoke-Phase0Run -Name "rafdb_newrecipe_ctkd_250e" -ExtraArgs @("--mixup", "0", "--ctkd-enable")

Write-Host "All RAF-DB (new recipe) Phase 0 ablation runs completed successfully. Artifacts under: $SaveRoot"
