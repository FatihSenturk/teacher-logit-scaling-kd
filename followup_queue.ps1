param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("mean_logvar", "target_logvar", "top2_logvar", "entropy")]
    [string]$WinningSource,

    [string]$TeacherCheckpoint = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23\best.pt",
    [ValidateSet("vae", "vich", "none")]
    [string]$TeacherHeadType = "vae",
    [string]$RunTag = "vae9182",
    [int]$Epochs = 200,
    [double]$Alpha = 0.3,
    [double]$Temperature = 6.0,
    [double]$LabelSmoothing = 0.1,
    [double]$Mixup = 0.1,
    [switch]$Swa,
    [int]$SwaStart = 90,
    [double]$SwaLr = 1e-4,
    [string]$DataRoot = "data\rafdb_aligned",
    [int[]]$Seeds = @(1, 43),
    [double]$GateAlphaLo = 0.1,
    [double]$GateAlphaHi = 0.7,
    [double]$GateK = 2.0,
    [double]$GateTau = 0.0,
    [ValidateSet("batch", "running")]
    [string]$GateNorm = "batch",
    [int]$MaxRetries = 3,
    [int]$RetryDelaySeconds = 15
)

# Priority 5 follow-up (see user plan, 2026-07-17): once run_rafdb_uncertainty_
# gated_matrix.ps1 identifies a winning gate_uncertainty_source at seed=42,
# complete it to a 3-seed set (seed=1, seed=43) for a mean +/- std comparison
# against the classic-KD 3-seed baseline (89.928/89.342/... at seed 42/43,
# see 20_HAZIRAN_RAFDB_VAE9182_TEACHER_224VICH_STUDENT.md) and the single-seed
# 90.059% ceiling. Mirrors the matrix script's exact command construction for
# -WinningSource so seed is the only variable that changes.
#
# Same caveat as run_rafdb_priority1_queue.ps1: train_rafdb_kd.py has no
# --resume, so a crash restarts that seed's run from epoch 0.

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
if (($needsMuLogvar -contains $WinningSource) -and ($TeacherHeadType -eq "none")) {
    throw "gate_uncertainty_source=$WinningSource requires a VAE/VICH-headed teacher; -TeacherHeadType is 'none'."
}

function Invoke-FollowupSeed {
    param([int]$Seed)

    $runName = "RAFDB_${RunTag}_gate_${WinningSource}_seed${Seed}"
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
        "--gate-uncertainty-source", "$WinningSource",
        "--gate-norm", "$GateNorm",
        "--gate-alpha-lo", "$GateAlphaLo",
        "--gate-alpha-hi", "$GateAlphaHi",
        "--gate-k", "$GateK",
        "--gate-tau", "$GateTau"
    )
    if ($TeacherHeadType -eq "vae") { $cmd += "--teacher-vae-head" }
    elseif ($TeacherHeadType -eq "vich") { $cmd += "--teacher-vich-head" }
    if ($Swa) { $cmd += @("--swa", "--swa-start", "$SwaStart", "--swa-lr", "$SwaLr") }

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        Write-Host ""
        Write-Host "########## FOLLOWUP: $runName, attempt $attempt/$MaxRetries : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ##########"
        Write-Host "Command: python -u $($cmd -join ' ')"
        & python -u @cmd
        $exitCode = $LASTEXITCODE
        Write-Host "[$runName] Exit code: $exitCode at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

        if ($exitCode -eq 0) { return $true }
        Write-Host "[$runName] Exited non-zero. No --resume support -- next attempt restarts from epoch 0."
        Start-Sleep -Seconds $RetryDelaySeconds
    }
    return $false
}

foreach ($seed in $Seeds) {
    $ok = Invoke-FollowupSeed -Seed $seed
    if (-not $ok) {
        throw "Follow-up run for seed=$seed ($WinningSource) did not complete after $MaxRetries attempts."
    }
}

Write-Host ""
Write-Host "=== Follow-up queue completed: $WinningSource across seeds $($Seeds -join ', '). ==="
