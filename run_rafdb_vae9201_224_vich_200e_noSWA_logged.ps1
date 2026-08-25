param(
    [string]$TargetBat = "run_rafdb_vae9201_224_vich_200e_noSWA.bat"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$targetPath = Join-Path $PSScriptRoot $TargetBat
if (-not (Test-Path $targetPath)) {
    throw "Target BAT not found: $targetPath"
}

$logDir = Join-Path $PSScriptRoot "launcher_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-dd-HH-mm-ss"
$launcherLog = Join-Path $logDir "RAFDB_vae9201_224_vich_200e_noSWA_$timestamp.log"

New-Item -ItemType File -Force -Path $launcherLog | Out-Null

"Launcher log: $launcherLog" | Tee-Object -FilePath $launcherLog -Append
"Target: $targetPath" | Tee-Object -FilePath $launcherLog -Append

& cmd /c "`"$targetPath`"" 2>&1 | Tee-Object -FilePath $launcherLog
exit $LASTEXITCODE
