$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$logFile = "phase0_extended_ablation_console.log"

function Invoke-Grid {
    param([string]$Label, [string]$ScriptName)
    Add-Content -Path $logFile -Value "=== EXTENDED ABLATION: $Label ==="
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $ScriptName 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) { throw "$Label failed." }
}

# NOTE: RAF-DB-newrecipe, AffectNet+7, and FERPlus grids (18 runs) now run on the
# second machine (2070S, same network) instead of here -- their teachers were
# already done and needed no local GPU time on this machine. This machine (5070)
# only needs to do AffectNet+8 (its own teacher, no transfer needed) + RAF-DB
# multiseed (teacher_vich9237 already local too).
Invoke-Grid -Label "AffectNet+8cls 6-run grid" -ScriptName "run_phase0_full_ablation_affectnet8.ps1"
Invoke-Grid -Label "RAF-DB multi-seed validation (baseline+ctkd x2 seeds)" -ScriptName "run_phase0_rafdb_multiseed.ps1"

Add-Content -Path $logFile -Value "=== Extended Phase 0 ablation (this machine: 10 runs) complete ==="
