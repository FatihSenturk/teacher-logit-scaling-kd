$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logFile = "new_vich_teachers_console.log"

function Get-LastBestAccSince {
    param([string]$LogPath, [string]$Marker)
    $lines = Get-Content -Path $LogPath
    $startIdx = 0
    for ($i = $lines.Length - 1; $i -ge 0; $i--) {
        if ($lines[$i] -like "*$Marker*") { $startIdx = $i; break }
    }
    $best = $null
    for ($i = $startIdx; $i -lt $lines.Length; $i++) {
        if ($lines[$i] -match 'best_acc:([0-9.]+)') {
            $best = [double]$matches[1]
        }
    }
    return $best
}

function Promote-Newest {
    param([string]$SearchRoot, [string]$OutName)
    $newest = Get-ChildItem -Path $SearchRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $bestPt = Join-Path $newest.FullName "best.pt"
    $dest = Join-Path $PSScriptRoot "checkpoints\$OutName"
    Copy-Item -Path $bestPt -Destination $dest -Force
    Add-Content -Path $logFile -Value "Promoted $bestPt -> $dest"
}

Add-Content -Path $logFile -Value "=== RECOVERY: Resume AffectNetPlus 8cls VICH (7 epochs remaining) ==="
python -u main_encoder.py --c AffectNetPlus_8_vich_kld_27may_resume.yaml --resume "results/teacher_logs/AffectNetPlus/POSTERv2/2026-07-08-15-00-00/last.pt" 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "AffectNetPlus 8cls resume failed." }

$newBest = Get-LastBestAccSince -LogPath $logFile -Marker "RECOVERY: Resume AffectNetPlus"
$oldBest = 0.6355
$oldBestPt = Join-Path $PSScriptRoot "results\teacher_logs\AffectNetPlus\POSTERv2\2026-07-08-15-00-00\best.pt"
$dest8 = Join-Path $PSScriptRoot "checkpoints\teacher_affectnetplus8_vich_best.pt"

if ($null -ne $newBest -and $newBest -ge $oldBest) {
    Promote-Newest -SearchRoot "results\teacher_logs\AffectNetPlus\POSTERv2" -OutName "teacher_affectnetplus8_vich_best.pt"
    Add-Content -Path $logFile -Value "Resumed-run best ($newBest) >= historical best ($oldBest); promoted resumed run."
} else {
    Copy-Item -Path $oldBestPt -Destination $dest8 -Force
    Add-Content -Path $logFile -Value "Resumed-run best ($newBest) did not beat historical best ($oldBest); promoted original best.pt instead."
}

Add-Content -Path $logFile -Value "=== New VICH teacher: FERPlus 8cls (processed) ==="
python -u main_encoder.py --c FERPlus_8_vich_kld_200e_lr3e5_sam_processed_27may.yaml 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "FERPlus VICH teacher training failed." }
Promote-Newest -SearchRoot "results\teacher_logs\FER2013\POSTERv2" -OutName "teacher_ferplus_vich_best.pt"

Add-Content -Path $logFile -Value "=== New VICH teacher: RAF-DB (published recipe, no rotation/crop) ==="
python -u main_encoder.py --c RAFDB_posterv2_vich_recipe.yaml 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "RAF-DB VICH (published-recipe) teacher training failed." }
Promote-Newest -SearchRoot "results\teacher_logs\RAFDB\POSTERv2" -OutName "teacher_rafdb_vich_recipe_best.pt"

Add-Content -Path $logFile -Value "=== Recovery chain complete: AffectNet+8 (resumed) -> FERPlus -> RAF-DB ==="
