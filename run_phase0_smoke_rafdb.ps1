param(
    [int]$Epochs = 2,
    [int]$BatchSize = 8,
    [int]$Workers = 0,
    [switch]$Cpu
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherCkpt = "checkpoints/teacher_vich9237_best.pt"
$AlignedDir = "data/rafdb_aligned"
$Metadata = "data/rafdb_aligned/metadata_rafdb_poster_var.csv"
$SaveRoot = "kd_logs_rafdb_phase0_smoke"

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

function Invoke-Phase0Smoke {
    param([string]$Name, [string[]]$ExtraArgs)
    $cmd = @("train_rafdb_kd.py") + $commonArgs + @("--name", $Name) + $ExtraArgs
    Write-Host "=== Phase 0 smoke: $Name ==="
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd
    if ($LASTEXITCODE -ne 0) { throw "Phase 0 smoke run failed: $Name" }
}

# Five short (2-epoch, batch-8) RAF-DB runs, one component each, per the
# Phase 0 spec's single-variable ablation discipline and acceptance criteria.
Invoke-Phase0Smoke -Name "phase0_smoke_baseline" -ExtraArgs @()
Invoke-Phase0Smoke -Name "phase0_smoke_gate" -ExtraArgs @("--gate-enable", "--gate-uncertainty-source", "mean_logvar")
Invoke-Phase0Smoke -Name "phase0_smoke_g2g_kl" -ExtraArgs @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl")
Invoke-Phase0Smoke -Name "phase0_smoke_logit_std" -ExtraArgs @("--logit-std-enable")
Invoke-Phase0Smoke -Name "phase0_smoke_adaptive_t" -ExtraArgs @("--adaptive-t-enable")

Write-Host "All 5 Phase 0 smoke runs completed successfully. Artifacts under: $SaveRoot"
