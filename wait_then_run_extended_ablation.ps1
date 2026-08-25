$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$sentinel = "checkpoints\teacher_affectnetplus8_vich_best.pt"
$pollSeconds = 90

Write-Host "Watching for $sentinel (marks AffectNet+8cls teacher training complete)..."
while (-not (Test-Path $sentinel)) {
    Start-Sleep -Seconds $pollSeconds
}
Write-Host "Detected $sentinel at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'). Starting extended Phase 0 ablation (28 runs)."

& "$PSScriptRoot\run_phase0_extended_ablation_all.ps1"
if ($LASTEXITCODE -ne 0) { throw "Extended ablation chain failed." }
Write-Host "Extended Phase 0 ablation chain complete."
