param(
    [string]$TeacherCheckpoint = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt",
    [ValidateSet("vae", "vich", "none")]
    [string]$TeacherHeadType = "vae",
    [string]$RunTag = "vae9182",
    [int]$Epochs = 200,
    [int]$Seed = 42,
    [double]$Alpha = 0.3,
    [double]$Temperature = 6.0,
    [double]$LabelSmoothing = 0.1,
    [double]$Mixup = 0.1,
    [switch]$Swa,
    [int]$SwaStart = 90,
    [double]$SwaLr = 1e-4,
    [string]$DataRoot = "data\rafdb_aligned",
    [string[]]$Sources = @("mean_logvar", "target_logvar", "top2_logvar", "entropy"),
    [double]$GateAlphaLo = 0.1,
    [double]$GateAlphaHi = 0.7,
    [double]$GateK = 2.0,
    [double]$GateTau = 0.0,
    [ValidateSet("batch", "running")]
    [string]$GateNorm = "batch"
)

# Uncertainty-gated KD matrix (Component A / "Gate"), teacher-parametric.
#
# gate_uncertainty_source={mean_logvar,target_logvar,top2_logvar} all read
# teacher (mu, logvar) (kd_uncertainty.py::resolve_uncertainty) -- they
# require --teacher-vae-head or --teacher-vich-head. Only "entropy" works off
# a plain-logits teacher (kd_uncertainty.py:57-65). This script drops the
# mu/logvar-dependent sources automatically when -TeacherHeadType is "none",
# instead of letting them hard-crash mid-run.
#
# Base recipe defaults to the VAE9182+224px+VICH-student line documented in
# 20_HAZIRAN_RAFDB_VAE9182_TEACHER_224VICH_STUDENT.md (best known non-gated
# result at 224px: 90.059% single-seed, 89.928/89.342 on two more seeds) --
# alpha=0.3, T=6, label_smoothing=0.1, mixup=0.1, class-weighted CE,
# cosine_warm_restarts, kd augment preset, no VICH sampling on the student.
# Swap -TeacherCheckpoint/-TeacherHeadType to run the same matrix against a
# different teacher (e.g. ce9241, -TeacherHeadType none -> entropy-only).

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path $TeacherCheckpoint)) {
    throw "Teacher checkpoint not found: $TeacherCheckpoint"
}
$metadata = Join-Path $DataRoot "metadata_rafdb_poster_var.csv"
if (-not (Test-Path $metadata)) {
    throw "RAF-DB metadata not found at $metadata (pass -DataRoot)."
}

$needsMuLogvar = @("mean_logvar", "target_logvar", "top2_logvar")
$effectiveSources = @()
foreach ($src in $Sources) {
    if (($needsMuLogvar -contains $src) -and ($TeacherHeadType -eq "none")) {
        Write-Host "Skipping gate_uncertainty_source=$src : requires teacher (mu, logvar), but -TeacherHeadType is 'none' (plain-logits teacher $TeacherCheckpoint)."
        continue
    }
    $effectiveSources += $src
}
if ($effectiveSources.Count -eq 0) {
    throw "No usable gate_uncertainty_source left after filtering for TeacherHeadType=$TeacherHeadType. Pass -Sources entropy explicitly, or use a VAE/VICH-headed teacher."
}
Write-Host "Matrix arms to run: $($effectiveSources -join ', ')"

foreach ($source in $effectiveSources) {
    $runName = "RAFDB_${RunTag}_gate_${source}_seed${Seed}"

    $cmd = @(
        "train_rafdb_kd.py",
        "--teacher-ckpt", "$TeacherCheckpoint",
        "--teacher-layer-embedding",
        "--teacher-input-size", "224",
        "--aligned-dir", "$DataRoot",
        "--metadata", "$metadata",
        "--name", "$runName",
        "--save-root", "results\unified_students",
        "--epochs", "$Epochs",
        "--batch-size", "64",
        "--workers", "0",
        "--img-size", "224",
        "--resize-size", "0",
        "--augment-preset", "kd",
        "--student-head-type", "vich",
        "--student-layer-embedding",
        "--student-lightweight-layer-embedding",
        "--student-layer-embedding-layers", "3",
        "--no-vich-sampling",
        "--alpha", "$Alpha",
        "--temperature", "$Temperature",
        "--label-smoothing", "$LabelSmoothing",
        "--mixup", "$Mixup",
        "--use-amp",
        "--class-weight-mode", "effective_number",
        "--class-weight-beta", "0.9999",
        "--scheduler-name", "cosine_warm_restarts",
        "--min-lr", "1e-6",
        "--gamma", "0.98",
        "--scheduler-t0", "10",
        "--scheduler-t-mult", "2",
        "--seed", "$Seed",
        "--gate-enable",
        "--gate-uncertainty-source", "$source",
        "--gate-norm", "$GateNorm",
        "--gate-alpha-lo", "$GateAlphaLo",
        "--gate-alpha-hi", "$GateAlphaHi",
        "--gate-k", "$GateK",
        "--gate-tau", "$GateTau"
    )

    if ($TeacherHeadType -eq "vae") { $cmd += "--teacher-vae-head" }
    elseif ($TeacherHeadType -eq "vich") { $cmd += "--teacher-vich-head" }

    if ($Swa) { $cmd += @("--swa", "--swa-start", "$SwaStart", "--swa-lr", "$SwaLr") }

    Write-Host ""
    Write-Host "########## GATE ARM: $source ($runName) : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
    Write-Host "Command: python -u $($cmd -join ' ')"
    & python -u @cmd

    if ($LASTEXITCODE -ne 0) {
        throw "Run failed for gate_uncertainty_source=$source (name=$runName) with exit code $LASTEXITCODE."
    }
}

Write-Host ""
Write-Host "=== Uncertainty-gated matrix completed: $($effectiveSources.Count) arm(s). ==="
