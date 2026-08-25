param(
    [ValidateSet("linear", "vich", "lightle_vich", "lightle_vich_sampling", "lightle_vich_beta0", "lightle_vich_beta1e5", "lightle_vich_beta1e3")]
    [string]$Variant = "lightle_vich",
    [int]$Epochs = 200,
    [int]$BatchSize = 64,
    [int]$Workers = 0,
    [int]$Seed = 42,
    [double]$Lr = 3e-4,
    [double]$WeightDecay = 1e-4,
    [double]$Dropout = 0.5,
    [double]$LabelSmoothing = 0.2,
    [double]$Mixup = 0.2,
    [int]$ImgSize = 256,
    [int]$RaMag = 7,
    [int]$SwaStart = 90,
    [double]$SwaLr = 1e-4,
    [int]$MaxTrainBatches = 0,
    [int]$MaxValBatches = 0,
    [switch]$NoSwa
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:TORCH_HOME = Join-Path $PSScriptRoot "pretrained"

$alignedDir = Join-Path $PSScriptRoot "data\rafdb_aligned"
$metadata = Join-Path $alignedDir "metadata_rafdb_poster_var.csv"
if (-not (Test-Path $metadata)) {
    throw "RAF-DB metadata not found: $metadata"
}

$runName = "rafdb_nokd_mbv2_$Variant"
$headArgs = @()
$betaVich = 0.0

switch ($Variant) {
    "linear" {
        $headArgs += @("--student-head-type", "linear")
        $betaVich = 0.0
    }
    "vich" {
        $headArgs += @("--student-head-type", "vich", "--no-vich-sampling")
        $betaVich = 1e-4
    }
    "lightle_vich" {
        $headArgs += @("--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--no-vich-sampling")
        $betaVich = 1e-4
    }
    "lightle_vich_sampling" {
        $headArgs += @("--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3")
        $betaVich = 1e-4
    }
    "lightle_vich_beta0" {
        $headArgs += @("--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--no-vich-sampling")
        $betaVich = 0.0
    }
    "lightle_vich_beta1e5" {
        $headArgs += @("--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--no-vich-sampling")
        $betaVich = 1e-5
    }
    "lightle_vich_beta1e3" {
        $headArgs += @("--student-head-type", "vich", "--student-layer-embedding", "--student-lightweight-layer-embedding", "--student-layer-embedding-layers", "3", "--no-vich-sampling")
        $betaVich = 1e-3
    }
}

$cmd = @(
    "train_rafdb_kd.py",
    "--disable-kd",
    "--aligned-dir", "$alignedDir",
    "--metadata", "$metadata",
    "--name", "$runName",
    "--save-root", "results",
    "--epochs", "$Epochs",
    "--batch-size", "$BatchSize",
    "--workers", "$Workers",
    "--max-train-batches", "$MaxTrainBatches",
    "--max-val-batches", "$MaxValBatches",
    "--width-mult", "1.0",
    "--lr", "$Lr",
    "--weight-decay", "$WeightDecay",
    "--dropout", "$Dropout",
    "--label-smoothing", "$LabelSmoothing",
    "--mixup", "$Mixup",
    "--img-size", "$ImgSize",
    "--ra-mag", "$RaMag",
    "--beta-vich", "$betaVich",
    "--seed", "$Seed"
) + $headArgs

if (-not $NoSwa) {
    $cmd += @("--swa", "--swa-start", "$SwaStart", "--swa-lr", "$SwaLr")
}

Write-Host "Running RAF-DB teacher-free / no-KD ablation"
Write-Host "Variant: $Variant"
Write-Host "Run name: $runName"
Write-Host "Beta VICH: $betaVich"
Write-Host "Data: $alignedDir"
Write-Host "Command: python -u $($cmd -join ' ')"
& python -u @cmd
