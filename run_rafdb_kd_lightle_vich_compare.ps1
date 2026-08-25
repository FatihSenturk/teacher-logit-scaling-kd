param(
    [ValidateSet("ce9241", "vich9237")]
    [string]$Teacher = "ce9241",
    [int]$Epochs = 200,
    [int]$BatchSize = 64,
    [int]$Workers = 0,
    [double]$BetaVich = 1e-4,
    [int]$Seed = 42,
    [switch]$NoLayerEmbedding,
    [switch]$NoSwa
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:TORCH_HOME = Join-Path $PSScriptRoot "pretrained"

$teacherCkpt = ""
$teacherArgs = @()
if ($Teacher -eq "ce9241") {
    $teacherCkpt = Join-Path $PSScriptRoot "checkpoints\teacher_ce9241_best.pt"
    $runName = "rafdb_kd_ce9241_mbv2_lightle_vich"
} elseif ($Teacher -eq "vich9237") {
    $teacherCkpt = Join-Path $PSScriptRoot "checkpoints\teacher_vich9237_best.pt"
    $teacherArgs += @(
        "--teacher-vich-head",
        "--teacher-vich-init-logvar-bias", "0.0"
    )
    $runName = "rafdb_kd_vich9237_mbv2_lightle_vich"
}

if ($NoLayerEmbedding) {
    $runName = $runName + "_nole"
}

$cmd = @(
    "train_rafdb_kd.py",
    "--teacher-ckpt", "$teacherCkpt",
    "--teacher-layer-embedding",
    "--teacher-votes-sum", "0",
    "--aligned-dir", (Join-Path $PSScriptRoot "data\rafdb_aligned"),
    "--metadata", (Join-Path $PSScriptRoot "data\rafdb_aligned\metadata_rafdb_poster_var.csv")
) + $teacherArgs + @(
    "--name", "$runName",
    "--save-root", "results",
    "--epochs", "$Epochs",
    "--batch-size", "$BatchSize",
    "--workers", "$Workers",
    "--width-mult", "1.0",
    "--lr", "3e-4",
    "--weight-decay", "1e-4",
    "--alpha", "0.2",
    "--temperature", "6.0",
    "--dropout", "0.5",
    "--label-smoothing", "0.2",
    "--mixup", "0.2",
    "--img-size", "256",
    "--ra-mag", "7",
    "--student-head-type", "vich",
    "--beta-vich", "$BetaVich",
    "--no-vich-sampling",
    "--seed", "$Seed"
)

if (-not $NoLayerEmbedding) {
    $cmd += @(
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3"
    )
}

if (-not $NoSwa) {
    $cmd += @(
        "--swa",
        "--swa-start", "90",
        "--swa-lr", "1e-4"
    )
}

Write-Host "Running RAF-DB lightweight LayerEmbedding + VICH student KD"
Write-Host "Teacher: $Teacher"
Write-Host "Teacher checkpoint: $teacherCkpt"
Write-Host "Data: $(Join-Path $PSScriptRoot 'data\rafdb_aligned')"
Write-Host "Run name: $runName"
Write-Host "Command: python -u $($cmd -join ' ')"
& python -u @cmd
