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

Add-Content -Path $logFile -Value "=== CORRECTED RECIPE: AffectNetPlus 8cls VICH from scratch (sample_numbers=6000, 300 epochs) [AffectNet+7 extend skipped per user request - existing 200e result already close to paper] ==="
python -u main_encoder.py --c AffectNetPlus_8_vich_kld_27may_v2.yaml 2>&1 | Tee-Object -FilePath $logFile -Append
if ($LASTEXITCODE -ne 0) { throw "AffectNetPlus 8cls v2 training failed." }
Promote-Newest -SearchRoot "results\teacher_logs\AffectNetPlus\POSTERv2" -OutName "teacher_affectnetplus8_vich_best.pt"

Add-Content -Path $logFile -Value "=== Recovery chain 6 complete: AffectNet+8 (corrected recipe, 300e) ==="
