$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logFile = "new_vich_teachers_console.log"

function Promote-Newest {
    param([string]$SearchRoot, [string]$OutName)
    $newest = Get-ChildItem -Path $SearchRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $bestPt = Join-Path $newest.FullName "best.pt"
    $dest = Join-Path $PSScriptRoot "checkpoints\$OutName"
    Copy-Item -Path $bestPt -Destination $dest -Force
    Add-Content -Path $logFile -Value "Promoted $bestPt -> $dest"
}

Add-Content -Path $logFile -Value "=== RESTART 2: FERPlus 8cls VICH with corrected fold split (train=[0,1], val=[2], 300 epochs, QCS-ferplus transform, matching verified reference recipe) ==="
python -u main_encoder.py --c FERPlus_8_vich_teacher_vae_ce_kld.yaml 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "FERPlus 8cls training failed." }
Promote-Newest -SearchRoot "results\teacher_logs\FER2013\POSTERv2" -OutName "teacher_ferplus_vich_best.pt"

Add-Content -Path $logFile -Value "=== New VICH teacher: RAF-DB (published recipe, no rotation/crop) ==="
python -u main_encoder.py --c RAFDB_posterv2_vich_recipe.yaml 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "RAF-DB VICH (published-recipe) teacher training failed." }
Promote-Newest -SearchRoot "results\teacher_logs\RAFDB\POSTERv2" -OutName "teacher_rafdb_vich_recipe_best.pt"

Add-Content -Path $logFile -Value "=== Recovery chain 4 complete: FERPlus (corrected split) -> RAF-DB ==="
