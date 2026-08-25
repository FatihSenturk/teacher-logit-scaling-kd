param(
    [int]$Epochs = 250,
    [int]$BatchSize = 48,
    [int]$Workers = 8,
    [int]$SampleNumbers = 5000,
    [int]$SwaStart = 165,
    [double]$BetaVich = 1e-4,
    [int]$Seed = 42
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$TeacherConfig = "configs/AffectNetPlus_7_vich_kld_27may.yaml"
$TeacherCkpt = "checkpoints/teacher_affectnetplus7_vich_best.pt"
$SaveRoot = "kd_logs_affectnet7"

$commonArgs = @(
    "--teacher-config", $TeacherConfig,
    "--teacher-ckpt", $TeacherCkpt,
    "--num-classes", "7",
    "--save-root", $SaveRoot,
    "--epochs", "$Epochs",
    "--batch-size", "$BatchSize",
    "--workers", "$Workers",
    "--sample-numbers", "$SampleNumbers",
    "--cache-index",
    "--alpha", "0.2",
    "--temperature", "6.0",
    "--dropout", "0.5",
    "--label-smoothing", "0.2",
    "--mixup", "0.2",
    "--student-head-type", "vich",
    "--student-layer-embedding",
    "--student-lightweight-layer-embedding",
    "--student-layer-embedding-layers", "3",
    "--beta-vich", "$BetaVich",
    "--no-vich-sampling",
    "--swa", "--swa-start", "$SwaStart", "--swa-lr", "1e-4",
    "--seed", "$Seed"
)

function Invoke-Phase0Run {
    param([string]$Name, [string[]]$ExtraArgs)
    $cmd = @("train_affectnetplus_kd.py") + $commonArgs + @("--name", $Name) + $ExtraArgs
    Write-Host "=== Phase 0 full run: $Name ==="
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd
    if ($LASTEXITCODE -ne 0) { throw "Phase 0 run failed: $Name" }
    Write-Host "Finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

Invoke-Phase0Run -Name "affectnet7_baseline_250e" -ExtraArgs @()
Invoke-Phase0Run -Name "affectnet7_gate_250e" -ExtraArgs @("--gate-enable", "--gate-uncertainty-source", "mean_logvar")
Invoke-Phase0Run -Name "affectnet7_g2g_kl_250e" -ExtraArgs @("--g2g-enable", "--g2g-weight", "0.1", "--g2g-mode", "kl")
Invoke-Phase0Run -Name "affectnet7_logit_std_250e" -ExtraArgs @("--logit-std-enable")
Invoke-Phase0Run -Name "affectnet7_adaptive_t_250e" -ExtraArgs @("--adaptive-t-enable")
Invoke-Phase0Run -Name "affectnet7_ctkd_250e" -ExtraArgs @("--mixup", "0", "--ctkd-enable")

Write-Host "All AffectNet+7cls Phase 0 ablation runs completed successfully. Artifacts under: $SaveRoot"
