param(
    [int]$Epochs = 250,
    [int]$BatchSize = 64,
    [int]$Workers = 0,
    [switch]$Cpu,
    [switch]$SkipBaseline
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherCkpt = "checkpoints/teacher_vich9237_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb"

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
    "--workers", "$Workers"
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

# Full-duration (250-epoch) counterparts of the 5-run Phase 0 smoke grid, plus
# CTKD (built but not in the original spec's smoke list). Run sequentially --
# a single GPU shared across concurrent runs would slow all of them down.
if (-not $SkipBaseline) {
    Invoke-Phase0Run -Name "rafdb_baseline_250e" -ExtraArgs @()
}
Invoke-Phase0Run -Name "rafdb_gate_250e" -ExtraArgs @("--gate-enable", "--gate-uncertainty-source", "mean_logvar")
Invoke-Phase0Run -Name "rafdb_g2g_kl_250e" -ExtraArgs @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl")
Invoke-Phase0Run -Name "rafdb_logit_std_250e" -ExtraArgs @("--logit-std-enable")
Invoke-Phase0Run -Name "rafdb_adaptive_t_250e" -ExtraArgs @("--adaptive-t-enable")
Invoke-Phase0Run -Name "rafdb_ctkd_250e" -ExtraArgs @("--mixup", "0", "--ctkd-enable")

Write-Host "All Phase 0 full ablation runs completed successfully. Artifacts under: $SaveRoot"
