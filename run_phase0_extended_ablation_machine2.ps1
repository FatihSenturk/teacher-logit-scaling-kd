$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logFile = "phase0_extended_ablation_machine2_console.log"

function Invoke-Grid {
    param([string]$Label, [string]$ScriptName)
    Add-Content -Path $logFile -Value "=== EXTENDED ABLATION (machine 2): $Label ==="
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ScriptName 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) { throw "$Label failed." }
}

# This machine (2070S) covers the 3 grids whose teachers were already done and
# didn't need to wait on anything: RAF-DB (new recipe), AffectNet+7, FERPlus.
# Needs beforehand: teacher_rafdb_vich_recipe_best.pt, teacher_affectnetplus7_vich_best.pt,
# teacher_ferplus_vich_best.pt in checkpoints/, plus data/rafdb_aligned, data/AffectNet+,
# data/FERPlus_processed, and pretrained/ copied over from the 5070 machine.
Invoke-Grid -Label "RAF-DB (new recipe) 6-run grid" -ScriptName "run_phase0_full_ablation_rafdb_newrecipe.ps1"
Invoke-Grid -Label "AffectNet+7cls 6-run grid" -ScriptName "run_phase0_full_ablation_affectnet7.ps1"
Invoke-Grid -Label "FERPlus 6-run grid" -ScriptName "run_phase0_full_ablation_ferplus.ps1"

Add-Content -Path $logFile -Value "=== Extended Phase 0 ablation (machine 2: 18 runs) complete ==="
