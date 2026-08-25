param(
    [ValidateSet("224", "112", "256", "all")]
    [string]$Resolution = "all",
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
    [string]$TeacherCheckpoint = "",
    [switch]$NoSwa
)

# Pinned to --augment-preset kd (direct Resize((img_size,img_size)), no crop)
# for every resolution, instead of the original poster_var_rafdb preset
# (Resize(resize_size) -> RandomCrop/CenterCrop(img_size)). RAF-DB's aligned
# crops are already tight face crops; poster_var_rafdb's CenterCrop at val
# time cuts additional content off the edges on top of that, so comparing
# resolutions through two different crop geometries confounded the resolution
# effect with a crop-induced accuracy drop. kd preset removes that confound
# (same resize-only pipeline at every resolution) at the cost of losing the
# mild scale/translation jitter RandomCrop gave at train time.

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
        "C:\rafdb_aligned",
        "D:\27may\poster-var\data\rafdb_aligned"
    )
    $DataRoot = $candidates | Where-Object {
        Test-Path (Join-Path $_ "metadata_rafdb_poster_var.csv")
    } | Select-Object -First 1
}

if ([string]::IsNullOrWhiteSpace($DataRoot)) {
    throw "RAF-DB data could not be found. Pass -DataRoot <rafdb_aligned path>."
}

if ([string]::IsNullOrWhiteSpace($TeacherCheckpoint)) {
    $teacherCandidates = @(
        (Join-Path $PSScriptRoot "checkpoints\teacher_ce9241_best.pt"),
        "C:\Users\mfati\21mar\poster-var\logs\RAFDB\POSTERv2\2026-03-30-13-28-13\best.pt",
        "D:\27may\poster-var\checkpoints\teacher_ce9241_best.pt"
    )
    $TeacherCheckpoint = $teacherCandidates | Where-Object {
        Test-Path $_
    } | Select-Object -First 1
}

if ([string]::IsNullOrWhiteSpace($TeacherCheckpoint)) {
    throw "CE 92.41 teacher checkpoint could not be found. Pass -TeacherCheckpoint <best.pt path>."
}

$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
$resolutions = if ($Resolution -eq "all") { @(256, 224, 112) } else { @([int]$Resolution) }

foreach ($cropSize in $resolutions) {
    $runName = "rafdb_kd_ce9241_mbv2_lightle_vich_kdpreset_${cropSize}"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$TeacherCheckpoint",
        "--teacher-layer-embedding",
        "--teacher-votes-sum", "0",
        "--teacher-input-size", "224",
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
        "--alpha", "0.2",
        "--temperature", "6.0",
        "--dropout", "0.5",
        "--label-smoothing", "0.2",
        "--mixup", "0.2",
        "--img-size", "$cropSize",
        "--resize-size", "0",
        "--augment-preset", "kd",
        "--ra-mag", "7",
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
    Write-Host "RAF-DB KD native-resolution comparison (kd preset, no crop confound)"
    Write-Host "Run: $runName"
    Write-Host "Student preprocessing: direct Resize(${cropSize}x${cropSize}), RandAugment(2,7)"
    Write-Host "Teacher input: 224x224"
    Write-Host "Teacher checkpoint: $TeacherCheckpoint"
    Write-Host "Student pretrained: $pretrainedPath"
    Write-Host "Data: $DataRoot"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd

    if ($LASTEXITCODE -ne 0) {
        throw "Run failed for crop size $cropSize with exit code $LASTEXITCODE."
    }
}
