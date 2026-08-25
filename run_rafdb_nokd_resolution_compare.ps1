param(
    [ValidateSet("224", "112", "both")]
    [string]$Resolution = "both",
    [int]$Epochs = 200,
    [int]$BatchSize = 64,
    [int]$Workers = 0,
    [int]$Seed = 42,
    [double]$BetaVich = 1e-4,
    [int]$SwaStart = 90,
    [double]$SwaLr = 1e-4,
    [int]$MaxTrainBatches = 0,
    [int]$MaxValBatches = 0,
    [string]$DataRoot = "",
    [switch]$NoSwa
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
$env:TORCH_HOME = Join-Path $PSScriptRoot "pretrained"
$pretrainedPath = Join-Path $env:TORCH_HOME "hub\checkpoints\mobilenet_v2-b0353104.pth"

if (-not (Test-Path $pretrainedPath)) {
    throw "MobileNetV2 ImageNet V1 checkpoint not found: $pretrainedPath"
}

if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    $candidates = @(
        (Join-Path $PSScriptRoot "data\rafdb_aligned"),
        "C:\dataset\rafdb_aligned",
        "C:\rafdb_aligned"
    )
    $DataRoot = $candidates | Where-Object {
        Test-Path (Join-Path $_ "metadata_rafdb_poster_var.csv")
    } | Select-Object -First 1
}

if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    throw "RAF-DB data could not be found. Pass -DataRoot <rafdb_aligned path>."
}

$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
$resolutions = if ($Resolution -eq "both") { @(224, 112) } else { @([int]$Resolution) }

foreach ($cropSize in $resolutions) {
    # Preserve the MobileNetV2 V1 preprocessing ratio: 256/224 = 128/112.
    $resizeSize = if ($cropSize -eq 224) { 256 } else { 128 }
    $runName = "rafdb_nokd_mbv2_lightle_vich_native_${cropSize}"

    $cmd = @(
        "train_rafdb_kd.py",
        "--disable-kd",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results",
        "--epochs", "$Epochs",
        "--batch-size", "$BatchSize",
        "--workers", "$Workers",
        "--max-train-batches", "$MaxTrainBatches",
        "--max-val-batches", "$MaxValBatches",
        "--width-mult", "1.0",
        "--lr", "3e-4",
        "--weight-decay", "1e-4",
        "--dropout", "0.5",
        "--label-smoothing", "0.2",
        "--mixup", "0.2",
        "--img-size", "$cropSize",
        "--resize-size", "$resizeSize",
        "--augment-preset", "poster_var_rafdb",
        "--rotation-degrees", "12",
        "--color-jitter", "0.2",
        "--random-erasing-p", "0.1",
        "--student-head-type", "vich",
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3",
        "--beta-vich", "$BetaVich",
        "--no-vich-sampling",
        "--seed", "$Seed"
    )

    if (-not $NoSwa) {
        $cmd += @("--swa", "--swa-start", "$SwaStart", "--swa-lr", "$SwaLr")
    }

    Write-Host ""
    Write-Host "RAF-DB teacher-free native-resolution ablation"
    Write-Host "Run: $runName"
    Write-Host "Preprocessing: Resize($resizeSize) -> Crop($cropSize)"
    Write-Host "Pretrained: $pretrainedPath"
    Write-Host "Data: $DataRoot"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd

    if ($LASTEXITCODE -ne 0) {
        throw "Run failed for crop size $cropSize with exit code $LASTEXITCODE."
    }
}
