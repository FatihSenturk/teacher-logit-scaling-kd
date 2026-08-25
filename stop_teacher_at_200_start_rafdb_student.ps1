param(
    [string]$TeacherRunDir = "results\teacher_logs\RAFDB\POSTERv2\2026-06-16-23-33-23",
    [int]$TeacherPid = 9148,
    [int]$TargetCompletedEpochs = 200,
    [int]$PollSeconds = 60,
    [ValidateSet(112, 224, 256)]
    [int]$StudentResolution = 224,
    [int]$StudentEpochs = 200,
    [int]$StudentWorkers = 0
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$runDir = Resolve-Path -Path $TeacherRunDir -ErrorAction Stop
$lastCkpt = Join-Path $runDir.Path "last.pt"
$bestCkpt = Join-Path $runDir.Path "best.pt"
$logDir = Join-Path $PSScriptRoot "pipeline_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $logDir "stop_teacher_200_start_student_$stamp.log"

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $logPath -Append
}

function Get-CheckpointEpoch {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }

    $escaped = $Path.Replace("\", "\\").Replace("'", "\'")
    $code = "import torch; ckpt=torch.load('$escaped', map_location='cpu'); print(ckpt.get('epoch', -1))"
    $value = & python -c $code 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $null
    }
    return [int]$value.Trim()
}

$targetZeroBasedEpoch = $TargetCompletedEpochs - 1
Write-Log "Watching teacher run: $($runDir.Path)"
Write-Log "Target: checkpoint epoch >= $targetZeroBasedEpoch ($TargetCompletedEpochs completed epochs)"
Write-Log "Teacher PID: $TeacherPid"
Write-Log "Student resolution: $StudentResolution, epochs: $StudentEpochs, workers: $StudentWorkers"

while ($true) {
    $epoch = Get-CheckpointEpoch -Path $lastCkpt
    if ($null -eq $epoch) {
        Write-Log "last.pt not found yet; sleeping $PollSeconds seconds."
    } else {
        Write-Log "Current last.pt epoch: $epoch"
        if ($epoch -ge $targetZeroBasedEpoch) {
            break
        }
    }
    Start-Sleep -Seconds $PollSeconds
}

Write-Log "Teacher reached target epoch. Stopping PID $TeacherPid."
$proc = Get-Process -Id $TeacherPid -ErrorAction SilentlyContinue
if ($proc) {
    Stop-Process -Id $TeacherPid -Force
    Start-Sleep -Seconds 5
    Write-Log "Teacher process stopped."
} else {
    Write-Log "Teacher process already stopped."
}

if (-not (Test-Path $bestCkpt)) {
    throw "Best teacher checkpoint not found: $bestCkpt"
}

$bestEpoch = Get-CheckpointEpoch -Path $bestCkpt
Write-Log "Using teacher best.pt from epoch $bestEpoch for student KD: $bestCkpt"

$studentScript = Join-Path $PSScriptRoot "run_rafdb_unified_student.ps1"
Write-Log "Starting RAF-DB student training."
& powershell -NoProfile -ExecutionPolicy Bypass -File $studentScript `
    -TeacherCheckpoint $bestCkpt `
    -Resolution $StudentResolution `
    -Epochs $StudentEpochs `
    -Workers $StudentWorkers

if ($LASTEXITCODE -ne 0) {
    throw "RAF-DB student training failed with exit code $LASTEXITCODE"
}

Write-Log "RAF-DB student training finished."
