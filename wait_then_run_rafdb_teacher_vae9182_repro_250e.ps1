param(
    [int]$WaitPid = 0,
    [int]$PollSeconds = 60,
    [string]$TargetBat = "run_rafdb_teacher_vae9182_repro_250e.bat"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$targetPath = Join-Path $PSScriptRoot $TargetBat
if (-not (Test-Path $targetPath)) {
    throw "Target BAT not found: $targetPath"
}

if ($WaitPid -le 0) {
    $candidates = @(Get-Process python -ErrorAction SilentlyContinue | Sort-Object StartTime -Descending)
    if ($candidates.Count -eq 0) {
        Write-Host "No active python process found. Starting target immediately."
    } else {
        $selected = $candidates[0]
        $WaitPid = $selected.Id
        Write-Host "No WaitPid provided. Waiting for newest python process:"
        Write-Host "  PID: $($selected.Id)"
        Write-Host "  Name: $($selected.ProcessName)"
        Write-Host "  StartTime: $($selected.StartTime)"
    }
} else {
    Write-Host "Waiting for provided PID: $WaitPid"
}

if ($WaitPid -gt 0) {
    while (Get-Process -Id $WaitPid -ErrorAction SilentlyContinue) {
        $now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Write-Host "[$now] PID $WaitPid is still running. Checking again in $PollSeconds seconds..."
        Start-Sleep -Seconds $PollSeconds
    }
    Write-Host "PID $WaitPid finished."
}

Write-Host "Starting target: $targetPath"
& cmd /c "`"$targetPath`""
exit $LASTEXITCODE
