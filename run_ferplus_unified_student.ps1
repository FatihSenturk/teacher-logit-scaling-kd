param(
    [Parameter(Mandatory = $true)]
    [string]$TeacherCheckpoint,
    [ValidateSet(112, 224, 256)]
    [int]$Resolution = 224,
    [int]$Epochs = 200,
    [int]$Workers = 4,
    [string]$DataRoot = "",
    [string]$Metadata = "",
    [switch]$CloudSwanLab,
    [int]$MaxTrainBatches = 0,
    [int]$MaxValBatches = 0
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $DataRoot) {
    $portableRoot = Join-Path $PSScriptRoot "data\FERPlus_processed"
    $DataRoot = if (Test-Path $portableRoot) { $portableRoot } else { "C:\datasets\processed" }
}
if (-not $Metadata) {
    $Metadata = Join-Path $PSScriptRoot "configs\FERPlus_majority_metadata.csv"
}
$resizeMap = @{ 112 = 128; 224 = 256; 256 = 293 }
$resize = $resizeMap[$Resolution]
$runName = "FERPlus_8cls_unified_lightle_vich_${Resolution}"
$swanMode = if ($CloudSwanLab) { "cloud" } else { "offline" }

$cmd = @(
    "train_ferplus_kd.py",
    "--teacher-config", "configs\FERPlus_8_teacher_vae_ce_kld.yaml",
    "--teacher-ckpt", $TeacherCheckpoint,
    "--num-classes", "8",
    "--dataset-name", "FERPlus",
    "--name", $runName,
    "--save-root", "results\unified_students",
    "--train-root", $DataRoot,
    "--val-root", $DataRoot,
    "--metadata", $Metadata,
    "--epochs", "$Epochs",
    "--batch-size", "48",
    "--workers", "$Workers",
    "--sample-numbers", "0",
    "--max-train-batches", "$MaxTrainBatches",
    "--max-val-batches", "$MaxValBatches",
    "--expected-train-samples", "28259",
    "--expected-val-samples", "3153",
    "--supervision", "soft",
    "--img-size", "$Resolution",
    "--resize-size", "$resize",
    "--teacher-input-size", "224",
    "--unified-resolution-crop",
    "--color-jitter", "0.2",
    "--random-erasing-p", "0.5",
    "--width-mult", "1.0",
    "--dropout", "0.3",
    "--student-head-type", "vich",
    "--student-layer-embedding",
    "--student-lightweight-layer-embedding",
    "--student-layer-embedding-layers", "3",
    "--beta-vich", "1e-4",
    "--no-vich-sampling",
    "--lr", "3e-4",
    "--weight-decay", "1e-4",
    "--alpha", "0.3",
    "--temperature", "4",
    "--label-smoothing", "0",
    "--mixup", "0.1",
    "--scheduler-name", "cosine",
    "--min-lr", "1e-6",
    "--ema",
    "--ema-decay", "0.999",
    "--seed", "42",
    "--use-swanlab",
    "--swanlab-project", "Unified-FER-KD",
    "--swanlab-mode", $swanMode
)

Write-Host "Running $runName (Resize $resize -> Crop $Resolution)"
& python -u @cmd
if ($LASTEXITCODE -ne 0) { throw "FERPlus unified student failed." }
