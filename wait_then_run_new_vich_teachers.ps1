$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logFile = "kd_logs_rafdb\phase0_ablation_remaining_console.log"
$marker = "All Phase 0 full ablation runs completed successfully"
$pollSeconds = 90

Write-Host "Watching $logFile for RAF-DB Phase 0 ablation grid completion (polling every $pollSeconds s)..."
while ($true) {
    if (Test-Path $logFile) {
        $tail = Get-Content -Path $logFile -Tail 10 -ErrorAction SilentlyContinue
        if ($tail -match [regex]::Escape($marker)) {
            Write-Host "Completion marker detected at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')."
            break
        }
    }
    Start-Sleep -Seconds $pollSeconds
}

Write-Host "Launching new VICH teacher training chain (AffectNet+7 -> AffectNet+8 -> FERPlus)..."
& "$PSScriptRoot\run_phase0_new_vich_teachers.ps1"
if ($LASTEXITCODE -ne 0) { throw "New VICH teacher training chain failed." }
Write-Host "New VICH teacher training chain completed."
