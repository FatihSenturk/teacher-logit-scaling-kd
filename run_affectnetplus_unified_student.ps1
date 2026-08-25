param(
    [ValidateSet(7, 8)]
    [int]$Classes = 7,
    [ValidateSet(112, 224, 256)]
    [int]$Resolution = 224,
    [string]$TeacherCheckpoint = "",
    [int]$Epochs = 200,
    [int]$Workers = 0,
    [string]$DataRoot = "",
    [switch]$CloudSwanLab,
    [int]$MaxTrainBatches = 0,
    [int]$MaxValBatches = 0
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $DataRoot) {
    $portableRoot = Join-Path $PSScriptRoot "data\AffectNet+"
    $DataRoot = if (Test-Path $portableRoot) { $portableRoot } else { "D:\Veriseti\AffectNet+" }
}
if (-not $TeacherCheckpoint) {
    $portableName = "affectnetplus${Classes}_teacher_best.pt"
    $portableCheckpoint = Join-Path $PSScriptRoot "checkpoints\$portableName"
    if (Test-Path $portableCheckpoint) {
        $TeacherCheckpoint = $portableCheckpoint
    } elseif ($Classes -eq 7) {
        $TeacherCheckpoint = Join-Path $PSScriptRoot "lg\logs\AffectNetPlus\POSTERv2\2026-05-12-15-43-13\best.pt"
    } else {
        $TeacherCheckpoint = Join-Path $PSScriptRoot "lg\logs\AffectNetPlus\POSTERv2\2026-05-13-14-14-54\best.pt"
    }
}
if (-not (Test-Path $TeacherCheckpoint)) {
    throw "AffectNet+ teacher checkpoint not found: $TeacherCheckpoint"
}

$resizeMap = @{ 112 = 128; 224 = 256; 256 = 293 }
$resize = $resizeMap[$Resolution]
$teacherConfig = "configs\AffectNetPlus_${Classes}_ce_kld.yaml"
$runName = "AffectNetPlus_${Classes}cls_unified_lightle_vich_${Resolution}"
$swanMode = if ($CloudSwanLab) { "cloud" } else { "offline" }

$cmd = @(
    "train_affectnetplus_kd.py",
    "--teacher-config", $teacherConfig,
    "--teacher-ckpt", $TeacherCheckpoint,
    "--num-classes", "$Classes",
    "--dataset-name", "AffectNetPlus",
    "--name", $runName,
    "--save-root", "results\unified_students",
    "--train-root", $DataRoot,
    "--val-root", $DataRoot,
    "--epochs", "$Epochs",
    "--batch-size", "48",
    "--workers", "$Workers",
    "--sample-numbers", "5000",
    "--max-train-batches", "$MaxTrainBatches",
    "--max-val-batches", "$MaxValBatches",
    "--cache-index",
    "--cache-dir", (Join-Path $PSScriptRoot "dataset_cache"),
    "--supervision", "hard",
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
if ($LASTEXITCODE -ne 0) { throw "AffectNet+ unified student failed." }
