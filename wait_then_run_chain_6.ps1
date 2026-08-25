$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$sentinel = "checkpoints\teacher_rafdb_vich_recipe_best.pt"
$pollSeconds = 90

Write-Host "Watching for $sentinel (marks end of FERPlus -> RAF-DB chain)..."
while (-not (Test-Path $sentinel)) {
    Start-Sleep -Seconds $pollSeconds
}
Write-Host "Detected $sentinel at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'). Starting AffectNet+7 extend -> AffectNet+8 corrected-recipe chain."

& "$PSScriptRoot\run_recovery_chain_6.ps1"
if ($LASTEXITCODE -ne 0) { throw "Chain 6 failed." }
Write-Host "Chain 6 complete."
