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
    $portableRoot = Join-Path $PSScriptRoot "data\rafdb_aligned"
    $DataRoot = if (Test-Path $portableRoot) { $portableRoot } else { "C:\dataset\rafdb_aligned" }
}
if (-not $Metadata) {
    $Metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
}
$resizeMap = @{ 112 = 128; 224 = 256; 256 = 293 }
$resize = $resizeMap[$Resolution]
$runName = "RAFDB_7cls_unified_lightle_vich_${Resolution}"
$swanMode = if ($CloudSwanLab) { "cloud" } else { "offline" }

$cmd = @(
    "train_rafdb_kd.py",
    "--teacher-ckpt", $TeacherCheckpoint,
    "--teacher-vae-head",
    "--teacher-layer-embedding",
    "--teacher-input-size", "224",
    "--aligned-dir", $DataRoot,
    "--metadata", $Metadata,
    "--train-folds", "2",
    "--val-folds", "3",
    "--name", $runName,
    "--save-root", "results\unified_students",
    "--epochs", "$Epochs",
    "--batch-size", "48",
    "--workers", "$Workers",
    "--max-train-batches", "$MaxTrainBatches",
    "--max-val-batches", "$MaxValBatches",
    "--img-size", "$Resolution",
    "--resize-size", "$resize",
    "--augment-preset", "poster_var_rafdb",
    "--rotation-degrees", "12",
    "--color-jitter", "0.2",
    "--random-erasing-p", "0.1",
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
    "--label-smoothing", "0.05",
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
if ($LASTEXITCODE -ne 0) { throw "RAF-DB unified student failed." }
