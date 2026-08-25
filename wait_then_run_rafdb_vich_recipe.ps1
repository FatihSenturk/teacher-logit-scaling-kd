$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$sentinel = "checkpoints\teacher_ferplus_vich_best.pt"
$pollSeconds = 90

Write-Host "Watching for $sentinel (marks end of AffectNet+7/8 -> FERPlus VICH teacher chain)..."
while (-not (Test-Path $sentinel)) {
    Start-Sleep -Seconds $pollSeconds
}
Write-Host "Detected $sentinel at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'). Starting RAF-DB VICH (published-recipe) teacher training."

& "$PSScriptRoot\run_rafdb_teacher_vich_recipe.ps1"
if ($LASTEXITCODE -ne 0) { throw "RAF-DB VICH (published-recipe) teacher training failed." }

$searchRoot = Join-Path $PSScriptRoot "results\teacher_logs\RAFDB\POSTERv2"
$newest = Get-ChildItem -Path $searchRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($newest) {
    $bestPt = Join-Path $newest.FullName "best.pt"
    if (Test-Path $bestPt) {
        $dest = Join-Path $PSScriptRoot "checkpoints\teacher_rafdb_vich_recipe_best.pt"
        Copy-Item -Path $bestPt -Destination $dest -Force
        Write-Host "Promoted $bestPt -> $dest"
    }
}

Write-Host "RAF-DB VICH (published-recipe) teacher training complete."
