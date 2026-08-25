param(
    [switch]$SmokeOnly,
    [switch]$CloudSwanLab
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$statusDir = Join-Path $PSScriptRoot "pipeline_logs"
New-Item -ItemType Directory -Path $statusDir -Force | Out-Null
$statusPath = Join-Path $statusDir "unified_pipeline_status.json"

function Write-Status([string]$Stage, [string]$State, [string]$Detail = "") {
    [ordered]@{
        updated_at = (Get-Date).ToString("o")
        stage = $Stage
        state = $State
        detail = $Detail
    } | ConvertTo-Json | Set-Content -LiteralPath $statusPath -Encoding UTF8
    Write-Host "[$State] $Stage $Detail"
}

function Get-LatestRun([string]$Dataset, [string]$ConfigName) {
    $roots = @(
        (Join-Path $PSScriptRoot "lg\logs\$Dataset\POSTERv2"),
        (Join-Path $PSScriptRoot "results\teacher_logs\$Dataset\POSTERv2")
    )
    $candidate = $roots |
        Where-Object { Test-Path $_ } |
        ForEach-Object { Get-ChildItem -LiteralPath $_ -Directory } |
        Sort-Object LastWriteTime -Descending |
        Where-Object {
            (Test-Path (Join-Path $_.FullName $ConfigName)) -and
            (Test-Path (Join-Path $_.FullName "best.pt"))
        } |
        Select-Object -First 1
    if (-not $candidate) { throw "No completed run found for $ConfigName." }
    return $candidate.FullName
}

Write-Status "RAF-DB teacher smoke" "running"
& powershell -NoProfile -ExecutionPolicy Bypass -File .\run_rafdb_teacher_vae_ce_kld.ps1 -SmokeOnly -CpuSmoke
if ($LASTEXITCODE -ne 0) { throw "RAF-DB teacher smoke failed." }

Write-Status "FERPlus teacher smoke" "running"
& powershell -NoProfile -ExecutionPolicy Bypass -File .\run_ferplus_teacher_vae_ce_kld.ps1 -SmokeOnly -CpuSmoke
if ($LASTEXITCODE -ne 0) { throw "FERPlus teacher smoke failed." }
if ($SmokeOnly) {
    Write-Status "Unified architecture smoke tests" "complete"
    return
}

Write-Status "RAF-DB VAE teacher" "running"
& powershell -NoProfile -ExecutionPolicy Bypass -File .\run_rafdb_teacher_vae_ce_kld.ps1
if ($LASTEXITCODE -ne 0) { throw "RAF-DB teacher failed." }
$rafRun = Get-LatestRun "RAFDB" "RAFDB_teacher_vae_ce_kld.yaml"
$rafTeacher = Join-Path $rafRun "best.pt"
python -u tools\evaluate_teacher.py --config configs\RAFDB_teacher_vae_ce_kld.yaml --checkpoint $rafTeacher
if ($LASTEXITCODE -ne 0) { throw "RAF-DB teacher evaluation failed." }

Write-Status "FERPlus CE+KL teacher" "running"
& powershell -NoProfile -ExecutionPolicy Bypass -File .\run_ferplus_teacher_vae_ce_kld.ps1
if ($LASTEXITCODE -ne 0) { throw "FERPlus teacher failed." }
$ferRun = Get-LatestRun "FER2013" "FERPlus_8_teacher_vae_ce_kld.yaml"
$ferTeacher = Join-Path $ferRun "best.pt"
python -u tools\evaluate_teacher.py `
    --config configs\FERPlus_8_teacher_vae_ce_kld.yaml `
    --checkpoint $ferTeacher `
    --expected-train-samples 28259 `
    --expected-val-samples 3153
if ($LASTEXITCODE -ne 0) { throw "FERPlus teacher evaluation failed." }

Write-Status "12-run student resolution matrix" "running"
$matrixArgs = @(
    "-RafTeacherCheckpoint", $rafTeacher,
    "-FerTeacherCheckpoint", $ferTeacher,
    "-Epochs", "200"
)
if ($CloudSwanLab) { $matrixArgs += "-CloudSwanLab" }
& powershell -NoProfile -ExecutionPolicy Bypass -File .\run_unified_student_matrix.ps1 @matrixArgs
if ($LASTEXITCODE -ne 0) { throw "Student matrix failed." }

Write-Status "Unified result table" "running"
python -u tools\build_unified_matrix_results.py `
    --raf-teacher-metrics (Join-Path $rafRun "metrics_best.json") `
    --fer-teacher-metrics (Join-Path $ferRun "metrics_best.json") `
    --output UNIFIED_RESOLUTION_MATRIX_RESULTS.md
if ($LASTEXITCODE -ne 0) { throw "Unified result table failed." }

Write-Status "Unified teacher-student pipeline" "complete"
